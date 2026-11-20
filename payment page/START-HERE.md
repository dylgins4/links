# Smart EV Guides department payment page

This folder contains the editable files from checkpoint `57899bc` on `review/department-purchase`. Open this folder as the working directory. The source is already extracted. The ZIP is a portable copy of the original checkpoint.

## Where to start

- [HANDOFF.md](HANDOFF.md) gives the original checkpoint, Git base and restart instructions.
- [.owner-review/REVIEW.md](.owner-review/REVIEW.md) records the commercial decisions and launch gates that still need owner review.
- [purchase.html](purchase.html) and [assets/purchase](assets/purchase/) contain the general quote and invoice request form. [.owner-review](.owner-review/) contains the calculator, server pricing, checkout, ledger and mock tests.
- [TEST-RESULTS.txt](TEST-RESULTS.txt) records the original test evidence. [screenshots](screenshots/) contains six captures. [The example printout](evidence/example-print.pdf) shows the full offer on paper.

## Run the private mock preview on Windows

Use PowerShell from this folder with Python 3.10 or later. The mock server uses the standard library.

```powershell
python -B -m unittest discover -s .owner-review -p "test_*.py" -v
python -B .owner-review/serve.py --mode mock --port 8175 --state-dir "$env:TEMP\smart-ev-department-review-state"
```

Open [the local owner preview](http://127.0.0.1:8175/) while the server is running. Press Ctrl+C to stop it. The historical Cloud paths in the original notes refer to the previous machine.

## Owner review scope

Preserve Whitby’s existing whole-department offer. The smaller-device pricing and terms are proposals. The mock checkout ends at pending manual activation. Real Stripe sandbox checkout and webhook delivery still need verification. Keep the work in private test preparation until the owner authorizes go-live. Deployment, pushes, PRs, live billing, customer messages, production settings and access changes are outside this handoff.
