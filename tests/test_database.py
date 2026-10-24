"""Database regression tests for schema v1.2 and database/db_manager.py.

Runs under the project's CI command (unittest, not pytest):

    python -m unittest discover -s tests -v

Every test works on a throw-away database in a temporary directory, so
backend/lms.db is never touched.
"""

import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("db_manager", ROOT / "database" / "db_manager.py")
dbm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dbm)

# The v1.1 structure (before this change). Used to prove that `migrate` really
# upgrades an existing database, not just a new one.
V11_SCHEMA = """
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer',
    phone TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE hubs (
    hub_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hub_name TEXT NOT NULL, district TEXT NOT NULL, address TEXT NOT NULL
);
CREATE TABLE items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    sku TEXT UNIQUE,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    unit_price REAL NOT NULL DEFAULT 0.00
);
CREATE TABLE shipments (
    shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_number TEXT NOT NULL UNIQUE,
    sender_id INTEGER NOT NULL,
    receiver_name TEXT NOT NULL, receiver_phone TEXT NOT NULL,
    delivery_address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
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
    quantity INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);
CREATE TABLE tracking_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER NOT NULL,
    hub_id INTEGER,
    status TEXT NOT NULL,
    description TEXT NOT NULL,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE,
    FOREIGN KEY (hub_id) REFERENCES hubs(hub_id)
);
CREATE INDEX idx_tracking_events_lookup ON tracking_events(shipment_id, event_time DESC);

INSERT INTO users (username, password_hash, role, phone) VALUES
    ('admin_alan', 'x', 'admin', '+852-91234567'),
    ('customer_alice', 'x', 'customer', '+852-94567890');
INSERT INTO hubs (hub_name, district, address) VALUES ('Kowloon Sorting Center', 'Kowloon', '88 Kwun Tong Road');
INSERT INTO items (item_name, sku, stock_quantity, unit_price) VALUES
    ('Wireless Optical Mouse', 'TECH-WM-001', 120, 150.00),
    ('Mechanical Gaming Keyboard', 'TECH-KB-002', 45, 480.00);
INSERT INTO shipments (tracking_number, sender_id, receiver_name, receiver_phone,
                       delivery_address, status) VALUES
    ('HK202610001', 2, 'David Cheung', '+852-98765432', 'Mong Kok', 'shipped');
INSERT INTO shipment_items (shipment_id, item_id, quantity) VALUES (1, 2, 1), (1, 2, 1);
INSERT INTO tracking_events (shipment_id, hub_id, status, description) VALUES
    (1, NULL, 'pending', 'created'),
    (1, 1, 'shipped', 'picked up');
"""


