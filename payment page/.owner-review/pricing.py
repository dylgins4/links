"""Private review only. DRAFT - under owner review, not approved."""
INBOX = "dylan@smartevguides.com"
FULL_CENTS = 250000
BANDS = [(10, 2500), (25, 2000), (50, 1600), (100, 1200), (500, 900)]
# 30 devices = 10x$25 + 15x$20 + 5x$16 = $630/yr.
OFFER = {
    "title": "September 25 department offer",
    "amount": f"${FULL_CENTS / 100:,.0f} USD per year",
    "scope": "The whole department, all 152 members and every device.",
    "devices": "Individual plans are intended for personal phones. Department-owned tablets and mobile data terminals (MDTs) require the department license.",
    "refund": "A full refund if Smart EV Guides is not working for your crews within three months of licensing.",
}

def price(spec):
    if spec == {"plan": "full"}:
        return {"cents": FULL_CENTS, "bands": [], "quote": False}
    if set(spec) != {"plan", "quantity"} or spec["plan"] != "smaller":
        raise ValueError("Choose a valid review option.")
    count = spec["quantity"]
    if type(count) is not int or count < 1:
        raise ValueError("Enter a positive whole number of assigned devices.")
    if count > BANDS[-1][0]:
        return {"cents": None, "bands": [], "quote": True}
    rows, first = [], 1
    for last, rate in BANDS:
        units = min(last, count) - first + 1
        if units <= 0:
            break
        rows.append({"first": first, "last": first + units - 1, "units": units, "rate": rate})
        first = last + 1
    return {"cents": sum(row["units"] * row["rate"] for row in rows), "bands": rows, "quote": False}
