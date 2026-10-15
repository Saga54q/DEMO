#!/usr/bin/env python3
"""Генератор ER-диаграммы (PDF) для БД «Магазин обуви».

Задание 1 «Разработка базы данных средствами СУБД», КИМ 09.02.07-2-2027:
«ER-диаграмма должна быть представлена в формате PDF и содержать таблицы,
связи между ними, атрибуты и ключи».

Запуск: python3 tools/СделатьСхему.py
Результат: Практика1_МагазинОбуви/СхемаДанных.pdf
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A2, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "Практика1_МагазинОбуви", "СхемаДанных.pdf")

# --- шрифт с кириллицей ---
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def pick(cands):
    for p in cands:
        if os.path.exists(p):
            return p
    raise SystemExit("Не найден шрифт с кириллицей (DejaVuSans)")


pdfmetrics.registerFont(TTFont("Sans", pick(FONT_CANDIDATES)))
pdfmetrics.registerFont(TTFont("Sans-Bold", pick(FONT_BOLD_CANDIDATES)))

W, H = landscape(A2)  # 1684 x 1191 pt

HEADER_BG = colors.HexColor("#1F3864")
HEADER_FG = colors.white
PK_C = colors.HexColor("#B8860B")
FK_C = colors.HexColor("#444444")
TYPE_C = colors.HexColor("#666666")
LINE_C = colors.HexColor("#1F3864")

ROW_H = 20
HEAD_H = 28
PAD = 8

# (таблица, поля[(имя, тип, ключ)])  ключ: "PK" | "FK" | ""
TABLES = {
    "Клиенты": [
        ("ID_Клиента", "Счётчик", "PK"),
        ("ФИО", "Короткий текст (100)", ""),
        ("Логин", "Короткий текст (50)", ""),
        ("Телефон", "Короткий текст (20)", ""),
    ],
    "Заказы": [
        ("ID_Заказа", "Счётчик", "PK"),
        ("ID_Клиента", "Числовой (Длинное целое)", "FK"),
        ("ДатаЗаказа", "Дата/время", ""),
    ],
    "СоставЗаказа": [
        ("ID_Строки", "Счётчик", "PK"),
        ("ID_Заказа", "Числовой (Длинное целое)", "FK"),
        ("ID_Позиции", "Числовой (Длинное целое)", "FK"),
        ("Количество", "Числовой (Длинное целое)", ""),
        ("ЦенаЗаЕдиницу", "Денежный", ""),
    ],
    "ТоварныеПозиции": [
        ("ID_Позиции", "Счётчик", "PK"),
        ("ID_Модели", "Числовой (Длинное целое)", "FK"),
        ("Размер", "Числовой (Байт)", ""),
        ("Количество", "Числовой (Длинное целое)", ""),
    ],
    "Модели": [
        ("ID_Модели", "Счётчик", "PK"),
        ("Наименование", "Короткий текст (100)", ""),
        ("ID_Категории", "Числовой (Длинное целое)", "FK"),
        ("ID_Производителя", "Числовой (Длинное целое)", "FK"),
        ("Состав", "Короткий текст (100)", ""),
        ("Описание", "Длинный текст", ""),
        ("Цена", "Денежный", ""),
        ("Изображение", "Вложение", ""),
    ],
    "Категории": [
        ("ID_Категории", "Счётчик", "PK"),
        ("Наименование", "Короткий текст (50)", ""),
    ],
    "Производители": [
        ("ID_Производителя", "Счётчик", "PK"),
        ("Наименование", "Короткий текст (50)", ""),
        ("Страна", "Короткий текст (50)", ""),
    ],
}

# позиции: (x, y_from_top) верхнего левого угла
POS = {
    "Клиенты": (60, 140),
    "Заказы": (430, 140),
    "СоставЗаказа": (800, 140),
    "ТоварныеПозиции": (1170, 140),
    "Категории": (150, 430),
    "Производители": (150, 560),
    "Модели": (720, 430),
}
BOX_W = 300

# связи: (родитель, дочерняя, поле-ВК у ребёнка, каскад-примечание)
LINKS = [
    ("Клиенты", "Заказы", "ID_Клиента", ""),
    ("Заказы", "СоставЗаказа", "ID_Заказа", "ON DELETE CASCADE"),
    ("ТоварныеПозиции", "СоставЗаказа", "ID_Позиции", ""),
    ("Модели", "ТоварныеПозиции", "ID_Модели", ""),
    ("Категории", "Модели", "ID_Категории", ""),
    ("Производители", "Модели", "ID_Производителя", ""),
]


def box_h(name):
    return HEAD_H + ROW_H * len(TABLES[name]) + PAD


def py(name):
    """pdf-y верхней границы"""
    return H - POS[name][1]


def center(name):
    x, y = POS[name]
    return x + BOX_W / 2, py(name) - box_h(name) / 2


def draw_table(c, name):
    x, y_top = POS[name]
    y = H - y_top  # верх в pdf-координатах
    fields = TABLES[name]
    h = box_h(name)
    # тело
    c.setFillColor(colors.white)
    c.setStrokeColor(LINE_C)
    c.setLineWidth(1)
    c.rect(x, y - h, BOX_W, h, fill=1, stroke=1)
    # шапка
    c.setFillColor(HEADER_BG)
    c.rect(x, y - HEAD_H, BOX_W, HEAD_H, fill=1, stroke=0)
    c.setFillColor(HEADER_FG)
    c.setFont("Sans-Bold", 13)
    c.drawCentredString(x + BOX_W / 2, y - HEAD_H + 9, name)
    # поля
    cy = y - HEAD_H - 14
    for fname, ftype, key in fields:
        if key == "PK":
            c.setFillColor(PK_C)
            c.setFont("Sans-Bold", 9)
            c.drawString(x + 6, cy, "PK")
        elif key == "FK":
            c.setFillColor(FK_C)
            c.setFont("Sans-Bold", 9)
            c.drawString(x + 6, cy, "FK")
        c.setFillColor(colors.black)
        c.setFont("Sans", 10.5)
        c.drawString(x + 34, cy, fname)
        c.setFillColor(TYPE_C)
        c.setFont("Sans", 8.5)
        c.drawRightString(x + BOX_W - 8, cy, ftype)
        cy -= ROW_H


def row_y(name, field):
    """pdf-y строки поля (по базовой линии текста)."""
    fields = TABLES[name]
    idx = [i for i, (f, _, _) in enumerate(fields) if f == field][0]
    return H - POS[name][1] - HEAD_H - 14 - idx * ROW_H + 3


def pk_field(name):
    for f, _, k in TABLES[name]:
        if k == "PK":
            return f
    raise KeyError(name)


def anchor(name, field, other):
    """Точка на боковой границе box на уровне строки field — ближе к other."""
    x, y_top = POS[name]
    y = row_y(name, field)
    ox, _ = POS[other]
    px = x if ox + BOX_W / 2 < x + BOX_W / 2 else x + BOX_W
    return px, y


def draw_link(c, parent, child, fk_field, note):
    x1, y1 = anchor(parent, pk_field(parent), child)
    x2, y2 = anchor(child, fk_field, parent)
    c.setStrokeColor(LINE_C)
    c.setLineWidth(1.4)
    c.line(x1, y1, x2, y2)
    # подписи 1 и ∞
    c.setFont("Sans-Bold", 12)
    c.setFillColor(LINE_C)
    t = 0.12
    c.drawString(x1 + (x2 - x1) * t - 4, y1 + (y2 - y1) * t + 6, "1")
    t = 0.88
    c.drawString(x1 + (x2 - x1) * t - 4, y1 + (y2 - y1) * t + 6, "∞")
    if note:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        c.setFont("Sans", 7.5)
        tw = c.stringWidth(note, "Sans", 7.5)
        c.setFillColor(colors.white)
        c.rect(mx - tw / 2 - 3, my - 2, tw + 6, 12, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#8B0000"))
        c.drawCentredString(mx, my + 1, note)


def main():
    from reportlab.pdfgen import canvas as rl_canvas

    c = rl_canvas.Canvas(OUT, pagesize=(W, H))
    c.setTitle("ER-диаграмма БД «Магазин обуви»")

    # заголовок
    c.setFillColor(HEADER_BG)
    c.setFont("Sans-Bold", 22)
    c.drawCentredString(W / 2, H - 48, "ER-диаграмма базы данных «Магазин обуви»")
    c.setFont("Sans", 11)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawCentredString(
        W / 2, H - 70,
        "Задание 1 «Разработка базы данных средствами СУБД» · КИМ 09.02.07-2-2027 (стр. 30–31) · "
        "третья нормальная форма · ссылочная целостность",
    )

    for name in TABLES:
        draw_table(c, name)
    for parent, child, fk_field, note in LINKS:
        draw_link(c, parent, child, fk_field, note)

    # легенда
    lx, ly = 70, H - 1010
    c.setStrokeColor(colors.HexColor("#999999"))
    c.setLineWidth(0.8)
    c.rect(lx, ly - 78, 1080, 78, fill=0, stroke=1)
    c.setFont("Sans-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(lx + 12, ly - 20, "Условные обозначения:")
    c.setFont("Sans", 10)
    c.setFillColor(PK_C)
    c.drawString(lx + 190, ly - 20, "PK")
    c.setFillColor(colors.black)
    c.drawString(lx + 215, ly - 20, "— первичный ключ (уникально определяет запись)")
    c.setFillColor(FK_C)
    c.drawString(lx + 560, ly - 20, "FK")
    c.setFillColor(colors.black)
    c.drawString(lx + 585, ly - 20, "— внешний ключ (указатель на запись родительской таблицы)")
    c.setFillColor(colors.black)
    c.drawString(lx + 12, ly - 42, "1 — родительская таблица (одна запись)   ·   ∞ — дочерняя таблица (много записей)   ·   "
                                   "все 6 связей — со ссылочной целостностью (ON UPDATE CASCADE)")
    c.setFillColor(colors.HexColor("#8B0000"))
    c.drawString(lx + 12, ly - 62, "ON DELETE CASCADE — только у связи Заказы → СоставЗаказа "
                                   "(удаление заказа удаляет его строки); у остальных связей удаление «родителя» с данными запрещено")

    c.showPage()
    c.save()
    print("OK:", OUT)


if __name__ == "__main__":
    main()
