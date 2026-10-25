"""Учебное приложение магазина «ЧитайГород». Запуск: python main.py"""
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import date
from uuid import uuid4

import database as db

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

ROOT = Path(__file__).resolve().parent
BG, PANEL, ACCENT = "#FFFFFF", "#ABCFCE", "#546F94"
CYAN, GRAY, TEXT = "#23E1EF", "#E1E1E1", "#202020"
FONT = ("Comic Sans MS", 10)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ЧитайГород — информационная система")
        self.geometry("1380x780")
        self.minsize(1000, 650)
        self.configure(bg=BG)
        self.option_add("*Font", FONT)
        style = ttk.Style(self)
        style.configure("Treeview", font=FONT, rowheight=26)
        style.configure("Treeview.Heading", font=("Comic Sans MS", 10, "bold"))
        style.configure("TCombobox", font=FONT)
        self.edit_window = None
        self.preview_image = None
        self.logo_image = None
        self._set_icon()
        self.show_login()

    def _set_icon(self):
        try:
            self.iconbitmap(ROOT / "import" / "app_icon.ico")
        except tk.TclError:
            pass

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def show_login(self):
        self.current_user = None
        self.clear()
        box = tk.Frame(self, bg=BG, padx=30, pady=22)
        box.pack(expand=True)
        logo = ROOT / "import" / "icon.png"
        if logo.exists():
            try:
                self.logo_image = tk.PhotoImage(file=logo).subsample(4, 4)
                tk.Label(box, image=self.logo_image, bg=BG).pack(pady=8)
            except tk.TclError:
                pass
        tk.Label(box, text="Вход в систему", font=("Comic Sans MS", 18, "bold"),
                 bg=BG, fg=ACCENT).pack(pady=8)
        tk.Label(box, text="Логин", bg=BG).pack(anchor="w")
        self.login_entry = tk.Entry(box, width=32)
        self.login_entry.pack(pady=(2, 10))
        tk.Label(box, text="Пароль", bg=BG).pack(anchor="w")
        self.password_entry = tk.Entry(box, width=32, show="*")
        self.password_entry.pack(pady=(2, 12))
        self.password_entry.bind("<Return>", lambda _event: self.login())
        tk.Button(box, text="Войти", bg=ACCENT, fg="white", width=24,
                  command=self.login).pack(pady=4)
        tk.Button(box, text="Продолжить как гость", bg=PANEL, width=24,
                  command=lambda: self.open_shop({"fio": "Гость", "role": "Гость"})).pack(pady=4)
        tk.Label(box, text="Демо-вход: администратор 1 / 1 · менеджер 2 / 2 · клиент 3 / 3",
                 bg=BG, fg="#555555").pack(pady=10)
        self.login_entry.focus_set()

    def login(self):
        user = db.authenticate(self.login_entry.get(), self.password_entry.get())
        if not user:
            messagebox.showerror("Ошибка входа", "Проверьте логин и пароль.", parent=self)
            self.password_entry.delete(0, "end")
            return
        self.open_shop(dict(user))

    def open_shop(self, user):
        self.current_user = user
        self.clear()
        self._build_header()
        self._build_toolbar()
        self._build_products()
        self.refresh_products()

    def _build_header(self):
        bar = tk.Frame(self, bg=PANEL, padx=12, pady=8)
        bar.pack(fill="x")
        logo = ROOT / "import" / "icon.png"
        if logo.exists():
            try:
                self.logo_image = tk.PhotoImage(file=logo).subsample(8, 8)
                tk.Label(bar, image=self.logo_image, bg=PANEL).pack(side="left", padx=(0, 10))
            except tk.TclError:
                pass
        tk.Label(bar, text="Каталог книг", font=("Comic Sans MS", 16, "bold"),
                 bg=PANEL, fg=ACCENT).pack(side="left")
        tk.Label(bar, text=f"{self.current_user['fio']} · {self.current_user['role']}",
                 bg=PANEL).pack(side="right", padx=8)
        if self.current_user["role"] in ("Менеджер", "Администратор"):
            tk.Button(bar, text="Заказы", command=self.open_orders).pack(side="right", padx=4)
        tk.Button(bar, text="Выйти", command=self.show_login).pack(side="right", padx=4)

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BG, padx=10, pady=8)
        bar.pack(fill="x")
        if self.current_user["role"] not in ("Менеджер", "Администратор"):
            tk.Label(bar, text="Режим просмотра: поиск, сортировка и фильтры недоступны.",
                     bg=BG, fg=ACCENT).pack(side="left")
            return
        tk.Label(bar, text="Поиск:", bg=BG).pack(side="left")
        self.search_var = tk.StringVar()
        search = tk.Entry(bar, textvariable=self.search_var, width=28)
        search.pack(side="left", padx=5)
        tk.Label(bar, text="Скидка:", bg=BG).pack(side="left", padx=(10, 0))
        self.range_var = tk.StringVar(value="Все диапазоны")
        self.range_box = ttk.Combobox(bar, textvariable=self.range_var, state="readonly", width=16,
            values=["Все диапазоны", "0–12,99%", "13–16,99%", "17% и более"])
        self.range_box.pack(side="left", padx=5)
        tk.Label(bar, text="Сортировка:", bg=BG).pack(side="left", padx=(10, 0))
        self.sort_var = tk.StringVar(value="Без сортировки")
        self.sort_box = ttk.Combobox(bar, textvariable=self.sort_var, state="readonly", width=16,
            values=["Без сортировки", "Цена ↑", "Цена ↓", "Остаток ↑", "Остаток ↓"])
        self.sort_box.pack(side="left", padx=5)
        tk.Button(bar, text="Сбросить", command=self.reset_filters).pack(side="left", padx=8)
        self.search_var.trace_add("write", lambda *_: self.refresh_products())
        self.range_var.trace_add("write", lambda *_: self.refresh_products())
        self.sort_var.trace_add("write", lambda *_: self.refresh_products())
        if self.current_user["role"] == "Администратор":
            tk.Button(bar, text="Удалить товар", command=self.delete_product).pack(side="right", padx=3)
            tk.Button(bar, text="Изменить", command=self.edit_product).pack(side="right", padx=3)
            tk.Button(bar, text="Добавить товар", command=self.add_product).pack(side="right", padx=3)

    def reset_filters(self):
        self.search_var.set("")
        self.range_var.set("Все диапазоны")
        self.sort_var.set("Без сортировки")

    def _build_products(self):
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        columns = ("id", "article", "name", "type", "description", "maker", "supplier",
                   "cost", "final", "unit", "stock", "discount")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        headings = {"id": "ID", "article": "Артикул", "name": "Наименование",
            "type": "Категория", "description": "Описание", "maker": "Производитель",
            "supplier": "Поставщик", "cost": "Цена", "final": "Цена со скидкой",
            "unit": "Ед.", "stock": "Остаток", "discount": "Скидка"}
        widths = {"id": 48, "article": 82, "name": 220, "type": 145, "description": 270,
                  "maker": 140, "supplier": 180, "cost": 85, "final": 115,
                  "unit": 48, "stock": 75, "discount": 75}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], minwidth=45,
                             anchor="w" if column in ("name", "description", "supplier") else "center")
        ybar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        xbar = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.tree.tag_configure("discount", background=CYAN)
        self.tree.tag_configure("empty", background=GRAY)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)
        self.tree.bind("<Double-1>", lambda _e: self.edit_product()
                       if self.current_user["role"] == "Администратор" else None)
        self._build_details()

    def _build_details(self):
        panel = tk.Frame(self, bg=PANEL, padx=10, pady=8)
        panel.pack(fill="x", padx=10, pady=(0, 10))
        self.photo_label = tk.Label(panel, text="Выберите книгу", bg=PANEL, width=22, height=6)
        self.photo_label.pack(side="left", padx=(0, 12))
        info = tk.Frame(panel, bg=PANEL)
        info.pack(side="left", fill="x", expand=True)
        self.detail_name = tk.Label(info, text="", font=("Comic Sans MS", 12, "bold"), bg=PANEL)
        self.detail_name.pack(anchor="w")
        self.old_price = tk.Label(info, text="", bg=PANEL, fg="#C62828")
        self.old_price.pack(anchor="w")
        self.new_price = tk.Label(info, text="", bg=PANEL, fg=TEXT)
        self.new_price.pack(anchor="w")
        self.detail_info = tk.Label(info, text="", bg=PANEL, justify="left", wraplength=950)
        self.detail_info.pack(anchor="w")

    def refresh_products(self):
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            return
        manager = self.current_user["role"] in ("Менеджер", "Администратор")
        data = db.products(self.search_var.get() if manager else "",
                           self.range_var.get() if manager else "Все диапазоны",
                           self.sort_var.get() if manager else "Без сортировки")
        self.tree.delete(*self.tree.get_children())
        for row in data:
            tag = "empty" if row["stock"] == 0 else ("discount" if row["discount"] > 25 else "")
            self.tree.insert("", "end", iid=str(row["product_id"]), tags=(tag,), values=(
                row["product_id"], row["article"], row["name"], row["type_name"],
                row["description"] or "", row["manufacturer"], row["supplier"],
                f"{row['cost']:.2f}", f"{row['final_price']:.2f}", row["unit"],
                row["stock"], f"{row['discount']:g}%"))

    def show_details(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        row = db.product(int(selected[0]))
        self.detail_name.config(text=f"{row['name']} · {row['article']}")
        if row["discount"]:
            strike_font = ("Comic Sans MS", 10, "overstrike")
            self.old_price.config(text=f"Обычная цена: {row['cost']:.2f} ₽", font=strike_font)
        else:
            self.old_price.config(text="", font=FONT)
        final = row["cost"] * (100 - row["discount"]) / 100
        self.new_price.config(text=f"Итоговая цена: {final:.2f} ₽ · скидка {row['discount']:g}%")
        self.detail_info.config(text=f"На складе: {row['stock']} {row['unit']}\n{row['description'] or 'Описание не указано.'}")
        self._show_photo(row["image"])

    def _show_photo(self, relative_path):
        path = ROOT / (relative_path or "import/picture.png")
        try:
            if Image is not None and path.exists():
                image = Image.open(path).convert("RGB")
                image.thumbnail((160, 105))
                self.preview_image = ImageTk.PhotoImage(image)
            else:
                self.preview_image = tk.PhotoImage(file=ROOT / "import" / "picture.png").subsample(5, 5)
            self.photo_label.config(image=self.preview_image, text="")
        except Exception:
            self.photo_label.config(image="", text="Изображение недоступно")

    def add_product(self):
        self.product_form()

    def edit_product(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Выбор товара", "Сначала выберите строку товара.", parent=self)
            return
        if self.current_user["role"] == "Администратор":
            self.product_form(int(selection[0]))

    def product_form(self, product_id=None):
        if self.edit_window and self.edit_window.winfo_exists():
            self.edit_window.lift()
            return
        old = db.product(product_id) if product_id else None
        window = tk.Toplevel(self)
        self.edit_window = window
        window.title("Редактирование товара" if old else "Добавление товара")
        window.geometry("610x690")
        window.configure(bg=BG)
        window.transient(self)
        window.grab_set()
        fields = {}
        row = 0
        if old:
            tk.Label(window, text=f"ID товара: {old['product_id']} (только чтение)",
                     bg=BG).grid(row=row, column=0, columnspan=2, sticky="w", padx=14, pady=5)
            row += 1
        definitions = [
            ("Артикул", "article", "entry"), ("Наименование", "name", "entry"),
            ("Единица измерения", "unit", "entry"), ("Цена", "cost", "entry"),
            ("Поставщик", "supplier_id", "Supplier"),
            ("Производитель", "manufacturer_id", "Manufacturer"),
            ("Категория", "type_id", "ProductType"),
            ("Скидка (%)", "discount", "entry"), ("Остаток", "stock", "entry"),
        ]
        for label, key, kind in definitions:
            tk.Label(window, text=label, bg=BG).grid(row=row, column=0, sticky="w", padx=14, pady=4)
            if kind == "entry":
                field = tk.Entry(window, width=42)
                field.insert(0, str(old[key] if old else ("0" if key in ("discount", "stock") else "")))
                field.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
            else:
                lookup = {"Supplier": ("Supplier", "supplier_id"),
                          "Manufacturer": ("Manufacturer", "manufacturer_id"),
                          "ProductType": ("ProductType", "type_id")}[kind]
                records = db.choices(lookup[0], "supplier_id" if kind == "Supplier" else
                    "manufacturer_id" if kind == "Manufacturer" else "type_id", "name")
                field = ttk.Combobox(window, state="readonly", width=39,
                                     values=[r["label"] for r in records])
                if records:
                    match = next((i for i, r in enumerate(records)
                                  if old and r["id"] == old[key]), 0)
                    field.current(match)
                field.records = records
                field.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
            fields[key] = field
            row += 1
        tk.Label(window, text="Описание", bg=BG).grid(row=row, column=0, sticky="nw", padx=14, pady=4)
        description = tk.Text(window, width=42, height=7, wrap="word")
        description.insert("1.0", old["description"] if old else "")
        description.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        row += 1
        image_label = tk.Label(window, text="Текущее изображение сохранится, если новое не выбрать.",
                               bg=BG, wraplength=400)
        image_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=14, pady=5)
        image_source = {"path": None}

        def choose_image():
            name = filedialog.askopenfilename(parent=window, title="Выберите изображение",
                filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp")])
            if name:
                image_source["path"] = Path(name)
                image_label.config(text=Path(name).name)

        row += 1
        tk.Button(window, text="Выбрать фото…", command=choose_image).grid(
            row=row, column=0, sticky="w", padx=14, pady=5)
        tk.Label(window, text="Фото автоматически приводится к 300 × 200 px.",
                 bg=BG).grid(row=row, column=1, sticky="w", padx=8)
        row += 1

        def save():
            try:
                cost = float(fields["cost"].get().replace(",", "."))
                discount = float(fields["discount"].get().replace(",", "."))
                stock = int(fields["stock"].get())
                if cost < 0 or stock < 0 or not 0 <= discount <= 100:
                    raise ValueError("Цена и остаток не могут быть отрицательными; скидка — от 0 до 100%.")
                values = {key: fields[key].get().strip() for key in ("article", "name", "unit")}
                if not all(values.values()):
                    raise ValueError("Заполните артикул, наименование и единицу измерения.")
                values.update(cost=cost, discount=discount, stock=stock,
                              description=description.get("1.0", "end").strip())
                for key in ("supplier_id", "manufacturer_id", "type_id"):
                    combo = fields[key]
                    index = combo.current()
                    if index < 0:
                        raise ValueError("Выберите поставщика, производителя и категорию.")
                    values[key] = combo.records[index]["id"]
                old_image = old["image"] if old else None
                new_image = None
                if image_source["path"]:
                    if Image is None:
                        raise ValueError("Для обработки фото установите Pillow: pip install pillow")
                    new_image = self.store_image(image_source["path"])
                values["image"] = f"images/{new_image}" if new_image else old_image
                try:
                    db.save_product(values, product_id)
                except Exception:
                    if new_image:
                        (ROOT / "images" / new_image).unlink(missing_ok=True)
                    raise
                if new_image and old_image:
                    self.remove_unused_image(old_image)
                window.destroy()
                self.edit_window = None
                self.refresh_products()
            except ValueError as error:
                messagebox.showerror("Проверьте данные", str(error), parent=window)
            except Exception as error:
                messagebox.showerror("Не удалось сохранить товар", str(error), parent=window)

        tk.Button(window, text="Сохранить", bg=ACCENT, fg="white", command=save).grid(
            row=row, column=1, sticky="e", padx=14, pady=12)
        window.protocol("WM_DELETE_WINDOW", lambda: (window.destroy(), setattr(self, "edit_window", None)))

    @staticmethod
    def store_image(source):
        if Image is None:
            raise ValueError("Установите Pillow для загрузки изображений.")
        output = ROOT / "images"
        output.mkdir(exist_ok=True)
        filename = f"product_{uuid4().hex[:10]}.jpg"
        image = Image.open(source).convert("RGB")
        image.thumbnail((300, 200))
        canvas = Image.new("RGB", (300, 200), "white")
        canvas.paste(image, ((300 - image.width) // 2, (200 - image.height) // 2))
        canvas.save(output / filename, "JPEG", quality=88)
        return filename

    def remove_unused_image(self, relative_path):
        with db.connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM Product WHERE image=?",
                                       (relative_path,)).fetchone()[0]
        path = ROOT / relative_path
        if count == 0 and path.exists():
            path.unlink()

    def delete_product(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Выбор товара", "Сначала выберите товар.", parent=self)
            return
        product_id = int(selection[0])
        if not messagebox.askyesno("Удаление товара", "Удалить выбранный товар?", parent=self):
            return
        try:
            old = db.product(product_id)
            db.delete_product(product_id)
            if old["image"]:
                self.remove_unused_image(old["image"])
            self.refresh_products()
        except Exception:
            messagebox.showerror("Удаление запрещено",
                "Товар используется в заказе и не может быть удалён. Сначала проверьте заказы.",
                parent=self)

    def open_orders(self):
        OrdersWindow(self)


class OrdersWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Заказы — ЧитайГород")
        self.geometry("1120x510")
        self.configure(bg=BG)
        self.transient(parent)
        columns = ("id", "date", "delivery", "customer", "pickup", "code", "status", "items")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        labels = ("№", "Дата", "Доставка", "Клиент", "Пункт выдачи", "Код", "Статус", "Строк")
        for col, label in zip(columns, labels):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=120 if col != "pickup" else 230, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=10, pady=8)
        if parent.current_user["role"] == "Администратор":
            tk.Button(bar, text="Добавить", command=self.add).pack(side="left", padx=3)
            tk.Button(bar, text="Изменить", command=self.edit).pack(side="left", padx=3)
            tk.Button(bar, text="Удалить", command=self.delete).pack(side="left", padx=3)
        tk.Button(bar, text="Закрыть", command=self.destroy).pack(side="right")
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for row in db.orders():
            self.tree.insert("", "end", iid=str(row["order_id"]), values=(row["order_id"],
                row["order_date"], row["delivery_date"], row["fio"], row["pickup"],
                row["code"], row["status"], row["item_count"]))

    def selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Выбор заказа", "Выберите заказ в списке.", parent=self)
            return None
        return int(selected[0])

    def add(self):
        OrderForm(self, None)

    def edit(self):
        order_id = self.selected_id()
        if order_id:
            OrderForm(self, order_id)

    def delete(self):
        order_id = self.selected_id()
        if order_id and messagebox.askyesno("Удаление заказа",
                f"Удалить заказ №{order_id} и его состав?", parent=self):
            db.delete_order(order_id)
            self.refresh()


class OrderForm(tk.Toplevel):
    def __init__(self, parent, order_id):
        super().__init__(parent)
        self.parent, self.order_id = parent, order_id
        self.title("Редактирование заказа" if order_id else "Новый заказ")
        self.configure(bg=BG)
        self.transient(parent)
        old = db.order(order_id) if order_id else None
        self.controls = {}
        self.maps = {}
        options = [
            ("Дата заказа (ГГГГ-ММ-ДД)", "order_date", None),
            ("Дата доставки (ГГГГ-ММ-ДД)", "delivery_date", None),
            ("Клиент", "customer_id", ("Customer", "customer_id")),
            ("Пункт выдачи", "point_id", ("PickupPoint", "point_id")),
            ("Код получения", "code", None),
            ("Статус", "status_id", ("OrderStatus", "status_id")),
        ]
        for row, (label, key, source) in enumerate(options):
            tk.Label(self, text=label, bg=BG).grid(row=row, column=0, sticky="w", padx=12, pady=6)
            if source:
                id_field = source[1]
                records = db.choices(source[0], id_field,
                    "fio" if source[0] == "Customer" else
                    "postal_code || ' · ' || city || street || ' ' || number" if source[0] == "PickupPoint" else "name")
                field = ttk.Combobox(self, state="readonly", width=48,
                                     values=[r["label"] for r in records])
                self.maps[key] = records
                if records:
                    value = old[key] if old else records[0]["id"]
                    field.current(next((i for i, item in enumerate(records)
                                        if item["id"] == value), 0))
            else:
                field = tk.Entry(self, width=50)
                default = date.today().isoformat() if key == "order_date" else ""
                field.insert(0, str(old[key] if old else default))
            field.grid(row=row, column=1, padx=8, pady=6)
            self.controls[key] = field
        tk.Button(self, text="Сохранить", bg=ACCENT, fg="white",
                  command=self.save).grid(row=len(options), column=1, sticky="e", padx=12, pady=12)

    def save(self):
        try:
            values = {}
            for key in ("order_date", "delivery_date"):
                value = self.controls[key].get().strip()
                date.fromisoformat(value)
                values[key] = value
            values["code"] = self.controls["code"].get().strip()
            if not values["code"]:
                raise ValueError("Введите код получения заказа.")
            for key, records in self.maps.items():
                index = self.controls[key].current()
                if index < 0:
                    raise ValueError("Выберите клиента, пункт выдачи и статус.")
                values[key] = records[index]["id"]
            db.save_order(values, self.order_id)
            self.parent.refresh()
            self.destroy()
        except ValueError as error:
            messagebox.showerror("Проверьте данные", str(error), parent=self)
        except Exception as error:
            messagebox.showerror("Ошибка сохранения", str(error), parent=self)


def main():
    try:
        db.initialize()
    except Exception as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Запуск не выполнен",
            f"Не удалось создать базу. Проверьте папку import и установку библиотек.\n\n{error}")
        root.destroy()
        return
    App().mainloop()


if __name__ == "__main__":
    main()
