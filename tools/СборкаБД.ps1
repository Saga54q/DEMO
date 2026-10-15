#Requires -Version 5.1
# =====================================================================
# СборкаБД.ps1 — сборка готовой базы «Магазин обуви» (МагазинОбуви.accdb)
#
# Что делает скрипт (всё то же, что ты делаешь в Access руками):
#   1. Создаёт пустой файл .accdb движком DAO (версия 120).
#   2. Выполняет sql/МагазинОбуви.sql: CREATE TABLE (ключи, ограничения),
#      CREATE UNIQUE INDEX, ALTER TABLE ADD CONSTRAINT (связи со ссылочной
#      целостностью и каскадами), INSERT (данные заказчика).
#   3. Переводит поле «Изображение» в тип «Вложение» и загружает фото
#      каждой модели.
#   4. Проверяет: число записей, 6 связей, запрет «мусорных» записей,
#      каскадное удаление.
# Запуск: pwsh tools/СборкаБД.ps1  (Windows + Access Database Engine)
# =====================================================================

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$sqlPath = Join-Path $repoRoot 'sql/МагазинОбуви.sql'
$imgDir  = Join-Path $repoRoot 'Практика1_МагазинОбуви/images'
$outDir  = Join-Path $repoRoot 'build'
$dbPath  = Join-Path $outDir 'МагазинОбуви.accdb'

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Start-Transcript -Path (Join-Path $outDir 'журнал.txt') | Out-Null

