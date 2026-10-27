"""Подключение к локальной базе Microsoft Access."""
import pyodbc

from .config import ACCESS_DRIVER, DB_PATH


def db_connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Не найдена база данных: {DB_PATH}\nСначала создайте её согласно инструкции.")
    if ACCESS_DRIVER not in pyodbc.drivers():
        raise RuntimeError("Не найден Microsoft Access ODBC Driver. Установите Access Database Engine той же разрядности, что и Python.")
    return pyodbc.connect(f"DRIVER={{{ACCESS_DRIVER}}};DBQ={DB_PATH};", autocommit=False)
