"""Учебная система учёта мебели и складских остатков. Запуск: python main.py"""
from datetime import date
from pathlib import Path
from uuid import uuid4
import shutil
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import database as db

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

ROOT = Path(__file__).resolve().parent
BG = "#FFFFFF"
TEAL = "#008080"  # точный цвет строк при скидке строго выше 15% из условия
LIGHT = "#EAF2F0"
EMPTY = "#D9D9D9"
TEXT = "#202020"
FONT = ("Arial", 10)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("МебельМаркет — склад и каталог")
        self.geometry("1400x820")
        self.minsize(1000, 660)
        self.configure(bg=BG)
        self.option_add("*Font", FONT)
        style = ttk.Style(self)
        style.configure("Treeview", font=FONT, rowheight=28)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        style.configure("TCombobox", font=FONT)
        self.preview_image = None
        self.logo_image = None
        self.edit_window = None
        self._set_icon()
        self.show_login()

    def _set_icon(self):
        try:
            self.iconbitmap(ROOT / "import" / "app.ico")
        except tk.TclError:
            pass

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def show_login(self):
        self.current_user = None
        self.clear()
        box = tk.Frame(self, bg=BG, padx=32, pady=20)
        box.pack(expand=True)
        logo = ROOT / "import" / "logo.png"
        if logo.exists() and Image is not None:
            try:
                image = Image.open(logo).resize((310, 75))
                self.logo_image = ImageTk.PhotoImage(image)
                tk.Label(box, image=self.logo_image, bg=BG).pack(pady=(0, 10))
            except Exception:
                pass
        tk.Label(box, text="Вход в систему", font=("Arial", 18, "bold"),
                 bg=BG, fg=TEAL).pack(pady=8)
        tk.Label(box, text="Логин", bg=BG).pack(anchor="w")
        self.login_entry = tk.Entry(box, width=34)
        self.login_entry.pack(pady=(2, 10))
        tk.Label(box, text="Пароль", bg=BG).pack(anchor="w")
        self.password_entry = tk.Entry(box, width=34, show="*")
        self.password_entry.pack(pady=(2, 12))
        self.password_entry.bind("<Return>", lambda _event: self.login())
        tk.Button(box, text="Войти", bg=TEAL, fg="white", width=26,
                  command=self.login).pack(pady=4)
        tk.Button(box, text="Продолжить как гость", bg=LIGHT, width=26,
                  command=lambda: self.open_catalog({"fio": "Гость", "role": "Гость"})).pack(pady=4)
        tk.Label(box, text="Учебные входы: admin@mebel.local / Admin2026 · "
                 "manager@mebel.local / Manager2026 · client@mebel.local / Client2026",
                 bg=BG, fg="#52605D", wraplength=550, justify="center").pack(pady=12)
        self.login_entry.focus_set()

    def login(self):
        user = db.authenticate(self.login_entry.get(), self.password_entry.get())
        if not user:
            messagebox.showerror("Ошибка входа", "Проверьте логин и пароль.", parent=self)
            self.password_entry.delete(0, "end")
            return
        self.open_catalog(dict(user))

    def open_catalog(self, user):
        self.current_user = user
        self.clear()
        self._build_header()
        self._build_toolbar()
        self._build_catalog()
        self.refresh_products()

    def _build_header(self):
        bar = tk.Frame(self, bg=TEAL, padx=14, pady=9)
        bar.pack(fill="x")
        tk.Label(bar, text="МебельМаркет · Каталог и склады",
                 font=("Arial", 16, "bold"), bg=TEAL, fg="white").pack(side="left")
        tk.Label(bar, text=f"{self.current_user['fio']} · {self.current_user['role']}",
                 bg=TEAL, fg="white").pack(side="right", padx=8)
        role = self.current_user["role"]
        if role in ("Менеджер", "Администратор"):
            tk.Button(bar, text="Заказы", command=self.open_orders).pack(side="right", padx=4)
        tk.Button(bar, text="Выйти", command=self.show_login).pack(side="right", padx=4)

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BG, padx=10, pady=8)
        bar.pack(fill="x")
        role = self.current_user["role"]
        if role not in ("Менеджер", "Администратор"):
            tk.Label(bar, text="Режим просмотра: поиск, фильтры и сортировка недоступны.",
                     bg=BG, fg=TEAL).pack(side="left")
            return
        tk.Label(bar, text="Поиск:", bg=BG).pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(bar, textvariable=self.search_var, width=25).pack(side="left", padx=5)
        tk.Label(bar, text="Категория:", bg=BG).pack(side="left", padx=(7, 0))
        self.category_var = tk.StringVar(value="Все категории")
        categories = ["Все категории"] + [row["label"] for row in db.choices("category")]
        ttk.Combobox(bar, textvariable=self.category_var, state="readonly", width=16,
                     values=categories).pack(side="left", padx=4)
        tk.Label(bar, text="Скидка:", bg=BG).pack(side="left", padx=(7, 0))
        self.discount_var = tk.StringVar(value="Все скидки")
        ttk.Combobox(bar, textvariable=self.discount_var, state="readonly", width=14,
                     values=["Все скидки", "Без скидки", "Есть скидка", "Свыше 15%"]
                     ).pack(side="left", padx=4)
        tk.Label(bar, text="Сортировка:", bg=BG).pack(side="left", padx=(7, 0))
        self.sort_var = tk.StringVar(value="По умолчанию")
        ttk.Combobox(bar, textvariable=self.sort_var, state="readonly", width=15,
                     values=["По умолчанию", "Название А–Я", "Цена ↑", "Цена ↓",
                             "Остаток ↑", "Остаток ↓", "Скидка ↑", "Скидка ↓"]
                     ).pack(side="left", padx=4)
        tk.Button(bar, text="Сбросить", command=self.reset_filters).pack(side="left", padx=5)
        for variable in (self.search_var, self.category_var, self.discount_var, self.sort_var):
            variable.trace_add("write", lambda *_: self.refresh_products())
        if role == "Администратор":
            tk.Button(bar, text="Удалить", command=self.delete_product).pack(side="right", padx=3)
            tk.Button(bar, text="Изменить", command=self.edit_product).pack(side="right", padx=3)
            tk.Button(bar, text="Добавить мебель", bg=TEAL, fg="white",
                      command=self.add_product).pack(side="right", padx=3)

    def reset_filters(self):
        self.search_var.set("")
        self.category_var.set("Все категории")
        self.discount_var.set("Все скидки")
        self.sort_var.set("По умолчанию")

    def _build_catalog(self):
        wrapper = tk.Frame(self, bg=BG)
        wrapper.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.card_canvas = tk.Canvas(wrapper, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=self.card_canvas.yview)
        self.card_canvas.configure(yscrollcommand=scrollbar.set)
        self.card_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.cards_frame = tk.Frame(self.card_canvas, bg=BG)
        self.cards_window = self.card_canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", lambda _e: self.card_canvas.configure(
            scrollregion=self.card_canvas.bbox("all")))
        self.card_canvas.bind("<Configure>", lambda event: self.card_canvas.itemconfigure(
            self.cards_window, width=event.width))
        self.card_canvas.bind_all("<MouseWheel>", self._scroll_cards)
        self.card_widgets = {}
        self.card_images = []
        self.selected_product_id = None

    def _scroll_cards(self, event):
        if hasattr(self, "card_canvas") and self.card_canvas.winfo_exists():
            self.card_canvas.yview_scroll(int(-event.delta / 120), "units")

    def refresh_products(self):
        if not hasattr(self, "cards_frame") or not self.cards_frame.winfo_exists():
            return
        manager = self.current_user["role"] in ("Менеджер", "Администратор")
        data = db.products(self.search_var.get() if manager else "",
                           self.category_var.get() if manager else "Все категории",
                           self.discount_var.get() if manager else "Все скидки",
                           self.sort_var.get() if manager else "По умолчанию")
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.card_images = []
        self.card_widgets = {}
        self.selected_product_id = None
        if not data:
            tk.Label(self.cards_frame, text="По выбранным условиям товары не найдены.",
                     bg=BG, fg=TEXT, pady=24).pack(fill="x")
            return
        for row in data:
            self._create_product_card(row)

    def _create_product_card(self, row):
        product_id = row["product_id"]
        zero_stock = row["stock"] == 0
        high_discount = row["discount"] > 15
        background = EMPTY if zero_stock else (TEAL if high_discount else "#F5F7F6")
        foreground = TEXT if zero_stock or not high_discount else "#FFFFFF"
        card = tk.Frame(self.cards_frame, bg=background, bd=2, relief="solid",
                        highlightthickness=0, padx=8, pady=7)
        card.pack(fill="x", padx=3, pady=4)
        self.card_widgets[product_id] = card

        photo_path = ROOT / (row["image_path"] or "import/picture.png")
        try:
            source = photo_path if photo_path.exists() else ROOT / "import" / "picture.png"
            if Image is not None:
                picture = Image.open(source).convert("RGB")
                picture.thumbnail((170, 118))
                photo = ImageTk.PhotoImage(picture)
            else:
                photo = tk.PhotoImage(file=source).subsample(2, 2)
            self.card_images.append(photo)
            photo_label = tk.Label(card, image=photo, bg=background, bd=0)
        except Exception:
            photo_label = tk.Label(card, text="Фото / picture.png", bg=background,
                                   fg=foreground, width=22, height=7)
        photo_label.pack(side="left", padx=(0, 12))

        info = tk.Frame(card, bg=background)
        info.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(info, text=f"{row['category']}  |  {row['name']}  |  {row['article']}",
                 bg=background, fg=foreground, font=("Arial", 12, "bold"),
                 anchor="w").pack(fill="x", anchor="w")
        tk.Label(info, text=row["description"] or "Описание не указано.",
                 bg=background, fg=foreground, justify="left", anchor="w",
                 wraplength=720).pack(fill="x", anchor="w", pady=(3, 2))
        tk.Label(info, text=f"Производитель: {row['manufacturer']}   ·   Поставщик: {row['supplier']}",
                 bg=background, fg=foreground, anchor="w").pack(fill="x", anchor="w")
        stock_text = row["stock_by_warehouse"] or "Остатки по складам не заведены"
        tk.Label(info, text=f"Единица: {row['unit']}   ·   Всего на складах: {row['stock']} {row['unit']}\n"
                            f"{stock_text}", bg=background, fg=foreground,
                 anchor="w", justify="left").pack(fill="x", anchor="w", pady=(2, 0))

        price_panel = tk.Frame(card, bg="#FFFFFF", padx=11, pady=8,
                               highlightbackground="#D0D9D7", highlightthickness=1)
        price_panel.pack(side="right", fill="y", padx=(10, 2))
        discount_text = f"Скидка {row['discount']:g}%" if row["discount"] else "Без скидки"
        tk.Label(price_panel, text=discount_text, bg="#FFFFFF",
                 fg=TEAL if high_discount else TEXT,
                 font=("Arial", 10, "bold")).pack(anchor="e", pady=(0, 5))
        if row["discount"] > 0:
            tk.Label(price_panel, text=f"{row['price']:.2f} ₽", bg="#FFFFFF",
                     fg="#C62828", font=("Arial", 10, "overstrike")).pack(anchor="e")
        else:
            tk.Label(price_panel, text=f"{row['price']:.2f} ₽", bg="#FFFFFF",
                     fg=TEXT, font=FONT).pack(anchor="e")
        tk.Label(price_panel, text=f"Итого: {row['final_price']:.2f} ₽", bg="#FFFFFF",
                 fg="#000000", font=("Arial", 11, "bold")).pack(anchor="e", pady=(3, 0))

        def select(_event=None, pid=product_id):
            self.select_product(pid)
        def bind_all(widget):
            widget.bind("<Button-1>", select, add="+")
            for child in widget.winfo_children():
                bind_all(child)
        bind_all(card)

    def select_product(self, product_id):
        previous = self.selected_product_id
        if previous in self.card_widgets:
            previous_row = db.product(previous)
            previous_color = EMPTY if previous_row["stock"] == 0 else (
                TEAL if previous_row["discount"] > 15 else "#F5F7F6")
            self.card_widgets[previous].configure(bg=previous_color, highlightthickness=0)
        self.selected_product_id = product_id
        if product_id in self.card_widgets:
            self.card_widgets[product_id].configure(highlightbackground="#172B2A",
                                                     highlightthickness=2)

    def add_product(self):
        self.product_form()

    def edit_product(self):
        product_id = self.selected_product_id
        if product_id is None:
            messagebox.showwarning("Выбор товара", "Сначала выберите карточку товара.", parent=self)
            return
        if self.current_user["role"] == "Администратор":
            self.product_form(product_id)

    def product_form(self, product_id=None):
        if self.edit_window and self.edit_window.winfo_exists():
            self.edit_window.lift()
            return
        old = db.product(product_id) if product_id else None
        window = tk.Toplevel(self)
        self.edit_window = window
        window.title("Изменение товара" if old else "Добавление товара")
        window.geometry("650x760")
        window.configure(bg=BG)
        window.transient(self)
        window.grab_set()
        controls, records_by_key = {}, {}
        definitions = [
            ("Артикул", "article", "entry"), ("Наименование", "name", "entry"),
            ("Категория", "category_id", "category"), ("Описание", "description", "text"),
            ("Производитель", "manufacturer_id", "manufacturer"),
            ("Поставщик", "supplier_id", "supplier"), ("Цена", "price", "entry"),
            ("Единица измерения", "unit_id", "unit"), ("Действующая скидка (%)", "discount", "entry"),
            ("Склад для изменения остатка", "warehouse_id", "warehouse"),
            ("Количество на выбранном складе", "quantity", "entry"),
        ]
        stock_rows = db.product_stocks(product_id) if old else []
        current_stock = {row["warehouse_id"]: row["quantity"] for row in stock_rows}
        row_num = 0
        for label, key, kind in definitions:
            tk.Label(window, text=label, bg=BG).grid(row=row_num, column=0, sticky="w", padx=14, pady=4)
            if kind == "entry":
                field = tk.Entry(window, width=45)
                default = "0" if key in ("discount", "quantity") else ""
                if key == "quantity" and old:
                    first_warehouse = db.choices("warehouse")
                    default = str(current_stock.get(first_warehouse[0]["id"], 0) if first_warehouse else 0)
                field.insert(0, str(old[key] if old and key in old.keys() else default))
            elif kind == "text":
                field = tk.Text(window, width=45, height=4, wrap="word")
                field.insert("1.0", old["description"] if old else "")
            else:
                records = db.choices(kind)
                records_by_key[key] = records
                field = ttk.Combobox(window, state="readonly", width=42,
                                     values=[item["label"] for item in records])
                old_key = key
                if kind == "category": old_key = "category_id"
                elif kind == "manufacturer": old_key = "manufacturer_id"
                elif kind == "supplier": old_key = "supplier_id"
                elif kind == "unit": old_key = "unit_id"
                elif kind == "warehouse": old_key = "warehouse_id"
                if records:
                    selected_id = old[old_key] if old and old_key in old.keys() else records[0]["id"]
                    index = next((i for i, item in enumerate(records) if item["id"] == selected_id), 0)
                    field.current(index)
                    if key == "quantity" and old:
                        field.insert(0, str(current_stock.get(selected_id, 0)))
            field.grid(row=row_num, column=1, sticky="ew", padx=8, pady=4)
            controls[key] = field
            row_num += 1
        # The inventory field follows the selected warehouse; refresh its quantity on selection.
        warehouse_combo = controls["warehouse_id"]
        quantity_field = controls["quantity"]
        def set_quantity(_event=None):
            index = warehouse_combo.current()
            records = records_by_key.get("warehouse_id", [])
            if index >= 0 and records:
                quantity_field.delete(0, "end")
                quantity_field.insert(0, str(current_stock.get(records[index]["id"], 0)))
        warehouse_combo.bind("<<ComboboxSelected>>", set_quantity)

        image_label = tk.Label(window, text="Фото не предоставлено — используется заглушка; можно выбрать своё.",
                               bg=BG, wraplength=560)
        image_label.grid(row=row_num, column=0, columnspan=2, sticky="w", padx=14, pady=7)
        image_source = {"path": None}
        def choose_image():
            filename = filedialog.askopenfilename(parent=window, title="Выберите фото мебели",
                filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp")])
            if filename:
                image_source["path"] = Path(filename)
                image_label.config(text=Path(filename).name)
        row_num += 1
        tk.Button(window, text="Выбрать фото…", command=choose_image).grid(
            row=row_num, column=0, sticky="w", padx=14, pady=5)
        tk.Label(window, text="При сохранении изображение приводится к 300 × 200 px.",
                 bg=BG).grid(row=row_num, column=1, sticky="w", padx=8)
        row_num += 1

        def save():
            try:
                text_value = lambda key: controls[key].get().strip()
                article, name = text_value("article"), text_value("name")
                if not article or not name:
                    raise ValueError("Заполните артикул и наименование.")
                price = float(text_value("price").replace(",", "."))
                discount = float(text_value("discount").replace(",", "."))
                quantity = int(text_value("quantity"))
                if price < 0 or quantity < 0 or not 0 <= discount <= 100:
                    raise ValueError("Цена и остаток неотрицательные; скидка от 0 до 100%.")
                values = {"article": article, "name": name,
                          "description": controls["description"].get("1.0", "end").strip(),
                          "price": price, "discount": discount, "quantity": quantity}
                for key in ("category_id", "manufacturer_id", "supplier_id", "unit_id", "warehouse_id"):
                    combo = controls[key]
                    index = combo.current()
                    if index < 0:
                        raise ValueError("Выберите категорию, производителя, поставщика, единицу и склад.")
                    values[key] = records_by_key[key][index]["id"]
                previous_image = old["image_path"] if old else None
                new_image = self.store_image(image_source["path"]) if image_source["path"] else None
                values["image_path"] = f"images/{new_image}" if new_image else previous_image
                try:
                    db.save_product(values, product_id)
                except Exception:
                    if new_image:
                        (ROOT / "images" / new_image).unlink(missing_ok=True)
                    raise
                if new_image and previous_image:
                    self.remove_unused_image(previous_image)
                window.destroy()
                self.edit_window = None
                self.refresh_products()
            except ValueError as error:
                messagebox.showerror("Проверьте данные", str(error), parent=window)
            except Exception as error:
                messagebox.showerror("Сохранение не выполнено", str(error), parent=window)
        tk.Button(window, text="Сохранить", bg=TEAL, fg="white", command=save).grid(
            row=row_num, column=1, sticky="e", padx=14, pady=12)
        window.protocol("WM_DELETE_WINDOW", lambda: (window.destroy(), setattr(self, "edit_window", None)))

    @staticmethod
    def store_image(source):
        if Image is None:
            raise ValueError("Для загрузки фото установите Pillow.")
        output = ROOT / "images"
        output.mkdir(exist_ok=True)
        filename = f"furniture_{uuid4().hex[:10]}.jpg"
        image = Image.open(source).convert("RGB")
        image.thumbnail((300, 200))
        canvas = Image.new("RGB", (300, 200), "white")
        canvas.paste(image, ((300-image.width)//2, (200-image.height)//2))
        canvas.save(output / filename, "JPEG", quality=88)
        return filename

    def remove_unused_image(self, relative_path):
        with db.connect() as connection:
            used = connection.execute("SELECT COUNT(*) FROM Product WHERE image_path=?",
                                      (relative_path,)).fetchone()[0]
        path = ROOT / relative_path
        if not used and path.exists():
            path.unlink()

    def delete_product(self):
        product_id = self.selected_product_id
        if product_id is None:
            messagebox.showwarning("Выбор товара", "Сначала выберите карточку мебели.", parent=self)
            return
        if not messagebox.askyesno("Удалить товар", "Удалить выбранную запись?", parent=self):
            return
        try:
            old = db.product(product_id)
            db.delete_product(product_id)
            if old["image_path"]:
                self.remove_unused_image(old["image_path"])
            self.refresh_products()
        except sqlite3.IntegrityError:
            messagebox.showerror("Удаление запрещено",
                "Этот товар присутствует в заказе. Сначала проверьте заказы.", parent=self)
        except Exception as error:
            messagebox.showerror("Ошибка удаления", str(error), parent=self)

    def open_orders(self):
        OrdersWindow(self)


class OrdersWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Заказы мебельного магазина")
        self.geometry("1120x520")
        self.configure(bg=BG)
        self.transient(parent)
        columns = ("id", "date", "delivery", "customer", "warehouse", "address", "status", "items")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        labels = ("№", "Дата заказа", "Дата доставки", "Клиент", "Склад", "Адрес доставки", "Статус", "Строк")
        widths = (55, 110, 110, 180, 150, 250, 110, 55)
        for col, label, width in zip(columns, labels, widths):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=10, pady=8)
        if parent.current_user["role"] == "Администратор":
            tk.Button(bar, text="Добавить заказ", command=self.add).pack(side="left", padx=3)
            tk.Button(bar, text="Изменить", command=self.edit).pack(side="left", padx=3)
            tk.Button(bar, text="Удалить", command=self.delete).pack(side="left", padx=3)
        tk.Button(bar, text="Закрыть", command=self.destroy).pack(side="right")
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for row in db.orders():
            self.tree.insert("", "end", iid=str(row["order_id"]), values=(
                row["order_id"], row["order_date"], row["delivery_date"], row["fio"],
                row["warehouse"], row["delivery_address"], row["status"], row["item_count"]))

    def selected_id(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Выбор заказа", "Выберите заказ.", parent=self)
            return None
        return int(selection[0])

    def add(self):
        OrderForm(self, None)

    def edit(self):
        order_id = self.selected_id()
        if order_id:
            OrderForm(self, order_id)

    def delete(self):
        order_id = self.selected_id()
        if order_id and messagebox.askyesno("Удаление заказа",
                f"Удалить заказ №{order_id} и его строки состава?", parent=self):
            db.delete_order(order_id)
            self.refresh()


class OrderForm(tk.Toplevel):
    def __init__(self, parent, order_id):
        super().__init__(parent)
        self.parent, self.order_id = parent, order_id
        old = db.order(order_id) if order_id else None
        self.title("Изменить заказ" if old else "Новый заказ")
        self.configure(bg=BG)
        self.transient(parent)
        self.controls, self.records = {}, {}
        definitions = [
            ("Дата заказа (ГГГГ-ММ-ДД)", "order_date", None),
            ("Дата доставки (ГГГГ-ММ-ДД)", "delivery_date", None),
            ("Клиент", "customer_id", "customer"),
            ("Склад отправки", "warehouse_id", "warehouse"),
            ("Адрес доставки", "delivery_address", None),
            ("Код заказа", "code", None),
            ("Статус", "status_id", "status"),
        ]
        for row_num, (label, key, source) in enumerate(definitions):
            tk.Label(self, text=label, bg=BG).grid(row=row_num, column=0, sticky="w", padx=12, pady=5)
            if source:
                records = db.choices(source)
                self.records[key] = records
                field = ttk.Combobox(self, state="readonly", width=48,
                                     values=[record["label"] for record in records])
                if records:
                    value = old[key] if old else records[0]["id"]
                    field.current(next((i for i, record in enumerate(records)
                                        if record["id"] == value), 0))
            else:
                field = tk.Entry(self, width=52)
                default = date.today().isoformat() if key == "order_date" else ""
                if key == "delivery_date" and not old:
                    default = date.today().isoformat()
                field.insert(0, str(old[key] if old else default))
            field.grid(row=row_num, column=1, padx=8, pady=5)
            self.controls[key] = field
        tk.Label(self, text="Состав: артикул:количество, через запятую", bg=BG).grid(
            row=len(definitions), column=0, sticky="w", padx=12, pady=5)
        self.items_entry = tk.Entry(self, width=52)
        if old:
            self.items_entry.insert(0, ", ".join(f"{r['article']}:{r['quantity']}"
                                                  for r in db.order_items(order_id)))
        self.items_entry.grid(row=len(definitions), column=1, padx=8, pady=5)
        tk.Label(self, text="Пример: MF-001:1, MF-007:2", fg="#53615E", bg=BG).grid(
            row=len(definitions)+1, column=1, sticky="w", padx=8)
        tk.Button(self, text="Сохранить", bg=TEAL, fg="white", command=self.save).grid(
            row=len(definitions)+2, column=1, sticky="e", padx=12, pady=12)

    def save(self):
        try:
            values = {}
            for key in ("order_date", "delivery_date"):
                values[key] = self.controls[key].get().strip()
                date.fromisoformat(values[key])
            if date.fromisoformat(values["delivery_date"]) < date.fromisoformat(values["order_date"]):
                raise ValueError("Дата доставки не может быть раньше даты заказа.")
            values["delivery_address"] = self.controls["delivery_address"].get().strip()
            values["code"] = self.controls["code"].get().strip()
            if not values["code"] or not values["delivery_address"]:
                raise ValueError("Укажите адрес доставки и код заказа.")
            for key, records in self.records.items():
                index = self.controls[key].current()
                if index < 0:
                    raise ValueError("Выберите клиента, склад и статус.")
                values[key] = records[index]["id"]
            raw_items = self.items_entry.get().strip()
            items = []
            for part in raw_items.split(","):
                if not part.strip():
                    continue
                article, separator, quantity = part.strip().partition(":")
                if not separator or not article.strip():
                    raise ValueError("Состав вводите как MF-001:1, MF-007:2.")
                quantity = int(quantity.strip())
                if quantity <= 0:
                    raise ValueError("Количество товара в заказе должно быть больше нуля.")
                items.append((article.strip(), quantity))
            if not items:
                raise ValueError("Добавьте в заказ хотя бы одну позицию.")
            db.save_order(values, items, self.order_id)
            self.parent.refresh()
            self.destroy()
        except ValueError as error:
            messagebox.showerror("Проверьте заказ", str(error), parent=self)
        except Exception as error:
            messagebox.showerror("Заказ не сохранён", str(error), parent=self)


def main():
    try:
        db.initialize()
    except Exception as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Не удалось запустить приложение",
            f"Проверьте файл import/Furniture_demo_import.xlsx и библиотеки проекта.\n\n{error}")
        root.destroy()
        return
    App().mainloop()


if __name__ == "__main__":
    main()
