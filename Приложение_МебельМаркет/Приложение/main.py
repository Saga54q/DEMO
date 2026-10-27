"""Точка входа: запустите этот файл из PyCharm или VS Code."""
import tkinter as tk
from tkinter import messagebox

from mebelmarket.app import FurnitureApp


if __name__ == "__main__":
    try:
        app = FurnitureApp()
        app.mainloop()
    except Exception as exc:
        messagebox.showerror("МебельМаркет", str(exc))
