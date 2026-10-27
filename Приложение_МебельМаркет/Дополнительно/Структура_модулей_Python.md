# Как разложен Python-код по модулям

Исходный большой файл больше не нужно вставлять целиком в `main.py`. Код уже разбит на модули в `Приложение/mebelmarket/`. Создайте эту структуру файлов и поместите соответствующую часть кода в каждый файл (или используйте файлы из ZIP/репозитория).

```text
Приложение/
├── main.py                         # единственная точка запуска
├── ЗаполнитьБД.py                  # разовый импорт Excel в Access
├── requirements.txt
├── images/
│   └── picture.png                 # заглушка для отсутствующего фото
└── mebelmarket/
    ├── __init__.py                 # отмечает каталог как Python-пакет
    ├── app.py                      # FurnitureApp: главное окно и сборка вкладок
    ├── authmixin.py                # вход, регистрация, роли, выход из аккаунта
    ├── catalogmixin.py             # карточки товаров, фильтры, CRUD товаров
    ├── ordersmixin.py              # корзина, заказ, остатки, CRUD заказов
    ├── database.py                 # подключение через Access ODBC
    ├── security.py                 # hash_password()
    └── config.py                   # путь к .accdb, имя драйвера, статусы
```

## 1. `Приложение/main.py` — с этого начинается запуск

Создайте файл `main.py` в папке `Приложение/`. Вставьте только точку входа:

```python
"""Точка входа приложения МебельМаркет."""
import tkinter as tk
from tkinter import messagebox

from mebelmarket.app import FurnitureApp


if __name__ == "__main__":
    try:
        app = FurnitureApp()
        app.mainloop()
    except Exception as exc:
        messagebox.showerror("МебельМаркет", str(exc))
```

Запускайте именно `Приложение/main.py` и в PyCharm/VS Code указывайте рабочую папку `Приложение/`. Не запускайте `app.py` напрямую: это компонент, а не файл-точка-входа.

## 2. `Приложение/mebelmarket/config.py`

Сюда перенесены глобальные настройки из начала исходного файла:

- `PROJECT` — корневая папка проекта;
- `DB_PATH` — путь `БД/МебельМаркет.accdb`;
- `ACCESS_DRIVER` — имя Microsoft Access ODBC Driver;
- `STATUSES` — допустимые состояния заказа.

## 3. `Приложение/mebelmarket/database.py`

Сюда перенесена функция `db_connect()`: проверяет наличие `.accdb`, ищет ODBC-драйвер и возвращает соединение `pyodbc`. Все части интерфейса импортируют её как `from .database import db_connect`.

## 4. `Приложение/mebelmarket/security.py`

Сюда перенесена функция `hash_password()`, вычисляющая SHA-256-дайджест. Вход и регистрация используют её из `authmixin.py`.

## 5. `Приложение/mebelmarket/app.py`

Здесь класс `FurnitureApp`. В нём остались `__init__()`, `_style()` и `_build_header()`. Класс соединяет функциональные части через наследование:

```python
class FurnitureApp(AuthMixin, CatalogMixin, OrdersMixin, tk.Tk):
    ...
```

В `__init__()` вызываются сборщики `_build_catalog()`, `_build_cart()` и `_build_orders()`, определённые в mixin-файлах.

## 6. Функции из исходного кода → файлы модулей

### `authmixin.py` — вход и состояние пользователя

Перенесите сюда методы класса `FurnitureApp`:

- `_auth_dialog()` — окно входа, регистрации и кнопка «Как гость»;
- `_ensure_customer()` — получение/создание профиля покупателя;
- `_logout()` — выход и возврат ко входу;
- `_update_session()` — права вкладок, отображение ФИО и доступность действий.

### `catalogmixin.py` — каталог и товары

- `_build_catalog()` — панель поиска/фильтра/сортировки и карточки;
- `_refresh_catalog()`, `_fill_catalog()` — чтение и отображение товаров;
- `_make_product_card()` — карточка, фото-заглушка, цена, остаток и стили скидки;
- `_select_product()`, `_product_by_id()`, `_add_to_cart()`;
- `_product_form()`, `_edit_selected_product()`, `_delete_product()` — CRUD товаров администратора.

### `ordersmixin.py` — корзина и заказы

- `_build_cart()`, `_refresh_cart()`, `_remove_from_cart()`;
- `_refresh_warehouses()`, `_place_order()`;
- `_build_orders()`, `_refresh_orders()`;
- `_selected_order_id()`, `_edit_selected_order()`, `_order_form()`, `_delete_order()`.

## 7. Импорты и запуск

В начале каждого mixin-файла оставьте импорты, нужные его методам. Например, каталог использует `tkinter`, `messagebox`, `simpledialog`, `Path`, `PROJECT` и `db_connect`; модуль заказов — `date`, `timedelta`, `messagebox`, `STATUSES` и `db_connect`. Относительные импорты внутри пакета начинаются с точки (`from .config import ...`). Файлы `__init__.py` обязаны находиться в папке `mebelmarket/`.

Установите зависимости один раз из папки `Приложение/`:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Если переносите код вручную, сохраняйте отступы методов: внутри каждого mixin-класса методы начинаются с четырёх пробелов. Проще всего использовать готовую папку `mebelmarket/` из комплекта и изменять её модули по отдельности.
