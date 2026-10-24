# Database Index Plan (v1.2, P2 / Task #24)

**Author:** CEN Yin Chi (Database Engineer)
**Target database:** SQLite (`backend/lms.db`, overridable with `LMS_DB_PATH`)
**Schema version:** v1.2 (v1.1 from PR #4 plus the additive changes listed in §6)
**Related tooling:** `database/db_manager.py` (`migrate` / `backup` / `rebuild` / `verify`)

## 1. Overview

The backend (`backend/server.py`) uses hand-written SQLite statements. Its current reads
are login/profile lookups, unfiltered shipment and inventory lists, order-line expansion,
and individual shipment/event/hub/item lookups. Most point lookups already use primary
keys or UNIQUE constraints.

The additional indexes below also support planned reporting and tracking queries and
foreign-key child lookups. The backend does not yet expose filtered shipment lists, a
timeline read endpoint, hub feeds or KPI reports. Example query plans demonstrate those
access paths; they are not measurements of existing endpoint speedups. All indexes add
storage and write overhead, so revisit the planned indexes when those features arrive.

All new statements use `CREATE INDEX IF NOT EXISTS`, so the block is idempotent: it can be
re-applied to a freshly migrated database or to a populated one without error and without
touching existing rows.

## 2. Lookups that are already indexed - deliberately no new index

SQLite creates an implicit index for every `PRIMARY KEY` and `UNIQUE` constraint. Adding a
second index on the same column would double the write cost and would never be chosen by
the planner.

| Column | Existing implicit index | Backend access path | Action |
| :--- | :--- | :--- | :--- |
| `shipments.tracking_number` | `UNIQUE` -> `sqlite_autoindex_shipments_1` | INSERT uniqueness enforcement; future tracking-number lookup | none |
| `items.sku` | `UNIQUE` -> `sqlite_autoindex_items_1` | `POST /api/shipments` item lookup | none |
| `users.username` | `UNIQUE` -> `sqlite_autoindex_users_1` | `POST /api/auth/login` credential lookup | none |
| `users.user_id`, `hubs.hub_id`, `shipments.shipment_id`, `tracking_events.event_id` | rowid primary key | `get_shipment`, hub validation, status update | none |
| `shipment_items.shipment_id` | `UNIQUE(shipment_id, item_id)` (v1.2) | order-line expansion, `ON DELETE CASCADE` | none - the unique key's leading column already covers it |

`GET /api/shipments` and `GET /api/items` intentionally scan their tables: they return all
rows ordered by their integer primary key. The shipment list joins each sender by
`users.user_id`; an index on `shipments.sender_id` does not accelerate that join direction.
Order-line expansion filters by shipment ID but orders by `shipment_item_id`, so the
composite UNIQUE key can narrow the rows while SQLite may still use a temporary sort.

## 3. Indexes in this plan

Added at the bottom of `database/schema.sql` (and applied to an existing database by
`python database/db_manager.py migrate`).

| # | Index | Target table & columns | Supported access path |
| :--- | :--- | :--- | :--- |
| A | `idx_tracking_events_lookup` *(upgraded)* | `tracking_events(shipment_id, event_time DESC, event_id DESC)` | Planned timeline with explicit `ORDER BY event_time DESC, event_id DESC`; also shipment FK child lookups. The query must request both sort keys for deterministic ordering. |
| 1 | `idx_shipments_sender_time` | `shipments(sender_id, created_at DESC)` | Planned `WHERE sender_id = ? ORDER BY created_at DESC`; sender FK child lookup. |
| 2 | `idx_shipments_status_created_at` | `shipments(status, created_at DESC)` | Planned status-filtered listing and dashboard counts. |
| 3 | `idx_shipments_current_hub_id` | `shipments(current_hub_id)` | Planned hub workload query and hub FK child lookup. |
| 4 | `idx_shipment_items_item_id` | `shipment_items(item_id)` | Planned item-level reporting and item FK child lookup. |
| 5 | `idx_tracking_events_hub_time` | `tracking_events(hub_id, event_time DESC) WHERE hub_id IS NOT NULL` | Planned hub feed and hub FK child lookup. NULL hubs are excluded from the index. |
| 6 | `idx_tracking_events_status_time` | `tracking_events(status, event_time DESC)` | Planned status history and KPI queries across shipments. |

Seven custom indexes in total. Primary-key and UNIQUE access paths are additional.

## 4. Verification

Check a scratch database rebuilt from `database/schema.sql`, and migrate it twice to
check idempotency. Planner output can vary with SQLite version and row counts:

* `PRAGMA integrity_check` -> `ok`
* `PRAGMA foreign_key_check` -> no rows (all foreign keys still valid)
* `python database/db_manager.py verify` -> 12/12 checks pass

Representative `EXPLAIN QUERY PLAN` access paths (including planned queries from §3):

| Query | Plan |
| :--- | :--- |
| status filter | `SEARCH shipments USING INDEX idx_shipments_status_created_at (status=?)` |
| my shipments | `SEARCH shipments USING COVERING INDEX idx_shipments_sender_time (sender_id=?)` |
| current hub | `SEARCH shipments USING COVERING INDEX idx_shipments_current_hub_id (current_hub_id=?)` |
| tracking number | `SEARCH shipments USING COVERING INDEX sqlite_autoindex_shipments_1 (tracking_number=?)` |
| sku lookup | `SEARCH items USING INDEX sqlite_autoindex_items_1 (sku=?)` |
| shipment timeline | `SEARCH tracking_events USING INDEX idx_tracking_events_lookup (shipment_id=?)` |
| hub feed | `SEARCH tracking_events USING COVERING INDEX idx_tracking_events_hub_time (hub_id=?)` |
| status history | `SEARCH tracking_events USING COVERING INDEX idx_tracking_events_status_time (status=?)` |
| order lines | `SEARCH shipment_items USING INDEX sqlite_autoindex_shipment_items_1 (shipment_id=?)`; the API's `ORDER BY shipment_item_id` may also need a temporary B-tree |
| item reporting | `SEARCH shipment_items USING INDEX idx_shipment_items_item_id (item_id=?)` |
| full listing | `SCAN shipments` (intentional: no predicate) |
| inventory listing | `SCAN items` (intentional: no predicate) |

To reproduce locally:

```powershell
python database/db_manager.py rebuild --db database/backups/index-plan-check.db --force
python database/db_manager.py migrate --db database/backups/index-plan-check.db
python database/db_manager.py migrate --db database/backups/index-plan-check.db
python database/db_manager.py verify  --db database/backups/index-plan-check.db
```

For example, run `EXPLAIN QUERY PLAN SELECT * FROM tracking_events WHERE shipment_id = 1
ORDER BY event_time DESC, event_id DESC LIMIT 10`. The timeline regression test checks that
this query uses `idx_tracking_events_lookup` without a temporary sort. Compare the other
queries with the actual statements and sort keys in `backend/server.py`; a full scan is
expected for an unfiltered list.

## 5. Maintenance notes

* **Write cost:** seven indexes add a small constant cost to `INSERT`/`UPDATE` on
  `shipments`, `shipment_items` and `tracking_events`. With the current data volume this is
  small, but several indexed read paths are planned and have no current API consumer.
* **When to revisit:** if a new endpoint filters on a column that is not covered here,
  extend this table and add the index in the same PR.
* `idx_tracking_events_lookup` supports timeline queries and the shipment FK. Its column list
  changed in v1.2 (the `event_id` tie-break); `db_manager.py migrate` detects the old
  two-column version and replaces it.
* `CREATE INDEX IF NOT EXISTS` is safe to re-run from the migration script, so
  `db_manager.py migrate` does not need to know whether this block already ran.

## 6. Schema guards added in the same change

The index work sits in one PR with four small schema changes; they are grouped because they
all protect the same data the indexes serve, and because a schema change has to travel
through the same review anyway. Each one is additive: no column is removed, no value is
renamed.

| Change | Why the database and not the API |
| :--- | :--- |
| `shipment_items.unit_price` (price snapshot) | New orders capture the catalogue price via `trg_shipment_items_price`. Existing v1.1 orders can only be backfilled from the catalogue price at migration time. The summary view is available to SQL consumers; the API does not yet expose it. |
| `UNIQUE(shipment_id, item_id)` | Prevents duplicate product rows. The API inserts one line per order. Migration combines existing duplicate quantities without altering stock. |
| `CHECK(stock_quantity >= 0)`, `CHECK(quantity > 0)` | The API already guards both, but a direct SQL fix or a future script could still write a negative stock row. The constraint makes that impossible rather than unlikely. |
| `items.sku NOT NULL` | A `NULL` sku is allowed by a `UNIQUE` index in SQLite, so one missing sku would silently defeat de-duplication and the API's lookup-by-sku path. |

`database/db_manager.py` supports forward migration with transaction rollback on failure;
there is no downgrade command. To restore an older schema, use a pre-migration backup.
`tests/test_database.py` checks successful upgrades, whole-transaction rollback, duplicate
consolidation, ID preservation and both backup formats.
