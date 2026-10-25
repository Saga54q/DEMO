PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Role(
    role_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS User(
    user_id INTEGER PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES Role(role_id),
    fio TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS Supplier(
    supplier_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS Manufacturer(
    manufacturer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS ProductType(
    type_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS Customer(
    customer_id INTEGER PRIMARY KEY,
    fio TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS PickupPoint(
    point_id INTEGER PRIMARY KEY,
    postal_code TEXT,
    city TEXT,
    street TEXT,
    number TEXT
);
CREATE TABLE IF NOT EXISTS OrderStatus(
    status_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS Product(
    product_id INTEGER PRIMARY KEY,
    article TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    cost REAL NOT NULL CHECK(cost >= 0),
    supplier_id INTEGER NOT NULL REFERENCES Supplier(supplier_id),
    manufacturer_id INTEGER NOT NULL REFERENCES Manufacturer(manufacturer_id),
    type_id INTEGER NOT NULL REFERENCES ProductType(type_id),
    discount REAL NOT NULL DEFAULT 0 CHECK(discount BETWEEN 0 AND 100),
    stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
    description TEXT,
    image TEXT
);
CREATE TABLE IF NOT EXISTS ShopOrder(
    order_id INTEGER PRIMARY KEY,
    order_date TEXT NOT NULL,
    delivery_date TEXT NOT NULL,
    point_id INTEGER NOT NULL REFERENCES PickupPoint(point_id),
    customer_id INTEGER NOT NULL REFERENCES Customer(customer_id),
    code TEXT NOT NULL,
    status_id INTEGER NOT NULL REFERENCES OrderStatus(status_id)
);
CREATE TABLE IF NOT EXISTS OrderItem(
    order_id INTEGER NOT NULL REFERENCES ShopOrder(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES Product(product_id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    PRIMARY KEY(order_id, product_id)
);
