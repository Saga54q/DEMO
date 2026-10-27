PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Role (
    role_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS User (
    user_id INTEGER PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES Role(role_id),
    fio TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Category (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Manufacturer (
    manufacturer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Supplier (
    supplier_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Unit (
    unit_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Warehouse (
    warehouse_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    address TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS Product (
    product_id INTEGER PRIMARY KEY,
    article TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES Category(category_id),
    description TEXT NOT NULL DEFAULT '',
    manufacturer_id INTEGER NOT NULL REFERENCES Manufacturer(manufacturer_id),
    supplier_id INTEGER NOT NULL REFERENCES Supplier(supplier_id),
    price REAL NOT NULL CHECK(price >= 0),
    unit_id INTEGER NOT NULL REFERENCES Unit(unit_id),
    discount REAL NOT NULL DEFAULT 0 CHECK(discount >= 0 AND discount <= 100),
    image_path TEXT
);

CREATE TABLE IF NOT EXISTS Inventory (
    product_id INTEGER NOT NULL REFERENCES Product(product_id) ON DELETE CASCADE,
    warehouse_id INTEGER NOT NULL REFERENCES Warehouse(warehouse_id),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    PRIMARY KEY(product_id, warehouse_id)
);

CREATE TABLE IF NOT EXISTS Customer (
    customer_id INTEGER PRIMARY KEY,
    fio TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS OrderStatus (
    status_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ShopOrder (
    order_id INTEGER PRIMARY KEY,
    order_date TEXT NOT NULL,
    delivery_date TEXT NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES Customer(customer_id),
    warehouse_id INTEGER NOT NULL REFERENCES Warehouse(warehouse_id),
    delivery_address TEXT NOT NULL,
    code TEXT NOT NULL DEFAULT '',
    status_id INTEGER NOT NULL REFERENCES OrderStatus(status_id)
);

CREATE TABLE IF NOT EXISTS OrderItem (
    order_id INTEGER NOT NULL REFERENCES ShopOrder(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES Product(product_id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    PRIMARY KEY(order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_product_name ON Product(name);
CREATE INDEX IF NOT EXISTS idx_order_date ON ShopOrder(order_date);
CREATE INDEX IF NOT EXISTS idx_inventory_warehouse ON Inventory(warehouse_id);
