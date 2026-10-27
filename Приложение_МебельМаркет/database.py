"""Все запросы SQLite и операции с данными мебельного магазина."""
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "mebelmarket.db"


def connect():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize():
    with connect() as connection:
        connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        if connection.execute("SELECT COUNT(*) FROM Product").fetchone()[0] == 0:
            from import_data import load_data
            load_data(connection)


def authenticate(login, password):
    with connect() as connection:
        return connection.execute("""
            SELECT u.user_id, u.fio, r.name AS role
            FROM User AS u JOIN Role AS r ON r.role_id=u.role_id
            WHERE u.login=? AND u.password=?
        """, (login.strip(), password.strip())).fetchone()


def products(search="", category="Все категории", discount_filter="Все скидки", sort="По умолчанию"):
    sql = """
        SELECT p.product_id, p.article, p.name, p.description, p.price, p.discount,
               p.image_path, c.name AS category, m.name AS manufacturer,
               s.name AS supplier, u.name AS unit,
               COALESCE(SUM(i.quantity), 0) AS stock,
               GROUP_CONCAT(w.name || ': ' || i.quantity, ' | ') AS stock_by_warehouse,
               p.price * (100 - p.discount) / 100.0 AS final_price
        FROM Product p
        JOIN Category c ON c.category_id=p.category_id
        JOIN Manufacturer m ON m.manufacturer_id=p.manufacturer_id
        JOIN Supplier s ON s.supplier_id=p.supplier_id
        JOIN Unit u ON u.unit_id=p.unit_id
        LEFT JOIN Inventory i ON i.product_id=p.product_id
        LEFT JOIN Warehouse w ON w.warehouse_id=i.warehouse_id
        WHERE 1=1
    """
    args = []
    if search.strip():
        pattern = f"%{search.strip()}%"
        sql += " AND (p.article LIKE ? OR p.name LIKE ? OR p.description LIKE ? OR " \
               "c.name LIKE ? OR m.name LIKE ? OR s.name LIKE ?)"
        args.extend([pattern] * 6)
    if category and category != "Все категории":
        sql += " AND c.name=?"
        args.append(category)
    if discount_filter == "Есть скидка":
        sql += " AND p.discount > 0"
    elif discount_filter == "Свыше 15%":
        sql += " AND p.discount > 15"
    elif discount_filter == "Без скидки":
        sql += " AND p.discount = 0"
    ordering = {
        "Название А–Я": "p.name COLLATE NOCASE ASC",
        "Цена ↑": "p.price ASC", "Цена ↓": "p.price DESC",
        "Остаток ↑": "stock ASC", "Остаток ↓": "stock DESC",
        "Скидка ↑": "p.discount ASC", "Скидка ↓": "p.discount DESC",
    }
    sql += " GROUP BY p.product_id ORDER BY " + ordering.get(sort, "p.product_id ASC")
    with connect() as connection:
        return connection.execute(sql, args).fetchall()


def product(product_id):
    with connect() as connection:
        return connection.execute("""
            SELECT p.*, c.name AS category_name, m.name AS manufacturer_name,
                   s.name AS supplier_name, u.name AS unit_name,
                   COALESCE((SELECT SUM(i.quantity) FROM Inventory i
                             WHERE i.product_id=p.product_id),0) AS stock,
                   p.price * (100-p.discount)/100.0 AS final_price
            FROM Product p JOIN Category c ON c.category_id=p.category_id
            JOIN Manufacturer m ON m.manufacturer_id=p.manufacturer_id
            JOIN Supplier s ON s.supplier_id=p.supplier_id
            JOIN Unit u ON u.unit_id=p.unit_id WHERE p.product_id=?
        """, (product_id,)).fetchone()


def product_stocks(product_id):
    with connect() as connection:
        return connection.execute("""
            SELECT w.warehouse_id, w.name, COALESCE(i.quantity,0) AS quantity
            FROM Warehouse w LEFT JOIN Inventory i
              ON i.warehouse_id=w.warehouse_id AND i.product_id=?
            ORDER BY w.name
        """, (product_id,)).fetchall()


