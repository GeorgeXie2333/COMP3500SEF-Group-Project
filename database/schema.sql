-- Logistics Management System schema v1.2 (SQLite).
-- Responsibilities: docs/PROJECT.md. Review changes with affected module owners.
--
-- v1.2 (P2 / Task #24, Database Engineer: CEN Yin Chi) - additive except where
-- noted; every change is justified in docs/index-plan.md or the PR description:
--   1. items.sku becomes NOT NULL (a NULL sku defeats its own UNIQUE index).
--   2. items / shipment_items gain CHECK guards: stock >= 0, quantity > 0,
--      prices >= 0. The API already validates these; the database is the last
--      line of defence against a negative stock row.
--   3. shipment_items.unit_price - price snapshot taken at order time, filled by
--      trigger trg_shipment_items_price so backend/server.py needs no change.
--   4. UNIQUE (shipment_id, item_id) - the same product cannot be booked twice
--      in one order (which used to deduct stock twice and duplicate the line).
--   5. idx_tracking_events_lookup gains event_id: event_time has one-second
--      resolution, so two events in the same second had no defined order.
--   6. Indexes from the P2 plan (docs/index-plan.md).
--   7. View v_shipment_order_summary - order totals without application logic.
--
-- Upgrading an existing database:  python database/db_manager.py migrate
-- Clean rebuild (P4 check):        python database/db_manager.py rebuild

BEGIN IMMEDIATE;
DROP VIEW IF EXISTS v_shipment_order_summary;
DROP TABLE IF EXISTS tracking_events;
DROP TABLE IF EXISTS shipment_items;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS hubs;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer'
        CHECK (role IN ('customer', 'courier', 'warehouse_admin', 'admin')),
    phone TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE hubs (
    hub_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hub_name TEXT NOT NULL,
    district TEXT NOT NULL,
    address TEXT NOT NULL
);

CREATE TABLE items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    sku TEXT NOT NULL UNIQUE,
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    unit_price REAL NOT NULL DEFAULT 0.00 CHECK (unit_price >= 0)
);

CREATE TABLE shipments (
    shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_number TEXT NOT NULL UNIQUE,
    sender_id INTEGER NOT NULL,
    receiver_name TEXT NOT NULL,
    receiver_phone TEXT NOT NULL,
    delivery_address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'shipped', 'delivered')),
    current_hub_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (current_hub_id) REFERENCES hubs(hub_id)
);

CREATE TABLE shipment_items (
    shipment_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price REAL CHECK (unit_price IS NULL OR unit_price >= 0),
    UNIQUE (shipment_id, item_id),
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE TABLE tracking_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER NOT NULL,
    hub_id INTEGER,
    status TEXT NOT NULL CHECK (status IN ('pending', 'shipped', 'delivered')),
    description TEXT NOT NULL,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE,
    FOREIGN KEY (hub_id) REFERENCES hubs(hub_id)
);

-- Parcel timeline. event_time alone is not unique (one-second resolution), so
-- event_id is appended to make "newest first" a total order and to let the
-- index serve ORDER BY event_time DESC, event_id DESC without a temporary B-tree.
CREATE INDEX idx_tracking_events_lookup
    ON tracking_events(shipment_id, event_time DESC, event_id DESC);

-- ---------------------------------------------------------------------------
-- Price snapshot. Fires only when the caller did not supply a price, so
-- backend/server.py keeps its current INSERT statement and an explicitly agreed
-- price (for example a discount) is never overwritten.
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_shipment_items_price;
CREATE TRIGGER trg_shipment_items_price
AFTER INSERT ON shipment_items
FOR EACH ROW
WHEN NEW.unit_price IS NULL
BEGIN
    UPDATE shipment_items
       SET unit_price = (SELECT unit_price FROM items WHERE item_id = NEW.item_id)
     WHERE shipment_item_id = NEW.shipment_item_id;
END;

INSERT INTO users (username, password_hash, role, phone) VALUES
('admin_alan', 'hash_pwd_001', 'admin', '+852-91234567'),
('customer_alice', 'hash_pwd_002', 'customer', '+852-94567890'),
('courier_chan', 'hash_pwd_003', 'courier', '+852-92345678');

