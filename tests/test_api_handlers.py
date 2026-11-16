"""Exercise the API handlers in process against a fresh SQLite database per test."""
import json
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from email.message import Message
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from backend.server import Handler, database_connection, initialize_database


SESSION = "sender-session"
WAYBILL = {
    "sender_id": 2,
    "receiver_name": "Lee",
    "receiver_phone": "+852-91112222",
    "delivery_address": "8 Harbour Road, Wan Chai",
    "sku": "TECH-WM-001",
    "quantity": 3,
}


class InProcessHandler(Handler):
    """Supply HTTP inputs and capture the reply without binding a socket."""

    def __init__(self, server, path, data, token):
        self.server = server
        self.path = path
        self.headers = Message()
        body = b""
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            self.headers["Content-Type"] = "application/json"
            self.headers["Content-Length"] = str(len(body))
        if token is not None:
            self.headers["Authorization"] = "Bearer " + token
        self.rfile = BytesIO(body)

    def _send(self, data, code=200):
        self.response = (code, data)


class TestAPIHandlers(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "lms.db"
        initialize_database(path)
        self.server = SimpleNamespace(database_path=path, tokens={SESSION: WAYBILL["sender_id"]})
        self.db = sqlite3.connect(path)
        self.addCleanup(self.db.close)

    def request(self, method, path, data=None, token=None):
        handler = InProcessHandler(self.server, path, data, token)
        getattr(handler, "do_" + method)()
        return handler.response

    def inventory(self):
        return dict(self.db.execute("SELECT sku, stock_quantity FROM items"))

    def shipment_row_counts(self):
        return self.db.execute("""
            SELECT (SELECT COUNT(*) FROM shipments),
                   (SELECT COUNT(*) FROM shipment_items),
                   (SELECT COUNT(*) FROM tracking_events)
        """).fetchone()

    def shipment_lines(self, shipment_id):
        return self.db.execute("""
            SELECT items.sku, shipment_items.quantity FROM shipment_items
            JOIN items USING (item_id) WHERE shipment_items.shipment_id = ?
        """, (shipment_id,)).fetchall()

    def event_statuses(self, shipment_id):
        return [row[0] for row in self.db.execute(
            "SELECT status FROM tracking_events WHERE shipment_id = ? ORDER BY event_id",
            (shipment_id,),
        )]

    def test_login_issues_a_token_for_the_returned_user(self):
        code, login = self.request(
            "POST", "/api/auth/login", {"username": "demo", "password": "demo123"}
        )
        self.assertEqual(code, 200, login)
        self.assertEqual(set(login), {"token", "token_type", "user"})
        self.assertEqual(login["token_type"], "Bearer")
        self.assertIsInstance(login["token"], str)
        self.assertTrue(login["token"])
        demo_id, = self.db.execute("SELECT user_id FROM users WHERE username = 'demo'").fetchone()
        self.assertEqual(login["user"], {"id": demo_id, "username": "demo", "role": "admin"})
        profile = self.request("GET", "/api/auth/profile", token=login["token"])
        self.assertEqual(profile, (200, login["user"]))

    def test_invalid_credentials_do_not_issue_a_session(self):
        sessions_before = self.server.tokens.copy()
        for username in ("demo", "unknown-user"):
            with self.subTest(username=username):
                credentials = {"username": username, "password": "wrong"}
                result = self.request("POST", "/api/auth/login", credentials)
                self.assertEqual(result, (401, {"error": "invalid credentials"}))
                self.assertEqual(self.server.tokens, sessions_before)

    def test_create_deducts_only_the_requested_sku_and_records_a_pending_shipment(self):
        expected_stock = self.inventory()
        expected_stock[WAYBILL["sku"]] -= WAYBILL["quantity"]
        code, shipment = self.request("POST", "/api/shipments", WAYBILL, SESSION)
        self.assertEqual(code, 201, shipment)
        self.assertEqual(shipment["status"], "pending")
        self.assertEqual(self.inventory(), expected_stock)
        self.assertEqual(self.shipment_lines(shipment["id"]), [(WAYBILL["sku"], WAYBILL["quantity"])])
        self.assertEqual(self.event_statuses(shipment["id"]), ["pending"])

    def test_insufficient_stock_returns_conflict_without_partial_writes(self):
        stock = self.inventory()
        counts = self.shipment_row_counts()
        excessive = {**WAYBILL, "quantity": stock[WAYBILL["sku"]] + 1}
        result = self.request("POST", "/api/shipments", excessive, SESSION)
        self.assertEqual(result, (409, {"error": "insufficient inventory"}))
        self.assertEqual(self.inventory(), stock)
        self.assertEqual(self.shipment_row_counts(), counts)

    def test_status_update_appends_one_event_and_preserves_inventory(self):
        shipment_id, = self.db.execute(
            "SELECT shipment_id FROM shipments WHERE tracking_number = 'HK202610001'"
        ).fetchone()
        stock = self.inventory()
        events = self.event_statuses(shipment_id)
        code, updated = self.request(
            "PATCH", f"/api/shipments/{shipment_id}/status", {"status": "delivered"}, SESSION
        )
        self.assertEqual(code, 200, updated)
        self.assertEqual((updated["id"], updated["status"]), (shipment_id, "delivered"))
        persisted = self.db.execute("SELECT status FROM shipments WHERE shipment_id = ?", (shipment_id,))
        self.assertEqual(persisted.fetchone(), ("delivered",))
        self.assertEqual(self.event_statuses(shipment_id), events + ["delivered"])
        self.assertEqual(self.inventory(), stock)

    def test_public_reads_return_only_documented_fields(self):
        health = self.request("GET", "/api/health")
        self.assertEqual(health, (200, {"status": "ok", "service": "lms-backend"}))
        code, shipments = self.request("GET", "/api/shipments")
        self.assertEqual(code, 200)
        self.assertTrue(any(shipment["items"] for shipment in shipments))
        for shipment in shipments:
            self.assertEqual(set(shipment), {
                "id", "tracking_number", "sender_id", "sender", "receiver_name", "receiver_phone",
                "delivery_address", "status", "created_at", "updated_at", "items",
            })
            for line in shipment["items"]:
                self.assertEqual(set(line), {"item_id", "sku", "item_name", "quantity"})
        code, items = self.request("GET", "/api/items")
        self.assertEqual(code, 200)
        self.assertTrue(items)
        for item in items:
            self.assertEqual(set(item), {"id", "sku", "item_name", "stock_quantity", "unit_price"})

    def test_concurrent_waybills_for_the_last_unit_commit_only_one_shipment(self):
        with self.db:
            self.db.execute("UPDATE items SET stock_quantity = 1 WHERE sku = ?", (WAYBILL["sku"],))
        counts = self.shipment_row_counts()
        both_writers_ready = threading.Event()
        writers = threading.Barrier(2, action=both_writers_ready.set, timeout=5)

        def before_statement(sql):
            # Rendezvous before SQLite starts either write transaction. With an
            # unguarded read-then-write, both requests would have read the last unit.
            if sql.lstrip().upper().startswith("BEGIN"):
                writers.wait()

        @contextmanager
        def synchronized_connection(path):
            with database_connection(path) as connection:
                connection.set_trace_callback(before_statement)
                yield connection

        def create(receiver):
            order = {**WAYBILL, "receiver_name": receiver, "quantity": 1}
            return self.request("POST", "/api/shipments", order, SESSION)

        with patch("backend.server.database_connection", synchronized_connection):
            with ThreadPoolExecutor(max_workers=2) as clients:
                responses = list(clients.map(create, ("Lee", "Chan")))

        self.assertTrue(both_writers_ready.is_set(), "both connections must reach the write transaction")
        (code, shipment), conflict = sorted(responses, key=lambda response: response[0])
        self.assertEqual(code, 201, responses)
        self.assertEqual(conflict, (409, {"error": "insufficient inventory"}))
        self.assertEqual(self.inventory()[WAYBILL["sku"]], 0)
        self.assertEqual(self.shipment_row_counts(), tuple(n + 1 for n in counts))
        self.assertEqual(self.shipment_lines(shipment["id"]), [(WAYBILL["sku"], 1)])
        self.assertEqual(self.event_statuses(shipment["id"]), ["pending"])
