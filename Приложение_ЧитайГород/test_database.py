"""Проверки данных и ограничений. Запуск: python -m unittest -v"""
import sqlite3
import tempfile
import unittest
from pathlib import Path
import database as db


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        db.DB_FILE = Path(self.temp.name) / "test.db"
        db.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_import_and_referential_integrity(self):
        with db.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM Product").fetchone()[0], 20)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM ShopOrder").fetchone()[0], 10)
            self.assertEqual(list(connection.execute("PRAGMA foreign_key_check")), [])

    def test_login_search_filter_and_sort(self):
        self.assertEqual(db.authenticate("1", "1")["role"], "Администратор")
        self.assertIsNone(db.authenticate("1", "wrong"))
        self.assertEqual(len(db.products("Linux")), 1)
        low = db.products("", "0–12,99%")
        self.assertTrue(all(0 <= row["discount"] <= 12.99 for row in low))
        prices = [row["cost"] for row in db.products(sort="Цена ↑")]
        self.assertEqual(prices, sorted(prices))

    def test_referenced_product_cannot_be_deleted(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.delete_product(1)

    def test_product_crud_and_order_cascade(self):
        values = {"article": "TEST-1", "name": "Тестовая книга", "unit": "шт.",
            "cost": 123.45, "supplier_id": 1, "manufacturer_id": 1, "type_id": 1,
            "discount": 0, "stock": 2, "description": "тест", "image": None}
        product_id = db.save_product(values)
        values["cost"] = 199.99
        db.save_product(values, product_id)
        self.assertEqual(db.product(product_id)["cost"], 199.99)
        db.delete_product(product_id)
        before = len(db.orders())
        db.delete_order(1)
        self.assertEqual(len(db.orders()), before - 1)
        with db.connect() as connection:
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM OrderItem WHERE order_id=1").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
