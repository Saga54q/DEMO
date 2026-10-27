Attribute VB_Name = "modСозданиеБД"
Option Compare Database
Option Explicit

Private Const CASCADE_DELETE As Long = 4096

Public Sub BuildFurnitureDatabase()
    On Error GoTo BuildError
    Dim db As DAO.Database
    Set db = CurrentDb

    ' Минимальная нормализованная схема для ролей, каталога, нескольких складов и заказов.
    EnsureTable db, "Роли", _
        "CREATE TABLE [Роли] ([КодРоли] COUNTER CONSTRAINT [ПервичныйКлюч_Роли] PRIMARY KEY, [Название] TEXT(80) NOT NULL)"
    EnsureTable db, "Пользователи", _
        "CREATE TABLE [Пользователи] ([КодПользователя] COUNTER CONSTRAINT [ПервичныйКлюч_Пользователи] PRIMARY KEY, " & _
        "[КодРоли] LONG NOT NULL, [ФИО] TEXT(150) NOT NULL, [Логин] TEXT(100) NOT NULL, [Пароль] TEXT(100) NOT NULL, " & _
        "[КодПокупателя] LONG)"
    EnsureTable db, "Категории", _
        "CREATE TABLE [Категории] ([КодКатегории] COUNTER CONSTRAINT [ПервичныйКлюч_Категории] PRIMARY KEY, [Название] TEXT(100) NOT NULL)"
    EnsureTable db, "Производители", _
        "CREATE TABLE [Производители] ([КодПроизводителя] COUNTER CONSTRAINT [ПервичныйКлюч_Производители] PRIMARY KEY, [Название] TEXT(120) NOT NULL)"
    EnsureTable db, "Поставщики", _
        "CREATE TABLE [Поставщики] ([КодПоставщика] COUNTER CONSTRAINT [ПервичныйКлюч_Поставщики] PRIMARY KEY, [Название] TEXT(120) NOT NULL)"
    EnsureTable db, "Склады", _
        "CREATE TABLE [Склады] ([КодСклада] COUNTER CONSTRAINT [ПервичныйКлюч_Склады] PRIMARY KEY, [Название] TEXT(120) NOT NULL, [Адрес] TEXT(255))"
    EnsureTable db, "Товары", _
        "CREATE TABLE [Товары] ([КодТовара] COUNTER CONSTRAINT [ПервичныйКлюч_Товары] PRIMARY KEY, " & _
        "[Артикул] TEXT(40) NOT NULL, [Наименование] TEXT(180) NOT NULL, [КодКатегории] LONG NOT NULL, " & _
        "[Описание] MEMO, [КодПроизводителя] LONG NOT NULL, [КодПоставщика] LONG NOT NULL, " & _
        "[Цена] CURRENCY NOT NULL, [Единица] TEXT(30) NOT NULL, [Скидка] DOUBLE NOT NULL, [Фото] TEXT(255))"
    EnsureTable db, "Остатки", _
        "CREATE TABLE [Остатки] ([КодТовара] LONG NOT NULL, [КодСклада] LONG NOT NULL, " & _
        "[Количество] LONG NOT NULL, CONSTRAINT [ПервичныйКлюч_Остатки] PRIMARY KEY ([КодТовара], [КодСклада]))"
    EnsureTable db, "Покупатели", _
        "CREATE TABLE [Покупатели] ([КодПокупателя] COUNTER CONSTRAINT [ПервичныйКлюч_Покупатели] PRIMARY KEY, " & _
        "[ФИО] TEXT(150) NOT NULL, [Телефон] TEXT(40), [Адрес] TEXT(255))"
    EnsureTable db, "Заказы", _
        "CREATE TABLE [Заказы] ([КодЗаказа] COUNTER CONSTRAINT [ПервичныйКлюч_Заказы] PRIMARY KEY, " & _
        "[ДатаЗаказа] DATETIME NOT NULL, [ДатаДоставки] DATETIME NOT NULL, [КодПокупателя] LONG NOT NULL, " & _
        "[КодСклада] LONG NOT NULL, [АдресДоставки] TEXT(255) NOT NULL, [КодПолучения] TEXT(40), [Статус] TEXT(60) NOT NULL)"
    EnsureTable db, "СоставЗаказа", _
        "CREATE TABLE [СоставЗаказа] ([КодЗаказа] LONG NOT NULL, [КодТовара] LONG NOT NULL, " & _
        "[Количество] LONG NOT NULL, [ЦенаНаМоментЗаказа] CURRENCY NOT NULL, " & _
        "CONSTRAINT [ПервичныйКлюч_СоставЗаказа] PRIMARY KEY ([КодЗаказа], [КодТовара]))"

    ' Уникальные значения справочников, логинов и артикулов.
    EnsureIndex db, "Роли", "УникальныйИндекс_Роли_Название", "CREATE UNIQUE INDEX [УникальныйИндекс_Роли_Название] ON [Роли] ([Название])"
    EnsureIndex db, "Пользователи", "УникальныйИндекс_Пользователи_Логин", "CREATE UNIQUE INDEX [УникальныйИндекс_Пользователи_Логин] ON [Пользователи] ([Логин])"
    EnsureIndex db, "Категории", "УникальныйИндекс_Категории_Название", "CREATE UNIQUE INDEX [УникальныйИндекс_Категории_Название] ON [Категории] ([Название])"
    EnsureIndex db, "Производители", "УникальныйИндекс_Производители_Название", "CREATE UNIQUE INDEX [УникальныйИндекс_Производители_Название] ON [Производители] ([Название])"
    EnsureIndex db, "Поставщики", "УникальныйИндекс_Поставщики_Название", "CREATE UNIQUE INDEX [УникальныйИндекс_Поставщики_Название] ON [Поставщики] ([Название])"
    EnsureIndex db, "Склады", "УникальныйИндекс_Склады_Название", "CREATE UNIQUE INDEX [УникальныйИндекс_Склады_Название] ON [Склады] ([Название])"
    EnsureIndex db, "Товары", "УникальныйИндекс_Товары_Артикул", "CREATE UNIQUE INDEX [УникальныйИндекс_Товары_Артикул] ON [Товары] ([Артикул])"

    ' Допустимые значения.
    SetFieldRule db, "Товары", "Цена", ">=0", "Цена не может быть отрицательной."
    SetFieldRule db, "Товары", "Скидка", "Between 0 And 100", "Скидка должна быть от 0 до 100%."
    SetFieldRule db, "Остатки", "Количество", ">=0", "Остаток не может быть отрицательным."
    SetFieldRule db, "СоставЗаказа", "Количество", ">0", "Количество должно быть больше нуля."

    ' Связи; нельзя удалить товар, который включён в заказ.
    EnsureRelation db, "Связь_Пользователи_Роли", "Роли", "КодРоли", "Пользователи", "КодРоли", 0
    EnsureRelation db, "Связь_Пользователи_Покупатели", "Покупатели", "КодПокупателя", "Пользователи", "КодПокупателя", 0
    EnsureRelation db, "Связь_Товары_Категории", "Категории", "КодКатегории", "Товары", "КодКатегории", 0
    EnsureRelation db, "Связь_Товары_Производители", "Производители", "КодПроизводителя", "Товары", "КодПроизводителя", 0
    EnsureRelation db, "Связь_Товары_Поставщики", "Поставщики", "КодПоставщика", "Товары", "КодПоставщика", 0
    EnsureRelation db, "Связь_Остатки_Товары", "Товары", "КодТовара", "Остатки", "КодТовара", CASCADE_DELETE
    EnsureRelation db, "Связь_Остатки_Склады", "Склады", "КодСклада", "Остатки", "КодСклада", 0
    EnsureRelation db, "Связь_Заказы_Покупатели", "Покупатели", "КодПокупателя", "Заказы", "КодПокупателя", 0
    EnsureRelation db, "Связь_Заказы_Склады", "Склады", "КодСклада", "Заказы", "КодСклада", 0
    EnsureRelation db, "Связь_Состав_Заказы", "Заказы", "КодЗаказа", "СоставЗаказа", "КодЗаказа", CASCADE_DELETE
    EnsureRelation db, "Связь_Состав_Товары", "Товары", "КодТовара", "СоставЗаказа", "КодТовара", 0

    ' Сохранённые запросы Access.
    EnsureQuery db, "Запрос_ОстаткиПоТоварам", _
        "SELECT [КодТовара], Sum([Количество]) AS [ВсегоНаСкладах] FROM [Остатки] GROUP BY [КодТовара];"
    EnsureQuery db, "Запрос_КаталогМебели", _
        "SELECT [Т].[КодТовара], [Т].[Артикул], [Т].[Наименование], [Т].[КодКатегории], " & _
        "[К].[Название] AS [Категория], [Т].[Описание], [Т].[КодПроизводителя], " & _
        "[ПР].[Название] AS [Производитель], [Т].[КодПоставщика], [ПС].[Название] AS [Поставщик], " & _
        "[Т].[Цена], [Т].[Единица], [Т].[Скидка], [Т].[Фото], " & _
        "Nz([О].[ВсегоНаСкладах],0) AS [ВсегоНаСкладах], " & _
        "[Т].[Цена]*(100-[Т].[Скидка])/100 AS [ЦенаСоСкидкой] " & _
        "FROM (((([Товары] AS [Т] INNER JOIN [Категории] AS [К] ON [Т].[КодКатегории]=[К].[КодКатегории]) " & _
        "INNER JOIN [Производители] AS [ПР] ON [Т].[КодПроизводителя]=[ПР].[КодПроизводителя]) " & _
        "INNER JOIN [Поставщики] AS [ПС] ON [Т].[КодПоставщика]=[ПС].[КодПоставщика]) " & _
        "LEFT JOIN [Запрос_ОстаткиПоТоварам] AS [О] ON [Т].[КодТовара]=[О].[КодТовара]);"
    EnsureQuery db, "Запрос_ОстаткиПоСкладам", _
        "SELECT [Т].[КодТовара], [Т].[Артикул], [Т].[Наименование], [С].[КодСклада], " & _
        "[С].[Название] AS [Склад], [О].[Количество] " & _
        "FROM ([Товары] AS [Т] INNER JOIN [Остатки] AS [О] ON [Т].[КодТовара]=[О].[КодТовара]) " & _
        "INNER JOIN [Склады] AS [С] ON [О].[КодСклада]=[С].[КодСклада];"
    EnsureQuery db, "Запрос_Заказы", _
        "SELECT [З].[КодЗаказа], [З].[ДатаЗаказа], [З].[ДатаДоставки], [З].[КодПокупателя], " & _
        "[П].[ФИО], [З].[КодСклада], [С].[Название] AS [Склад], [З].[АдресДоставки], " & _
        "[З].[КодПолучения], [З].[Статус] " & _
        "FROM ([Заказы] AS [З] INNER JOIN [Покупатели] AS [П] ON [З].[КодПокупателя]=[П].[КодПокупателя]) " & _
        "INNER JOIN [Склады] AS [С] ON [З].[КодСклада]=[С].[КодСклада];"

    MsgBox "Таблицы, связи и запросы созданы или уже существуют.", vbInformation
    Exit Sub

