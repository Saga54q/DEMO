"""Окно входа, регистрация и роли пользователя."""
import tkinter as tk
from tkinter import messagebox, ttk

from .database import db_connect
from .security import hash_password


class AuthMixin:
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
