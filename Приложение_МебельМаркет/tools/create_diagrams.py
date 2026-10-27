"""Строит PDF-диаграммы векторными элементами по видимым страницам задания."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white

ROOT = Path(__file__).resolve().parents[1]
OUT_ER = ROOT / "ER_диаграмма.pdf"
OUT_FLOW = ROOT / "Блок-схема.pdf"
FONT_OPTIONS = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
]
REG, BOLD = "Helvetica", "Helvetica-Bold"
for regular_path, bold_path in FONT_OPTIONS:
    try:
        if Path(regular_path).exists() and Path(bold_path).exists():
            pdfmetrics.registerFont(TTFont("MebelDV", regular_path))
            pdfmetrics.registerFont(TTFont("MebelDV-Bold", bold_path))
            REG, BOLD = "MebelDV", "MebelDV-Bold"
            break
    except Exception:
        pass
TEAL = HexColor("#008080")
DARK = HexColor("#183D3A")
LIGHT = HexColor("#F2F7F6")
LINE = HexColor("#58716E")


def entity(c, x, y, width, title, fields):
    height = 26 + len(fields) * 14
    c.setFillColor(LIGHT); c.setStrokeColor(TEAL); c.setLineWidth(1.1)
    c.roundRect(x, y, width, height, 6, fill=1, stroke=1)
    c.setFillColor(TEAL); c.roundRect(x, y+height-25, width, 25, 6, fill=1, stroke=0)
    c.rect(x, y+height-25, width, 8, fill=1, stroke=0)
    c.setFillColor(white); c.setFont(BOLD, 9)
    c.drawString(x+8, y+height-17, title)
    c.setFillColor(DARK); c.setFont(REG, 7.1)
    yy = y+height-39
    for field in fields:
        c.drawString(x+8, yy, field)
        yy -= 14
    return height


def arrow(c, points, label=""):
    import math
    c.saveState(); c.setStrokeColor(LINE); c.setFillColor(LINE); c.setLineWidth(1)
    path = c.beginPath(); path.moveTo(*points[0])
    for point in points[1:]: path.lineTo(*point)
    c.drawPath(path, stroke=1, fill=0)
    x0,y0=points[-2];x1,y1=points[-1];angle=math.atan2(y1-y0,x1-x0);size=5
    c.line(x1,y1,x1-size*math.cos(angle-.45),y1-size*math.sin(angle-.45))
    c.line(x1,y1,x1-size*math.cos(angle+.45),y1-size*math.sin(angle+.45))
    if label:
        lx,ly=points[len(points)//2]
        c.setFillColor(DARK);c.setFont(BOLD,6.8);c.drawString(lx+3,ly+3,label)
    c.restoreState()


def create_er():
    width,height=landscape(A3)
    c=canvas.Canvas(str(OUT_ER),pagesize=(width,height))
    c.setTitle("ER-диаграмма — МебельМаркет, вариант №5")
    c.setFillColor(DARK);c.setFont(BOLD,17)
    c.drawCentredString(width/2,height-30,"ER-ДИАГРАММА · УЧЁТ МЕБЕЛИ И ОСТАТКОВ НА СКЛАДАХ")
    c.setFillColor(LINE);c.setFont(REG,8.5)
    c.drawCentredString(width/2,height-46,"Вариант № 5 · 3НФ · PK — первичный ключ · FK — внешний ключ · связи 1:N")
    # Отношения нарисованы до таблиц, чтобы проходить под блоками сущностей.
    arrow(c,[(140,700),(140,650)],"1:N")                       # Role -> User
    arrow(c,[(380,700),(470,700),(470,596),(560,596)],"1:N")  # Category -> Product
    arrow(c,[(610,700),(610,596)],"1:N")                       # Manufacturer -> Product
    arrow(c,[(842,700),(842,640),(800,596)],"1:N")              # Supplier -> Product
    arrow(c,[(1077,700),(1077,550),(800,550)],"1:N")           # Unit -> Product
    arrow(c,[(700,500),(700,368)],"1:N")                       # Product -> OrderItem
    arrow(c,[(800,530),(885,530),(885,368),(1020,368)],"1:N")  # Product -> Inventory
    arrow(c,[(1050,480),(1050,368)],"1:N")                     # Warehouse -> Inventory
    arrow(c,[(250,334),(320,350)],"1:N")                       # Customer -> ShopOrder
    arrow(c,[(950,500),(900,500),(900,270),(580,270),(580,330)],"1:N") # Warehouse -> Order
    arrow(c,[(425,174),(425,300)],"1:N")                       # Status -> Order
    arrow(c,[(580,350),(650,334)],"1:N")                       # Order -> OrderItem
    # Entity positions (landscape A3)
    entity(c,40,700,200,"Role",["PK role_id","name"])
    entity(c,40,530,200,"User",["PK user_id","FK role_id","fio","login (unique)","password"])
    entity(c,40,300,210,"Customer",["PK customer_id","fio","phone","address"])
    entity(c,320,300,260,"ShopOrder",["PK order_id","order_date · delivery_date","FK customer_id · warehouse_id","delivery_address · code","FK status_id"])
    entity(c,650,300,230,"OrderItem",["PK, FK order_id","PK, FK product_id","quantity · unit_price"])
    entity(c,520,500,280,"Product",["PK product_id · article (unique)","name · description","FK category_id · manufacturer_id","FK supplier_id · unit_id","price · discount · image_path"])
    entity(c,280,700,200,"Category",["PK category_id","name (unique)"])
    entity(c,500,700,220,"Manufacturer",["PK manufacturer_id","name (unique)"])
    entity(c,740,700,205,"Supplier",["PK supplier_id","name (unique)"])
    entity(c,990,700,175,"Unit",["PK unit_id","name (unique)"])
    entity(c,950,480,210,"Warehouse",["PK warehouse_id","name","address"])
    entity(c,930,300,230,"Inventory",["PK, FK product_id","PK, FK warehouse_id","quantity ≥ 0"])
    entity(c,320,120,210,"OrderStatus",["PK status_id","name (unique)"])
    c.setFillColor(DARK);c.setFont(REG,7.7)
    c.drawString(40,65,"Inventory хранит остаток отдельно для пары товар–склад; суммарный остаток каталога — сумма по складам.")
    c.drawString(40,51,"OrderItem связывает заказ и товар; товар с существующей позицией заказа нельзя удалить (FK RESTRICT).")
    c.showPage();c.save()


def process(c, x, y, w, h, text, fill=LIGHT, stroke=TEAL, size=8.5):
    c.setFillColor(fill);c.setStrokeColor(stroke);c.setLineWidth(1.1)
    c.rect(x,y,w,h,fill=1,stroke=1)
    c.setFillColor(DARK);c.setFont(REG,size)
    lines=text.split("\n");step=size+3
    top=y+h/2+(len(lines)-1)*step/2-3
    for i,line_text in enumerate(lines):c.drawCentredString(x+w/2,top-i*step,line_text)

def terminal(c, cx, cy, w, h, text):
    c.setFillColor(HexColor("#E7F5E8"));c.setStrokeColor(TEAL);c.setLineWidth(1.1)
    c.ellipse(cx-w/2,cy-h/2,cx+w/2,cy+h/2,fill=1,stroke=1)
    c.setFillColor(DARK);c.setFont(REG,8.5);c.drawCentredString(cx,cy-3,text)

def io(c, x, y, w, h, text, size=8.5):
    skew=14;c.setFillColor(LIGHT);c.setStrokeColor(TEAL);c.setLineWidth(1.1)
    p=c.beginPath();p.moveTo(x+skew,y);p.lineTo(x+w,y);p.lineTo(x+w-skew,y+h);p.lineTo(x,y+h);p.close()
    c.drawPath(p,fill=1,stroke=1)
    c.setFillColor(DARK);c.setFont(REG,size)
    lines=text.split("\n");step=size+3;top=y+h/2+(len(lines)-1)*step/2-3
    for i,line_text in enumerate(lines):c.drawCentredString(x+w/2,top-i*step,line_text)

def diamond(c,cx,cy,w,h,text):
    c.setFillColor(HexColor("#FFF8DF"));c.setStrokeColor(HexColor("#9D7B24"));c.setLineWidth(1.1)
    p=c.beginPath();p.moveTo(cx,cy+h/2);p.lineTo(cx+w/2,cy);p.lineTo(cx,cy-h/2);p.lineTo(cx-w/2,cy);p.close()
    c.drawPath(p,fill=1,stroke=1);c.setFillColor(DARK);c.setFont(REG,8)
    lines=text.split("\n");step=10;top=cy+(len(lines)-1)*step/2-3
    for i,line_text in enumerate(lines):c.drawCentredString(cx,top-i*step,line_text)

def flow_arrow(c, points, label=""):
    arrow(c,points,label)

def create_flow():
    width,height=landscape(A3)
    c=canvas.Canvas(str(OUT_FLOW),pagesize=(width,height))
    c.setTitle("Блок-схема приложения — мебельный магазин, вариант №5")
    c.setFillColor(DARK);c.setFont(BOLD,16)
    c.drawCentredString(width/2,height-28,"БЛОК-СХЕМА РАБОТЫ ПРИЛОЖЕНИЯ «МЕБЕЛЬМАРКЕТ»")
    c.setFont(REG,8);c.setFillColor(LINE)
    c.drawCentredString(width/2,height-44,"Алгоритм доступа к каталогу, складам и заказам · обозначения по ГОСТ 19.701-90")
    c.drawString(35,780,"Роль определяет доступные действия; после входа отображаются ФИО и роль.")
    c.drawString(35,767,"Скидка >15% — #008080; остаток 0 — серый; заказанный товар нельзя удалить.")
    # Main: start -> input -> decisions / role -> catalog
    terminal(c,595,735,145,34,"Начало")
    io(c,490,665,210,48,"Окно входа\nЛогин и пароль")
    diamond(c,595,590,150,72,"Гость?")
    process(c,195,500,245,58,"Задать роль «Гость»\nбез авторизации")
    process(c,490,500,210,58,"Проверить логин и пароль\nв базе SQLite")
    diamond(c,595,420,150,72,"Вход\nуспешен?")
    process(c,780,390,190,55,"Сообщить об ошибке\nвернуться ко входу",fill=HexColor("#FCE8E6"),stroke=HexColor("#A94442"))
    process(c,490,330,210,48,"Загрузить ФИО\nи роль пользователя")
    io(c,490,245,210,50,"Показать каталог\nтовары и остатки")
    diamond(c,595,195,150,70,"Определить\nроль")
    # Permissions by role
    process(c,40,95,270,78,"Гость / авторизованный клиент\nПросмотр без поиска, фильтра\nи сортировки")
    process(c,350,95,270,78,"Менеджер\nПоиск · фильтр · сортировка\nПросмотр заказов")
    process(c,660,95,280,78,"Администратор\nCRUD товаров и заказов\nСкладские остатки")
    io(c,455,25,280,42,"Чтение / сохранение данных")
    terminal(c,1050,130,160,56,"Выход → вход")
    # Main arrows
    flow_arrow(c,[(595,718),(595,713)])
    flow_arrow(c,[(595,665),(595,626)])
    flow_arrow(c,[(520,590),(440,590),(440,529)],"да")
    flow_arrow(c,[(595,554),(595,558),(595,558)])
    flow_arrow(c,[(595,500),(595,456)])
    flow_arrow(c,[(670,420),(780,420)],"нет")
    flow_arrow(c,[(595,384),(595,378)],"да")
    flow_arrow(c,[(875,390),(875,689),(700,689)],"повтор")
    flow_arrow(c,[(595,330),(595,295)])
    # Guest path and authenticated path both converge on the catalogue.
    flow_arrow(c,[(317,500),(317,270),(490,270)])
    flow_arrow(c,[(595,245),(595,230)])
    # Branch labels and role paths
    flow_arrow(c,[(520,195),(310,195),(310,173)],"гость / клиент")
    flow_arrow(c,[(595,160),(485,173)],"менеджер")
    flow_arrow(c,[(670,195),(800,195),(800,173)],"администратор")
    # Each role uses the database; the user can return to login at any time.
    flow_arrow(c,[(175,95),(455,46)])
    flow_arrow(c,[(485,95),(540,67)])
    flow_arrow(c,[(800,95),(700,46)])
    flow_arrow(c,[(735,46),(970,130)])
    flow_arrow(c,[(1050,158),(1050,690),(700,690)],"повторный вход")
    c.showPage();c.save()

if __name__ == "__main__":
    create_er();create_flow()
    print(OUT_ER);print(OUT_FLOW)
