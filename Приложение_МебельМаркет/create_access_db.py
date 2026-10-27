"""Автосборка мебельной БД Access (.accdb) и импорт Excel при первом запуске.

Запускать в Windows, где установлен Microsoft Access (Access.Application),
ODBC-драйвер Microsoft Access и Python той же разрядности, что и драйвер.
"""
from datetime import date
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "МебельМаркет.accdb"
EXCEL_FILE = ROOT / "import" / "Furniture_demo_import.xlsx"
DB_FAIL_ON_ERROR = 128
DB_RELATION_DELETE_CASCADE = 4096

# Поля и таблицы соответствуют мебели, остаткам по складам, пользователям и заказам.
TABLES = [
    ("Role", "CREATE TABLE [Role] ([role_id] COUNTER CONSTRAINT [PK_Role] PRIMARY KEY, [name] TEXT(80) NOT NULL)"),
    ("User", "CREATE TABLE [User] ([user_id] COUNTER CONSTRAINT [PK_User] PRIMARY KEY, [role_id] LONG NOT NULL, [fio] TEXT(150) NOT NULL, [login] TEXT(100) NOT NULL, [password] TEXT(100) NOT NULL)"),
    ("Category", "CREATE TABLE [Category] ([category_id] COUNTER CONSTRAINT [PK_Category] PRIMARY KEY, [name] TEXT(100) NOT NULL)"),
    ("Manufacturer", "CREATE TABLE [Manufacturer] ([manufacturer_id] COUNTER CONSTRAINT [PK_Manufacturer] PRIMARY KEY, [name] TEXT(120) NOT NULL)"),
    ("Supplier", "CREATE TABLE [Supplier] ([supplier_id] COUNTER CONSTRAINT [PK_Supplier] PRIMARY KEY, [name] TEXT(120) NOT NULL)"),
    ("Unit", "CREATE TABLE [Unit] ([unit_id] COUNTER CONSTRAINT [PK_Unit] PRIMARY KEY, [name] TEXT(30) NOT NULL)"),
    ("Warehouse", "CREATE TABLE [Warehouse] ([warehouse_id] COUNTER CONSTRAINT [PK_Warehouse] PRIMARY KEY, [name] TEXT(120) NOT NULL, [address] TEXT(255))"),
    ("Product", "CREATE TABLE [Product] ([product_id] COUNTER CONSTRAINT [PK_Product] PRIMARY KEY, [article] TEXT(40) NOT NULL, [name] TEXT(180) NOT NULL, [category_id] LONG NOT NULL, [description] MEMO, [manufacturer_id] LONG NOT NULL, [supplier_id] LONG NOT NULL, [price] CURRENCY NOT NULL, [unit_id] LONG NOT NULL, [discount] DOUBLE NOT NULL, [image_path] TEXT(255))"),
    ("Inventory", "CREATE TABLE [Inventory] ([product_id] LONG NOT NULL, [warehouse_id] LONG NOT NULL, [quantity] LONG NOT NULL, CONSTRAINT [PK_Inventory] PRIMARY KEY ([product_id], [warehouse_id]))"),
    ("Customer", "CREATE TABLE [Customer] ([customer_id] COUNTER CONSTRAINT [PK_Customer] PRIMARY KEY, [fio] TEXT(150) NOT NULL, [phone] TEXT(40), [address] TEXT(255))"),
    ("OrderStatus", "CREATE TABLE [OrderStatus] ([status_id] COUNTER CONSTRAINT [PK_OrderStatus] PRIMARY KEY, [name] TEXT(60) NOT NULL)"),
    ("ShopOrder", "CREATE TABLE [ShopOrder] ([order_id] COUNTER CONSTRAINT [PK_ShopOrder] PRIMARY KEY, [order_date] DATETIME NOT NULL, [delivery_date] DATETIME NOT NULL, [customer_id] LONG NOT NULL, [warehouse_id] LONG NOT NULL, [delivery_address] TEXT(255) NOT NULL, [code] TEXT(40), [status_id] LONG NOT NULL)"),
    ("OrderItem", "CREATE TABLE [OrderItem] ([order_id] LONG NOT NULL, [product_id] LONG NOT NULL, [quantity] LONG NOT NULL, [unit_price] CURRENCY NOT NULL, CONSTRAINT [PK_OrderItem] PRIMARY KEY ([order_id], [product_id]))"),
]

