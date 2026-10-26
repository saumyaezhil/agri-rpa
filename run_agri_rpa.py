"""Agri-RPA final live-demo robot.

Runs only against the local Agri-RPA backend and local mock government portal.
Creates timestamped logs, screenshots, CSV run report, downloaded documents,
and a PDF/text receipt after a confirmed successful mock submission.
"""
from __future__ import annotations

import csv
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

API_URL = os.getenv("AGRI_RPA_API_URL", "http://127.0.0.1:8000").rstrip("/")
PORTAL_URL = os.getenv("AGRI_RPA_PORTAL_URL", "http://127.0.0.1:8080/").rstrip("/") + "/"
USERNAME = os.getenv("AGRI_RPA_PORTAL_USERNAME", "officer")
PASSWORD = os.getenv("AGRI_RPA_PORTAL_PASSWORD", "officer123")
TIMEOUT_MS = 20_000
PAUSE_BETWEEN_STEPS = float(os.getenv("AGRI_RPA_STEP_PAUSE", "0.8"))

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rpa_evidence"
SCREENSHOTS = OUT / "screenshots"
DOCS = OUT / "downloaded_documents"
LOG_PATH = OUT / "execution.log"
CSV_PATH = OUT / "execution_report.csv"
LATEST_RECEIPT_TXT = OUT / "latest_receipt.txt"
LATEST_RECEIPT_PDF = OUT / "latest_receipt.pdf"

OUT.mkdir(exist_ok=True)
SCREENSHOTS.mkdir(exist_ok=True)
DOCS.mkdir(exist_ok=True)

FIELDS = [
    "timestamp", "application_id", "farmer_name", "service_type",
    "result", "government_reference", "duration_seconds", "details"
]
record = {
    "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    "application_id": "",
    "farmer_name": "",
    "service_type": "",
    "result": "STARTED",
    "government_reference": "",
    "duration_seconds": "",
    "details": "",
}
run_started = time.monotonic()


def log(message: str, level: str = "INFO") -> None:
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"{stamp} [{level}] {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def step(number: int, total: int, message: str) -> None:
    log(f"STEP {number}/{total} — {message}")
    if PAUSE_BETWEEN_STEPS > 0:
        time.sleep(PAUSE_BETWEEN_STEPS)


def save_report() -> None:
    record["duration_seconds"] = f"{time.monotonic() - run_started:.2f}"
    exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0
    with CSV_PATH.open("a", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: record.get(key, "") for key in FIELDS})


def api_get(path: str):
    response = requests.get(f"{API_URL}{path}", timeout=15)
    response.raise_for_status()
    return response.json()


def api_post(path: str, params=None):
    response = requests.post(f"{API_URL}{path}", params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def capture(page, name: str) -> None:
    target = SCREENSHOTS / name
    try:
        page.screenshot(path=str(target), full_page=True)
        log(f"Evidence screenshot saved: {target}")
    except Exception as exc:
        log(f"Could not capture screenshot {name}: {exc}", "WARN")


def download_documents(application_id: str) -> int:
    try:
        data = api_get(f"/api/rpa/{application_id}/documents")
    except Exception as exc:
        log(f"Document listing unavailable; continuing with portal submission: {exc}", "WARN")
        return 0

    count = 0
    for doc in data.get("documents", []):
        filename = Path(str(doc.get("filename", f"document_{count}"))).name
        document_id = doc.get("document_id")
        if not document_id:
            continue
        try:
            response = requests.get(
                f"{API_URL}/api/rpa/{application_id}/documents/{document_id}/download",
                timeout=30,
            )
            response.raise_for_status()
            (DOCS / filename).write_bytes(response.content)
            log(f"Supporting document saved for evidence: {filename}")
            count += 1
        except Exception as exc:
            log(f"Could not download {filename}: {exc}", "WARN")
    return count


def make_receipt(application_id: str, farmer: str, service: str, government_id: str) -> None:
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        "AGRI-RPA — MOCK GOVERNMENT SUBMISSION RECEIPT",
        "=" * 52,
        f"Agri-RPA application ID : {application_id}",
        f"Farmer                  : {farmer}",
        f"Service                 : {service}",
        f"Government reference    : {government_id}",
        "Submission outcome      : CONFIRMED SUCCESS",
        f"Timestamp               : {stamp}",
        "",
        "Scope: This receipt records a successful submission to the LOCAL",
        "mock government portal used for the project demonstration.",
        "It is not proof of submission to a live government department.",
    ]
    LATEST_RECEIPT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import mm

        styles = getSampleStyleSheet()
        story = [
            Paragraph("Agri-RPA Submission Receipt", styles["Title"]),
            Spacer(1, 8 * mm),
        ]
        for line in lines[2:]:
            if line:
                story.append(Paragraph(line.replace("&", "&amp;"), styles["BodyText"]))
            else:
                story.append(Spacer(1, 3 * mm))
        SimpleDocTemplate(str(LATEST_RECEIPT_PDF), pagesize=A4).build(story)
        log(f"PDF receipt saved: {LATEST_RECEIPT_PDF}")
    except Exception as exc:
        log(f"PDF receipt could not be generated; text receipt is available: {exc}", "WARN")
    log(f"Text receipt saved: {LATEST_RECEIPT_TXT}")


