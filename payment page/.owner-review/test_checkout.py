import concurrent.futures
import hashlib
import hmac
import io
import json
import os
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

from checkout import Conflict, Ledger, Mock, StripeTest, Unavailable
from pricing import price

class CheckoutTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.gateway = Mock()
        self.ledger = Ledger(Path(tmp.name) / "mock.sqlite3", self.gateway, "http://127.0.0.1:8164")
        self.payload = {"plan": "smaller", "quantity": 20, "retry": "a" * 32}

    def order(self):
        url = self.ledger.checkout("one", self.payload)["url"]
        return self.ledger.owned("one", url.split("=")[-1])

    def event(self, order, kind="checkout.session.completed", identifier="evt_example", **changes):
        session = self.gateway.create(order, "")
        session.update({"payment_status": "paid", **changes})
        return {"id": identifier, "livemode": False, "type": kind, "data": {"object": session}}

    def deliver(self, event, offset=0, secret=None):
        raw = json.dumps(event).encode()
        stamp = str(int(time.time()) + offset)
        sig = hmac.digest(secret or self.gateway.signing, stamp.encode() + b"." + raw, hashlib.sha256).hex()
        self.ledger.webhook(raw, "t=" + stamp + ",v1=" + sig)

    def test_marginal_and_full(self):
        expected = {1:2500, 10:25000, 11:27000, 20:45000, 25:55000, 26:56600,
                    30:63000, 50:95000, 51:96200, 100:155000, 101:155900, 500:515000}
        for count, cents in expected.items():
            self.assertEqual(price({"plan":"smaller","quantity":count})["cents"], cents)
        self.assertTrue(price({"plan":"smaller","quantity":501})["quote"])
        self.assertEqual(price({"plan":"full"})["cents"], 250000)

    def test_client_inputs_do_not_price_orders(self):
        for extra in ({"amount":1}, {"currency":"cad"}, {"quantity":501}, {"quantity":True},
                      {"quantity":0}, {"quantity":2.5}, {"plan":"full"}, {"plan":"unknown"}):
            with self.assertRaises(ValueError):
                self.ledger.checkout("one", {**self.payload, **extra})

    def test_concurrent_retry(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            urls = list(pool.map(lambda _: self.ledger.checkout("one", self.payload)["url"], range(12)))
        self.assertEqual(len(set(urls)), 1)
        with self.assertRaises(Conflict):
            self.ledger.checkout("one", {**self.payload, "quantity":21})

    def test_browser_isolation(self):
        row = self.order()
        with self.assertRaises(ValueError):
            self.ledger.owned("two", row["ref"])
        self.assertEqual(row["state"], "awaiting_payment")

    def test_signature_and_freshness(self):
        row = self.order()
        for stamp, secret in [(0,b"invalid-mock-key"), (-400,None), (400,None)]:
            with self.assertRaises(ValueError):
                self.deliver(self.event(row), stamp, secret)
        self.assertEqual(self.ledger.owned("one", row["ref"])["state"], "awaiting_payment")

    def test_session_binding(self):
        row = self.order()
        for delta in [{"amount_total":45001}, {"currency":"cad"}, {"mode":"subscription"}, {"id":"wrong"},
                      {"livemode":True}, {"client_reference_id":"unknown"}]:
            with self.assertRaises(ValueError):
                self.deliver(self.event(row, **delta))
        event = self.event(row)
        event["livemode"] = True
        with self.assertRaises(ValueError):
            self.deliver(event)
        self.assertEqual(self.ledger.owned("one", row["ref"])["state"], "awaiting_payment")

    def test_paid_only_once_across_restart(self):
        row = self.order()
        self.deliver(self.event(row, payment_status="unpaid"))
        self.assertEqual(self.ledger.owned("one", row["ref"])["state"], "awaiting_payment")
        self.deliver(self.event(row, "checkout.session.async_payment_succeeded"))
        self.ledger = Ledger(self.ledger.path, self.gateway, self.ledger.base)
        self.deliver(self.event(row, "checkout.session.async_payment_succeeded"))
        with closing(self.ledger.connect()) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0], 1)
        self.deliver(self.event(row, "checkout.session.expired", "evt_late", payment_status="unpaid"))
        self.assertEqual(self.ledger.owned("one", row["ref"])["state"], "pending_manual_activation")

    def test_failed_or_expired_not_activated(self):
        row = self.order()
        for kind, status in [("checkout.session.async_payment_failed","payment_failed"),("checkout.session.expired","expired")]:
            self.deliver(self.event(row, kind, kind, payment_status="unpaid"))
            self.assertEqual(self.ledger.owned("one", row["ref"])["state"], status)

    def test_uncertain_session_retry(self):
        original = self.gateway.create
        with patch.object(self.gateway, "create", side_effect=Unavailable("timeout")):
            with self.assertRaises(Unavailable):
                self.order()
        with patch.object(self.gateway, "create", wraps=original):
            row = self.order()
        with closing(self.ledger.connect()) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM orders").fetchone()[0], 1)
        self.assertEqual(row["cents"], 45000)

    def test_test_bindings_required(self):
        for key, signing in [("",""), ("sk_live_dummy","whsec_dummy"), ("sk_test_dummy","")]:
            with patch.dict(os.environ, {"STRIPE_TEST_SECRET_KEY":key,"STRIPE_TEST_WEBHOOK_SECRET":signing}, clear=True):
                with self.assertRaises(SystemExit):
                    StripeTest()

    def test_stripe_adapter_contract_without_network(self):
        row = self.order()
        session = self.gateway.create(row, "")
        session["url"] = "https://checkout.stripe.com/c/pay/test-fixture"
        with patch.dict(os.environ, {"STRIPE_TEST_SECRET_KEY":"sk_test_dummy","STRIPE_TEST_WEBHOOK_SECRET":"whsec_dummy"}):
            adapter = StripeTest()
        with patch("checkout.request.build_opener") as factory:
            factory.return_value.open.return_value = io.BytesIO(json.dumps(session).encode())
            self.assertEqual(adapter.create(row, self.ledger.base), session)
            req = factory.return_value.open.call_args.args[0]
            args = parse_qs(req.data.decode())
            self.assertEqual(args["mode"], ["payment"])
            self.assertEqual(args["line_items[0][price_data][unit_amount]"], ["45000"])
            self.assertEqual(args["line_items[0][price_data][currency]"], ["usd"])
            self.assertEqual(req.get_header("Idempotency-key"), row["ref"])
            self.assertEqual(args["client_reference_id"], [row["ref"]])
            self.assertNotIn("subscription_data", args)

    def test_wrong_created_session_is_rejected(self):
        original = self.gateway.create
        def unexpected(order, base):
            return {**original(order, base), "amount_total":1}
        with patch.object(self.gateway, "create", side_effect=unexpected), self.assertRaises(Unavailable):
            self.order()
        with closing(self.ledger.connect()) as db:
            self.assertIsNone(db.execute("SELECT session FROM orders").fetchone()[0])

    def test_http_checkout_and_signed_webhook(self):
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from urllib import request, error
        from serve import Handler
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            base = "http://127.0.0.1:" + str(server.server_port)
            server.base, server.ledger, server.contact = base, self.ledger, {}
            Thread(target=server.serve_forever, daemon=True).start()
            try:
                with request.urlopen(base + "/owner/") as response:
                    cookie = response.headers["Set-Cookie"].split(";")[0]
                headers = {"Cookie":cookie, "Origin":base, "Content-Type":"application/json"}
                def post(path, raw, hdr):
                    req = request.Request(base + path, data=raw, headers=hdr)
                    with request.urlopen(req) as response:
                        return json.load(response)
                payload = json.dumps(self.payload).encode()
                with self.assertRaises(error.HTTPError) as rejected:
                    post("/api/checkout", payload, {**headers, "Origin":"https://example.invalid"})
                self.assertEqual(rejected.exception.code, 403)
                with self.assertRaises(error.HTTPError) as invalid:
                    post("/api/checkout", json.dumps({**self.payload,"amount":1}).encode(), headers)
                self.assertEqual(invalid.exception.code, 400)
                ref = post("/api/checkout", payload, headers)["url"].split("=")[-1]
                row = self.ledger.owned(cookie.split("=")[1], ref)
                raw = json.dumps(self.event(row)).encode()
                stamp = str(int(time.time()))
                sig = hmac.digest(self.gateway.signing, stamp.encode() + b"." + raw, "sha256").hex()
                hook = {"Stripe-Signature":"t=" + stamp + ",v1=" + sig}
                with self.assertRaises(error.HTTPError) as bad:
                    post("/webhook", raw + b" ", hook)
                self.assertEqual(bad.exception.code, 400)
                for _ in range(2):
                    self.assertTrue(post("/webhook", raw, hook)["received"])
                status = post("/api/status", json.dumps({"ref":ref}).encode(), headers)
                self.assertEqual((status["state"],status["cents"]), ("pending_manual_activation",45000))
            finally:
                server.shutdown()
