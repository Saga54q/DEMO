# Автосборка базы Microsoft Access

`create_access_db.py` при запуске создаёт `МебельМаркет.accdb`, затем таблицы, PK, индексы уникальности и связи, а при пустой базе импортирует строки из `import/Furniture_demo_import.xlsx`.

## Требования

- Windows;
- установленный настольный Microsoft Access с COM-автоматизацией `Access.Application`;
- Microsoft Access ODBC Driver для `.accdb`;
- Python той же разрядности, что Office/ODBC-драйвер (рекомендуется 64-bit);
- пакеты проекта и `requirements-access.txt`.

ODBC-драйвер и Microsoft Access не устанавливаются через `pip`. Если Python 64-bit, а драйвер 32-bit (или наоборот), подключение не заработает.

## Запуск из VS Code

1. Откройте папку `Приложение_МебельМаркет`.
2. Выберите виртуальное окружение проекта в командной палитре: **Python: Select Interpreter**.
3. В Terminal из корня проекта выполните:

   ```powershell
   python -m pip install -r requirements.txt
   python -m pip install -r requirements-access.txt
   python create_access_db.py
   ```

4. Если всё настроено, рядом со скриптом появится `МебельМаркет.accdb`; его можно открыть в Access.
5. При повторном запуске существующий файл не удаляется. Если в таблице Product уже есть записи, повторный импорт пропускается.

Для пересоздания сначала закройте базу в Access и сделайте резервную копию. Удаляйте `.accdb` вручную только если точно хотите создать базу заново.

## Что создаётся

`Role`, `User`, `Category`, `Manufacturer`, `Supplier`, `Unit`, `Warehouse`, `Product`, `Inventory`, `Customer`, `OrderStatus`, `ShopOrder`, `OrderItem`.

Остаток хранится на пару товар–склад. Состав заказа вынесен в `OrderItem`. Внешние связи создаются средствами DAO; товар из существующего заказа удалить нельзя.

## Важное различие

Этот файл **создаёт Access-БД**, но текущий `main.py` проекта всё ещё использует SQLite через `database.py`. Созданную `.accdb` нельзя считать подключённой к приложению до замены backend-функций на ODBC/`pyodbc`. Для полноценного перехода приложения нужно отдельно перевести `database.py` и тесты на Access и проверить это на Windows с установленным Access/драйвером. В этой среде Access отсутствует, поэтому COM/ODBC-часть здесь не исполнялась.
