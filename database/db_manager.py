#!/usr/bin/env python3
"""Database migration, backup and clean-rebuild tool.

Owner: CEN Yin Chi (Database Engineer) - P2 deliverable (Task #24).

Usage
-----
    python database/db_manager.py migrate            # upgrade an existing database
    python database/db_manager.py backup             # bin copy + SQL dump
    python database/db_manager.py rebuild            # drop, recreate, seed (P4 check)
    python database/db_manager.py verify             # integrity checks, exit 1 on FAIL
    python database/db_manager.py status             # version / row counts / indexes

Options
-------
    --db PATH     database file (default: backend/lms.db, same as server.py)
    --out DIR     backup directory (default: database/backups)
    --keep N      keep the last N backup pairs (default: 10)
    --force       skip the rebuild confirmation prompt

Why this exists
---------------
backend/server.py creates the schema only when the database has no tables; it
never upgrades an existing one. So once backend/lms.db exists, any change to
database/schema.sql has to reach the old file somewhere - that is `migrate`.

SQLite cannot add a CHECK or UNIQUE constraint in place, so the two tables that
need them are rebuilt with the documented 12-step procedure (disable foreign
keys, create the new table, copy, drop, rename, re-enable, verify). Every step
is idempotent: running `migrate` twice changes nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "database" / "schema.sql"
DEFAULT_DB = ROOT / "backend" / "lms.db"
DEFAULT_BACKUP_DIR = ROOT / "database" / "backups"
SCHEMA_VERSION = 2

EXPECTED_TABLES = ("users", "hubs", "items", "shipments", "shipment_items", "tracking_events")
EXPECTED_INDEXES = (
    "idx_tracking_events_lookup",
    "idx_shipments_sender_time",
    "idx_shipments_status_created_at",
    "idx_shipments_current_hub_id",
    "idx_shipment_items_item_id",
    "idx_tracking_events_hub_time",
    "idx_tracking_events_status_time",
)

# Same definitions as database/schema.sql. Duplicated here because a migration
# cannot re-run the whole schema file (that would drop the data).
SHIPMENT_ITEMS_DDL = """
CREATE TABLE shipment_items_new (
    shipment_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price REAL CHECK (unit_price IS NULL OR unit_price >= 0),
    UNIQUE (shipment_id, item_id),
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(item_id)
)
"""

ITEMS_DDL = """
CREATE TABLE items_new (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    sku TEXT NOT NULL UNIQUE,
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    unit_price REAL NOT NULL DEFAULT 0.00 CHECK (unit_price >= 0)
)
"""

NEW_INDEXES = (
    ("idx_shipments_sender_time",
     "CREATE INDEX IF NOT EXISTS idx_shipments_sender_time "
     "ON shipments(sender_id, created_at DESC)"),
    ("idx_shipments_status_created_at",
     "CREATE INDEX IF NOT EXISTS idx_shipments_status_created_at "
     "ON shipments(status, created_at DESC)"),
    ("idx_shipments_current_hub_id",
     "CREATE INDEX IF NOT EXISTS idx_shipments_current_hub_id "
     "ON shipments(current_hub_id)"),
    ("idx_shipment_items_item_id",
     "CREATE INDEX IF NOT EXISTS idx_shipment_items_item_id "
     "ON shipment_items(item_id)"),
    ("idx_tracking_events_hub_time",
     "CREATE INDEX IF NOT EXISTS idx_tracking_events_hub_time "
     "ON tracking_events(hub_id, event_time DESC) WHERE hub_id IS NOT NULL"),
    ("idx_tracking_events_status_time",
     "CREATE INDEX IF NOT EXISTS idx_tracking_events_status_time "
     "ON tracking_events(status, event_time DESC)"),
)

TIMELINE_INDEX = (
    "CREATE INDEX idx_tracking_events_lookup "
    "ON tracking_events(shipment_id, event_time DESC, event_id DESC)"
)

TRIGGER_DDL = """
CREATE TRIGGER trg_shipment_items_price
AFTER INSERT ON shipment_items
FOR EACH ROW
WHEN NEW.unit_price IS NULL
BEGIN
    UPDATE shipment_items
       SET unit_price = (SELECT unit_price FROM items WHERE item_id = NEW.item_id)
     WHERE shipment_item_id = NEW.shipment_item_id;
