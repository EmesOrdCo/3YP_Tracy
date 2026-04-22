"""Capture clean Streamlit GUI screenshots for the report.

Navigates to each of the interesting pages of the simulation's Streamlit
interface, waits for the spinner to finish, optionally clicks the primary
run button, then saves a full-page PNG. Any page that throws a
StreamlitAPIException is skipped.

Requires: Playwright + Chromium (install with
``pip install playwright`` and ``playwright install chromium``).
Assumes Streamlit is running at http://localhost:8501.
"""

from __future__ import annotations

import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

FIG = Path(__file__).resolve().parent / "figures"
FIG.mkdir(exist_ok=True)

# URL path, output filename, description, optional "run" button text.
# Streamlit's multipage app builds URLs from page filenames without the
# leading "N_" prefix and with underscores -> spaces, or the original
# filename stem. We try both forms.
PAGES = [
    ("Compare_Configs",        "gui_compare.png",     None),
    ("Parameter_Sweep",         "gui_sweep.png",       None),
    ("Gearing",                 "gui_gearing.png",     None),
    ("Sensitivity",             "gui_sensitivity.png", None),
    ("Optimizer",               "gui_optimizer.png",   None),
    ("Track_Conditions",        "gui_track.png",       None),
]


def navigate_and_capture(page, path: str, out: Path, run_label: str | None) -> str:
    candidates = [
        f"http://localhost:8501/{path}",
        f"http://localhost:8501/{path.replace('_', '%20')}",
    ]
    loaded_url = None
    for url in candidates:
        try:
            page.goto(url, timeout=25000, wait_until="networkidle")
            loaded_url = url
            break
        except PwTimeout:
            continue
    if not loaded_url:
        return f"FAILED {path}: cannot navigate"

    # Dismiss any cookie / welcome banner.
    time.sleep(2.0)

    # Collapse the sidebar if it's open (increases usable width).
    try:
        btn = page.locator('button[kind="header"][aria-label*="sidebar" i]')
        if btn.count() > 0:
            btn.first.click(timeout=1500)
            time.sleep(0.5)
    except Exception:
        pass

    # If the page is an error page (StreamlitAPIException), skip.
    try:
        if page.locator("text=StreamlitAPIException").first.is_visible(timeout=500):
            return f"SKIPPED {path}: StreamlitAPIException visible"
    except Exception:
        pass

    # Optional run button.
    if run_label:
        try:
            page.get_by_role("button", name=run_label).first.click(timeout=3000)
        except Exception:
            pass

    # Give widgets / plots time to render.
    time.sleep(4.0)

    # Full-page screenshot.
    try:
        page.screenshot(path=str(out), full_page=True)
        return f"OK {path} -> {out.name}"
    except Exception as e:
        return f"FAILED {path}: screenshot error {e}"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000},
                                       device_scale_factor=2)
        page = context.new_page()
        # Load home first so Streamlit's client is warmed up.
        try:
            page.goto("http://localhost:8501/", timeout=25000,
                      wait_until="networkidle")
            time.sleep(3.0)
        except PwTimeout:
            print("Streamlit home page did not load; aborting.")
            return

        for path, out_name, run_label in PAGES:
            out = FIG / out_name
            result = navigate_and_capture(page, path, out, run_label)
            print(result)

        browser.close()


if __name__ == "__main__":
    main()