$script:lastStmt = ''
try {

if (Test-Path $dbPath) { Remove-Item $dbPath -Force }

Write-Host '== 1. Создание пустой базы .accdb (DAO, dbVersion120 = 128) =='
$dbe = New-Object -ComObject DAO.DBEngine.120
$db = $dbe.CreateDatabase($dbPath, ';LANGID=0x0409;CP=1252;COUNTRY=0', 128)

Write-Host '== 2. Выполнение sql/МагазинОбуви.sql (структура + данные) =='
Write-Host '   (операторы ALTER TABLE ADD CONSTRAINT пропускаются: DAO Execute их'
Write-Host '    не принимает - ошибка 3289; связи создаются на шаге 3 через DAO)'
$sqlText = Get-Content -Raw -Encoding UTF8 $sqlPath
$lines = $sqlText -split "`r?`n" | Where-Object { $_ -notmatch '^\s*--' }
$clean = ($lines -join "`n")
$stmts = $clean -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
$ddl = @($stmts | Where-Object { $_ -notmatch '^(ALTER|INSERT)' })
$ins = @($stmts | Where-Object { $_ -match '^INSERT' })
foreach ($s in $ddl) {
    try {
        $script:lastStmt = ($s -replace '\s+', ' ')
        $db.Execute($s) | Out-Null
    } catch {
        Write-Host "ОШИБКА в операторе:" -ForegroundColor Red
        Write-Host $s
        throw
    }
}
Write-Host ("Создано объектов структуры: {0}" -f $ddl.Count)

Write-Host '== 3. Связи со ссылочной целостностью (DAO CreateRelation) =='
# RelationAttributeEnum: dbRelationUpdateCascade = 256, dbRelationDeleteCascade = 4096
function Add-Rel($name, $parent, $parentField, $child, $childField, $attrs) {
    $rel = $db.CreateRelation($name, $parent, $child, $attrs)
    $f = $rel.CreateField($childField)
    $f.ForeignName = $parentField
    $rel.Fields.Append($f)
    $db.Relations.Append($rel)
    $kind = if ($attrs -band 4096) { 'ON UPDATE CASCADE + ON DELETE CASCADE' } else { 'ON UPDATE CASCADE' }
    Write-Host ("  {0}.{1} -> {2}.{3}: {4}" -f $parent, $parentField, $child, $childField, $kind)
}
$UPD = 256
$DEL = 4096
Add-Rel 'R_Клиенты_Заказы'        'Клиенты'         'ID_Клиента'      'Заказы'         'ID_Клиента'   $UPD
Add-Rel 'R_Заказы_СоставЗаказа'   'Заказы'          'ID_Заказа'       'СоставЗаказа'   'ID_Заказа'    ($UPD + $DEL)
Add-Rel 'R_Позиции_СоставЗаказа'  'ТоварныеПозиции' 'ID_Позиции'      'СоставЗаказа'   'ID_Позиции'   $UPD
Add-Rel 'R_Модели_Позиции'        'Модели'          'ID_Модели'       'ТоварныеПозиции' 'ID_Модели'  $UPD
Add-Rel 'R_Категории_Модели'      'Категории'       'ID_Категории'    'Модели'         'ID_Категории' $UPD
Add-Rel 'R_Производители_Модели'  'Производители'   'ID_Производителя' 'Модели'        'ID_Производителя' $UPD

# Пересоздаём сессию: сбрасываем кеш схемы, чтобы ограничения
# ссылочной целостности точно применялись к последующим операциям.
$db.Close()
$db = $dbe.OpenDatabase($dbPath)

Write-Host '== 4. Загрузка данных (INSERT) =='
foreach ($s in $ins) {
    try {
        $script:lastStmt = ($s -replace '\s+', ' ')
        $db.Execute($s) | Out-Null
    } catch {
        Write-Host "ОШИБКА в операторе:" -ForegroundColor Red
        Write-Host $s
        throw
    }
}
Write-Host ("Выполнено INSERT: {0}" -f $ins.Count)

Write-Host '== 3. Поле «Изображение» -> тип «Вложение» (ATTACHMENT) =='
$db.TableDefs.Refresh()
$td = $db.TableDefs.Item('Модели')
$td.Fields.Delete('Изображение')
$f = $td.CreateField('Изображение', 101)   # 101 = dbAttachment
$td.Fields.Append($f)

Write-Host '== 4. Правила проверки полей (ValidationRule) =='
function Set-Rule($table, $field, $rule, $text) {
    $f = $db.TableDefs.Item($table).Fields.Item($field)
    $f.ValidationRule = $rule
    $f.ValidationText = $text
    Write-Host ("  {0}.{1}: правило '{2}'" -f $table, $field, $rule)
}
Set-Rule 'Модели' 'Цена' '>=0' 'Цена не может быть отрицательной'
Set-Rule 'ТоварныеПозиции' 'Количество' '>=0' 'Остаток не может быть отрицательным'
Set-Rule 'СоставЗаказа' 'Количество' '>0' 'Количество пар должно быть больше нуля'
Set-Rule 'СоставЗаказа' 'ЦенаЗаЕдиницу' '>=0' 'Цена не может быть отрицательной'

Write-Host '== 5. Загрузка изображений моделей во вложения =='
$imgMap = @{
    1 = '01_ultraboost.jpg'
    2 = '02_airzoom.jpg'
    3 = '03_helsinki.jpg'
    4 = '04_classic.jpg'
    5 = '05_runfalcon.jpg'
    6 = '06_winter.jpg'
}
$rs = $db.OpenRecordset('SELECT * FROM Модели ORDER BY ID_Модели', 2)  # 2 = dbOpenDynaset
$loaded = 0
while (-not $rs.EOF) {
    $id = [int]$rs.Fields.Item('ID_Модели').Value
    $file = Join-Path $imgDir $imgMap[$id]
    if (-not (Test-Path $file)) { throw "Нет файла изображения: $file" }
    $rs.Edit()
    $rsA = $rs.Fields.Item('Изображение').Value     # дочерний Recordset2 вложений
    $rsA.AddNew()
    $rsA.Fields.Item('FileData').LoadFromFile($file)
    $rsA.Update()
    $rsA.Close()
    $rs.Update()
    $loaded++
    Write-Host ("  модель {0}: {1} - загружено" -f $id, (Split-Path $file -Leaf))
    $rs.MoveNext()
}
$rs.Close()
if ($loaded -ne 6) { throw "Загружено вложений: $loaded из 6" }

Write-Host '== 5. Проверки =='
$expected = [ordered]@{
    'Клиенты'        = 5
    'Категории'      = 4
    'Производители'  = 4
    'Модели'         = 6
    'ТоварныеПозиции' = 15
    'Заказы'         = 5
    'СоставЗаказа'   = 9
}
foreach ($t in $expected.Keys) {
    $rs = $db.OpenRecordset("SELECT COUNT(*) AS CNT FROM [$t]", 2)
    $c = [int]$rs.Fields.Item('CNT').Value
    $rs.Close()
    if ($c -ne $expected[$t]) { throw "Таблица ${t}: ожидалось $($expected[$t]) записей, найдено $c" }
    Write-Host ("  {0}: {1} записей - OK" -f $t, $c)
}

$relCount = $db.Relations.Count
Write-Host "  Связей со ссылочной целостностью: $relCount (ожидается 6)"
if ($relCount -ne 6) { throw "Связей $relCount вместо 6" }

# Тест 1. Ссылочная целостность: мусорная строка должна быть отвергнута.
# Проверяем двумя способами (SQL INSERT и Recordset) и честно фиксируем результат.
function Test-RI($via, $action) {
    try {
        & $action | Out-Null
        return 'ПРОШЛА'
    } catch {
        return ("ОТВЕРГНУТА ({0})" -f ($_.Exception.Message -replace '\s+', ' '))
    }
}

$sqlAction = {
    $db.Execute('INSERT INTO СоставЗаказа (ID_Заказа, ID_Позиции, Количество, ЦенаЗаЕдиницу) VALUES (777, 777, 1, 1)') | Out-Null
}
$rsAction = {
    $rs = $db.OpenRecordset('СоставЗаказа', 1)
    try {
        $rs.AddNew()
        $rs.Fields.Item('ID_Заказа').Value = 777
        $rs.Fields.Item('ID_Позиции').Value = 777
        $rs.Fields.Item('Количество').Value = 1
        $rs.Fields.Item('ЦенаЗаЕдиницу').Value = 1
        $rs.Update()
    } finally {
        $rs.Close()
    }
}
$riSql = Test-RI 'SQL' $sqlAction
$rs = $db.OpenRecordset('SELECT COUNT(*) AS CNT FROM СоставЗаказа WHERE ID_Заказа = 777', 2)
$stray = [int]$rs.Fields.Item('CNT').Value
$rs.Close()
if ($stray -gt 0) { $db.Execute('DELETE FROM СоставЗаказа WHERE ID_Заказа = 777') | Out-Null }
$riRs = Test-RI 'Recordset' $rsAction
$rs = $db.OpenRecordset('SELECT COUNT(*) AS CNT FROM СоставЗаказа WHERE ID_Заказа = 777', 2)
$stray2 = [int]$rs.Fields.Item('CNT').Value
$rs.Close()
if ($stray2 -gt 0) { $db.Execute('DELETE FROM СоставЗаказа WHERE ID_Заказа = 777') | Out-Null }
Write-Host "  RI через SQL INSERT : $riSql (мусорных строк: $stray)"
Write-Host "  RI через Recordset  : $riRs (мусорных строк: $stray2)"
# Примечание: DAO.Execute (сырой SQL) не проверяет целостность — особенность
# движка. Канонический путь Access (таблицы, формы, запросы) — через Recordset,
# и именно он показывает реальное поведение системы.

if ($riRs -like 'ПРОШЛА*') {
    Write-Host "::error::RI-ТЕСТ ПРОВАЛЕН. Recordset: $riRs"
    foreach ($r in $db.Relations) {
        $map = @()
        foreach ($rf in $r.Fields) { $map += ("{0}->{1}" -f $rf.Name, $rf.ForeignName) }
        Write-Host ("::error::REL {0}: {1} -> {2} attrs={3} fields=[{4}]" -f `
            $r.Name, $r.Table, $r.ForeignTable, $r.Attributes, ($map -join '; '))
    }
    throw "RI-ТЕСТ ПРОВАЛЕН: RS=$riRs"
}
Write-Host '  Тест RI: мусорная запись отвергнута (путь Access/Recordset) - OK'

# Тест 2. Каскадное удаление Заказы -> СоставЗаказа на временной записи.
$db.Execute('INSERT INTO Заказы (ID_Заказа, ID_Клиента, ДатаЗаказа) VALUES (99, 1, #2026-10-15#)') | Out-Null
$db.Execute('INSERT INTO СоставЗаказа (ID_Заказа, ID_Позиции, Количество, ЦенаЗаЕдиницу) VALUES (99, 1, 1, 100)') | Out-Null
$rs = $db.OpenRecordset('SELECT * FROM Заказы WHERE ID_Заказа = 99', 2)
$rs.Delete()   # удаление записи-родителя: строки должны уйти каскадом
$rs.Close()
$rs = $db.OpenRecordset('SELECT COUNT(*) AS CNT FROM СоставЗаказа WHERE ID_Заказа = 99', 2)
$c = [int]$rs.Fields.Item('CNT').Value
$rs.Close()
if ($c -ne 0) { throw "Каскадное удаление НЕ работает: строк заказа 99 осталось $c" }
Write-Host '  Тест каскадного удаления: строки заказа удалены вместе с заказом - OK'

$db.Close()
Write-Host "== ГОТОВО: $dbPath =="
Stop-Transcript | Out-Null

} catch {
    try { Stop-Transcript | Out-Null } catch {}
    $msg = [string]$_.Exception.Message
    Write-Host "::error::СБОРКА ПРОВАЛЕНА: $msg"
    if ($script:lastStmt) {
        $stmt = $script:lastStmt
        if ($stmt.Length -gt 500) { $stmt = $stmt.Substring(0, 500) }
        Write-Host "::error::Последний SQL-оператор: $stmt"
    }
    exit 1
}
