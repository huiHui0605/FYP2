"""Run against an initialized demo server. Uses the installed system Chromium."""

import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
SCREENSHOTS = Path("docs/screenshots")
SCREENSHOTS.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.environ.get("CHROMIUM_PATH")
        or shutil.which("chromium")
        or p.chromium.executable_path,
        headless=True,
        args=["--no-sandbox"],
    )
    page = browser.new_page(
        viewport={"width": 1440, "height": 1100}, device_scale_factor=1
    )
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE)
    page.get_by_role("link", name="Sign in", exact=True).click()
    page.get_by_label("Email address").fill("resident@looplocal.test")
    page.get_by_label("Password", exact=True).fill("LoopLocal2026!")
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url("**/dashboard")
    assert page.get_by_role("heading", name="Hello, Amira").is_visible()
    page.screenshot(path=str(SCREENSHOTS / "dashboard-desktop.png"), full_page=True)
    for path in [
        "/repairs",
        "/tools",
        "/clinics",
        "/impact",
        "/profile",
        "/notifications",
    ]:
        response = page.goto(BASE + path)
        assert response.status == 200, (path, response.status)
        assert page.locator("main h1").is_visible()
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), path
    page.goto(BASE + "/tools")
    page.locator("summary").first.click()
    assert page.get_by_role("button", name="Confirm reservation").first.is_visible()
    page.screenshot(path=str(SCREENSHOTS / "tools-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    for path in [
        "/dashboard",
        "/repairs",
        "/repairs/new",
        "/repairs/1",
        "/tools",
        "/clinics",
        "/impact",
        "/profile",
    ]:
        page.goto(BASE + path)
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), ("Mobile overflow", path)
    page.goto(BASE + "/dashboard")
    page.screenshot(path=str(SCREENSHOTS / "dashboard-mobile.png"), full_page=True)
    # Traverse a complete new repair in the actual browser using all three relevant screens.
    page.goto(BASE + "/repairs/new")
    page.get_by_label("Give your repair a title").fill("Browser test: bedside lamp")
    page.get_by_label("Item category").select_option("Electronics")
    page.get_by_label("What's happening?").fill(
        "The low-voltage desk lamp switch is loose. No damage, smoke or other hazards."
    )
    page.get_by_label("Estimated item weight").fill("1.5")
    page.get_by_role("button", name="Create repair request").click()
    page.wait_for_url("**/repairs/*")
    repair_path = page.url
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.get_by_role("button", name="Sign out").click()
    page.goto(BASE + "/login")
    page.get_by_label("Email address").fill("fixer@looplocal.test")
    page.get_by_label("Password", exact=True).fill("LoopLocal2026!")
    page.get_by_role("button", name="Sign in").click()
    page.goto(repair_path)
    page.get_by_role("button", name="I can help repair this").click()
    page.get_by_label("Next step").select_option("in_progress")
    page.get_by_label("Repair notes / reason").fill(
        "Inspected the disconnected low-voltage lamp switch."
    )
    page.get_by_role("button", name="Update record", exact=True).click()
    page.get_by_label("Next step").select_option("repaired")
    page.get_by_label("Repair notes / reason").fill(
        "Replaced the loose switch. Checked low-voltage operation and safe assembly."
    )
    page.get_by_role("button", name="Update record", exact=True).click()
    page.get_by_role("link", name="Open item passport").click()
    assert page.get_by_role("heading", name="Browser test: bedside lamp").is_visible()
    assert "Daniel Tan" not in page.locator(".passport-document").inner_text()
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.screenshot(path=str(SCREENSHOTS / "passport-desktop.png"), full_page=True)
    assert not errors, errors
    browser.close()
print(
    "PASS: desktop/mobile pages, no overflow, no JS errors, complete resident → volunteer → passport workflow."
)
