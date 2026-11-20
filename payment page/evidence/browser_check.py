import json, pathlib, subprocess, sys, tempfile
from urllib.parse import urlsplit, parse_qs
from playwright.sync_api import sync_playwright, expect
from PIL import Image
from io import BytesIO

ROOT=pathlib.Path("/workspace/links")
WORK=pathlib.Path("/workspace/work/license-request")
AXE="/workspace/work/purchase-review/qa/node_modules/axe-core/axe.min.js"
def shot(page,name):
    raw=page.screenshot(full_page=True)
    Image.open(BytesIO(raw)).convert("RGB").save(WORK/"screens"/(name+".webp"),"WEBP",quality=88,method=6)
def audit(page,label):
    page.add_script_tag(path=AXE)
    issues=page.evaluate("""async () => (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.map(v=>[v.id,v.nodes.map(n=>n.target)])""")
    assert not issues,(label,issues)
def fit(page):
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
def set_contact(page):
    for key,value in {"department":"Example Fire Department","contact":"Purchasing Office","email":"purchasing@example.invalid"}.items():
        page.locator("#"+key).fill(value)
def assert_logo(page):
    assert page.locator(".brand img").evaluate("img=>img.complete && img.naturalWidth===441 && img.naturalHeight===565")
def email(page):
    u=urlsplit(page.locator("#draft").get_attribute("href"))
    assert u.scheme=="mailto" and u.path=="dylan@smartevguides.com"
    return parse_qs(u.query)["body"][0]
with tempfile.TemporaryDirectory() as state:
    proc=subprocess.Popen([sys.executable,str(ROOT/".owner-review/serve.py"),"--mode","mock","--port","0","--state-dir",state],stdout=subprocess.PIPE,text=True)
    try:
        base=proc.stdout.readline().strip().split()[-1]
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path="/usr/bin/chromium",args=["--no-sandbox"])
            page=browser.new_page(viewport={"width":1260,"height":950})
            errors=[]; external=[]
            page.on("pageerror",lambda err:errors.append(str(err)))
            page.on("request",lambda req:external.append(req.url) if not req.url.startswith(base+"/") else None)
            page.goto(base+"/purchase.html"); assert_logo(page); fit(page)
            assert "$" not in page.locator("body").inner_text()
            audit(page,"general edit"); shot(page,"01-general-form")
            page.get_by_role("button",name="Review request").click()
            expect(page.locator("#department")).to_be_focused()
            set_contact(page)
            page.locator("#email").fill("wrong"); page.locator("button[type=submit]").click()
            expect(page.locator("#email")).to_be_focused()
            set_contact(page)
            page.locator("#reference").fill("REF #2 & 10%"); page.locator("#billing summary").click()
            page.locator("#currency").select_option("CAD"); page.locator("#po").fill("Example PO")
            page.locator("button[type=submit]").click()
            expect(page.locator("#title")).to_be_focused()
            assert "REF #2 & 10%" in email(page) and "CAD" in email(page)
            assert "$" not in email(page)
            await_copy="window.__copied = ''; Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async s=>{window.__copied=s}}})"
            page.evaluate(await_copy); page.locator("#copy").click()
            assert page.evaluate("window.__copied")==page.locator("#message").input_value()
            page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error()}}})")
            page.locator("#copy").click(); expect(page.locator("#message")).to_be_focused()
            assert page.locator("#message").evaluate("x=>x.selectionEnd-x.selectionStart===x.value.length")
            page.locator("#edit").click(); expect(page.locator("#po")).to_have_value("Example PO")
            page.locator('input[value="Smaller rollout"]').check(); expect(page.locator("#quantity")).to_have_value("")
            page.locator("#quantity").fill("2.5"); page.locator("button[type=submit]").click()
            expect(page.locator("#quantity")).to_be_focused()
            page.locator("#quantity").fill("20"); page.locator("#needs").fill("Shared tablets and phones.")
            page.locator("button[type=submit]").click()
            assert "Desired license quantity: 20" in email(page) and "$" not in email(page) and "Refund" not in email(page)
            page.goto(base+"/offer/purchase.html"); set_contact(page); assert_logo(page)
            expect(page.locator("#brief-body")).to_contain_text("$2,500 USD per year")
            page.locator("button[type=submit]").click()
            body=email(page)
            assert all(s in body for s in ["$2,500 USD per year","152 members","three months","MDTs"])
            audit(page,"existing offer review"); shot(page,"02-full-offer-review")
            page.pdf(path=str(WORK/"full-offer-print.pdf"),format="Letter")
            page.locator("#edit").click(); page.locator('input[value="Smaller rollout"]').check()
            page.locator("#quantity").fill("20"); page.locator("button[type=submit]").click()
            assert "$" not in email(page) and "three months" not in email(page)
            for width in [320,390,768,1024]:
                page.set_viewport_size({"width":width,"height":844}); fit(page)
            page.set_viewport_size({"width":390,"height":844}); shot(page,"03-mobile-smaller-request"); audit(page,"mobile review")
            page.set_viewport_size({"width":1260,"height":880})
            page.goto(base+"/"); shot(page,"04-owner-comparison"); audit(page,"comparison")
            page.goto(base+"/owner/"); expect(page.locator("#total")).to_have_text("$2,500.00 USD"); assert_logo(page)
            page.locator('input[value="smaller"]').check()
            expect(page.locator("#total")).to_have_text("$450.00 USD")
            page.locator("#count").fill("30"); expect(page.locator("#total")).to_have_text("$630.00 USD")
            page.locator("#count").fill("501"); expect(page.locator("#total")).to_have_text("Request a quote")
            expect(page.locator("#checkout")).to_be_disabled()
            page.locator("#count").fill("20"); expect(page.locator("#total")).to_have_text("$450.00 USD")
            audit(page,"calculator"); shot(page,"05-calculator")
            page.locator("#checkout").click(); expect(page.locator("#return-title")).to_have_text("Mock payment review")
            ref=page.url.split("ref=")[-1]
            page.goto(base+"/owner/?result="+ref)
            expect(page.locator("#return-title")).to_have_text("Payment confirmation pending")
            page.goto(base+"/owner/?cancel="+ref); expect(page.locator("#return-text")).to_contain_text("No confirmed payment")
            page.goto(base+"/owner/mock?ref="+ref); page.locator("#simulate").click()
            expect(page.locator("#return-title")).to_have_text("Pending manual activation"); audit(page,"verified mock")
            shot(page,"06-mock-confirmation")
            page.goto(base+"/owner/?result="+ref); expect(page.locator("#return-title")).to_have_text("Pending manual activation")
            page.locator("#restart").click(); expect(page.locator("#total")).to_have_text("$2,500.00 USD")
            assert not errors and not external,(errors,len(external))
            # Compare prefill values on the independent owner-local server without logging any values or taking screenshots.
            personal=browser.new_page()
            personal.goto("http://127.0.0.1:8164/offer/purchase.html")
            expect(personal.locator("#app")).to_be_visible()
            expected=json.loads((WORK/"private/contact.json").read_text())
            assert all(personal.locator("#"+k).input_value()==v for k,v in expected.items())
            assert all(personal.locator("#"+k).input_value()=="" for k in ["quantity","needs","reference","phone","po","country","currency"])
            browser.close()
    finally:
        proc.terminate();proc.wait()
print("PASS: browser form paths, errors/focus, edit, mailto contents, clipboard and manual fallback, print, mobile widths, calculator, mock checkout and return states, logo decode and private prefill. Six accessibility scans passed. No off-origin requests in captured review.")
