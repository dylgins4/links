"""Run from an extracted private bundle. Only allow-listed files and loopback requests are served."""
import argparse
import json
import mimetypes
import os
import re
import secrets
import sqlite3
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from checkout import Conflict, Ledger, Mock, StripeTest, Unavailable
from pricing import INBOX, OFFER, price

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PUBLIC = {"purchase.html", "favicon.svg", "assets/5c214be88758.png",
          *("assets/purchase/" + name for name in ("purchase.css", "purchase.js", "purchase-config.js"))}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, body, mime, cookie=None):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        if cookie:
            # Hosted Checkout returns by a cross-site top-level GET. Every owner POST also checks Origin.
            self.send_header("Set-Cookie", "review_browser=" + cookie + "; Path=/; HttpOnly; SameSite=Lax")
        self.end_headers()
        self.wfile.write(body)

    def reply(self, status, value):
        self.send(status, json.dumps(value).encode(), "application/json")

    def valid_host(self):
        return self.headers.get("Host") == self.server.base.removeprefix("http://")

    def owner(self):
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        item = cookies.get("review_browser")
        return item.value if item and re.fullmatch(r"[a-f0-9]{48}", item.value) else None

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {})
        path = urlsplit(self.path).path
        if path == "/offer/assets/purchase/purchase-config.js":
            offer = dict(OFFER)
            if self.server.contact:
                offer["title"] = "September 25 offer to " + self.server.contact["department"]
            config = {"invoiceEmail": INBOX, "offer": offer, "prefill": self.server.contact}
            return self.send(200, ("const purchaseConfig = Object.freeze(" + json.dumps(config) + ");").encode(), "text/javascript")
        if path in ("/owner/", "/owner/mock", "/owner/tool.js", "/REVIEW.md", "/", "/REVIEW.html"):
            source = {"/owner/": "owner.html", "/owner/mock": "owner.html", "/owner/tool.js": "tool.js",
                      "/REVIEW.md": "REVIEW.md", "/": "REVIEW.html", "/REVIEW.html": "REVIEW.html"}[path]
            file = HERE / source
        else:
            name = path.removeprefix("/offer/") if path.startswith("/offer/") else path.removeprefix("/")
            if name not in PUBLIC:
                return self.reply(404, {})
            file = ROOT / name
        cookie = secrets.token_hex(24) if path in ("/owner/", "/owner/mock") and not self.owner() else None
        return self.send(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or "text/plain", cookie)

    def do_POST(self):
        if not self.valid_host():
            return self.reply(403, {})
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= 131072:
                return self.reply(413, {})
            raw = self.rfile.read(length)
            ledger = self.server.ledger
            if self.path == "/webhook":
                ledger.webhook(raw, self.headers.get("Stripe-Signature", ""))
                return self.reply(200, {"received": True})
            owner = self.owner()
            if not owner or self.headers.get("Origin") != self.server.base:
                return self.reply(403, {})
            if self.headers.get_content_type() != "application/json":
                return self.reply(415, {})
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Invalid request.")
            if self.path == "/api/estimate":
                result = {**price(data), "mode": ledger.gateway.mode}
            elif self.path == "/api/checkout":
                result = ledger.checkout(owner, data)
            elif self.path in ("/api/status", "/api/mock-paid") and set(data) == {"ref"}:
                if self.path == "/api/mock-paid":
                    ledger.simulate_paid(owner, data["ref"])
                row = ledger.owned(owner, data["ref"])
                result = {"state": row["state"], "mode": ledger.gateway.mode, "cents": row["cents"],
                          "plan": row["plan"], "quantity": row["quantity"]}
            else:
                return self.reply(404, {})
            self.reply(200, result)
        except (ValueError, KeyError, TypeError, AttributeError):
            self.reply(400, {"error": "Invalid or unverifiable request."})
        except Conflict:
            self.reply(409, {"error": "Request conflict. Review the selection or retry later."})
        except (Unavailable, sqlite3.Error, OSError):
            self.reply(503, {"error": "Test service unavailable. Retry the same request."})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("mock", "stripe-test"))
    parser.add_argument("--port", type=int, default=8164)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--contact-file", type=Path)
    args = parser.parse_args()
    gateway = Mock() if args.mode == "mock" else StripeTest()
    contact = {}
    if args.contact_file:
        contact = json.loads(args.contact_file.read_text())
        if set(contact) != {"department", "contact", "email"} or not all(isinstance(v,str) for v in contact.values()):
            parser.error("Contact file must contain only department, contact and email strings.")
    os.umask(0o077)
    args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        server.base = "http://127.0.0.1:" + str(server.server_address[1])
        server.contact = contact
        server.ledger = Ledger(args.state_dir / (args.mode + ".sqlite3"), gateway, server.base)
        print("Private " + args.mode + " review: " + server.base, flush=True)
        server.serve_forever()

if __name__ == "__main__":
    main()
