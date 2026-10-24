# database/ - schema, migration and backup

Owner: CEN Yin Chi (Database Engineer). Review schema changes with the affected module
owners (see `docs/PROJECT.md`).

| File | What it is |
| :--- | :--- |
| `schema.sql` | The schema (v1.2) **and** the seed data. `backend/server.py` runs it only when the database has no tables yet. |
| `db_manager.py` | Migration / backup / clean-rebuild / verify tool. Standard library only, no dependencies. |
| `backups/` | Output of `db_manager.py backup`. Do not commit it (`*.db` and the SQL dumps contain data). |

## Commands

Run from the repository root:

```bash
python database/db_manager.py migrate    # upgrade an existing backend/lms.db to v1.2
python database/db_manager.py verify     # integrity checks; exit code 1 means stop
python database/db_manager.py backup     # binary copy + SQL dump into database/backups/
python database/db_manager.py rebuild    # delete, recreate, seed (asks for confirmation)
python database/db_manager.py status     # schema version, row counts, indexes
```

`--db PATH` points at another database file (useful for a scratch copy); `LMS_DB_PATH` is
honoured as well, like the backend.

## When to use which

| Situation | Command |
| :--- | :--- |
| `backend/lms.db` already exists and `schema.sql` changed | `migrate`, then `verify` |
| Fresh checkout, no database yet | nothing - `python backend/server.py` creates it |
| Demo database is broken and time is short | `rebuild` (a few seconds) |
| Before merging, or before a demo | `verify` |
| Weekly, or before a risky change | `backup` |

`migrate` is idempotent: running it twice changes nothing. It is also the only command that
keeps existing rows - `rebuild` throws them away.

## What v1.2 changed

1. `shipment_items.unit_price` - the price snapshot taken at order time. Filled by trigger
   `trg_shipment_items_price`, so `backend/server.py` needs no change and an explicitly
   supplied price is never overwritten.
2. Guards: `stock_quantity >= 0`, `quantity > 0`, `sku NOT NULL`, and
   `UNIQUE (shipment_id, item_id)` so one product cannot be booked twice in one order.
3. Indexes from `docs/index-plan.md`, including the `event_id` tie-break on the timeline
   index.
4. `v_shipment_order_summary` - line count, units and amount per order in one place.

Existing databases receive all of this through `migrate`: SQLite cannot add a `CHECK` or a
`UNIQUE` constraint in place, so the two tables that need them are rebuilt with the
documented 12-step procedure (disable foreign keys, create the new table, copy, drop,
rename, re-enable, verify).

## Tests

```bash
python -m unittest discover -s tests -v
```

`tests/test_database.py` covers the schema, the guards, the price trigger, the order
summary, the index plan, the v1.1 -> v1.2 migration and backup/restore.