BuildError:
    MsgBox "Ошибка " & Err.Number & ": " & Err.Description, vbCritical
End Sub

Private Sub EnsureTable(ByVal db As DAO.Database, ByVal tableName As String, ByVal sql As String)
    If Not TableExists(db, tableName) Then
        db.Execute sql, dbFailOnError
        db.TableDefs.Refresh
    End If
End Sub

Private Function TableExists(ByVal db As DAO.Database, ByVal tableName As String) As Boolean
    Dim tableDef As DAO.TableDef
    For Each tableDef In db.TableDefs
        If StrComp(tableDef.Name, tableName, vbTextCompare) = 0 Then
            TableExists = True
            Exit Function
        End If
    Next tableDef
End Function

Private Sub EnsureIndex(ByVal db As DAO.Database, ByVal tableName As String, ByVal indexName As String, ByVal sql As String)
    Dim indexDef As DAO.Index
    For Each indexDef In db.TableDefs(tableName).Indexes
        If StrComp(indexDef.Name, indexName, vbTextCompare) = 0 Then Exit Sub
    Next indexDef
    db.Execute sql, dbFailOnError
End Sub

Private Sub EnsureRelation(ByVal db As DAO.Database, ByVal relationName As String, _
    ByVal parentTable As String, ByVal parentField As String, _
    ByVal childTable As String, ByVal childField As String, ByVal attributes As Long)
    Dim relation As DAO.Relation
    Dim relationField As DAO.Field
    For Each relation In db.Relations
        If StrComp(relation.Name, relationName, vbTextCompare) = 0 Then Exit Sub
    Next relation
    Set relation = db.CreateRelation(relationName, parentTable, childTable, attributes)
    Set relationField = relation.CreateField(parentField)
    relationField.ForeignName = childField
    relation.Fields.Append relationField
    db.Relations.Append relation
End Sub

Private Sub EnsureQuery(ByVal db As DAO.Database, ByVal queryName As String, ByVal sql As String)
    Dim queryDef As DAO.QueryDef
    For Each queryDef In db.QueryDefs
        If StrComp(queryDef.Name, queryName, vbTextCompare) = 0 Then Exit Sub
    Next queryDef
    db.CreateQueryDef queryName, sql
End Sub

Private Sub SetFieldRule(ByVal db As DAO.Database, ByVal tableName As String, _
    ByVal fieldName As String, ByVal rule As String, ByVal message As String)
    With db.TableDefs(tableName).Fields(fieldName)
        .ValidationRule = rule
        .ValidationText = message
    End With
End Sub
