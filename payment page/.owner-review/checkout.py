"""Local-only test checkout. Money and fulfillment state are server-owned."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from contextlib import closing
from urllib import error, parse, request

from pricing import price

class Conflict(Exception):
    pass

class Unavailable(Exception):
    pass

class StripeTest:
    mode = "stripe-test"

    def __init__(self):
        self.key = os.getenv("STRIPE_TEST_SECRET_KEY", "")
        self.signing = os.getenv("STRIPE_TEST_WEBHOOK_SECRET", "").encode()
        if not re.fullmatch(r"(sk|rk)_test_[A-Za-z0-9_]+", self.key) or not re.fullmatch(rb"whsec_[A-Za-z0-9_]+", self.signing):
            raise SystemExit("Stripe test mode requires a sandbox secret key and its endpoint signing secret.")

    def create(self, order, base):
        fields = {
            "mode": "payment", "payment_method_types[0]": "card",
            "success_url": base + "/owner/?result=" + order["ref"],
            "cancel_url": base + "/owner/?cancel=" + order["ref"],
            "client_reference_id": order["ref"],
            "line_items[0][quantity]": "1", "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][unit_amount]": str(order["cents"]),
            "line_items[0][price_data][product_data][name]": "TEST annual department license — " + (
                "full department" if order["plan"] == "full" else str(order["quantity"]) + " proposed assigned devices"),
        }
        req = request.Request("https://api.stripe.com/v1/checkout/sessions", parse.urlencode(fields).encode(),
            headers={"Authorization": "Bearer " + self.key, "Idempotency-Key": order["ref"],
                     "Stripe-Version": "2024-06-20", "Content-Type": "application/x-www-form-urlencoded"})
        class NoRedirect(request.HTTPRedirectHandler):
            def redirect_request(self, *args):
                return None
        try:
            with request.build_opener(NoRedirect).open(req, timeout=12) as response:
                session = json.load(response)
        except (error.URLError, TimeoutError, ValueError) as exc:
            raise Unavailable("Test checkout unavailable. Retry this request.") from exc
        if parse.urlsplit(session.get("url") or "").netloc != "checkout.stripe.com" or not session["url"].startswith("https://"):
            raise Unavailable("Unexpected checkout destination.")
        return session

class Mock:
    mode = "mock"

    def __init__(self):
        self.signing = secrets.token_bytes(32)

    def create(self, order, base):
        return {"id": "cs_test_mock_" + order["ref"], "object": "checkout.session", "livemode": False,
                "mode": "payment", "currency": "usd", "amount_total": order["cents"],
                "client_reference_id": order["ref"], "url": "/owner/mock?ref=" + order["ref"]}

def matches(session, order):
    return (session.get("object") == "checkout.session" and session.get("livemode") is False
            and session.get("mode") == "payment" and session.get("currency") == "usd"
            and type(session.get("amount_total")) is int and session["amount_total"] == order["cents"]
            and session.get("client_reference_id") == order["ref"])

class Ledger:
    def __init__(self, path, gateway, base):
        self.path, self.gateway, self.base = path, gateway, base
        with closing(self.connect()) as db, db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS orders (
                ref TEXT PRIMARY KEY, owner TEXT NOT NULL, retry_key TEXT NOT NULL, plan TEXT NOT NULL,
                quantity INTEGER, cents INTEGER NOT NULL, created INTEGER NOT NULL, session TEXT UNIQUE,
                url TEXT, state TEXT NOT NULL DEFAULT 'awaiting_payment', UNIQUE(owner,retry_key));
              CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, ref TEXT NOT NULL);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=8)
        db.row_factory = sqlite3.Row
        return db

    def checkout(self, owner, payload):
        spec = dict(payload)
        key = spec.pop("retry", "")
        if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{32}", key):
            raise ValueError("Missing request key.")
        estimate = price(spec)
        if estimate["quote"]:
            raise ValueError("Request a quote for this quantity.")
        selection = (spec["plan"], spec.get("quantity"), estimate["cents"])
        with closing(self.connect()) as db, db:
            db.execute("""INSERT INTO orders(ref,owner,retry_key,plan,quantity,cents,created)
                       VALUES(?,?,?,?,?,?,?) ON CONFLICT(owner,retry_key) DO NOTHING""",
                       (uuid.uuid4().hex, owner, key, *selection, int(time.time())))
            order = db.execute("SELECT * FROM orders WHERE owner=? AND retry_key=?", (owner, key)).fetchone()
            if tuple(order[k] for k in ("plan", "quantity", "cents")) != selection:
                raise Conflict("This request has a different selection.")
        if order["state"] != "awaiting_payment":
            return {"url": "/owner/?result=" + order["ref"]}
        if order["session"]:
            return {"url": order["url"]}
        if time.time() - order["created"] >= 23 * 3600:
            raise Conflict("This incomplete request requires manual reconciliation.")
        session = self.gateway.create(order, self.base)
        if not matches(session, order) or not str(session.get("id", "")).startswith("cs_test_"):
            raise Unavailable("Test session details could not be verified.")
        with closing(self.connect()) as db, db:
            updated = db.execute("UPDATE orders SET session=?,url=? WHERE ref=? AND (session IS NULL OR session=?)",
                                 (session["id"], session["url"], order["ref"], session["id"]))
            if updated.rowcount != 1:
                raise Conflict("Session reconciliation required.")
        return {"url": session["url"]}

    def owned(self, owner, ref):
        with closing(self.connect()) as db:
            row = db.execute("SELECT * FROM orders WHERE ref=? AND owner=?", (ref, owner)).fetchone()
        if row is None:
            raise ValueError("Request unavailable.")
        return row

    def webhook(self, raw, signature):
        parts = [s.strip().partition("=") for s in signature.split(",")]
        stamps = [v for k, _, v in parts if k == "t"]
        if len(stamps) != 1 or not re.fullmatch(r"[0-9]{1,12}", stamps[0]) or abs(time.time() - int(stamps[0])) > 300:
            raise ValueError("Invalid signature timestamp.")
        expected = hmac.digest(self.gateway.signing, stamps[0].encode() + b"." + raw, hashlib.sha256).hex()
        if not any(k == "v1" and re.fullmatch(r"[0-9a-f]{64}", v) and hmac.compare_digest(v, expected) for k, _, v in parts):
            raise ValueError("Invalid signature.")
        event = json.loads(raw)
        if not isinstance(event, dict) or event.get("livemode") is not False or not isinstance(event.get("id"), str) or not event["id"]:
            raise ValueError("Invalid test event.")
        states = {"checkout.session.completed": "pending_manual_activation",
                  "checkout.session.async_payment_succeeded": "pending_manual_activation",
                  "checkout.session.async_payment_failed": "payment_failed", "checkout.session.expired": "expired"}
        state = states.get(event.get("type"))
        if state is None:
            return
        session = event.get("data", {}).get("object", {})
        if not isinstance(session, dict):
            raise ValueError("Invalid session.")
        if state == "pending_manual_activation" and session.get("payment_status") != "paid":
            return
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            order = db.execute("SELECT * FROM orders WHERE ref=?", (session.get("client_reference_id"),)).fetchone()
            if order is None or not matches(session, order):
                raise ValueError("Payment does not match a local test request.")
            if not order["session"]:
                raise Conflict("Session registration pending. Retry delivery.")
            if session.get("id") != order["session"]:
                raise ValueError("Payment session mismatch.")
            previous = db.execute("SELECT ref FROM events WHERE id=?", (event["id"],)).fetchone()
            if previous:
                if previous["ref"] != order["ref"]:
                    raise ValueError("Event reference mismatch.")
                return
            db.execute("INSERT INTO events VALUES(?,?)", (event["id"], order["ref"]))
            db.execute("UPDATE orders SET state=? WHERE ref=? AND state<>'pending_manual_activation'", (state, order["ref"]))

    def simulate_paid(self, owner, ref):
        if self.gateway.mode != "mock":
            raise ValueError("Simulation unavailable.")
        order = self.owned(owner, ref)
        session = self.gateway.create(order, self.base)
        session["payment_status"] = "paid"
        raw = json.dumps({"id": "evt_mock_" + ref, "livemode": False, "type": "checkout.session.completed",
                          "data": {"object": session}}).encode()
        stamp = str(int(time.time()))
        signature = hmac.digest(self.gateway.signing, stamp.encode() + b"." + raw, "sha256").hex()
        self.webhook(raw, "t=" + stamp + ",v1=" + signature)
