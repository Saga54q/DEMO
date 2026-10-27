"""Главное окно приложения и запуск его компонентов."""
import tkinter as tk
from tkinter import ttk

from .authmixin import AuthMixin
from .catalogmixin import CatalogMixin
from .ordersmixin import OrdersMixin


class FurnitureApp(AuthMixin, CatalogMixin, OrdersMixin, tk.Tk):
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
