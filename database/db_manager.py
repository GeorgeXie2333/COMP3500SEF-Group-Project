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
keys before BEGIN, validate, create/copy/drop/rename, validate again, COMMIT,
re-enable). The whole upgrade rolls back on failure. Running `migrate` twice
preserves the data and schema version.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import os
import re
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
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# migration steps (each one idempotent)
# ---------------------------------------------------------------------------
def merge_duplicate_lines(conn: sqlite3.Connection) -> int:
    """UNIQUE(shipment_id, item_id) cannot be added while duplicates exist.

    Duplicated rows are merged by summing quantity. This preserves ordered units
    and leaves stock unchanged; it does not undo any historical stock deduction.
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
    """Rebuild inside the caller's transaction, after validating foreign keys."""
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


def rebuild_items(conn: sqlite3.Connection) -> None:
    """Copy unchanged values; invalid legacy data must be corrected explicitly."""
    conn.execute(ITEMS_DDL)
    conn.execute("""
        INSERT INTO items_new (item_id, item_name, sku, stock_quantity, unit_price)
        SELECT item_id, item_name, sku, stock_quantity, unit_price FROM items
    """)
    conn.execute("DROP TABLE items")
    conn.execute("ALTER TABLE items_new RENAME TO items")


def check_foreign_keys(conn: sqlite3.Connection) -> None:
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise sqlite3.IntegrityError(
            f"{len(violations)} foreign-key violation(s); repair the source data before migrating")


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
    conn = connect(db_path)
    try:
        if user_version(conn) > SCHEMA_VERSION:
            raise ValueError("database was created by a newer schema version; refusing to downgrade")
        tables = table_names(conn)
        if not tables:
            say(f"creating a new database from {SCHEMA_PATH.name} ...")
            create_schema(conn)
            say(f"OK  {db_path} is at schema v{SCHEMA_VERSION}")
            return 0

        missing = set(EXPECTED_TABLES) - tables
        if missing:
            raise ValueError("unsupported or incomplete database; missing tables: "
                             + ", ".join(sorted(missing)))
        say(f"migrating {db_path} ...")
        steps = 0
        # One transaction covers data repair, both rebuilds, indexes and version.
        # FK enforcement must be disabled before BEGIN for SQLite table rebuilds.
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN IMMEDIATE")
        check_foreign_keys(conn)
        if conn.execute("SELECT 1 FROM shipment_items WHERE quantity <= 0 LIMIT 1").fetchone():
            raise sqlite3.IntegrityError("invalid order quantity; repair the source data before migrating")
        sequences = conn.execute(
            "SELECT name, seq FROM sqlite_sequence WHERE name IN ('items', 'shipment_items')"
        ).fetchall()
        # These objects reference the tables being replaced. Recreate them only
        # after both renames, within the same transaction.
        conn.execute("DROP VIEW IF EXISTS v_shipment_order_summary")
        conn.execute("DROP TRIGGER IF EXISTS trg_shipment_items_price")

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

        for name, seq in sequences:
            if conn.execute("SELECT 1 FROM sqlite_sequence WHERE name = ?", (name,)).fetchone():
                conn.execute("UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = ?", (seq, name))
            else:
                conn.execute("INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (name, seq))

        if ensure_timeline_index(conn):
            say("  - upgraded idx_tracking_events_lookup with the event_id tie-break")
            steps += 1

        created = ensure_indexes(conn)
        if created:
            say(f"  - created {created} index(es)")
            steps += 1

        ensure_trigger_and_view(conn)
        check_foreign_keys(conn)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.execute("COMMIT")

        say("  already up to date" if steps == 0 else f"  applied {steps} change set(s)")
        say(f"OK  {db_path} is at schema v{SCHEMA_VERSION}")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


# ---------------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------------
def backup(db_path: Path, out_dir: Path, keep: int) -> int:
    if not db_path.exists():
        say(f"ERROR database not found: {db_path}")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    # Exclusive reservation also handles repeated calls within one clock tick.
    suffix = 0
    while True:
        db_file = out_dir / f"{db_path.stem}_{stamp}_{suffix:06d}.db"
        try:
            with db_file.open("xb"):
                pass
            break
        except FileExistsError:
            suffix += 1
    sql_file = db_file.with_suffix(".sql")

    try:
        with closing(connect(db_path)) as src, closing(sqlite3.connect(db_file)) as dst:
            src.backup(dst)
            # Dump the completed copy, so both formats describe the same instant
            # even while the application keeps writing to the source database.
            with sql_file.open("w", encoding="utf-8") as fh:
                fh.write(f"-- {db_path.name} dump {stamp}\n")
                for line in dst.iterdump():
                    fh.write(line + "\n")
                # iterdump includes BEGIN/COMMIT, but omits user_version.
                fh.write(f"PRAGMA user_version = {user_version(dst)};\n")
    except Exception:
        db_file.unlink(missing_ok=True)
        sql_file.unlink(missing_ok=True)
        raise

    digest = hashlib.sha256(db_file.read_bytes()).hexdigest()
    say(f"OK  {db_file}  ({db_file.stat().st_size / 1024:.1f} KB)")
    say(f"OK  {sql_file} ({sql_file.stat().st_size / 1024:.1f} KB)")
    say(f"    sha256 {digest}")

    # Match this database's generated names only. A shared backup directory may
    # also contain backups for e.g. lms_archive.db, which share the lms_ prefix.
    backup_name = re.compile(
        re.escape(db_path.stem) + r"_\d{8}-\d{6}(?:-\d{6}_\d+)?\.db")
    pairs = sorted(path for path in out_dir.iterdir() if backup_name.fullmatch(path.name))
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
    try:
        if args.action == "migrate":
            return migrate(db_path)
        if args.action == "backup":
            return backup(db_path, args.out, args.keep)
        if args.action == "rebuild":
            return rebuild(db_path, args.force)
        if args.action == "verify":
            return verify(db_path)
        return status(db_path)
    except (sqlite3.Error, OSError, ValueError) as error:
        say(f"ERROR {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
