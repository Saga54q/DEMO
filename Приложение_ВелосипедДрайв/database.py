"""Простая работа с SQLite. Все запросы к БД находятся в этом файле."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "velodrive.db"


def connect():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize():
    with connect() as connection:
        connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        if connection.execute("SELECT COUNT(*) FROM Product").fetchone()[0] == 0:
            from import_data import load_excel_data
            load_excel_data(connection)


def authenticate(login, password):
    with connect() as connection:
        return connection.execute("""
            SELECT u.user_id, u.fio, r.name AS role
            FROM User u JOIN Role r ON r.role_id=u.role_id
            WHERE u.login=? AND u.password=?
        """, (login.strip(), password.strip())).fetchone()


def products(search="", discount_range="Все диапазоны", sort="Без сортировки"):
    sql = """
        SELECT p.*, t.name AS type_name, m.name AS manufacturer,
               s.name AS supplier, p.cost*(100-p.discount)/100 AS final_price
        FROM Product p JOIN ProductType t ON t.type_id=p.type_id
        JOIN Manufacturer m ON m.manufacturer_id=p.manufacturer_id
        JOIN Supplier s ON s.supplier_id=p.supplier_id WHERE 1=1
    """
    args = []
    if search.strip():
        pattern = f"%{search.strip()}%"
        sql += " AND (p.article LIKE ? OR p.name LIKE ? OR p.unit LIKE ? OR " \
               "COALESCE(p.description,'') LIKE ? OR t.name LIKE ? OR " \
               "m.name LIKE ? OR s.name LIKE ?)"
        args.extend([pattern] * 7)
    limits = {
        "0–11,99%": (0, 11.99),
        "12–18,99%": (12, 18.99),
        "19% и более": (19, 100),
    }
    if discount_range in limits:
        low, high = limits[discount_range]
        sql += " AND p.discount BETWEEN ? AND ?"
        args.extend([low, high])
    ordering = {
        "Цена ↑": "p.cost ASC", "Цена ↓": "p.cost DESC",
        "Остаток ↑": "p.stock ASC", "Остаток ↓": "p.stock DESC",
        "Скидка ↑": "p.discount ASC", "Скидка ↓": "p.discount DESC",
    }
    sql += " ORDER BY " + ordering.get(sort, "p.product_id")
    with connect() as connection:
        return connection.execute(sql, args).fetchall()


def product(product_id):
    with connect() as connection:
        return connection.execute("SELECT * FROM Product WHERE product_id=?", (product_id,)).fetchone()


def choices(table, id_field, label_field):
    allowed = {
        "ProductType": ("type_id", "name"), "Supplier": ("supplier_id", "name"),
        "Manufacturer": ("manufacturer_id", "name"), "Customer": ("customer_id", "fio"),
        "PickupPoint": ("point_id", "postal_code || ' · ' || city || street || ' ' || number"),
        "OrderStatus": ("status_id", "name"),
    }
    if (id_field, label_field) != allowed.get(table):
        raise ValueError("Недопустимый список справочника")
    with connect() as connection:
        return connection.execute(
            f"SELECT {id_field} AS id, {label_field} AS label FROM {table} ORDER BY 2").fetchall()


def save_product(values, product_id=None):
    fields = ("article", "name", "unit", "cost", "supplier_id", "manufacturer_id",
              "type_id", "discount", "stock", "description", "image")
    data = [values[key] for key in fields]
    with connect() as connection:
        if product_id is None:
            cur = connection.execute(
                "INSERT INTO Product(article,name,unit,cost,supplier_id,manufacturer_id,"
                "type_id,discount,stock,description,image) VALUES(?,?,?,?,?,?,?,?,?,?,?)", data)
            return cur.lastrowid
        connection.execute(
            "UPDATE Product SET article=?,name=?,unit=?,cost=?,supplier_id=?,manufacturer_id=?,"
            "type_id=?,discount=?,stock=?,description=?,image=? WHERE product_id=?",
            data + [product_id])
        return product_id


def delete_product(product_id):
    with connect() as connection:
        connection.execute("DELETE FROM Product WHERE product_id=?", (product_id,))


def orders():
    with connect() as connection:
        return connection.execute("""
            SELECT o.*, c.fio, s.name AS status,
                   (p.postal_code || ' ' || p.city || p.street || ' ' || p.number) AS pickup,
                   (SELECT COUNT(*) FROM OrderItem i WHERE i.order_id=o.order_id) AS item_count
            FROM ShopOrder o JOIN Customer c ON c.customer_id=o.customer_id
            JOIN OrderStatus s ON s.status_id=o.status_id
            JOIN PickupPoint p ON p.point_id=o.point_id
            ORDER BY o.order_id
        """).fetchall()


def order(order_id):
    with connect() as connection:
        return connection.execute("SELECT * FROM ShopOrder WHERE order_id=?", (order_id,)).fetchone()


def save_order(values, order_id=None):
    fields = ("order_date", "delivery_date", "point_id", "customer_id", "code", "status_id")
    data = [values[key] for key in fields]
    with connect() as connection:
        if order_id is None:
            return connection.execute(
                "INSERT INTO ShopOrder(order_date,delivery_date,point_id,customer_id,code,status_id) "
                "VALUES(?,?,?,?,?,?)", data).lastrowid
        connection.execute(
            "UPDATE ShopOrder SET order_date=?,delivery_date=?,point_id=?,customer_id=?,"
            "code=?,status_id=? WHERE order_id=?", data + [order_id])
        return order_id


def delete_order(order_id):
    with connect() as connection:
        connection.execute("DELETE FROM ShopOrder WHERE order_id=?", (order_id,))
