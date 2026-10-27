# Запуск проекта в Visual Studio Code

1. Установите Python 3.10+ и расширение **Python** от Microsoft. Для приложения на Windows также установите Microsoft Access и Access Database Engine/ODBC одной разрядности с Python.
2. В VS Code выберите **File → Open Folder…** и откройте папку `Приложение_МебельМаркет`.
3. Создайте окружение из интегрированного терминала (PowerShell):

```powershell
cd Приложение
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Если PowerShell запрещает активацию, можно не активировать окружение, а запускать `.venv\Scripts\python.exe` напрямую.

4. В Access создайте `БД/МебельМаркет.accdb` и выполните `BuildFurnitureDatabase` из `БД/Модуль_создания_БД.bas` по инструкции в `Дополнительно/Руководство.md`.
5. Сгенерируйте условные записи и импортируйте их:

```powershell
python ..\БД\СоздатьДемоДанные.py
python ЗаполнитьБД.py
```

6. Нажмите `Ctrl+Shift+P` → **Python: Select Interpreter** → выберите `Приложение/.venv/Scripts/python.exe`.
7. Откройте `Приложение/main.py` и нажмите `F5` → **Python Debugger**. Или запустите в терминале `python main.py` из `Приложение/`.
8. Для импорта при повторном запуске используйте конфигурацию запуска с файлом `ЗаполнитьБД.py`; импортёр намеренно не перезаписывает таблицу товаров.

Если модуль `pyodbc` установлен, но драйвер не находится, проверьте разрядность Python/Access Database Engine и наличие драйвера `Microsoft Access Driver (*.mdb, *.accdb)` в ODBC Data Sources. На macOS/Linux приложение не подключится к Access через этот драйвер.

Условные демо-входы: клиент `client@mebel.local` / `Client2026`; менеджер `manager@mebel.local` / `Manager2026`; администратор `admin@mebel.local` / `Admin2026`.
