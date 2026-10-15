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
$sqlText = Get-Content -Raw -Encoding UTF8 $sqlPath
$lines = $sqlText -split "`r?`n" | Where-Object { $_ -notmatch '^\s*--' }
$clean = ($lines -join "`n")
$stmts = $clean -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
foreach ($s in $stmts) {
    try {
        $script:lastStmt = ($s -replace '\s+', ' ')
        $db.Execute($s) | Out-Null
    } catch {
        Write-Host "ОШИБКА в операторе:" -ForegroundColor Red
        Write-Host $s
        throw
    }
}
Write-Host ("Выполнено операторов: {0}" -f $stmts.Count)

Write-Host '== 3. Поле «Изображение» -> тип «Вложение» (ATTACHMENT) =='
$db.TableDefs.Refresh()
$td = $db.TableDefs.Item('Модели')
$td.Fields.Delete('Изображение')
$f = $td.CreateField('Изображение', 101)   # 101 = dbAttachment
$td.Fields.Append($f)

Write-Host '== 4. Загрузка изображений моделей во вложения =='
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
$riBlocked = $false
try {
    $db.Execute('INSERT INTO СоставЗаказа (ID_Заказа, ID_Позиции, Количество, ЦенаЗаЕдиницу) VALUES (99, 99, 1, 1)') | Out-Null
} catch {
    $riBlocked = $true
}
if (-not $riBlocked) {
    $db.Execute('DELETE FROM СоставЗаказа WHERE ID_Заказа = 99') | Out-Null
    throw 'RI-ТЕСТ ПРОВАЛЕН: запись с несуществующими ключами прошла'
}
Write-Host '  Тест RI: мусорная запись отвергнута - OK'

# Тест 2. Каскадное удаление Заказы -> СоставЗаказа на временной записи.
$db.Execute('INSERT INTO Заказы (ID_Заказа, ID_Клиента, ДатаЗаказа) VALUES (99, 1, #2026-10-15#)') | Out-Null
$db.Execute('INSERT INTO СоставЗаказа (ID_Заказа, ID_Позиции, Количество, ЦенаЗаЕдиницу) VALUES (99, 1, 1, 100)') | Out-Null
$db.Execute('DELETE FROM Заказы WHERE ID_Заказа = 99') | Out-Null
$rs = $db.OpenRecordset('SELECT COUNT(*) AS CNT FROM СоставЗаказа WHERE ID_Заказа = 99', 2)
$c = [int]$rs.Fields.Item('CNT').Value
$rs.Close()
if ($c -ne 0) { throw 'Каскадное удаление НЕ работает: строки заказа 99 остались' }
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
