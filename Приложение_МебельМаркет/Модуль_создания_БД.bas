Attribute VB_Name = "modBuildFurnitureDB"
Option Compare Database
Option Explicit

Private Const REL_DELETE_CASCADE As Long = 4096

Public Sub BuildFurnitureDatabase()
    On Error GoTo BuildError

    Dim db As DAO.Database
    Set db = CurrentDb

    ' Справочники и учётные записи.
    EnsureTable db, "Role", _
        "CREATE TABLE [Role] ([RoleID] COUNTER CONSTRAINT [PK_Role] PRIMARY KEY, " & _
        "[RoleName] TEXT(80) NOT NULL)"
    EnsureTable db, "AppUser", _
        "CREATE TABLE [AppUser] ([UserID] COUNTER CONSTRAINT [PK_AppUser] PRIMARY KEY, " & _
        "[RoleID] LONG NOT NULL, [FIO] TEXT(150) NOT NULL, [Login] TEXT(100) NOT NULL, " & _
        "[Password] TEXT(100) NOT NULL)"
    EnsureTable db, "Category", _
        "CREATE TABLE [Category] ([CategoryID] COUNTER CONSTRAINT [PK_Category] PRIMARY KEY, " & _
        "[CategoryName] TEXT(100) NOT NULL)"
    EnsureTable db, "Manufacturer", _
        "CREATE TABLE [Manufacturer] ([ManufacturerID] COUNTER " & _
        "CONSTRAINT [PK_Manufacturer] PRIMARY KEY, [ManufacturerName] TEXT(120) NOT NULL)"
    EnsureTable db, "Supplier", _
        "CREATE TABLE [Supplier] ([SupplierID] COUNTER CONSTRAINT [PK_Supplier] PRIMARY KEY, " & _
        "[SupplierName] TEXT(120) NOT NULL)"
    EnsureTable db, "Unit", _
        "CREATE TABLE [Unit] ([UnitID] COUNTER CONSTRAINT [PK_Unit] PRIMARY KEY, " & _
        "[UnitName] TEXT(30) NOT NULL)"
    EnsureTable db, "Warehouse", _
        "CREATE TABLE [Warehouse] ([WarehouseID] COUNTER CONSTRAINT [PK_Warehouse] PRIMARY KEY, " & _
        "[WarehouseName] TEXT(120) NOT NULL, [Address] TEXT(255))"

    ' Товары и складские остатки. Остаток хранится отдельно для каждой пары товар–склад.
    EnsureTable db, "Product", _
        "CREATE TABLE [Product] ([ProductID] COUNTER CONSTRAINT [PK_Product] PRIMARY KEY, " & _
        "[Article] TEXT(40) NOT NULL, [ProductName] TEXT(180) NOT NULL, " & _
        "[CategoryID] LONG NOT NULL, [Description] MEMO, [ManufacturerID] LONG NOT NULL, " & _
        "[SupplierID] LONG NOT NULL, [Price] CURRENCY NOT NULL, [UnitID] LONG NOT NULL, " & _
        "[Discount] DOUBLE NOT NULL, [ImagePath] TEXT(255))"
    EnsureTable db, "Inventory", _
        "CREATE TABLE [Inventory] ([ProductID] LONG NOT NULL, [WarehouseID] LONG NOT NULL, " & _
        "[Quantity] LONG NOT NULL, CONSTRAINT [PK_Inventory] " & _
        "PRIMARY KEY ([ProductID], [WarehouseID]))"

    ' Клиенты, заказы и строки заказа.
    EnsureTable db, "Customer", _
        "CREATE TABLE [Customer] ([CustomerID] COUNTER CONSTRAINT [PK_Customer] PRIMARY KEY, " & _
        "[FIO] TEXT(150) NOT NULL, [Phone] TEXT(40), [Address] TEXT(255))"
    EnsureTable db, "OrderStatus", _
        "CREATE TABLE [OrderStatus] ([StatusID] COUNTER CONSTRAINT [PK_OrderStatus] PRIMARY KEY, " & _
        "[StatusName] TEXT(60) NOT NULL)"
    EnsureTable db, "ShopOrder", _
        "CREATE TABLE [ShopOrder] ([OrderID] COUNTER CONSTRAINT [PK_ShopOrder] PRIMARY KEY, " & _
        "[OrderDate] DATETIME NOT NULL, [DeliveryDate] DATETIME NOT NULL, " & _
        "[CustomerID] LONG NOT NULL, [WarehouseID] LONG NOT NULL, " & _
        "[DeliveryAddress] TEXT(255) NOT NULL, [OrderCode] TEXT(40), [StatusID] LONG NOT NULL)"
    EnsureTable db, "OrderItem", _
        "CREATE TABLE [OrderItem] ([OrderID] LONG NOT NULL, [ProductID] LONG NOT NULL, " & _
        "[Quantity] LONG NOT NULL, [UnitPrice] CURRENCY NOT NULL, " & _
        "CONSTRAINT [PK_OrderItem] PRIMARY KEY ([OrderID], [ProductID]))"

    ' Уникальность логина, артикула и названий справочников.
    EnsureIndex db, "Role", "UX_RoleName", "CREATE UNIQUE INDEX [UX_RoleName] ON [Role] ([RoleName])"
    EnsureIndex db, "AppUser", "UX_AppUserLogin", "CREATE UNIQUE INDEX [UX_AppUserLogin] ON [AppUser] ([Login])"
    EnsureIndex db, "Category", "UX_CategoryName", "CREATE UNIQUE INDEX [UX_CategoryName] ON [Category] ([CategoryName])"
    EnsureIndex db, "Manufacturer", "UX_ManufacturerName", "CREATE UNIQUE INDEX [UX_ManufacturerName] ON [Manufacturer] ([ManufacturerName])"
    EnsureIndex db, "Supplier", "UX_SupplierName", "CREATE UNIQUE INDEX [UX_SupplierName] ON [Supplier] ([SupplierName])"
    EnsureIndex db, "Unit", "UX_UnitName", "CREATE UNIQUE INDEX [UX_UnitName] ON [Unit] ([UnitName])"
    EnsureIndex db, "Warehouse", "UX_WarehouseName", "CREATE UNIQUE INDEX [UX_WarehouseName] ON [Warehouse] ([WarehouseName])"
    EnsureIndex db, "Product", "UX_ProductArticle", "CREATE UNIQUE INDEX [UX_ProductArticle] ON [Product] ([Article])"
    EnsureIndex db, "OrderStatus", "UX_OrderStatusName", "CREATE UNIQUE INDEX [UX_OrderStatusName] ON [OrderStatus] ([StatusName])"

    ' Ограничения значений на уровне полей Access.
    SetFieldRule db, "Product", "Price", ">=0", "Цена не может быть отрицательной."
    SetFieldRule db, "Product", "Discount", "Between 0 And 100", "Скидка должна быть от 0 до 100%."
    SetFieldRule db, "Inventory", "Quantity", ">=0", "Остаток не может быть отрицательным."
    SetFieldRule db, "OrderItem", "Quantity", ">0", "Количество в заказе должно быть больше нуля."
    SetFieldRule db, "OrderItem", "UnitPrice", ">=0", "Цена позиции не может быть отрицательной."

    ' Связи с обеспечением целостности данных.
    EnsureRelation db, "FK_AppUser_Role", "Role", "RoleID", "AppUser", "RoleID", 0
    EnsureRelation db, "FK_Product_Category", "Category", "CategoryID", "Product", "CategoryID", 0
    EnsureRelation db, "FK_Product_Manufacturer", "Manufacturer", "ManufacturerID", "Product", "ManufacturerID", 0
    EnsureRelation db, "FK_Product_Supplier", "Supplier", "SupplierID", "Product", "SupplierID", 0
    EnsureRelation db, "FK_Product_Unit", "Unit", "UnitID", "Product", "UnitID", 0
    EnsureRelation db, "FK_Inventory_Product", "Product", "ProductID", "Inventory", "ProductID", REL_DELETE_CASCADE
    EnsureRelation db, "FK_Inventory_Warehouse", "Warehouse", "WarehouseID", "Inventory", "WarehouseID", 0
    EnsureRelation db, "FK_Order_Customer", "Customer", "CustomerID", "ShopOrder", "CustomerID", 0
    EnsureRelation db, "FK_Order_Warehouse", "Warehouse", "WarehouseID", "ShopOrder", "WarehouseID", 0
    EnsureRelation db, "FK_Order_Status", "OrderStatus", "StatusID", "ShopOrder", "StatusID", 0
    EnsureRelation db, "FK_OrderItem_Order", "ShopOrder", "OrderID", "OrderItem", "OrderID", REL_DELETE_CASCADE
    ' Каскад удаления здесь не включён: товар из существующего заказа удалить нельзя.
    EnsureRelation db, "FK_OrderItem_Product", "Product", "ProductID", "OrderItem", "ProductID", 0

    MsgBox "Структура базы МебельМаркет создана или уже существует.", vbInformation
    Exit Sub