class DatabaseTestCase(unittest.TestCase):
    """Base class: one temporary directory per test, plus small helpers."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        self.db = self.tmp / "lms.db"

    def make_fresh_db(self) -> Path:
        self.assertEqual(dbm.migrate(self.db), 0)
        return self.db

    def make_v11_db(self) -> Path:
        connection = sqlite3.connect(self.db)
        connection.executescript(V11_SCHEMA)
        connection.commit()
        connection.close()
        return self.db

    def query(self, sql, params=()):
        connection = sqlite3.connect(self.db)
        connection.row_factory = sqlite3.Row
        try:
            return [dict(row) for row in connection.execute(sql, params)]
        finally:
            connection.close()

    def execute(self, sql, params=()):
        connection = sqlite3.connect(self.db)
        try:
            connection.execute(sql, params)
            connection.commit()
        finally:
            connection.close()


class TestSchema(DatabaseTestCase):
    def test_all_tables_view_and_trigger_exist(self):
        self.make_fresh_db()
        names = {row["name"] for row in self.query("SELECT name FROM sqlite_master")}
        for table in ("users", "hubs", "items", "shipments", "shipment_items", "tracking_events"):
            self.assertIn(table, names)
        self.assertIn("v_shipment_order_summary", names)
        self.assertIn("trg_shipment_items_price", names)

    def test_seed_data_matches_the_demo_screens(self):
        self.make_fresh_db()
        items = self.query("SELECT sku, stock_quantity, unit_price FROM items ORDER BY item_id")
        self.assertEqual([i["sku"] for i in items],
                         ["TECH-WM-001", "TECH-KB-002", "TECH-CB-003"])
        self.assertEqual(items[0]["stock_quantity"], 120)
        shipments = self.query("SELECT tracking_number, status FROM shipments")
        self.assertEqual(shipments[0]["tracking_number"], "HK202610001")
        self.assertEqual(shipments[0]["status"], "shipped")

    def test_verify_passes_on_a_fresh_database(self):
        self.make_fresh_db()
        self.assertEqual(dbm.verify(self.db), 0)


class TestDataIntegrity(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.make_fresh_db()

    def test_price_snapshot_is_filled_by_the_trigger(self):
        # exactly what backend/server.py does: no unit_price in the INSERT
        self.execute("INSERT INTO shipment_items (shipment_id, item_id, quantity) VALUES (1, 1, 3)")
        row = self.query("SELECT unit_price FROM shipment_items WHERE shipment_id = 1 AND item_id = 1")[0]
        self.assertEqual(row["unit_price"], 150.00)

    def test_price_snapshot_survives_a_catalogue_price_change(self):
        self.execute("INSERT INTO shipment_items (shipment_id, item_id, quantity) VALUES (1, 1, 1)")
        self.execute("UPDATE items SET unit_price = 999.00 WHERE item_id = 1")
        row = self.query("SELECT unit_price FROM shipment_items WHERE shipment_id = 1 AND item_id = 1")[0]
        self.assertEqual(row["unit_price"], 150.00)

    def test_duplicate_product_line_is_rejected(self):
        self.execute("INSERT INTO shipment_items (shipment_id, item_id, quantity) VALUES (1, 1, 1)")
        with self.assertRaises(sqlite3.IntegrityError):
            self.execute("INSERT INTO shipment_items (shipment_id, item_id, quantity) VALUES (1, 1, 2)")

    def test_negative_stock_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.execute("UPDATE items SET stock_quantity = -1 WHERE item_id = 1")

    def test_zero_quantity_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.execute("INSERT INTO shipment_items (shipment_id, item_id, quantity) VALUES (1, 3, 0)")

    def test_order_summary_totals(self):
        # seed order: 1 x keyboard (480.00) + 2 x cable (65.00)
        summary = self.query("SELECT * FROM v_shipment_order_summary WHERE shipment_id = 1")[0]
        self.assertEqual(summary["line_count"], 2)
        self.assertEqual(summary["total_quantity"], 3)
        self.assertAlmostEqual(summary["total_amount"], 610.00, places=2)


class TestIndexes(DatabaseTestCase):
    def test_index_plan_is_present(self):
        self.make_fresh_db()
        names = {row["name"] for row in self.query(
            "SELECT name FROM sqlite_master WHERE type = 'index'")}
        for expected in dbm.EXPECTED_INDEXES:
            self.assertIn(expected, names)

    def test_timeline_index_has_the_event_id_tie_break(self):
        self.make_fresh_db()
        row = self.query("SELECT sql FROM sqlite_master WHERE name = 'idx_tracking_events_lookup'")[0]
        self.assertIn("event_id", row["sql"])
        connection = sqlite3.connect(self.db)
        try:
            plan = " ".join(r[3] for r in connection.execute(
                "EXPLAIN QUERY PLAN SELECT * FROM tracking_events WHERE shipment_id = 1 "
                "ORDER BY event_time DESC, event_id DESC LIMIT 10"))
        finally:
            connection.close()
        self.assertIn("idx_tracking_events_lookup", plan)
        self.assertNotIn("TEMP B-TREE", plan)

    def test_verify_reports_a_missing_index(self):
        self.make_fresh_db()
        self.execute("DROP INDEX idx_shipments_status_created_at")
        self.assertEqual(dbm.verify(self.db), 1)


class TestMigration(DatabaseTestCase):
    def test_migrate_upgrades_a_v11_database(self):
        self.make_v11_db()
        columns_before = {row["name"] for row in self.query("PRAGMA table_info(shipment_items)")}
        self.assertNotIn("unit_price", columns_before)

        self.assertEqual(dbm.migrate(self.db), 0)

        columns_after = {row["name"] for row in self.query("PRAGMA table_info(shipment_items)")}
        self.assertIn("unit_price", columns_after)
        self.assertEqual(dbm.verify(self.db), 0)
        # the two duplicate seed lines were merged, not dropped
        lines = self.query("SELECT quantity, unit_price FROM shipment_items WHERE shipment_id = 1")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["quantity"], 2)
        self.assertEqual(lines[0]["unit_price"], 480.00)

    def test_migrate_is_idempotent(self):
        self.make_v11_db()
        self.assertEqual(dbm.migrate(self.db), 0)
        first = self.query("PRAGMA user_version")[0]["user_version"]
        self.assertEqual(dbm.migrate(self.db), 0)
        self.assertEqual(self.query("PRAGMA user_version")[0]["user_version"], first)


class TestBackup(DatabaseTestCase):
    def test_backup_creates_a_restorable_copy(self):
        self.make_fresh_db()
        out = self.tmp / "backups"
        self.assertEqual(dbm.backup(self.db, out, keep=5), 0)
        produced = sorted(out.glob("*.db"))
        self.assertTrue(produced, "backup produced no .db file")
        self.assertTrue(sorted(out.glob("*.sql")), "backup produced no .sql dump")

        restored = self.tmp / "restored.db"
        restored.write_bytes(produced[-1].read_bytes())
        self.assertEqual(dbm.verify(restored), 0)


if __name__ == "__main__":
    unittest.main()
