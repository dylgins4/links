# Smart EV Guides private project handoff

Checkpoint 57899bc59e197fa08ad78ceb46e11f3dfca9ee89 on the Cloud-only branch review/department-purchase. Original patch base 6f241c684acb772eeb37cbcba212ce7d9ef80e82 in dylgins4/links. Feature work is stopped at this checkpoint. No push, PR, deployment, Stripe resource creation, charge, email transmission or access change.

## Run the review

From the extracted ZIP root, using Python 3.10 or later:

    python3 -B .owner-review/serve.py --mode mock --port 8175 --state-dir ../department-review-state

Open http://127.0.0.1:8175/ on the computer running the command. The owner comparison links to both request forms and the calculator. Test checkout ends at pending manual activation. Press Ctrl+C to stop. No third-party Python packages are needed by the server.

In the existing Cloud environment the checkout is /workspace/links and the running loopback port is 8164. The private local contact override is /workspace/work/license-request/private/contact.json. To restart the identical owner-local preview after stopping the existing instance:

    cd /workspace/links
    python3 -B .owner-review/serve.py --mode mock --port 8164 --state-dir /workspace/work/license-request/state --contact-file /workspace/work/license-request/private/contact.json

The ZIP, patch, screenshots, copyable source and test evidence contain no identifying customer contact data. The transferable offer path starts with blank editable contacts. The Cloud-only copy has the requested three prefills. The original logo and favicon are bundled.

## Continue in a fresh local CLI session

Use the extracted folder as the CLI working directory, or apply department-purchase.patch in a clean site checkout at the base above:

    git switch -c review/local-department-license 6f241c6
    git apply --check /absolute/path/to/department-purchase.patch
    git apply /absolute/path/to/department-purchase.patch
    python3 -B -m unittest discover -s .owner-review -p 'test_*.py' -v

The frontend is purchase.html and assets/purchase/. The private backend, calculator, owner comparison and launch gates are in .owner-review/. Read .owner-review/REVIEW.md before making production decisions. SOURCE.md contains the complete changed source in fenced blocks. TEST-RESULTS.txt records the checks. screenshots/ contains six captures. evidence/browser_check.py is the exact Cloud browser QA script used for the captures; its paths refer to that Cloud workspace.

## Stripe access boundary

There is no callable Stripe MCP in this Cloud thread. The Cloud Codex CLI exists; its MCP list contained zero registered servers. The Stripe and Claude CLIs are absent here. No Stripe test credential binding or webhook signing secret was available. There is no authorized execution bridge from this session to the owner's machine. The owner's reported local MCP connection has not been independently verified from here.

A Codex CLI session launched by the owner on the machine holding the MCP registration can inspect its own MCP tool list and permitted test/read-only capabilities. Use codex mcp list there to verify registration; do not copy credentials into chat. MCP registration alone does not supply a running Python backend with an API key or matching webhook secret. No new login link is needed for this local mock review.

Real Stripe sandbox E2E remains unverified. See .owner-review/REVIEW.md for exact sandbox, pricing, finance, hosting, fulfillment and owner sign-off gates. The prepared adapter accepts only test credentials and fails closed. The one-time annual collection mechanic and proposed smaller schedule await owner approval.
