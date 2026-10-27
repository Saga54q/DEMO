"""Генерация русскоязычной блок-схемы алгоритма в PDF."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Блок-схема_алгоритма_ГОСТ.pdf"
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
pdfmetrics.registerFont(TTFont("DejaVu", str(FONT)))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_BOLD)))
PAGE = A3
W, H = PAGE
X_SCALE = 0.64
Y_OFFSET = 340
INK = HexColor("#223a36")
TEAL = HexColor("#087f78")
PALE = HexColor("#eaf3f1")
MINT = HexColor("#78a79f")


def centered_text(c, text, x, y, max_width, size=10, bold=False, leading=None):
    c.setFont("DejaVu-Bold" if bold else "DejaVu", size)
    leading = leading or size * 1.35
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = (line + " " + word).strip()
        if pdfmetrics.stringWidth(test, "DejaVu-Bold" if bold else "DejaVu", size) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    y0 = y + (len(lines)-1)*leading/2
    for i, line in enumerate(lines):
        c.drawCentredString(x, y0-i*leading, line)


def node(c, kind, x, y, w, h, text, fill=white, size=10):
    x, y, w, h, size = x*X_SCALE, y+Y_OFFSET, w*X_SCALE, h*0.78, size*0.82
    c.setFillColor(fill)
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.6)
    if kind == "terminal":
        c.ellipse(x-w/2, y-h/2, x+w/2, y+h/2, stroke=1, fill=1)
    elif kind == "decision":
        path = c.beginPath()
        path.moveTo(x, y+h/2)
        path.lineTo(x+w/2, y)
        path.lineTo(x, y-h/2)
        path.lineTo(x-w/2, y)
        path.close()
        c.drawPath(path, stroke=1, fill=1)
    elif kind == "io":
        skew = min(15, w*0.08)
        path = c.beginPath()
        path.moveTo(x-w/2+skew, y-h/2)
        path.lineTo(x+w/2, y-h/2)
        path.lineTo(x+w/2-skew, y+h/2)
        path.lineTo(x-w/2, y+h/2)
        path.close()
        c.drawPath(path, stroke=1, fill=1)
    else:
        c.roundRect(x-w/2, y-h/2, w, h, 4, stroke=1, fill=1)
    c.setFillColor(INK)
    centered_text(c, text, x, y, w*0.78, size=size, bold=kind in ("terminal", "decision"))


def arrow(c, points, label=None, label_pos=None):
    points = [(x*X_SCALE, y+Y_OFFSET) for x, y in points]
    if label_pos:
        label_pos = (label_pos[0]*X_SCALE, label_pos[1]+Y_OFFSET)
    c.setStrokeColor(MINT)
    c.setFillColor(MINT)
    c.setLineWidth(1.5)
    path = c.beginPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    c.drawPath(path, stroke=1, fill=0)
    x0, y0 = points[-2]
    x1, y1 = points[-1]
    c.saveState()
    c.translate(x1, y1)
    from math import atan2, degrees
    c.rotate(degrees(atan2(y1-y0, x1-x0)))
    c.line(0, 0, -7, 3)
    c.line(0, 0, -7, -3)
    c.restoreState()
    if label and label_pos:
        c.setFillColor(INK)
        c.setFont("DejaVu-Bold", 9)
        c.drawCentredString(*label_pos, label)


def title(c, text, subtitle):
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 19)
    c.drawString(34, H-36, text)
    c.setFillColor(INK)
    centered_text(c, subtitle, W/2, H-51, W-70, size=8)
    c.setStrokeColor(TEAL)
    c.line(34, H-68, W-34, H-68)


def page_auth(c):
    title(c, "МебельМаркет — алгоритм авторизации и выбора интерфейса",
          "Условные графические обозначения: терминатор — начало/конец; прямоугольник — процесс; параллелограмм — ввод/вывод; ромб — условие. Схема подготовлена по ГОСТ 19.701-90.")
    node(c, "terminal", 595, 755, 155, 42, "Начало")
    node(c, "process", 595, 665, 235, 58, "Запустить приложение; открыть Access через ODBC", PALE)
    node(c, "decision", 595, 555, 190, 90, "База доступна?")
    node(c, "io", 980, 555, 220, 62, "Вывести ошибку подключения")
    node(c, "terminal", 980, 455, 150, 42, "Завершить")
    node(c, "io", 595, 425, 250, 62, "Показать окно входа и гостевого просмотра", PALE)
    node(c, "decision", 595, 315, 190, 90, "Выбран режим гостя?")
    node(c, "io", 205, 315, 250, 66, "Показать каталог без поиска и сортировки")
    node(c, "terminal", 205, 205, 150, 42, "Завершить")
    node(c, "io", 595, 190, 240, 62, "Ввести логин и пароль из базы")
    node(c, "decision", 595, 82, 190, 82, "Данные верны?")
    node(c, "io", 945, 82, 220, 62, "Сообщить об ошибке; повторить вход")
    node(c, "terminal", 595, -10, 62, 62, "A", PALE, size=14)

    # Connections are placed in page coordinates; lower role branches continue on page 2.
    arrow(c, [(595,734),(595,694)])
    arrow(c, [(595,636),(595,600)])
    arrow(c, [(690,555),(870,555),(870,555)])
    arrow(c, [(980,524),(980,476)])
    arrow(c, [(595,510),(595,456)], "Да", (620,484))
    arrow(c, [(595,394),(595,360)])
    arrow(c, [(500,315),(330,315)], "Да", (414,330))
    arrow(c, [(205,282),(205,226)])
    arrow(c, [(595,270),(595,221)], "Нет", (622,245))
    arrow(c, [(595,159),(595,123)])
    arrow(c, [(690,82),(835,82)], "Нет", (762,98))
    arrow(c, [(945,51),(945,15),(715,15),(715,165),(710,190)])
    arrow(c, [(595,41),(595,21)])
    # Connector A continues to the role-specific catalog flow on the next page.
    c.showPage()


def page_roles_and_workflow(c):
    title(c, "МебельМаркет — каталог и операции по ролям",
          "Продолжение алгоритма: после успешной авторизации приложение открывает разрешённые функции; данные каталога читаются из базы Access.")
    node(c, "terminal", 595, 755, 62, 62, "A", PALE, size=14)
    node(c, "decision", 595, 635, 190, 90, "Какая роль?")
    node(c, "process", 210, 505, 270, 78, "Клиент: просмотреть товары без поиска/сортировки")
    node(c, "process", 595, 505, 280, 78, "Менеджер: фильтр/сортировка/поиск; просмотр заказов")
    node(c, "process", 980, 505, 300, 78, "Администратор: фильтр, поиск, сортировка; CRUD товаров и заказов")
    node(c, "process", 595, 375, 340, 74, "Загрузить товары, описания, остатки по складам и изображения")
    node(c, "decision", 595, 255, 190, 90, "Изображение есть?")
    node(c, "io", 300, 255, 230, 62, "Вывести picture.png как заглушку")
    node(c, "process", 595, 135, 310, 75, "Отобразить карточку: категория, название, описание, производитель, поставщик, цена, единица, остаток, скидка")
    node(c, "decision", 595, 20, 190, 80, "Остаток и скидка?")
    node(c, "process", 175, -95, 250, 65, "Нет остатка: серый фон")
    node(c, "process", 595, -95, 275, 65, "Скидка >15%: фон #008080; показать зачёркнутую старую и новую цену")
    node(c, "process", 1015, -95, 250, 65, "Иначе обычное оформление")
    node(c, "terminal", 595, -205, 160, 42, "Ожидать действия")
    arrow(c, [(595,734),(595,680)])
    arrow(c, [(500,635),(210,635),(210,544)])
    arrow(c, [(595,590),(595,544)])
    arrow(c, [(690,635),(980,635),(980,544)])
    arrow(c, [(210,466),(210,410),(595,410)])
    arrow(c, [(595,466),(595,412)])
    arrow(c, [(980,466),(980,410),(595,410)])
    arrow(c, [(595,338),(595,300)])
    arrow(c, [(500,255),(415,255)], "Нет", (455,271))
    arrow(c, [(300,224),(300,172),(440,172)])
    arrow(c, [(595,217),(595,173)], "Да", (620,196))
    arrow(c, [(595,97),(595,60)])
    arrow(c, [(500,20),(175,20),(175,-62)], "Нет", (335,36))
    arrow(c, [(595,-20),(595,-62)], "Скидка >15%", (690,-40))
    arrow(c, [(690,20),(1015,20),(1015,-62)], "Есть остаток; скидка ≤15%", (850,36))
    arrow(c, [(175,-128),(175,-184),(595,-184)])
    arrow(c, [(595,-128),(595,-184)])
    arrow(c, [(1015,-128),(1015,-184),(595,-184)])
    c.showPage()


def main():
    c = canvas.Canvas(str(OUT), pagesize=PAGE)
    c.setTitle("Блок-схема алгоритма МебельМаркет")
    page_auth(c)
    page_roles_and_workflow(c)
    c.save()
    print(OUT)


if __name__ == "__main__":
    main()
