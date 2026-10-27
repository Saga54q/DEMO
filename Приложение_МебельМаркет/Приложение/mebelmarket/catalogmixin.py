"""Каталог, карточки, поиск и управление товарами."""
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .config import PROJECT
from .database import db_connect


class CatalogMixin:
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
