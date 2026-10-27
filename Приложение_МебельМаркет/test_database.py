"""Автотесты импорта, ролей, фильтрации, склада и CRUD."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

import database as db


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.original_db = db.DB_FILE
        self.temp_dir = tempfile.TemporaryDirectory()
        db.DB_FILE = Path(self.temp_dir.name) / "test.db"
        db.initialize()

    def tearDown(self):
        db.DB_FILE = self.original_db
        self.temp_dir.cleanup()

    def test_import_and_foreign_keys(self):
        with db.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM Product").fetchone()[0], 12)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM ShopOrder").fetchone()[0], 5)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM OrderItem").fetchone()[0], 9)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM Inventory").fetchone()[0], 24)
            self.assertEqual(list(connection.execute("PRAGMA foreign_key_check")), [])

    def test_role_login(self):
        self.assertEqual(db.authenticate("admin@mebel.local", "Admin2026")["role"], "Администратор")
        self.assertEqual(db.authenticate("manager@mebel.local", "Manager2026")["role"], "Менеджер")
        self.assertEqual(db.authenticate("client@mebel.local", "Client2026")["role"], "Авторизованный клиент")
        self.assertIsNone(db.authenticate("admin@mebel.local", "wrong"))

    def test_search_filter_and_sort(self):
        discounted = db.products(discount_filter="Свыше 15%")
        self.assertTrue(discounted)
        self.assertTrue(all(row["discount"] > 15 for row in discounted))
        chairs = db.products(category="Кресла")
        self.assertTrue(chairs)
        self.assertTrue(all(row["category"] == "Кресла" for row in chairs))
        descending = db.products(sort="Цена ↓")
        self.assertEqual([row["price"] for row in descending],
                         sorted([row["price"] for row in descending], reverse=True))
        self.assertTrue(db.products(search="Лофт"))

    def test_product_and_inventory_crud(self):
        category = db.choices("category")[0]["id"]
        manufacturer = db.choices("manufacturer")[0]["id"]
        supplier = db.choices("supplier")[0]["id"]
        unit = db.choices("unit")[0]["id"]
        warehouse = db.choices("warehouse")[0]["id"]
        values = {"article": "TEST-1", "name": "Тестовый стол", "category_id": category,
                  "description": "Проверка CRUD", "manufacturer_id": manufacturer,
                  "supplier_id": supplier, "price": 12345.0, "unit_id": unit,
                  "discount": 16.0, "image_path": None, "warehouse_id": warehouse,
                  "quantity": 3}
        product_id = db.save_product(values)
        self.assertEqual(db.product(product_id)["stock"], 3)
        values["quantity"] = 7
        db.save_product(values, product_id)
        self.assertEqual(db.product(product_id)["stock"], 7)
        db.delete_product(product_id)
        with db.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM Product WHERE product_id=?",
                                                (product_id,)).fetchone()[0], 0)

    def test_order_crud_and_product_delete_restriction(self):
        with db.connect() as connection:
            customer_id = connection.execute("SELECT customer_id FROM Customer LIMIT 1").fetchone()[0]
            warehouse_id = connection.execute("SELECT warehouse_id FROM Warehouse LIMIT 1").fetchone()[0]
            status_id = connection.execute("SELECT status_id FROM OrderStatus LIMIT 1").fetchone()[0]
        values = {"order_date": "2026-06-01", "delivery_date": "2026-06-05",
                  "customer_id": customer_id, "warehouse_id": warehouse_id,
                  "delivery_address": "Москва, тестовый адрес", "code": "TEST-ORDER",
                  "status_id": status_id}
        order_id = db.save_order(values, [("MF-003", 1)])
        self.assertEqual(len(db.order_items(order_id)), 1)
        with self.assertRaises(sqlite3.IntegrityError):
            db.delete_product(db.product(1)["product_id"])
        db.delete_order(order_id)
        with db.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM OrderItem WHERE order_id=?",
                                                (order_id,)).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