def choices(kind):
    queries = {
        "category": "SELECT category_id AS id, name AS label FROM Category ORDER BY name",
        "manufacturer": "SELECT manufacturer_id AS id, name AS label FROM Manufacturer ORDER BY name",
        "supplier": "SELECT supplier_id AS id, name AS label FROM Supplier ORDER BY name",
        "unit": "SELECT unit_id AS id, name AS label FROM Unit ORDER BY name",
        "warehouse": "SELECT warehouse_id AS id, name AS label FROM Warehouse ORDER BY name",
        "customer": "SELECT customer_id AS id, fio AS label FROM Customer ORDER BY fio",
        "status": "SELECT status_id AS id, name AS label FROM OrderStatus ORDER BY status_id",
    }
    if kind not in queries:
        raise ValueError("Недопустимый справочник")
    with connect() as connection:
        return connection.execute(queries[kind]).fetchall()


def save_product(values, product_id=None):
    fields = ("article", "name", "category_id", "description", "manufacturer_id",
              "supplier_id", "price", "unit_id", "discount", "image_path")
    data = [values[key] for key in fields]
    with connect() as connection:
        if product_id is None:
            cursor = connection.execute("""
                INSERT INTO Product(article,name,category_id,description,manufacturer_id,
                    supplier_id,price,unit_id,discount,image_path)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, data)
            product_id = cursor.lastrowid
        else:
            connection.execute("""
                UPDATE Product SET article=?,name=?,category_id=?,description=?,manufacturer_id=?,
                    supplier_id=?,price=?,unit_id=?,discount=?,image_path=? WHERE product_id=?
            """, data + [product_id])
        connection.execute("""
            INSERT INTO Inventory(product_id,warehouse_id,quantity) VALUES(?,?,?)
            ON CONFLICT(product_id,warehouse_id) DO UPDATE SET quantity=excluded.quantity
        """, (product_id, int(values["warehouse_id"]), int(values["quantity"])))
    return product_id


def delete_product(product_id):
    with connect() as connection:
        connection.execute("DELETE FROM Product WHERE product_id=?", (product_id,))


def orders():
    with connect() as connection:
        return connection.execute("""
            SELECT o.order_id, o.order_date, o.delivery_date, o.delivery_address, o.code,
                   c.fio, w.name AS warehouse, st.name AS status,
                   (SELECT COUNT(*) FROM OrderItem i WHERE i.order_id=o.order_id) AS item_count
            FROM ShopOrder o JOIN Customer c ON c.customer_id=o.customer_id
            JOIN Warehouse w ON w.warehouse_id=o.warehouse_id
            JOIN OrderStatus st ON st.status_id=o.status_id ORDER BY o.order_id
        """).fetchall()


def order(order_id):
    with connect() as connection:
        return connection.execute("SELECT * FROM ShopOrder WHERE order_id=?", (order_id,)).fetchone()


def order_items(order_id):
    with connect() as connection:
        return connection.execute("""
            SELECT p.article, i.quantity FROM OrderItem i
            JOIN Product p ON p.product_id=i.product_id WHERE i.order_id=?
            ORDER BY p.article
        """, (order_id,)).fetchall()


def save_order(values, items, order_id=None):
    """Создаёт/изменяет заказ и его строки атомарно; items — [(артикул, количество), ...]."""
    with connect() as connection:
        fields = ("order_date", "delivery_date", "customer_id", "warehouse_id",
                  "delivery_address", "code", "status_id")
        data = [values[key] for key in fields]
        if order_id is None:
            order_id = connection.execute("""
                INSERT INTO ShopOrder(order_date,delivery_date,customer_id,warehouse_id,
                    delivery_address,code,status_id) VALUES(?,?,?,?,?,?,?)
            """, data).lastrowid
        else:
            connection.execute("""
                UPDATE ShopOrder SET order_date=?,delivery_date=?,customer_id=?,warehouse_id=?,
                    delivery_address=?,code=?,status_id=? WHERE order_id=?
            """, data + [order_id])
            connection.execute("DELETE FROM OrderItem WHERE order_id=?", (order_id,))
        for article, quantity in items:
            product_row = connection.execute(
                "SELECT product_id, price FROM Product WHERE article=?", (article,)).fetchone()
            if product_row is None:
                raise ValueError(f"Не найден артикул товара: {article}")
            connection.execute("""
                INSERT INTO OrderItem(order_id,product_id,quantity,unit_price) VALUES(?,?,?,?)
            """, (order_id, product_row["product_id"], quantity, product_row["price"]))
    return order_id


def delete_order(order_id):
    with connect() as connection:
        connection.execute("DELETE FROM ShopOrder WHERE order_id=?", (order_id,))