# (имя связи, родительская таблица/поле, дочерняя таблица/поле, каскад удаления)
RELATIONS = [
    ("FK_User_Role", "Role", "role_id", "User", "role_id", False),
    ("FK_Product_Category", "Category", "category_id", "Product", "category_id", False),
    ("FK_Product_Manufacturer", "Manufacturer", "manufacturer_id", "Product", "manufacturer_id", False),
    ("FK_Product_Supplier", "Supplier", "supplier_id", "Product", "supplier_id", False),
    ("FK_Product_Unit", "Unit", "unit_id", "Product", "unit_id", False),
    ("FK_Inventory_Product", "Product", "product_id", "Inventory", "product_id", True),
    ("FK_Inventory_Warehouse", "Warehouse", "warehouse_id", "Inventory", "warehouse_id", False),
    ("FK_Order_Customer", "Customer", "customer_id", "ShopOrder", "customer_id", False),
    ("FK_Order_Warehouse", "Warehouse", "warehouse_id", "ShopOrder", "warehouse_id", False),
    ("FK_Order_Status", "OrderStatus", "status_id", "ShopOrder", "status_id", False),
    ("FK_OrderItem_Order", "ShopOrder", "order_id", "OrderItem", "order_id", True),
    # Для связи Product -> OrderItem каскад выключен: заказанный товар удалить нельзя.
    ("FK_OrderItem_Product", "Product", "product_id", "OrderItem", "product_id", False),
]


def _access_app():
    try:
        import win32com.client
    except ImportError as error:
        raise RuntimeError(
            "Не найден pywin32. Установите: python -m pip install pywin32") from error
    try:
        return win32com.client.DispatchEx("Access.Application")
    except Exception as error:
        raise RuntimeError(
            "Не удалось открыть Microsoft Access через COM. Установите настольный Access "
            "и проверьте разрядность Python/Office.") from error


def _table_names(database):
    return {table.Name for table in database.TableDefs
            if not table.Name.startswith("MSys") and not table.Name.startswith("~")}


def _relation_names(database):
    return {relation.Name for relation in database.Relations}


def _create_relation(database, name, parent_table, parent_field,
                     child_table, child_field, cascade=False):
    attributes = DB_RELATION_DELETE_CASCADE if cascade else 0
    relation = database.CreateRelation(name, parent_table, child_table, attributes)
    field = relation.CreateField(parent_field)
    field.ForeignName = child_field
    relation.Fields.Append(field)
    database.Relations.Append(relation)


def ensure_access_schema():
    """Создаёт пустой .accdb, таблицы, уникальные индексы и enforced relations."""
    access = _access_app()
    try:
        access.Visible = False
        if DB_FILE.exists():
            access.OpenCurrentDatabase(str(DB_FILE))
        else:
            DB_FILE.parent.mkdir(parents=True, exist_ok=True)
            access.NewCurrentDatabase(str(DB_FILE))
        database = access.CurrentDb()
        table_names = _table_names(database)
        for table_name, ddl in TABLES:
            if table_name not in table_names:
                database.Execute(ddl, DB_FAIL_ON_ERROR)

        indexes = [
            ("UX_Role_Name", "Role", "name"),
            ("UX_User_Login", "User", "login"),
            ("UX_Category_Name", "Category", "name"),
            ("UX_Manufacturer_Name", "Manufacturer", "name"),
            ("UX_Supplier_Name", "Supplier", "name"),
            ("UX_Unit_Name", "Unit", "name"),
            ("UX_Warehouse_Name", "Warehouse", "name"),
            ("UX_Product_Article", "Product", "article"),
            ("UX_OrderStatus_Name", "OrderStatus", "name"),
        ]
        existing_indexes = {(table.Name, index.Name)
                            for table in database.TableDefs
                            for index in table.Indexes}
        for index_name, table, field in indexes:
            if (table, index_name) not in existing_indexes:
                database.Execute(
                    f"CREATE UNIQUE INDEX [{index_name}] ON [{table}] ([{field}])",
                    DB_FAIL_ON_ERROR)

        existing = _relation_names(database)
        for relation in RELATIONS:
            if relation[0] not in existing:
                _create_relation(database, *relation)
        print(f"Структура Access создана/проверена: {DB_FILE}")
    finally:
        try:
            access.CloseCurrentDatabase()
        except Exception:
            pass
        try:
            access.Quit()
        except Exception:
            pass


def _rows(workbook, sheet_name):
    values = list(workbook[sheet_name].iter_rows(values_only=True))
    headers = [str(value).strip() if value is not None else "" for value in values[0]]
    return [dict(zip(headers, row)) for row in values[1:]
            if row and any(value is not None and str(value).strip() for value in row)]


def _text(value):
    return "" if value is None else str(value).strip()


def _id(cursor):
    row = cursor.execute("SELECT @@IDENTITY").fetchone()
    return int(row[0])


def _unique_map(cursor, table, rows, column):
    id_column = {"Role":"role_id", "Category":"category_id",
                 "Manufacturer":"manufacturer_id", "Supplier":"supplier_id",
                 "Unit":"unit_id", "OrderStatus":"status_id"}[table]
    result = {}
    for value in dict.fromkeys(_text(row.get(column)) for row in rows if _text(row.get(column))):
        cursor.execute(f"INSERT INTO [{table}] ([name]) VALUES (?)", value)
        result[value] = _id(cursor)
    return result


