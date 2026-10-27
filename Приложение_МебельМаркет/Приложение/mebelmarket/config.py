"""Настройки и относительные пути проекта."""
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT / "БД" / "МебельМаркет.accdb"
ACCESS_DRIVER = "Microsoft Access Driver (*.mdb, *.accdb)"
STATUSES = ("Новый", "Собирается", "В пути", "Доставлен", "Отменён")
