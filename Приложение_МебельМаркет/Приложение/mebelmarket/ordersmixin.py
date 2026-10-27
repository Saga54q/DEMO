"""Корзина, заказы и складские остатки."""
from datetime import date, timedelta
import tkinter as tk
from tkinter import messagebox, ttk

from .config import STATUSES
from .database import db_connect


class OrdersMixin:
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