BuildError:
    MsgBox "Ошибка при создании базы: " & Err.Number & vbCrLf & Err.Description, vbCritical
End Sub

Private Sub EnsureTable(ByVal db As DAO.Database, ByVal tableName As String, ByVal createSql As String)
    If Not TableExists(db, tableName) Then
        db.Execute createSql, dbFailOnError
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

Private Sub EnsureIndex(ByVal db As DAO.Database, ByVal tableName As String, _
                        ByVal indexName As String, ByVal createSql As String)
    Dim indexDef As DAO.Index
    For Each indexDef In db.TableDefs(tableName).Indexes
        If StrComp(indexDef.Name, indexName, vbTextCompare) = 0 Then Exit Sub
    Next indexDef
    db.Execute createSql, dbFailOnError
End Sub

Private Sub EnsureRelation(ByVal db As DAO.Database, ByVal relationName As String, _
                           ByVal parentTable As String, ByVal parentField As String, _
                           ByVal childTable As String, ByVal childField As String, _
                           ByVal relationAttributes As Long)
    Dim relation As DAO.Relation
    Dim relationField As DAO.Field
    For Each relation In db.Relations
        If StrComp(relation.Name, relationName, vbTextCompare) = 0 Then Exit Sub
    Next relation

    Set relation = db.CreateRelation(relationName, parentTable, childTable, relationAttributes)
    Set relationField = relation.CreateField(parentField)
    relationField.ForeignName = childField
    relation.Fields.Append relationField
    db.Relations.Append relation
End Sub

Private Sub SetFieldRule(ByVal db As DAO.Database, ByVal tableName As String, _
                         ByVal fieldName As String, ByVal rule As String, ByVal message As String)
    With db.TableDefs(tableName).Fields(fieldName)
        .ValidationRule = rule
        .ValidationText = message
    End With
End Sub
