"use strict";
const el = id => document.getElementById(id);
const form = el("calc");
const money = cents => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100) + " USD";
const query = new URLSearchParams(location.search);
const mockScreen = location.pathname === "/owner/mock";
const ref = query.get("ref") || query.get("result") || query.get("cancel");
let revision = 0;
let submitting = false;
let retryKey;
let lastSpec;
async function api(path, payload) {
  const response = await fetch("/api/" + path, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) });
  const data = await response.json();
  if (!response.ok) throw Error(data.error || "Test service unavailable.");
  return data;
}
function spec() {
  return form.elements.plan.value === "full" ? {plan:"full"} : {plan:"smaller", quantity:el("count").valueAsNumber};
}
function modeLabel(mode) {
  el("mode").textContent = mode === "mock" ? "Isolated mock · no Stripe connection" : "Stripe sandbox · test only";
}
async function estimate() {
  const version = ++revision;
  const body = spec(), small = body.plan === "smaller";
  el("units").hidden = !small;
  el("count").disabled = !small;
  el("checkout").disabled = true;
  el("breakdown").replaceChildren();
  el("total").textContent = "—";
  el("notice").textContent = "";
  el("detail").textContent = small
    ? "PROPOSED FOR APPROVAL. Each shared rig tablet counts once. Extra phones count as additional assigned devices."
    : "September 25 full-department offer. The fixed annual amount covers all 152 members and every device.";
  if (small && (!Number.isSafeInteger(body.quantity) || body.quantity < 1)) {
    el("notice").textContent = "Enter a positive whole number of assigned devices.";
    return;
  }
  try {
    const result = await api("estimate", body);
    if (version !== revision) return;
    modeLabel(result.mode);
    el("total").textContent = result.quote ? "Request a quote" : money(result.cents);
    for (const b of result.bands) {
      const line = document.createElement("p");
      line.textContent = "Devices " + b.first + "–" + b.last + " · " + b.units + " × " + money(b.rate);
      el("breakdown").append(line);
    }
    el("checkout").disabled = result.quote || submitting;
  } catch (e) { if (version === revision) el("notice").textContent = e.message; }
}
form.oninput = estimate;
form.onsubmit = async event => {
  event.preventDefault();
  if (submitting || el("checkout").disabled) return;
  submitting = true;
  el("checkout").disabled = true;
  form.querySelector("fieldset").disabled = true;
  const body = spec();
  el("count").readOnly = true;
  try {
    const selection = JSON.stringify(body);
    if (selection !== lastSpec) {
      const slot = "test-checkout-" + selection;
      retryKey = sessionStorage.getItem(slot) || crypto.randomUUID().replaceAll("-", "");
      sessionStorage.setItem(slot, retryKey);
      lastSpec = selection;
    }
    const result = await api("checkout", {...body, retry:retryKey});
    location.assign(result.url);
  } catch (e) {
    submitting = false;
    form.querySelector("fieldset").disabled = false;
    el("count").readOnly = false;
    await estimate();
    el("notice").textContent = e.message;
  }
};
async function status(confirm = false) {
  el("simulate").disabled = true;
  try {
    const data = await api(confirm ? "mock-paid" : "status", {ref});
    modeLabel(data.mode);
    el("total").textContent = money(data.cents);
    const paid = data.state === "pending_manual_activation";
    el("return-title").textContent = paid ? "Pending manual activation" : mockScreen ? "Mock payment review" : "Payment confirmation pending";
    el("return-text").textContent = paid
      ? "A verified test event was recorded. This test grants no access. Staff would reconcile payment and arrange activation."
      : mockScreen ? "This isolated simulation records a test event only when you choose to continue."
        : query.has("cancel") ? "You returned from checkout. No confirmed payment is recorded." : "The server is waiting for a verified paid event. A browser return does not confirm payment.";
    const ended = ["expired", "payment_failed"].includes(data.state);
    if (ended) {
      el("return-title").textContent = data.state === "expired" ? "Test session expired" : "Test payment failed";
      el("return-text").textContent = "No confirmed payment was recorded for this session.";
    }
    el("simulate").hidden = paid || ended || !mockScreen || data.mode !== "mock";
    el("refresh").hidden = paid || ended || mockScreen;
    el("restart").hidden = !ended && !paid;
    el("restart").onclick = () => {
      const previous = data.plan === "full" ? {plan:"full"} : {plan:"smaller", quantity:data.quantity};
      sessionStorage.removeItem("test-checkout-" + JSON.stringify(previous));
      location.assign("/owner/");
    };
    el("notice").textContent = "";
  } catch (e) { el("notice").textContent = e.message; }
  el("simulate").disabled = false;
}
if (ref || mockScreen) {
  form.hidden = true;
  el("returned").hidden = false;
  el("simulate").onclick = () => status(true);
  el("refresh").onclick = () => status();
  status();
} else estimate();
