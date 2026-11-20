(function () {
  "use strict";
  // Display only. Must match Stripe price price_1UdvD3LLmx5C29mwSsMc44ob (graduated, USD, yearly).
  // The Stripe payment link enforces min 2 / max 1000 devices; above that we quote.
  // Checkout worker (EV_app/online/checkout-worker) opens Stripe with the chosen device count.
  var CHECKOUT = "https://sevg-checkout.dylan-ginsber.workers.dev/checkout";
  var TIERS = [[10, 25], [25, 23], [50, 21], [100, 19], [Infinity, 17]], MIN = 2, MAX = 1000;
  var el = function (id) { return document.getElementById(id); };
  var input = el("devices"), slider = el("slider");
  if (!input) return;
  var fmt = function (n) { return "$" + n.toLocaleString("en-US", { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 }); };

  if (/[?&]paid=1\b/.test(location.search)) {
    el("paid").classList.add("on");
    if (window.posthog) posthog.capture("department_checkout_completed");
  }

  var lo = 1;
  el("rates").innerHTML = TIERS.map(function (t, i) {
    var r = '<tr data-i="' + i + '"><td>' + (i === 0 ? MIN : lo) + (t[0] === Infinity ? "+" : "–" + t[0]) + "</td><td>$" + t[1] + "</td></tr>";
    lo = t[0] + 1; return r;
  }).join("");

  function price(n) {
    var rows = [], from = 1, total = 0;
    for (var i = 0; i < TIERS.length && from <= n; i++) {
      var to = Math.min(TIERS[i][0], n), units = to - from + 1;
      rows.push({ i: i, lo: from, hi: to, units: units, rate: TIERS[i][1] });
      total += units * TIERS[i][1]; from = TIERS[i][0] + 1;
    }
    return { total: total, rows: rows };
  }
  function render(n, src) {
    var over = n > MAX, hits = {};
    el("priced").style.display = over ? "none" : "";
    el("quote").classList.toggle("on", over);
    if (src !== "slider") slider.value = Math.min(n, +slider.max);
    if (src !== "input") input.value = n;
    if (!over) {
      var p = price(n);
      el("amt").textContent = fmt(p.total);
      el("avg").textContent = fmt(Math.round(p.total / n * 100) / 100) + " per device on average";
      el("breakdown").innerHTML = p.rows.length > 1 ? p.rows.map(function (r) {
        return "<li><span>" + r.units + " × $" + r.rate + " (" + r.lo + "–" + r.hi + ")</span><span>" + fmt(r.units * r.rate) + "</span></li>";
      }).join("") : "";
      p.rows.forEach(function (r) { hits[r.i] = 1; });
      el("checkout").href = CHECKOUT + "?qty=" + n;
    }
    [].forEach.call(document.querySelectorAll("#rates tr"), function (tr) {
      tr.classList.toggle("hit", over ? +tr.dataset.i === TIERS.length - 1 : !!hits[tr.dataset.i]);
    });
  }
  function clean(v) { v = Math.floor(Number(v)); return isFinite(v) && v >= MIN ? v : MIN; }
  input.addEventListener("input", function () { if (input.value !== "" && +input.value >= MIN) render(clean(input.value), "input"); });
  input.addEventListener("blur", function () { render(clean(input.value)); });
  slider.addEventListener("input", function () { render(clean(slider.value), "slider"); });
  el("minus").addEventListener("click", function () { render(Math.max(MIN, clean(input.value) - 1)); });
  el("plus").addEventListener("click", function () { render(clean(input.value) + 1); });
  el("checkout").addEventListener("click", function () {
    var n = clean(input.value);
    if (window.posthog) posthog.capture("department_checkout_click", { devices: n, annual_usd: price(n).total });
  });
  render(clean(input.value));
})();
