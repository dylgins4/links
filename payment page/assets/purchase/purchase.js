(() => {
  "use strict";
  const el = id => document.getElementById(id);
  const form = el("request");
  const { invoiceEmail, prefill = {}, offer } = purchaseConfig;
  const fields = { department: "Department", contact: "Contact", email: "Work email",
    phone: "Phone", reference: "Quote or reference", po: "PO number",
    quantity: "Desired license quantity", needs: "Device and coverage needs",
    country: "Billing country", currency: "Requested billing currency" };
  const smaller = () => form.elements.scope.value === "Smaller rollout";
  const existing = () => offer && !smaller();
  const kind = () => smaller() ? "Quote request" : existing() ? "Invoice request" : el("kind").value;
  function node(tag, text) {
    const item = document.createElement(tag);
    item.textContent = text;
    return item;
  }
  function displayScope() {
    el("quantity-row").hidden = !smaller();
    el("quantity").disabled = !smaller();
    el("kind-row").hidden = smaller() || Boolean(offer);
    el("brief-label").textContent = existing() ? "Existing offer" : "Purchasing information";
    el("brief-title").textContent = existing() ? offer.title : smaller() ? "Smaller rollout" : "Full department";
    const body = el("brief-body");
    body.replaceChildren();
    if (existing()) {
      const amount = node("p", offer.amount);
      amount.className = "amount";
      body.append(amount, node("h3", "Coverage"), node("p", offer.scope), node("p", offer.devices),
        node("h3", "Refund provision"), node("p", offer.refund));
    } else {
      body.append(node("p", smaller()
        ? "Tell us how many licenses you are considering and which devices need access. Smart EV Guides will confirm the price, license unit and exact coverage in a separate quote."
        : "Include your quote reference if you have one. If you need a quote, describe the members and equipment you want to cover."),
        node("h3", "What happens next"), node("p", "Review your details, then prepare an email to Smart EV Guides. A team member will check the request and reply with the next steps."));
    }
    el("errors").textContent = "";
  }
  function review(event) {
    event.preventDefault();
    el("errors").textContent = "";
    for (const id of Object.keys(fields)) {
      const field = el(id);
      field.removeAttribute("aria-invalid");
      field.removeAttribute("aria-describedby");
      if (field.disabled) continue;
      field.value = field.value.trim();
      if (!field.validity.valid || (id === "quantity" && field.value && !Number.isSafeInteger(field.valueAsNumber))) {
        const message = field.validity.valueMissing ? "Enter " + fields[id].toLowerCase() + "."
          : id === "email" ? "Enter a valid work email address." : "Enter a whole license quantity greater than zero.";
        el("errors").textContent = message;
        field.setAttribute("aria-invalid", "true");
        field.setAttribute("aria-describedby", "errors");
        field.focus();
        return;
      }
    }
    const rows = [["Request", kind()], ["Rollout", form.elements.scope.value]];
    for (const [id, label] of Object.entries(fields)) {
      if (!el(id).disabled && el(id).value) rows.push([label, el(id).value]);
    }
    el("lines").replaceChildren(...rows.map(([label, value]) => {
      const row = document.createElement("div");
      row.append(node("dt", label), node("dd", value));
      return row;
    }));
    const subject = kind() + " — " + el("department").value;
    const lines = rows.map(([label, value]) => label + ": " + value);
    if (existing()) lines.push("", offer.title, offer.amount, offer.scope, offer.devices, offer.refund);
    if (smaller()) lines.push("", "Please confirm the price, license unit and coverage for this separate rollout.");
    lines.push("", el("terms").textContent, el("obligation").textContent);
    const body = lines.join("\r\n");
    el("draft").href = "mailto:" + invoiceEmail + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
    el("message").value = "To: " + invoiceEmail + "\nSubject: " + subject + "\n\n" + body;
    el("manual").open = false;
    el("status").textContent = "";
    showStep(true);
  }
  function showStep(reviewing) {
    form.hidden = reviewing;
    el("review").hidden = !reviewing;
    el("title").textContent = reviewing ? "Review your request" : "Request a department license";
    el("lead").textContent = reviewing ? "Check the details before preparing an email for your purchasing records."
      : "Request an invoice for an existing quote or describe the coverage your department needs.";
    el("title").focus();
  }
  for (const id of ["department", "contact", "email"]) el(id).value = prefill[id] || "";
  el("recipient").textContent = invoiceEmail;
  el("print-contact").textContent = "Purchasing contact · " + invoiceEmail;
  form.addEventListener("submit", review);
  form.addEventListener("change", e => { if (e.target.name === "scope") displayScope(); });
  form.addEventListener("input", e => {
    e.target.removeAttribute("aria-invalid");
    e.target.removeAttribute("aria-describedby");
    el("errors").textContent = "";
  });
  el("edit").onclick = () => showStep(false);
  el("print").onclick = () => window.print();
  el("copy").onclick = async () => {
    try {
      await navigator.clipboard.writeText(el("message").value);
      el("status").textContent = "Email text copied.";
    } catch {
      el("manual").open = true;
      el("message").focus();
      el("message").select();
      el("status").textContent = "Text selected. Use your device’s Copy command.";
    }
  };
  displayScope();
  el("app").hidden = false;
})();