def mark_failed(application_id: str) -> None:
    try:
        result = api_post(f"/api/rpa/{application_id}/failed")
        log(f"Failure endpoint response: {result}", "WARN")
    except Exception as exc:
        log(f"Could not notify backend of RPA failure: {exc}", "WARN")


def main() -> int:
    print("\n" + "=" * 70)
    print(" AGRI-RPA | LIVE AUTOMATION + EXECUTION EVIDENCE")
    print("=" * 70)
    log(f"Evidence directory: {OUT.resolve()}")

    step(1, 7, "Checking backend health")
    try:
        health = api_get("/health")
        if health.get("status") != "healthy":
            raise RuntimeError(f"Unexpected health response: {health}")
        log(f"Backend is healthy: {health}")
    except Exception as exc:
        record["result"] = "BACKEND_UNAVAILABLE"
        record["details"] = str(exc)
        log(f"Cannot reach backend at {API_URL}: {exc}", "ERROR")
        save_report()
        return 1

    step(2, 7, "Checking local mock portal")
    try:
        portal_response = requests.get(PORTAL_URL, timeout=10)
        portal_response.raise_for_status()
    except Exception as exc:
        record["result"] = "MOCK_PORTAL_UNAVAILABLE"
        record["details"] = str(exc)
        log(f"Cannot reach mock portal at {PORTAL_URL}: {exc}", "ERROR")
        save_report()
        return 1

    step(3, 7, "Fetching next eligible application")
    try:
        app = api_get("/api/rpa/next-application")
    except Exception as exc:
        record["result"] = "QUEUE_ERROR"
        record["details"] = str(exc)
        log(f"Could not fetch queue: {exc}", "ERROR")
        save_report()
        return 1

    if not app.get("available"):
        message = app.get("message", "No eligible AUTO_APPROVED / AUTO_PROCESS application is available.")
        record["result"] = "NO_ELIGIBLE_APPLICATION"
        record["details"] = message
        log(message, "WARN")
        log("Human-review cases are intentionally not auto-submitted.")
        log(f"Report saved to {CSV_PATH}")
        save_report()
        return 0

    application_id = str(app.get("application_id", ""))
    record["application_id"] = application_id
    record["farmer_name"] = str(app.get("farmer_name", ""))
    record["service_type"] = str(app.get("service_type", ""))
    required = ("farmer_name", "mobile", "service_type", "survey_number", "village")
    missing = [key for key in required if not str(app.get(key, "")).strip()]
    if missing:
        record["result"] = "VALIDATION_ERROR"
        record["details"] = "Missing fields: " + ", ".join(missing)
        log(record["details"], "ERROR")
        save_report()
        return 1

    log(f"Selected application: {application_id}")
    log(f"Farmer: {app['farmer_name']} | Service: {app['service_type']}")

    started = False
    page = None
    browser = None
    try:
        step(4, 7, "Marking application as RPA processing and collecting documents")
        start_result = api_post(f"/api/rpa/{application_id}/start")
        started = True
        log(f"Backend start response: {start_result}")
        doc_count = download_documents(application_id)
        log(f"Supporting documents downloaded: {doc_count}")

        target_url = f"{PORTAL_URL}?{urlencode({'application_id': application_id})}"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False, slow_mo=350)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(TIMEOUT_MS)

            step(5, 7, "Opening visible Chromium and signing into mock government portal")
            page.goto(target_url, wait_until="domcontentloaded")
            capture(page, f"{application_id}_01_login.png")
            page.locator("#username").fill(USERNAME)
            page.locator("#password").fill(PASSWORD)
            page.get_by_role("button", name=re.compile("login", re.I)).click()

            page.locator("#portalSection:not(.hidden)").wait_for(state="visible")
            page.locator("#farmerName").wait_for(state="visible")
            page.wait_for_function(
                "() => (document.querySelector('#farmerName')?.value || '').trim().length > 0",
                timeout=TIMEOUT_MS,
            )
            shown_id = page.locator("#applicationIdDisplay").inner_text().strip()
            if shown_id != application_id:
                raise RuntimeError(f"Portal application ID mismatch: expected {application_id}, got {shown_id}")

            expected = {
                "#farmerName": str(app["farmer_name"]),
                "#mobile": str(app["mobile"]),
                "#serviceType": str(app["service_type"]),
                "#surveyNumber": str(app["survey_number"]),
                "#village": str(app["village"]),
            }
            for selector, expected_value in expected.items():
                actual = page.locator(selector).input_value().strip()
                if actual != expected_value.strip():
                    raise RuntimeError(
                        f"Portal data mismatch at {selector}: expected {expected_value!r}, got {actual!r}"
                    )
            capture(page, f"{application_id}_02_verified_form.png")
            log("Portal data matches the backend record; submitting now.")

            step(6, 7, "Submitting the application and waiting for portal confirmation")
            page.get_by_role("button", name=re.compile("submit application", re.I)).click()
            page.locator("#submitResult").wait_for(state="visible")
            page.wait_for_function(
                "() => { const t = document.querySelector('#submitResult')?.innerText || ''; "
                "return t.includes('Application submitted successfully.') || t.includes('Submission failed:'); }",
                timeout=TIMEOUT_MS,
            )
            result_text = page.locator("#submitResult").inner_text().strip()
            capture(page, f"{application_id}_03_submission_result.png")
            print("\n--- MOCK GOVERNMENT PORTAL RESPONSE ---")
            print(result_text)
            print("---------------------------------------\n")

            if "Application submitted successfully." not in result_text:
                raise RuntimeError(f"Portal did not confirm successful submission: {result_text}")

            match = re.search(r"Government Application ID:\s*(GOV-\d+)", result_text)
            if not match:
                raise RuntimeError("Portal success message did not include a GOV- reference.")

            government_id = match.group(1)
            step(7, 7, "Verifying backend status and generating evidence")
            final_app = api_get(f"/api/applications/{application_id}")
            final_status = final_app.get("status")
            stored_gov_id = final_app.get("government_application_id")
            if final_status != "SUBMITTED_TO_GOVERNMENT" or not stored_gov_id:
                raise RuntimeError(
                    "Portal showed a result, but backend confirmation is missing. "
                    f"status={final_status!r}, government_application_id={stored_gov_id!r}"
                )
            if str(stored_gov_id) != government_id:
                raise RuntimeError(
                    f"Reference mismatch: portal={government_id}, backend={stored_gov_id}"
                )

            record["result"] = "SUBMITTED_SUCCESSFULLY"
            record["government_reference"] = government_id
            record["details"] = f"Backend status={final_status}; portal confirmation verified"
            make_receipt(application_id, str(app["farmer_name"]), str(app["service_type"]), government_id)
            save_report()

            print("\n" + "=" * 70)
            print(" DEMO RESULT: SUCCESS")
            print(f" Agri-RPA application : {application_id}")
            print(f" Government reference : {government_id}")
            print(f" Final status         : {final_status}")
            print(f" Evidence folder      : {OUT.resolve()}")
            print("=" * 70)
            print("Leave the browser open for your teacher to inspect.")
            input("Press Enter in this terminal when ready to close the browser...")
            context.close()
            browser.close()
            return 0

    except KeyboardInterrupt:
        record["result"] = "INTERRUPTED"
        record["details"] = "Stopped by user; check backend status before retrying."
        log("Interrupted. Check application status before running again.", "WARN")
        save_report()
        return 130
    except Exception as exc:
        record["result"] = "RPA_FAILED_OR_UNCONFIRMED"
        record["details"] = f"{type(exc).__name__}: {exc}"
        log(f"Automation failed or submission is unconfirmed: {exc}", "ERROR")
        if page is not None:
            capture(page, f"{application_id or 'unknown'}_failure.png")
        log("Check the backend status before rerunning to avoid duplicate submissions.", "WARN")
        if started:
            # Backend endpoint only moves eligible in-progress failures to human review.
            mark_failed(application_id)
        save_report()
        if browser is not None:
            try:
                input("Press Enter to exit after reviewing the browser...")
                browser.close()
            except Exception:
                pass
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.RequestException as exc:
        print(f"[FATAL] Network/API error: {exc}", file=sys.stderr)
        sys.exit(1)
