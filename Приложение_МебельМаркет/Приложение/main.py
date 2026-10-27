"""Учебное приложение мебельного магазина. Требуются Windows, Access и pyodbc."""
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import pyodbc

PROJECT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT / "БД" / "МебельМаркет.accdb"
ACCESS_DRIVER = "Microsoft Access Driver (*.mdb, *.accdb)"
STATUSES = ("Новый", "Собирается", "В пути", "Доставлен", "Отменён")


def db_connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Не найдена база данных: {DB_PATH}\nСначала создайте её согласно инструкции.")
    if ACCESS_DRIVER not in pyodbc.drivers():
        raise RuntimeError("Не найден Microsoft Access ODBC Driver. Установите Access Database Engine той же разрядности, что и Python.")
    return pyodbc.connect(f"DRIVER={{{ACCESS_DRIVER}}};DBQ={DB_PATH};", autocommit=False)


def hash_password(value):
    return sha256(value.encode("utf-8")).hexdigest()


class FurnitureApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("МебельМаркет — магазин мебели")
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.configure(bg="#f4f6f5")
        self.user = None
        self.products = []
        self.cart = {}
        self.warehouses = []
        self._style()
        self._build_header()
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=22, pady=(4, 18))
        self.catalog_tab = ttk.Frame(self.tabs, padding=16)
        self.cart_tab = ttk.Frame(self.tabs, padding=16)
        self.orders_tab = ttk.Frame(self.tabs, padding=16)
        self.tabs.add(self.catalog_tab, text="Каталог")
        self.tabs.add(self.cart_tab, text="Корзина")
        self.tabs.add(self.orders_tab, text="Мои заказы")
        self._build_catalog()
        self._build_cart()
        self._build_orders()
        self._refresh_catalog()
        self._refresh_warehouses()
        self._update_session()
        self.after(120, self._auth_dialog)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#ffffff")
        style.configure("TLabel", background="#ffffff", foreground="#25332f", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 19, "bold"), foreground="#0d5957")
        style.configure("Sub.TLabel", foreground="#65716d")
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7))
        style.configure("Accent.TButton", background="#087f78", foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#06655f")])
        style.configure("Treeview", rowheight=29, font=("Segoe UI", 10), background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e8f1ef")

    def _build_header(self):
        head = tk.Frame(self, bg="#ffffff", padx=24, pady=14)
        head.pack(fill="x", padx=22, pady=(18, 0))
        tk.Label(head, text="МЕБЕЛЬМАРКЕТ", bg="white", fg="#087f78", font=("Segoe UI", 19, "bold")).pack(side="left")
        self.session_label = tk.Label(head, text="Вы вошли как гость", bg="white", fg="#65716d", font=("Segoe UI", 10))
        self.session_label.pack(side="right", padx=(10, 0))
        self.auth_button = ttk.Button(head, text="Войти", command=self._auth_dialog)
        self.auth_button.pack(side="right")
        self.message_label = tk.Label(self, text="", bg="#f4f6f5", fg="#61716c", font=("Segoe UI", 9))
        self.message_label.pack(fill="x", padx=26, pady=(7, 0))

    def _build_catalog(self):
        bar = ttk.Frame(self.catalog_tab)
        bar.pack(fill="x", pady=(0, 12))
        ttk.Label(bar, text="Мебель для дома", style="Title.TLabel").pack(side="left")
        self.staff_controls = ttk.Frame(bar)
        self.filter_var = tk.StringVar(value="Все категории")
        self.filter_box = ttk.Combobox(self.staff_controls, textvariable=self.filter_var, values=("Все категории",), state="readonly", width=18)
        self.filter_box.pack(side="right", padx=(8, 0))
        self.filter_box.bind("<<ComboboxSelected>>", lambda _event: self._fill_catalog())
        self.search_var = tk.StringVar()
        ttk.Label(self.staff_controls, text="Поиск:").pack(side="right", padx=(8, 0))
        self.search_entry = ttk.Entry(self.staff_controls, textvariable=self.search_var, width=24)
        self.search_entry.pack(side="right", padx=(8, 0))
        self.search_var.trace_add("write", lambda *_: self._fill_catalog())
        self.sort_var = tk.StringVar(value="По названию")
        self.sort_box = ttk.Combobox(self.staff_controls, textvariable=self.sort_var,
            values=("По названию", "Цена: по возрастанию", "Цена: по убыванию", "Остаток: по убыванию"),
            state="readonly", width=25)
        self.sort_box.pack(side="right", padx=(8, 12))
        self.sort_box.bind("<<ComboboxSelected>>", lambda _event: self._fill_catalog())
        self.catalog_canvas = tk.Canvas(self.catalog_tab, bg="#f4f6f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.catalog_tab, orient="vertical", command=self.catalog_canvas.yview)
        self.catalog_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.catalog_canvas.pack(side="left", fill="both", expand=True)
        self.products_frame = tk.Frame(self.catalog_canvas, bg="#f4f6f5")
        self.products_window = self.catalog_canvas.create_window((0, 0), window=self.products_frame, anchor="nw")
        self.products_frame.bind("<Configure>", lambda _e: self.catalog_canvas.configure(scrollregion=self.catalog_canvas.bbox("all")))
        self.catalog_canvas.bind("<Configure>", lambda e: self.catalog_canvas.itemconfigure(self.products_window, width=e.width))
        buttons = ttk.Frame(self.catalog_tab, padding=(0, 10, 0, 0))
        buttons.pack(fill="x")
        self.add_cart_button = ttk.Button(buttons, text="Добавить выбранное в корзину", style="Accent.TButton", command=self._add_to_cart)
        self.add_cart_button.pack(side="right")
        self.product_admin_buttons = ttk.Frame(buttons)
        self.product_admin_buttons.pack(side="left")
        ttk.Button(self.product_admin_buttons, text="Добавить товар", command=lambda: self._product_form()).pack(side="left", padx=(0, 6))
        ttk.Button(self.product_admin_buttons, text="Изменить товар", command=self._edit_selected_product).pack(side="left", padx=6)
        ttk.Button(self.product_admin_buttons, text="Удалить товар", command=self._delete_product).pack(side="left", padx=6)
        self.selected_product_id = None

    def _build_cart(self):
        ttk.Label(self.cart_tab, text="Ваша корзина", style="Title.TLabel").pack(anchor="w", pady=(0, 12))
        cols = ("name", "quantity", "price", "sum")
        self.cart_tree = ttk.Treeview(self.cart_tab, columns=cols, show="headings", height=10)
        for col, label, width in [("name", "Товар", 500), ("quantity", "Количество", 120), ("price", "Цена, ₽", 150), ("sum", "Сумма, ₽", 160)]:
            self.cart_tree.heading(col, text=label)
            self.cart_tree.column(col, width=width, anchor="w" if col == "name" else "center")
        self.cart_tree.pack(fill="both", expand=True)
        controls = ttk.Frame(self.cart_tab, padding=(0, 12))
        controls.pack(fill="x")
        ttk.Button(controls, text="Удалить выбранный товар", command=self._remove_from_cart).pack(side="left")
        self.total_label = ttk.Label(controls, text="Итого: 0 ₽", style="Title.TLabel")
        self.total_label.pack(side="right")
        form = ttk.LabelFrame(self.cart_tab, text="Оформление заказа", padding=14)
        form.pack(fill="x", pady=(6, 0))
        ttk.Label(form, text="Склад:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        self.warehouse_var = tk.StringVar()
        self.warehouse_box = ttk.Combobox(form, textvariable=self.warehouse_var, state="readonly", width=28)
        self.warehouse_box.grid(row=0, column=1, sticky="w", pady=5)
        ttk.Label(form, text="Дата доставки (ГГГГ-ММ-ДД):").grid(row=0, column=2, sticky="w", padx=(24, 8), pady=5)
        self.delivery_var = tk.StringVar(value=(date.today() + timedelta(days=5)).isoformat())
        ttk.Entry(form, textvariable=self.delivery_var, width=16).grid(row=0, column=3, sticky="w", pady=5)
        ttk.Label(form, text="Адрес доставки:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=5)
        self.address_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.address_var, width=60).grid(row=1, column=1, columnspan=2, sticky="ew", pady=5)
        ttk.Button(form, text="Оформить заказ", style="Accent.TButton", command=self._place_order).grid(row=1, column=3, sticky="e", pady=5)
        form.columnconfigure(2, weight=1)
        ttk.Label(self.cart_tab, text="Для оформления нужно войти или зарегистрироваться. Демо-данные условные.", style="Sub.TLabel").pack(anchor="w", pady=(8, 0))

    def _build_orders(self):
        ttk.Label(self.orders_tab, text="История заказов", style="Title.TLabel").pack(anchor="w", pady=(0, 12))
        cols = ("code", "created", "delivery", "status", "address")
        self.orders_tree = ttk.Treeview(self.orders_tab, columns=cols, show="headings")
        for col, label, width in [("code", "Код", 110), ("created", "Дата заказа", 145), ("delivery", "Доставка", 145), ("status", "Статус", 150), ("address", "Адрес", 430)]:
            self.orders_tree.heading(col, text=label)
            self.orders_tree.column(col, width=width, anchor="w")
        self.orders_tree.pack(fill="both", expand=True)
        self.orders_note = ttk.Label(self.orders_tab, text="Войдите как клиент, чтобы увидеть заказы.", style="Sub.TLabel")
        self.orders_note.pack(anchor="w", pady=(10, 0))
        self.admin_frame = ttk.LabelFrame(self.orders_tab, text="Управление заказами (администратор)", padding=10)
        ttk.Button(self.admin_frame, text="Добавить заказ", command=lambda: self._order_form()).pack(side="left", padx=4)
        ttk.Button(self.admin_frame, text="Изменить выбранный", command=self._edit_selected_order).pack(side="left", padx=4)
        ttk.Button(self.admin_frame, text="Удалить выбранный", command=self._delete_order).pack(side="left", padx=4)
        ttk.Button(self.admin_frame, text="Обновить", command=self._refresh_orders).pack(side="right")

    def _refresh_catalog(self):
        try:
            cn = db_connect()
            cursor = cn.cursor()
            rows = cursor.execute("SELECT * FROM [Запрос_КаталогМебели] ORDER BY [Наименование]").fetchall()
            stock_rows = cursor.execute("SELECT [КодТовара], [Склад], [Количество] FROM [Запрос_ОстаткиПоСкладам]").fetchall()
            cn.close()
            stock_map = {}
            for product_id, warehouse_name, quantity in stock_rows:
                stock_map.setdefault(product_id, []).append((warehouse_name, int(quantity)))
            self.products = []
            for row in rows:
                self.products.append({
                    "id": row[0], "sku": row[1], "name": row[2], "category_id": row[3], "category": row[4],
                    "description": row[5] or "", "manufacturer_id": row[6], "manufacturer": row[7],
                    "supplier_id": row[8], "supplier": row[9], "price": float(row[10]), "unit": row[11],
                    "discount": float(row[12]), "photo": row[13], "stock": int(row[14] or 0),
                    "final_price": float(row[15]), "stocks": stock_map.get(row[0], []),
                })
            categories = ["Все категории"] + sorted({item["category"] for item in self.products}, key=str.casefold)
            self.filter_box["values"] = categories
            if self.filter_var.get() not in categories:
                self.filter_var.set("Все категории")
            self._fill_catalog()
            self.message_label.configure(text=f"Товаров в каталоге: {len(self.products)}")
        except Exception as exc:
            messagebox.showerror("Не удалось открыть базу", str(exc))
            self.message_label.configure(text="Проверьте путь к .accdb, установленный ODBC-драйвер и выполнение модуля Access.")

    def _fill_catalog(self):
        if not hasattr(self, "products_frame"):
            return
        for widget in self.products_frame.winfo_children():
            widget.destroy()
        query = self.search_var.get().strip().casefold()
        staff = bool(self.user and self.user["role"] in ("Менеджер", "Администратор"))
        visible = list(self.products)
        category_filter = self.filter_var.get() if staff else "Все категории"
        if staff and category_filter != "Все категории":
            visible = [item for item in visible if item["category"] == category_filter]
        if staff and query:
            visible = [item for item in visible if query in " ".join((item["sku"], item["name"], item["category"], item["manufacturer"], item["supplier"])).casefold()]
        sort_key = self.sort_var.get() if staff else "По названию"
        if sort_key == "Цена: по возрастанию":
            visible.sort(key=lambda item: item["final_price"])
        elif sort_key == "Цена: по убыванию":
            visible.sort(key=lambda item: item["final_price"], reverse=True)
        elif sort_key == "Остаток: по убыванию":
            visible.sort(key=lambda item: item["stock"], reverse=True)
        else:
            visible.sort(key=lambda item: item["name"].casefold())
        self._photo_refs = []
        for item in visible:
            self._make_product_card(item)
        self.products_frame.update_idletasks()
        self.catalog_canvas.configure(scrollregion=self.catalog_canvas.bbox("all"))

    def _make_product_card(self, item):
        if item["stock"] <= 0:
            background, foreground = "#dedede", "#6d7371"
        elif item["discount"] > 15:
            background, foreground = "#008080", "#ffffff"
        else:
            background, foreground = "#ffffff", "#263a36"
        card = tk.Frame(self.products_frame, bg=background, highlightbackground="#d3dfdc", highlightthickness=1, padx=10, pady=8)
        card.pack(fill="x", padx=4, pady=4)
        card.columnconfigure(1, weight=1)
        image_label = tk.Label(card, bg=background)
        image_label.grid(row=0, column=0, rowspan=5, padx=(0, 14), sticky="ns")
        try:
            from PIL import Image, ImageTk
            photo_path = Path(item["photo"]) if item["photo"] else None
            candidates = []
            if photo_path:
                candidates.extend([photo_path, PROJECT / photo_path, Path(__file__).parent / photo_path])
            candidates.append(Path(__file__).parent / "images" / "picture.png")
            selected = next((path for path in candidates if path and path.exists()), candidates[-1])
            image = Image.open(selected).convert("RGB")
            image.thumbnail((155, 120))
            image_obj = ImageTk.PhotoImage(image)
            self._photo_refs.append(image_obj)
            image_label.configure(image=image_obj, width=155, height=120)
        except Exception:
            image_label.configure(text="Фото недоступно", width=20, height=7, fg=foreground)

        title = tk.Label(card, text=f"{item['category']} | {item['name']}", bg=background, fg=foreground,
                         font=("Segoe UI", 12, "bold"), anchor="w")
        title.grid(row=0, column=1, sticky="ew")
        details = [f"Описание: {item['description'] or '—'}",
                   f"Производитель: {item['manufacturer']}    Поставщик: {item['supplier']}",
                   f"Единица измерения: {item['unit']}",
                   "Количество на складе: " + ("; ".join(f"{name}: {count}" for name, count in item["stocks"]) or "нет записей")]
        for index, text in enumerate(details, start=1):
            tk.Label(card, text=text, bg=background, fg=foreground, font=("Segoe UI", 9), anchor="w", justify="left", wraplength=620).grid(row=index, column=1, sticky="ew", pady=1)
        price_frame = tk.Frame(card, bg=background)
        price_frame.grid(row=0, column=2, rowspan=5, padx=(16, 5), sticky="ns")
        if item["discount"] > 0:
            tk.Label(price_frame, text=f"{item['price']:,.2f} ₽", bg=background, fg="#c43d3d",
                     font=("Segoe UI", 10, "overstrike")).pack(pady=(3, 0))
        tk.Label(price_frame, text=f"{item['final_price']:,.2f} ₽", bg=background, fg="#000000" if item["discount"] > 0 else foreground,
                 font=("Segoe UI", 12, "bold")).pack(pady=3)
        tk.Label(price_frame, text=f"Скидка: {item['discount']:g}%", bg=background, fg=foreground,
                 font=("Segoe UI", 9, "bold")).pack(pady=2)
        if item["stock"] <= 0:
            tk.Label(price_frame, text="Нет на складе", bg=background, fg=foreground, font=("Segoe UI", 9)).pack(pady=2)
        elif self.user and self.user["role"] == "Авторизованный клиент":
            ttk.Button(price_frame, text="В корзину", command=lambda product_id=item["id"]: self._add_to_cart(product_id)).pack(pady=4)
        def bind_selection(widget):
            if not isinstance(widget, ttk.Button):
                widget.bind("<Button-1>", lambda _event, product_id=item["id"]: self._select_product(product_id))
            for child in widget.winfo_children():
                bind_selection(child)
        bind_selection(card)

    def _select_product(self, product_id):
        self.selected_product_id = product_id

    def _product_by_id(self, product_id):
        return next(item for item in self.products if item["id"] == product_id)

    def _add_to_cart(self, product_id=None):
        if not self.user or self.user["role"] != "Авторизованный клиент":
            messagebox.showinfo("Корзина", "Войти как клиент можно через кнопку «Войти / выйти».")
            return
        if product_id is None:
            product_id = self.selected_product_id
        if product_id is None:
            messagebox.showinfo("Корзина", "Выберите товар.")
            return
        item = self._product_by_id(product_id)
        if item["stock"] <= 0:
            messagebox.showwarning("Корзина", "Товара нет на складе.")
            return
        quantity = simpledialog.askinteger("Количество", f"Сколько единиц добавить?\nВсего на складах: {item['stock']}", minvalue=1, maxvalue=999, parent=self)
        if quantity:
            self.cart[item["id"]] = self.cart.get(item["id"], 0) + quantity
            self._refresh_cart()
            self.tabs.select(self.cart_tab)

    def _refresh_cart(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        total = 0
        for product_id, quantity in self.cart.items():
            item = self._product_by_id(product_id)
            subtotal = item["final_price"] * quantity
            total += subtotal
            self.cart_tree.insert("", "end", iid=str(product_id), values=(item["name"], quantity, f"{item['final_price']:,.2f}", f"{subtotal:,.2f}"))
        self.total_label.configure(text=f"Итого: {total:,.2f} ₽")

    def _remove_from_cart(self):
        selected = self.cart_tree.selection()
        if selected:
            self.cart.pop(int(selected[0]), None)
            self._refresh_cart()

    def _refresh_warehouses(self):
        try:
            cn = db_connect()
            self.warehouses = cn.cursor().execute("SELECT [КодСклада], [Название] FROM [Склады] ORDER BY [Название]").fetchall()
            cn.close()
            self.warehouse_box["values"] = [row[1] for row in self.warehouses]
            if self.warehouses and not self.warehouse_var.get():
                self.warehouse_var.set(self.warehouses[0][1])
        except Exception:
            pass

    def _auth_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Вход в МебельМаркет")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Войти в аккаунт", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(frame, text="Логин:").grid(row=1, column=0, sticky="w", pady=5)
        login_var = tk.StringVar()
        ttk.Entry(frame, textvariable=login_var, width=32).grid(row=1, column=1, pady=5)
        ttk.Label(frame, text="Пароль:").grid(row=2, column=0, sticky="w", pady=5)
        password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=password_var, show="•", width=32).grid(row=2, column=1, pady=5)
        ttk.Label(frame, text="ФИО (для регистрации):").grid(row=3, column=0, sticky="w", pady=5)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=32).grid(row=3, column=1, pady=5)
        ttk.Label(frame, text="Телефон:").grid(row=4, column=0, sticky="w", pady=5)
        phone_var = tk.StringVar()
        ttk.Entry(frame, textvariable=phone_var, width=32).grid(row=4, column=1, pady=5)

        def login():
            try:
                cn = db_connect()
                cursor = cn.cursor()
                row = cursor.execute("SELECT [Пользователи].[КодПользователя], [Пользователи].[ФИО], [Пользователи].[Логин], [Пользователи].[Пароль], [Роли].[Название], [Пользователи].[КодПокупателя] FROM [Пользователи] INNER JOIN [Роли] ON [Пользователи].[КодРоли]=[Роли].[КодРоли] WHERE [Логин]=?", login_var.get().strip()).fetchone()
                if not row or row[3] not in (hash_password(password_var.get()), password_var.get()):
                    cn.close()
                    messagebox.showerror("Вход", "Неверный логин или пароль.", parent=dialog)
                    return
                if row[3] == password_var.get():
                    cursor.execute("UPDATE [Пользователи] SET [Пароль]=? WHERE [КодПользователя]=?", hash_password(password_var.get()), row[0])
                    cn.commit()
                cn.close()
                self.user = {"id": row[0], "name": row[1], "login": row[2], "role": row[4], "customer_id": row[5]}
                dialog.destroy()
                self._update_session()
            except Exception as exc:
                messagebox.showerror("Вход", str(exc), parent=dialog)

        def register():
            login_text, password, name = login_var.get().strip(), password_var.get(), name_var.get().strip()
            if not login_text or len(password) < 6 or not name:
                messagebox.showwarning("Регистрация", "Укажите логин, ФИО и пароль длиной не менее 6 символов.", parent=dialog)
                return
            try:
                cn = db_connect()
                cursor = cn.cursor()
                role = cursor.execute("SELECT [КодРоли] FROM [Роли] WHERE [Название]='Авторизованный клиент'").fetchone()
                if not role:
                    raise RuntimeError("Роль клиента отсутствует. Сначала выполните импорт демонстрационных данных.")
                cursor.execute("INSERT INTO [Пользователи] ([КодРоли], [ФИО], [Логин], [Пароль]) VALUES (?, ?, ?, ?)", role[0], name, login_text, hash_password(password))
                cn.commit()
                customer_id = self._ensure_customer(name, phone_var.get().strip(), "")
                link = db_connect()
                link.cursor().execute("UPDATE [Пользователи] SET [КодПокупателя]=? WHERE [Логин]=?", customer_id, login_text)
                link.commit()
                link.close()
                self.user = {"id": None, "name": name, "login": login_text, "role": "Авторизованный клиент", "customer_id": customer_id}
                dialog.destroy()
                self._update_session()
            except Exception as exc:
                try:
                    cn.rollback()
                    cn.close()
                except Exception:
                    pass
                messagebox.showerror("Регистрация", f"Не удалось зарегистрировать пользователя. Возможно, логин уже занят.\n{exc}", parent=dialog)

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Как гость", command=lambda: (dialog.destroy(), self._update_session())).pack(side="left", padx=5)
        ttk.Button(buttons, text="Войти", command=login).pack(side="left", padx=5)
        ttk.Button(buttons, text="Зарегистрироваться", style="Accent.TButton", command=register).pack(side="left", padx=5)

    def _ensure_customer(self, full_name, phone, address):
        cn = db_connect()
        cursor = cn.cursor()
        row = cursor.execute("SELECT [КодПокупателя] FROM [Покупатели] WHERE [ФИО]=?", full_name).fetchone()
        if row:
            if phone or address:
                cursor.execute("UPDATE [Покупатели] SET [Телефон]=?, [Адрес]=? WHERE [КодПокупателя]=?", phone, address, row[0])
            customer_id = row[0]
        else:
            cursor.execute("INSERT INTO [Покупатели] ([ФИО], [Телефон], [Адрес]) VALUES (?, ?, ?)", full_name, phone, address)
            cursor.execute("SELECT @@IDENTITY")
            customer_id = cursor.fetchone()[0]
        cn.commit()
        cn.close()
        return customer_id

    def _logout(self):
        self.user = None
        self.cart.clear()
        self._refresh_cart()
        self._update_session()
        self.after(80, self._auth_dialog)

    def _update_session(self):
        role = self.user["role"] if self.user else "Гость"
        if self.user:
            self.session_label.configure(text=f"{self.user['name']} · {role}")
            self.auth_button.configure(text="Выйти", command=self._logout)
        else:
            self.session_label.configure(text="Режим гостя")
            self.auth_button.configure(text="Войти", command=self._auth_dialog)
        staff = role in ("Менеджер", "Администратор")
        if staff:
            self.staff_controls.pack(side="right")
        else:
            self.staff_controls.pack_forget()
            self.search_var.set("")
            self.filter_var.set("Все категории")
            self.sort_var.set("По названию")
        if role == "Администратор":
            self.product_admin_buttons.pack(side="left")
        else:
            self.product_admin_buttons.pack_forget()
        if role == "Авторизованный клиент":
            self.add_cart_button.pack(side="right")
        else:
            self.add_cart_button.pack_forget()
        self.tabs.tab(self.cart_tab, state="normal" if role == "Авторизованный клиент" else "disabled")
        self.tabs.tab(self.orders_tab, state="normal" if role in ("Авторизованный клиент", "Менеджер", "Администратор") else "disabled")
        if role == "Администратор":
            self.admin_frame.pack(fill="x", pady=(14, 0))
        else:
            self.admin_frame.pack_forget()
        if hasattr(self, "orders_note"):
            self._refresh_orders()
        self._fill_catalog()

    def _place_order(self):
        if not self.user or self.user["role"] != "Авторизованный клиент":
            messagebox.showinfo("Оформление", "Войдите как клиент или зарегистрируйтесь.")
            self._auth_dialog()
            return
        if not self.cart:
            messagebox.showinfo("Оформление", "Корзина пуста.")
            return
        address = self.address_var.get().strip()
        if not address:
            messagebox.showwarning("Оформление", "Введите адрес доставки.")
            return
        try:
            delivery = date.fromisoformat(self.delivery_var.get().strip())
            if delivery < date.today():
                raise ValueError("Дата доставки не может быть в прошлом.")
            warehouse = next((row[0] for row in self.warehouses if row[1] == self.warehouse_var.get()), None)
            if warehouse is None:
                raise ValueError("Выберите склад.")
            cn = db_connect()
            cursor = cn.cursor()
            for product_id, quantity in self.cart.items():
                stock = cursor.execute("SELECT [Количество] FROM [Остатки] WHERE [КодТовара]=? AND [КодСклада]=?", product_id, warehouse).fetchone()
                available = stock[0] if stock else 0
                if quantity > available:
                    item = self._product_by_id(product_id)
                    raise ValueError(f"Недостаточно товара «{item['name']}» на выбранном складе. Остаток: {available}.")
            customer_id = self.user.get("customer_id")
            if not customer_id:
                raise RuntimeError("Профиль покупателя не связан с аккаунтом. Выйдите и войдите снова или создайте аккаунт заново.")
            cursor.execute("UPDATE [Покупатели] SET [Адрес]=? WHERE [КодПокупателя]=?", address, customer_id)
            cursor.execute("INSERT INTO [Заказы] ([ДатаЗаказа], [ДатаДоставки], [КодПокупателя], [КодСклада], [АдресДоставки], [КодПолучения], [Статус]) VALUES (?, ?, ?, ?, ?, ?, ?)", date.today(), delivery, customer_id, warehouse, address, "", "Новый")
            cursor.execute("SELECT @@IDENTITY")
            order_id = cursor.fetchone()[0]
            for product_id, quantity in self.cart.items():
                item = self._product_by_id(product_id)
                cursor.execute("INSERT INTO [СоставЗаказа] ([КодЗаказа], [КодТовара], [Количество], [ЦенаНаМоментЗаказа]) VALUES (?, ?, ?, ?)", order_id, product_id, quantity, item["final_price"])
                cursor.execute("UPDATE [Остатки] SET [Количество]=[Количество]-? WHERE [КодТовара]=? AND [КодСклада]=?", quantity, product_id, warehouse)
            cn.commit()
            cn.close()
            self.cart.clear()
            self._refresh_cart()
            self._refresh_catalog()
            self._refresh_orders()
            messagebox.showinfo("Заказ создан", f"Ваш заказ №{order_id} оформлен. Статус: Новый.")
            self.tabs.select(self.orders_tab)
        except Exception as exc:
            try:
                cn.rollback()
                cn.close()
            except Exception:
                pass
            messagebox.showerror("Не удалось оформить заказ", str(exc))

    def _product_form(self, product_id=None):
        if not self.user or self.user["role"] != "Администратор":
            return
        item = self._product_by_id(product_id) if product_id else None
        dialog = tk.Toplevel(self)
        dialog.title("Изменение товара" if item else "Новый товар")
        dialog.transient(self)
        dialog.grab_set()
        form = ttk.Frame(dialog, padding=18)
        form.pack(fill="both", expand=True)
        values = {
            "Артикул": tk.StringVar(value=item["sku"] if item else ""),
            "Наименование": tk.StringVar(value=item["name"] if item else ""),
            "Категория": tk.StringVar(value=item["category"] if item else ""),
            "Производитель": tk.StringVar(value=item["manufacturer"] if item else ""),
            "Поставщик": tk.StringVar(value=item["supplier"] if item else ""),
            "Цена": tk.StringVar(value=str(item["price"]) if item else "0"),
            "Единица": tk.StringVar(value=item["unit"] if item else "шт."),
            "Скидка": tk.StringVar(value=str(item["discount"]) if item else "0"),
            "Фото": tk.StringVar(value=item["photo"] or "" if item else ""),
            "Описание": tk.StringVar(value=item["description"] if item else ""),
        }
        try:
            cn = db_connect()
            cursor = cn.cursor()
            refs = {
                "Категория": cursor.execute("SELECT [КодКатегории], [Название] FROM [Категории] ORDER BY [Название]").fetchall(),
                "Производитель": cursor.execute("SELECT [КодПроизводителя], [Название] FROM [Производители] ORDER BY [Название]").fetchall(),
                "Поставщик": cursor.execute("SELECT [КодПоставщика], [Название] FROM [Поставщики] ORDER BY [Название]").fetchall(),
            }
            cn.close()
        except Exception as exc:
            messagebox.showerror("Товар", str(exc), parent=dialog)
            dialog.destroy()
            return
        combo_names = {"Категория": "Категория", "Производитель": "Производитель", "Поставщик": "Поставщик"}
        widgets = {}
        for row_number, (label, variable) in enumerate(values.items()):
            ttk.Label(form, text=label + ":").grid(row=row_number, column=0, sticky="w", padx=(0, 12), pady=5)
            if label in combo_names:
                widget = ttk.Combobox(form, textvariable=variable, state="readonly", width=45,
                                      values=[row[1] for row in refs[label]])
            elif label == "Описание":
                widget = ttk.Entry(form, textvariable=variable, width=48)
            else:
                widget = ttk.Entry(form, textvariable=variable, width=48)
            widget.grid(row=row_number, column=1, sticky="ew", pady=5)
            widgets[label] = widget
        form.columnconfigure(1, weight=1)

        def save():
            try:
                if not values["Артикул"].get().strip() or not values["Наименование"].get().strip():
                    raise ValueError("Заполните артикул и наименование.")
                price = float(values["Цена"].get().replace(",", "."))
                discount = float(values["Скидка"].get().replace(",", "."))
                if price < 0 or not 0 <= discount <= 100:
                    raise ValueError("Цена должна быть неотрицательной, скидка — от 0 до 100.")
                lookup = {}
                for key in refs:
                    match = next((ref[0] for ref in refs[key] if ref[1] == values[key].get()), None)
                    if match is None:
                        raise ValueError(f"Выберите {key.lower()} из списка.")
                    lookup[key] = match
                cn = db_connect()
                cursor = cn.cursor()
                args = (values["Артикул"].get().strip(), values["Наименование"].get().strip(), lookup["Категория"],
                        values["Описание"].get().strip(), lookup["Производитель"], lookup["Поставщик"], price,
                        values["Единица"].get().strip() or "шт.", discount, values["Фото"].get().strip() or None)
                if item:
                    cursor.execute("UPDATE [Товары] SET [Артикул]=?, [Наименование]=?, [КодКатегории]=?, [Описание]=?, [КодПроизводителя]=?, [КодПоставщика]=?, [Цена]=?, [Единица]=?, [Скидка]=?, [Фото]=? WHERE [КодТовара]=?", *args, item["id"])
                else:
                    cursor.execute("INSERT INTO [Товары] ([Артикул], [Наименование], [КодКатегории], [Описание], [КодПроизводителя], [КодПоставщика], [Цена], [Единица], [Скидка], [Фото]) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", *args)
                cn.commit()
                cn.close()
                dialog.destroy()
                self._refresh_catalog()
            except Exception as exc:
                messagebox.showerror("Товар не сохранён", str(exc), parent=dialog)

        ttk.Button(form, text="Сохранить", style="Accent.TButton", command=save).grid(row=len(values), column=1, sticky="e", pady=(12, 0))

    def _edit_selected_product(self):
        if self.selected_product_id is None:
            messagebox.showinfo("Товар", "Щёлкните по карточке товара, которую нужно изменить.")
            return
        self._product_form(self.selected_product_id)

    def _delete_product(self):
        if not self.user or self.user["role"] != "Администратор":
            return
        if self.selected_product_id is None:
            messagebox.showinfo("Товар", "Щёлкните по карточке товара, которую нужно удалить.")
            return
        item = self._product_by_id(self.selected_product_id)
        if not messagebox.askyesno("Удаление товара", f"Удалить товар «{item['name']}»? Заказанные товары удалить нельзя."):
            return
        try:
            cn = db_connect()
            cn.cursor().execute("DELETE FROM [Товары] WHERE [КодТовара]=?", item["id"])
            cn.commit()
            cn.close()
            self.selected_product_id = None
            self._refresh_catalog()
        except Exception as exc:
            messagebox.showerror("Товар не удалён", f"Проверьте связанные строки заказов и остатков.\n{exc}")

    def _selected_order_id(self):
        selected = self.orders_tree.selection()
        if not selected:
            messagebox.showinfo("Заказ", "Сначала выберите заказ в списке.")
            return None
        return int(selected[0])

    def _edit_selected_order(self):
        order_id = self._selected_order_id()
        if order_id is not None:
            self._order_form(order_id)

    def _order_form(self, order_id=None):
        if not self.user or self.user["role"] != "Администратор":
            return
        try:
            cn = db_connect()
            cursor = cn.cursor()
            buyers = cursor.execute("SELECT [КодПокупателя], [ФИО] FROM [Покупатели] ORDER BY [ФИО]").fetchall()
            warehouses = cursor.execute("SELECT [КодСклада], [Название] FROM [Склады] ORDER BY [Название]").fetchall()
            existing = cursor.execute("SELECT [ДатаЗаказа], [ДатаДоставки], [КодПокупателя], [КодСклада], [АдресДоставки], [КодПолучения], [Статус] FROM [Заказы] WHERE [КодЗаказа]=?", order_id).fetchone() if order_id else None
            cn.close()
            if not buyers or not warehouses:
                raise RuntimeError("Перед добавлением заказа создайте хотя бы одного покупателя и один склад.")
        except Exception as exc:
            messagebox.showerror("Заказ", str(exc))
            return
        def iso(value):
            if hasattr(value, "date"):
                value = value.date()
            return value.isoformat()[:10]
        dialog = tk.Toplevel(self)
        dialog.title("Изменить заказ" if existing else "Добавить заказ")
        dialog.transient(self)
        dialog.grab_set()
        form = ttk.Frame(dialog, padding=18)
        form.pack(fill="both", expand=True)
        buyer_var = tk.StringVar(value=next((r[1] for r in buyers if existing and r[0] == existing[2]), buyers[0][1]))
        warehouse_var = tk.StringVar(value=next((r[1] for r in warehouses if existing and r[0] == existing[3]), warehouses[0][1]))
        order_date = tk.StringVar(value=iso(existing[0]) if existing else date.today().isoformat())
        delivery_date = tk.StringVar(value=iso(existing[1]) if existing else (date.today()+timedelta(days=5)).isoformat())
        address_var = tk.StringVar(value=existing[4] if existing else "")
        pickup_var = tk.StringVar(value=existing[5] or "" if existing else "")
        status_var = tk.StringVar(value=existing[6] if existing else "Новый")
        fields = [("Покупатель", ttk.Combobox(form, textvariable=buyer_var, state="readonly", values=[r[1] for r in buyers], width=42)),
                  ("Склад", ttk.Combobox(form, textvariable=warehouse_var, state="readonly", values=[r[1] for r in warehouses], width=42)),
                  ("Дата заказа (ГГГГ-ММ-ДД)", ttk.Entry(form, textvariable=order_date, width=45)),
                  ("Дата доставки (ГГГГ-ММ-ДД)", ttk.Entry(form, textvariable=delivery_date, width=45)),
                  ("Адрес доставки", ttk.Entry(form, textvariable=address_var, width=45)),
                  ("Код получения", ttk.Entry(form, textvariable=pickup_var, width=45)),
                  ("Статус", ttk.Combobox(form, textvariable=status_var, state="readonly", values=STATUSES, width=42))]
        for row_number, (label, widget) in enumerate(fields):
            ttk.Label(form, text=label + ":").grid(row=row_number, column=0, sticky="w", padx=(0, 12), pady=5)
            widget.grid(row=row_number, column=1, sticky="ew", pady=5)
        form.columnconfigure(1, weight=1)

        def save():
            try:
                order_day = date.fromisoformat(order_date.get().strip())
                delivery_day = date.fromisoformat(delivery_date.get().strip())
                if delivery_day < order_day or not address_var.get().strip():
                    raise ValueError("Дата доставки должна быть не раньше заказа; адрес обязателен.")
                buyer_id = next(r[0] for r in buyers if r[1] == buyer_var.get())
                warehouse_id = next(r[0] for r in warehouses if r[1] == warehouse_var.get())
                cn = db_connect()
                cursor = cn.cursor()
                args = (order_day, delivery_day, buyer_id, warehouse_id, address_var.get().strip(), pickup_var.get().strip(), status_var.get())
                if existing:
                    cursor.execute("UPDATE [Заказы] SET [ДатаЗаказа]=?, [ДатаДоставки]=?, [КодПокупателя]=?, [КодСклада]=?, [АдресДоставки]=?, [КодПолучения]=?, [Статус]=? WHERE [КодЗаказа]=?", *args, order_id)
                else:
                    cursor.execute("INSERT INTO [Заказы] ([ДатаЗаказа], [ДатаДоставки], [КодПокупателя], [КодСклада], [АдресДоставки], [КодПолучения], [Статус]) VALUES (?, ?, ?, ?, ?, ?, ?)", *args)
                cn.commit()
                cn.close()
                dialog.destroy()
                self._refresh_orders()
            except Exception as exc:
                messagebox.showerror("Заказ не сохранён", str(exc), parent=dialog)

        ttk.Button(form, text="Сохранить", style="Accent.TButton", command=save).grid(row=len(fields), column=1, sticky="e", pady=(12, 0))

    def _delete_order(self):
        if not self.user or self.user["role"] != "Администратор":
            return
        order_id = self._selected_order_id()
        if order_id is None or not messagebox.askyesno("Удаление заказа", f"Удалить заказ №{order_id} и его строки?"):
            return
        try:
            cn = db_connect()
            cn.cursor().execute("DELETE FROM [Заказы] WHERE [КодЗаказа]=?", order_id)
            cn.commit()
            cn.close()
            self._refresh_orders()
        except Exception as exc:
            messagebox.showerror("Заказ не удалён", str(exc))

    def _refresh_orders(self):
        if not hasattr(self, "orders_tree"):
            return
        self.orders_tree.delete(*self.orders_tree.get_children())
        if not self.user:
            self.orders_note.configure(text="Войдите как клиент, чтобы увидеть заказы.")
            return
        try:
            cn = db_connect()
            cursor = cn.cursor()
            if self.user["role"] in ("Менеджер", "Администратор"):
                rows = cursor.execute("SELECT [КодЗаказа], [КодПолучения], [ДатаЗаказа], [ДатаДоставки], [Статус], [АдресДоставки] FROM [Заказы] ORDER BY [ДатаЗаказа] DESC").fetchall()
            else:
                rows = cursor.execute("SELECT [Заказы].[КодЗаказа], [Заказы].[КодПолучения], [Заказы].[ДатаЗаказа], [Заказы].[ДатаДоставки], [Заказы].[Статус], [Заказы].[АдресДоставки] FROM [Заказы] INNER JOIN [Покупатели] ON [Заказы].[КодПокупателя]=[Покупатели].[КодПокупателя] WHERE [Заказы].[КодПокупателя]=? ORDER BY [ДатаЗаказа] DESC", self.user["customer_id"]).fetchall()
            cn.close()
            for row in rows:
                self.orders_tree.insert("", "end", iid=str(row[0]), values=(row[1] or row[0], str(row[2])[:10], str(row[3])[:10], row[4], row[5]))
            self.orders_note.configure(text=f"Заказов: {len(rows)}")
        except Exception as exc:
            self.orders_note.configure(text=f"Не удалось загрузить заказы: {exc}")

if __name__ == "__main__":
    try:
        app = FurnitureApp()
        app.mainloop()
    except Exception as exc:
        messagebox.showerror("МебельМаркет", str(exc))
