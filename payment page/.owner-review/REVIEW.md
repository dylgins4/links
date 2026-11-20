# Department license review

Run with Python 3.10+ from the extracted bundle. Keep the state directory outside the site. The server binds only to the specified loopback address and serves an explicit file list.

    python3 .owner-review/serve.py --mode mock --state-dir ../department-review-state

Open http://127.0.0.1:8164/ for the comparison. Use /purchase.html for the general request, /offer/purchase.html for the existing offer, and /owner/ for the calculator and test checkout. Only the general form works by opening purchase.html directly. The server is required for the other paths. Stop it with Ctrl+C.

The downloadable bundle omits identifying contact data. The owner-local preview can load the three editable prefill values from an existing private JSON file with --contact-file PATH. Its only keys are department, contact and email. The offer belongs to its original recipient regardless of contact edits. Printed and emailed smaller-rollout requests ask for separate pricing and coverage.

## What runs today

The calculator obtains prices from pricing.py on the server. The graduated schedule is DRAFT - under owner review, not approved. The whole-department offer uses a fixed annual USD amount. Both checkout paths model a one-time payment for a year. The owner must approve that collection mechanic. The test checkout does not calculate tax.

Mock mode exchanges no Stripe traffic. Its confirmation control signs a local synthetic paid event. Stripe-test mode requires existing STRIPE_TEST_SECRET_KEY and STRIPE_TEST_WEBHOOK_SECRET bindings. Missing bindings stop startup. There is no fallback between modes. They use separate SQLite files. The live website is static and has no checkout server. The mobile app has store purchasing and entitlement logic. A compatible department-device assignment or fulfillment integration has not been verified.

A return URL only reads state. A valid, recent signed test event must match a locally created session, reference, amount and currency before a transaction records pending manual activation. No app entitlement changes. A repeated checkout request reuses the same session. An uncertain creation can be retried with the original key during the recovery window. Older unresolved attempts require manual reconciliation.

## Remaining gates

1. Approve the license unit, schedule, eligible devices and any feature parity or separate refund for a smaller rollout. Whether the proposed $9 marginal band covers plate-lookup costs is unresolved. Verify supplier costs, limits, geographic availability and reassignment/enforcement. Preserve the original full-package offer. Confirm currency individually. Do not generalize a prior customer exception or a historical CAD estimate.
2. Finance must confirm tax/exemption treatment, billing currency, accepted methods, any payment terms and documentation. Confirm whether a one-time annual card payment is suitable. Establish refund handling and manual invoice reconciliation.
3. Use an authorized Stripe sandbox with its existing test secret and matching endpoint signing secret. Run the server with --mode stripe-test. Using an approved webhook delivery path, deliver signed Checkout completion, delayed success, failure and expiry events to /webhook. Test successful and abandoned test checkout, matching totals, redelivery and reconciliation. Real Stripe end-to-end behavior remains unverified until this is done.
4. Select a private backend host, TLS, access controls and a durable backed-up ledger. Bind private offers to authorized recipients server-side. Review retention, privacy and monitoring. Isolate owner assets, contacts, pricing proposals and credentials from the public static distribution. Loopback checks and a browser correlation cookie are for local review only.
5. Assign a fulfillment owner. Match cleared payment to the agreed quote, reconcile retries and exceptions, log activation once, verify the exact grant, then email setup instructions manually. Confirm who responds to quote and invoice drafts and collects any necessary billing address later.
6. Dylan reviews the finished screens and sandbox evidence, approves the exact published files and explicitly authorizes a separate launch. Keep customer contact, live configuration changes, real charges and access changes outside this review. No automatic renewal is proposed here.

## Reproduce the integration checks

    python3 -m unittest discover -s .owner-review -p 'test_*.py' -v

The patch applies to the original website base 6f241c684acb772eeb37cbcba212ce7d9ef80e82. Apply it to a clean local checkout. The ZIP includes the original site logo and favicon for independent preview.