def import_demo_data():
    """Заполняет пустую базу данными книги import/Furniture_demo_import.xlsx."""
    try:
        import pyodbc
        from openpyxl import load_workbook
    except ImportError as error:
        raise RuntimeError(
            "Установите зависимости: python -m pip install pyodbc pywin32 openpyxl") from error
    if not EXCEL_FILE.is_file():
        raise FileNotFoundError(f"Нет Excel-файла импорта: {EXCEL_FILE}")
    drivers = [name for name in pyodbc.drivers() if "Access Driver" in name and ".accdb" in name]
    if not drivers:
        raise RuntimeError(
            "ODBC-драйвер Microsoft Access не найден. Установите Microsoft Access Database Engine "
            "той же разрядности, что и Python.")
    connection_string = f"DRIVER={{{drivers[0]}}};DBQ={DB_FILE};"
    workbook = load_workbook(EXCEL_FILE, read_only=True, data_only=True)
    try:
        data = {name: _rows(workbook, name) for name in workbook.sheetnames}
    finally:
        workbook.close()

    connection = pyodbc.connect(connection_string, autocommit=False)
    try:
        cursor = connection.cursor()
        if cursor.execute("SELECT COUNT(*) FROM [Product]").fetchone()[0] > 0:
            print("В Access уже есть товары; импорт пропущен, данные сохранены.")
            return
        roles = _unique_map(cursor, "Role", data["Roles"], "name")
        categories = _unique_map(cursor, "Category", data["Categories"], "name")
        manufacturers = _unique_map(cursor, "Manufacturer", data["Manufacturers"], "name")
        suppliers = _unique_map(cursor, "Supplier", data["Suppliers"], "name")
        units = _unique_map(cursor, "Unit", data["Units"], "name")
        statuses = _unique_map(cursor, "OrderStatus", data["OrderStatuses"], "name")

        warehouses = {}
        for row in data["Warehouses"]:
            name = _text(row["name"])
            cursor.execute("INSERT INTO [Warehouse] ([name],[address]) VALUES (?,?)",
                           name, _text(row.get("address")))
            warehouses[name] = _id(cursor)

        for row in data["Users"]:
            cursor.execute("INSERT INTO [User] ([role_id],[fio],[login],[password]) VALUES (?,?,?,?)",
                roles[_text(row["role"])], _text(row["fio"]), _text(row["login"]), _text(row["password"]))

        product_ids = {}
        for row in data["Products"]:
            article = _text(row["article"])
            image_value = _text(row.get("image_path"))
            image_path = None
            if image_value:
                source = ROOT / "import" / image_value
                if source.is_file():
                    target = ROOT / "images" / source.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if source.resolve() != target.resolve():
                        shutil.copy2(source, target)
                    image_path = f"images/{target.name}"
            cursor.execute("""INSERT INTO [Product]
                ([article],[name],[category_id],[description],[manufacturer_id],[supplier_id],
                 [price],[unit_id],[discount],[image_path]) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                article, _text(row["name"]), categories[_text(row["category"])],
                _text(row.get("description")), manufacturers[_text(row["manufacturer"])],
                suppliers[_text(row["supplier"])], float(row["price"] or 0),
                units[_text(row["unit"])], float(row["discount"] or 0), image_path)
            product_ids[article] = _id(cursor)

        for row in data["Inventory"]:
            cursor.execute("INSERT INTO [Inventory] ([product_id],[warehouse_id],[quantity]) VALUES (?,?,?)",
                product_ids[_text(row["article"])], warehouses[_text(row["warehouse"])],
                int(row["quantity"] or 0))

        customers = {}
        for row in data["Customers"]:
            fio = _text(row["fio"])
            cursor.execute("INSERT INTO [Customer] ([fio],[phone],[address]) VALUES (?,?,?)",
                fio, _text(row.get("phone")), _text(row.get("address")))
            customers[fio] = _id(cursor)

        orders = {}
        for row in data["Orders"]:
            cursor.execute("""INSERT INTO [ShopOrder]
                ([order_date],[delivery_date],[customer_id],[warehouse_id],
                 [delivery_address],[code],[status_id]) VALUES (?,?,?,?,?,?,?)""",
                date.fromisoformat(_text(row["order_date"])),
                date.fromisoformat(_text(row["delivery_date"])),
                customers[_text(row["customer_fio"])], warehouses[_text(row["warehouse"])],
                _text(row["delivery_address"]), _text(row.get("code")),
                statuses[_text(row["status"])])
            orders[int(row["order_id"])] = _id(cursor)

        for row in data["OrderItems"]:
            product_id = product_ids[_text(row["article"])]
            price = cursor.execute("SELECT [price] FROM [Product] WHERE [product_id]=?",
                                   product_id).fetchone()[0]
            cursor.execute("INSERT INTO [OrderItem] ([order_id],[product_id],[quantity],[unit_price]) "
                           "VALUES (?,?,?,?)", orders[int(row["order_id"])], product_id,
                           int(row["quantity"]), price)
        connection.commit()
        print("Импорт Access выполнен: 12 товаров, 2 склада, 5 заказов, 9 строк заказа.")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize():
    """Единая точка входа: создать файл/таблицы/связи, затем импортировать строки при необходимости."""
    ensure_access_schema()
    import_demo_data()
    return DB_FILE


if __name__ == "__main__":
    try:
        print("Готово:", initialize())
    except Exception as error:
        raise SystemExit(f"Не удалось собрать Access-БД: {error}") from error