END
"""

VIEW_DDL = """
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
GROUP BY s.shipment_id, s.tracking_number, s.status, s.receiver_name, s.created_at
"""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None          # explicit BEGIN/COMMIT only
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def table_names(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")}


def column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def object_sql(conn: sqlite3.Connection, name: str) -> str:
    row = conn.execute(
        "SELECT COALESCE(sql, '') FROM sqlite_master WHERE name = ?", (name,)).fetchone()
    return (row[0] if row else "") or ""


def index_names(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'")}


def user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def say(msg: str = "") -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# schema creation
# ---------------------------------------------------------------------------
def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


# ---------------------------------------------------------------------------
# migration steps (each one idempotent)
# ---------------------------------------------------------------------------
def merge_duplicate_lines(conn: sqlite3.Connection) -> int:
    """UNIQUE(shipment_id, item_id) cannot be added while duplicates exist.

    Duplicated rows are merged by summing quantity: the customer still gets the
    units they ordered, and the double stock deduction disappears.
    """
    dupes = conn.execute("""
        SELECT shipment_id, item_id, SUM(quantity) AS total_qty, MIN(shipment_item_id) AS keep_id
        FROM shipment_items
        GROUP BY shipment_id, item_id
        HAVING COUNT(*) > 1
    """).fetchall()
    for row in dupes:
        conn.execute("UPDATE shipment_items SET quantity = ? WHERE shipment_item_id = ?",
                     (row["total_qty"], row["keep_id"]))
        conn.execute("""DELETE FROM shipment_items
                        WHERE shipment_id = ? AND item_id = ? AND shipment_item_id <> ?""",
                     (row["shipment_id"], row["item_id"], row["keep_id"]))
    return len(dupes)


def rebuild_shipment_items(conn: sqlite3.Connection) -> None:
    """Add unit_price, UNIQUE and CHECKs (SQLite cannot ALTER for these)."""
    orphan_sql = """
        SELECT COUNT(*) FROM shipment_items
        WHERE shipment_id NOT IN (SELECT shipment_id FROM shipments)
           OR item_id NOT IN (SELECT item_id FROM items)
    """
    orphan = conn.execute(orphan_sql).fetchone()[0]
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(SHIPMENT_ITEMS_DDL)
        conn.execute("""
            INSERT INTO shipment_items_new
                (shipment_item_id, shipment_id, item_id, quantity, unit_price)
            SELECT si.shipment_item_id, si.shipment_id, si.item_id, si.quantity, i.unit_price
            FROM shipment_items AS si
            JOIN items AS i ON i.item_id = si.item_id
        """)
        conn.execute("DROP TABLE shipment_items")
        conn.execute("ALTER TABLE shipment_items_new RENAME TO shipment_items")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    if orphan:
        say(f"  ! dropped {orphan} orphan order line(s) whose shipment/item no longer exists")


def rebuild_items(conn: sqlite3.Connection) -> None:
    """sku NOT NULL plus CHECK guards on stock and price."""
    blanks = conn.execute(
        "SELECT COUNT(*) FROM items WHERE sku IS NULL OR TRIM(sku) = ''").fetchone()[0]
    if blanks:
        conn.execute("UPDATE items SET sku = 'SKU-' || item_id WHERE sku IS NULL OR TRIM(sku) = ''")
        say(f"  ! gave {blanks} item(s) a placeholder sku (SKU-<item_id>)")
    negative = conn.execute("SELECT COUNT(*) FROM items WHERE stock_quantity < 0").fetchone()[0]
    if negative:
        conn.execute("UPDATE items SET stock_quantity = 0 WHERE stock_quantity < 0")
        say(f"  ! clamped {negative} negative stock value(s) to 0")

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(ITEMS_DDL)
        conn.execute("""
            INSERT INTO items_new (item_id, item_name, sku, stock_quantity, unit_price)
            SELECT item_id, item_name, sku, stock_quantity, unit_price FROM items
        """)
        conn.execute("DROP TABLE items")
        conn.execute("ALTER TABLE items_new RENAME TO items")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def ensure_timeline_index(conn: sqlite3.Connection) -> bool:
    """Upgrade (shipment_id, event_time) to include the event_id tie-break."""
    sql = object_sql(conn, "idx_tracking_events_lookup")
    if "event_id" in sql:
        return False
    conn.execute("DROP INDEX IF EXISTS idx_tracking_events_lookup")
    conn.execute(TIMELINE_INDEX)
    return True


def ensure_indexes(conn: sqlite3.Connection) -> int:
    created = 0
    for name, ddl in NEW_INDEXES:
        if name not in index_names(conn):
            conn.execute(ddl)
            created += 1
    return created


def ensure_trigger_and_view(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TRIGGER IF EXISTS trg_shipment_items_price")
    conn.execute(TRIGGER_DDL)
    conn.execute("DROP VIEW IF EXISTS v_shipment_order_summary")
    conn.execute(VIEW_DDL)


def migrate(db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not db_path.exists() or "shipments" not in table_names(connect(db_path))

    conn = connect(db_path)
    try:
        if fresh:
            say(f"creating a new database from {SCHEMA_PATH.name} ...")
            create_schema(conn)
            say(f"OK  {db_path} is at schema v{SCHEMA_VERSION}")
            return 0

        say(f"migrating {db_path} ...")
        steps = 0

        if "unit_price" not in column_names(conn, "shipment_items"):
            merged = merge_duplicate_lines(conn)
            if merged:
                say(f"  ! merged {merged} duplicated order line(s)")
            say("  - rebuilding shipment_items (price snapshot, UNIQUE, CHECKs)")
            rebuild_shipment_items(conn)
            steps += 1

        if "CHECK" not in object_sql(conn, "items").upper():
            say("  - rebuilding items (sku NOT NULL, stock/price CHECKs)")
            rebuild_items(conn)
            steps += 1

        if ensure_timeline_index(conn):
            say("  - upgraded idx_tracking_events_lookup with the event_id tie-break")
            steps += 1

        created = ensure_indexes(conn)
        if created:
            say(f"  - created {created} index(es)")
            steps += 1

        ensure_trigger_and_view(conn)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

        say("  already up to date" if steps == 0 else f"  applied {steps} change set(s)")
        say(f"OK  {db_path} is at schema v{SCHEMA_VERSION}")
        return 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------------
def backup(db_path: Path, out_dir: Path, keep: int) -> int:
    if not db_path.exists():
        say(f"ERROR database not found: {db_path}")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    db_file = out_dir / f"{db_path.stem}_{stamp}.db"
    sql_file = out_dir / f"{db_path.stem}_{stamp}.sql"

    src = connect(db_path)
    try:
        dst = sqlite3.connect(db_file)
        with dst:
            src.backup(dst)
        dst.close()
        with sql_file.open("w", encoding="utf-8") as fh:
            fh.write(f"-- {db_path.name} dump {stamp}\n")
            for line in src.iterdump():
                fh.write(line + "\n")
            fh.write("COMMIT;\n")
    finally:
        src.close()

    digest = hashlib.sha256(db_file.read_bytes()).hexdigest()
    say(f"OK  {db_file}  ({db_file.stat().st_size / 1024:.1f} KB)")
    say(f"OK  {sql_file} ({sql_file.stat().st_size / 1024:.1f} KB)")
    say(f"    sha256 {digest}")

    pairs = sorted(out_dir.glob(f"{db_path.stem}_*.db"))
    if keep > 0:
        for old in pairs[:-keep]:
            old.unlink(missing_ok=True)
            old.with_suffix(".sql").unlink(missing_ok=True)
            say(f"    pruned {old.name}")
    return 0


# ---------------------------------------------------------------------------
# rebuild / verify / status
# ---------------------------------------------------------------------------
def rebuild(db_path: Path, force: bool) -> int:
    if db_path.exists():
        if not force:
            answer = input(f"DELETE {db_path} and rebuild from schema.sql? type 'yes': ")
            if answer.strip().lower() not in ("yes", "y"):
                say("aborted")
                return 1
        db_path.unlink()
    rc = migrate(db_path)
    if rc == 0:
        say("clean rebuild finished - running verification:")
        return verify(db_path)
    return rc


def verify(db_path: Path) -> int:
    if not db_path.exists():
        say(f"ERROR database not found: {db_path}")
        return 1
    conn = connect(db_path)
    results: list[tuple[str, int, bool]] = []
    try:
        missing = [t for t in EXPECTED_TABLES if t not in table_names(conn)]
        results.append(("C1  all tables exist", len(missing), not missing))

        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        results.append(("C2  foreign keys intact", len(fk), not fk))

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        results.append(("C3  sqlite integrity_check is ok", 0 if integrity == "ok" else 1,
                        integrity == "ok"))

        neg = conn.execute("SELECT COUNT(*) FROM items WHERE stock_quantity < 0").fetchone()[0]
        results.append(("C4  no negative stock", neg, neg == 0))

        bad_qty = conn.execute("SELECT COUNT(*) FROM shipment_items WHERE quantity <= 0").fetchone()[0]
        results.append(("C5  every order line quantity > 0", bad_qty, bad_qty == 0))

        dupes = conn.execute("""
            SELECT COUNT(*) FROM (SELECT 1 FROM shipment_items
                                  GROUP BY shipment_id, item_id HAVING COUNT(*) > 1)
        """).fetchone()[0]
        results.append(("C6  one line per product per order", dupes, dupes == 0))

        no_events = conn.execute("""
            SELECT COUNT(*) FROM shipments s
            WHERE NOT EXISTS (SELECT 1 FROM tracking_events t WHERE t.shipment_id = s.shipment_id)
        """).fetchone()[0]
        results.append(("C7  every shipment has a tracking event", no_events, no_events == 0))

        null_price = conn.execute(
            "SELECT COUNT(*) FROM shipment_items WHERE unit_price IS NULL").fetchone()[0]
        results.append(("C8  every order line carries a price", null_price, null_price == 0))

        idx = index_names(conn)
        missing_idx = [i for i in EXPECTED_INDEXES if i not in idx]
        results.append(("C9  index plan applied", len(missing_idx), not missing_idx))

        timeline = object_sql(conn, "idx_tracking_events_lookup")
        has_tiebreak = "event_id" in timeline
        results.append(("C10 timeline index has the event_id tie-break",
                        0 if has_tiebreak else 1, has_tiebreak))

        version = user_version(conn)
        results.append((f"C11 schema version is v{SCHEMA_VERSION}",
                        abs(version - SCHEMA_VERSION), version == SCHEMA_VERSION))

        total = conn.execute(
            "SELECT IFNULL(SUM(total_amount), 0) FROM v_shipment_order_summary").fetchone()[0]
        results.append(("C12 order totals computable", 0 if total >= 0 else 1, total >= 0))
    finally:
        conn.close()

    say("")
    say(f"{'check':46} {'violations':>10}  result")
    say("-" * 68)
    failed = 0
    for name, count, ok in results:
        say(f"{name:46} {count:>10}  {'PASS' if ok else 'FAIL'}")
        failed += 0 if ok else 1
    say("-" * 68)
    say(f"{len(results) - failed}/{len(results)} checks passed")
    if failed:
        say("FAILED - do not demo on this database")
        return 1
    return 0


def status(db_path: Path) -> int:
    if not db_path.exists():
        say(f"database not found: {db_path}")
        return 1
    conn = connect(db_path)
    try:
        say(f"database   {db_path}")
        say(f"schema     v{user_version(conn)} (tool expects v{SCHEMA_VERSION})")
        say(f"size       {db_path.stat().st_size / 1024:.1f} KB")
        for table in EXPECTED_TABLES:
            try:
                n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                say(f"  {table:18} {n:>5} rows")
            except sqlite3.Error:
                say(f"  {table:18} MISSING")
        idx = sorted(index_names(conn))
        say(f"indexes    {', '.join(idx) if idx else '(none)'}")
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LMS SQLite migration & backup tool")
    parser.add_argument("action", choices=["migrate", "backup", "rebuild", "verify", "status"])
    parser.add_argument("--db", type=Path, default=None, help="database file")
    parser.add_argument("--out", type=Path, default=DEFAULT_BACKUP_DIR, help="backup directory")
    parser.add_argument("--keep", type=int, default=10, help="keep the last N backups")
    parser.add_argument("--force", action="store_true", help="skip confirmation")
    args = parser.parse_args(argv)

    db_path = (args.db or Path(os.environ.get("LMS_DB_PATH", DEFAULT_DB))).resolve()
    if args.action == "migrate":
        return migrate(db_path)
    if args.action == "backup":
        return backup(db_path, args.out, args.keep)
    if args.action == "rebuild":
        return rebuild(db_path, args.force)
    if args.action == "verify":
        return verify(db_path)
    return status(db_path)


if __name__ == "__main__":
    sys.exit(main())