INSERT INTO hubs (hub_name, district, address) VALUES
('Kowloon Sorting Center', 'Kowloon', 'No. 88 Kwun Tong Road, Kwun Tong'),
('Central Distribution Hub', 'Hong Kong Island', 'No. 12 Connaught Road Central, Central'),
('Shatin Express Facility', 'New Territories', 'No. 6 Shatin Rural Committee Road, Shatin');

INSERT INTO items (item_name, sku, stock_quantity, unit_price) VALUES
('Wireless Optical Mouse', 'TECH-WM-001', 120, 150.00),
('Mechanical Gaming Keyboard', 'TECH-KB-002', 45, 480.00),
('USB-C Fast Charging Cable', 'TECH-CB-003', 300, 65.00);

INSERT INTO shipments (tracking_number, sender_id, receiver_name, receiver_phone, delivery_address, status, current_hub_id) VALUES
('HK202610001', 2, 'David Cheung', '+852-98765432', 'Flat B, 12/F, Nathan Tower, Mong Kok, Kowloon', 'shipped', 1);

INSERT INTO shipment_items (shipment_id, item_id, quantity) VALUES
(1, 2, 1),
(1, 3, 2);

INSERT INTO tracking_events (shipment_id, hub_id, status, description) VALUES
(1, NULL, 'pending', 'Shipping order created by sender.'),
(1, 1, 'shipped', 'Parcel picked up and arrived at Kowloon Sorting Center.');

-- ---------------------------------------------------------------------------
-- Order totals in one place, so no client has to re-derive them and QA has a
-- single place to check the arithmetic.
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_shipment_order_summary;
CREATE VIEW v_shipment_order_summary AS
SELECT s.shipment_id,
       s.tracking_number,
       s.status,
       s.receiver_name,
       s.created_at,
       COUNT(si.shipment_item_id)                    AS line_count,
       IFNULL(SUM(si.quantity), 0)                   AS total_quantity,
       IFNULL(SUM(si.quantity * si.unit_price), 0.0) AS total_amount
FROM shipments AS s
LEFT JOIN shipment_items AS si ON si.shipment_id = s.shipment_id
GROUP BY s.shipment_id, s.tracking_number, s.status, s.receiver_name, s.created_at;

-- ---------------------------------------------------------------------------
-- Index plan (P2 / Task #24). Justification for every index below lives in
-- docs/index-plan.md. All statements are idempotent, so this block is safe to
-- re-apply to an existing database as well as to a freshly migrated one.
-- Lookups that are already served by a PRIMARY KEY or UNIQUE constraint
-- (shipments.tracking_number, items.sku, users.username, hubs.hub_id,
-- tracking_events.event_id) deliberately get no redundant index here.
-- shipment_items.shipment_id needs no separate index either: it is the leading
-- column of UNIQUE(shipment_id, item_id).
-- ---------------------------------------------------------------------------

-- 1. FK join path shipments -> users, plus "shipments sent by user X" newest
--    first. The composite key keeps the ORDER BY on the index and drops the
--    temporary B-tree sort.
CREATE INDEX IF NOT EXISTS idx_shipments_sender_time
    ON shipments(sender_id, created_at DESC);

-- 2. Status-filtered shipment listing, newest first (dashboard / QA queries).
CREATE INDEX IF NOT EXISTS idx_shipments_status_created_at
    ON shipments(status, created_at DESC);

-- 3. FK lookup for hub workload views and the current_hub_id FK check.
CREATE INDEX IF NOT EXISTS idx_shipments_current_hub_id
    ON shipments(current_hub_id);

-- 4. Item-level reporting ("which orders contain this item") and the item_id FK.
CREATE INDEX IF NOT EXISTS idx_shipment_items_item_id
    ON shipment_items(item_id);

-- 5. Hub activity feed. Partial index: status changes generated by the API carry
--    hub_id NULL and would only bloat the tree.
CREATE INDEX IF NOT EXISTS idx_tracking_events_hub_time
    ON tracking_events(hub_id, event_time DESC)
    WHERE hub_id IS NOT NULL;

-- 6. Status history / KPI counts across shipments, newest first.
CREATE INDEX IF NOT EXISTS idx_tracking_events_status_time
    ON tracking_events(status, event_time DESC);

PRAGMA user_version = 2;
COMMIT;
