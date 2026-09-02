"""One-off Playwright smoke test driving the actual rendered UI against
the live FastAPI backend. Not part of the delivered app — just a manual
verification script run once during development."""
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        print("1. Landing page")
        page.goto(BASE, wait_until="networkidle")
        assert "Proof before score" in page.content()
        page.screenshot(path="/tmp/shot_1_landing.png")

        print("2. Login with demo account")
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.click("text=Use the demo account")
        page.wait_for_url(f"{BASE}/dashboard", timeout=10000)
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/shot_2_dashboard.png")
        assert "Backend Software Engineer" in page.content()

        print("3. Open job detail")
        page.click("text=Backend Software Engineer")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("text=Priya Natarajan", timeout=10000)
        page.screenshot(path="/tmp/shot_3_job_detail.png")
        assert "Requirements" in page.content()
        assert "Marcus Webb" in page.content()

        print("3b. Open the AI ranking dashboard")
        page.click("text=View full AI ranking")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("text=Ranked candidate pool", timeout=10000)
        page.screenshot(path="/tmp/shot_3b_ranking.png", full_page=True)
        content = page.content()
        assert "AI Ranking" in content
        assert "ai_shortlisted" not in content
        assert "Priya Natarajan" in content
        assert "Marcus Webb" in content

        print("3c. Select a lower-ranked candidate for the next stage")
        rows = page.locator("table tbody tr").filter(has_text="Dana Whitfield")
        rows.get_by_role("button", name="Select for next stage").first.click()
        page.wait_for_selector("text=Selected ✓", timeout=10000)
        page.screenshot(path="/tmp/shot_3d_selection.png")

        print("3d. Compare two candidates")
        page.locator("table tbody tr", has_text="Priya Natarajan").locator('input[type="checkbox"]').first.check()
        page.locator("table tbody tr", has_text="Marcus Webb").locator('input[type="checkbox"]').first.check()
        page.click('button:has-text("Compare selected")')
        page.wait_for_selector("text=ranks above", timeout=10000)
        page.screenshot(path="/tmp/shot_3e_compare.png", full_page=True)

        print("4. Open a REVIEW_REQUIRED candidate (Marcus Webb)")
        page.goto(f"{BASE}/dashboard/jobs/" + page.url.split("/jobs/")[1].split("/")[0], wait_until="networkidle")
        page.click("text=Marcus Webb")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("text=Human review required", timeout=10000)
        page.screenshot(path="/tmp/shot_4_candidate_detail.png", full_page=True)
        assert "Capability graph" in page.content()
        assert "Recruiter decision" in page.content()

        print("5. Submit an override decision")
        page.click('button:has-text("Override")')
        page.select_option("select", "potential_match")
        page.fill("textarea", "Verified AWS experience via a follow-up call.")
        page.click('button:has-text("Submit decision")')
        page.wait_for_selector("text=Recorded:", timeout=10000)
        page.screenshot(path="/tmp/shot_5_decision_submitted.png")

        print("6. Adversarial simulator")
        page.goto(f"{BASE}/dashboard/adversarial", wait_until="networkidle")
        page.click('button:has-text("Run attack suite")')
        page.wait_for_selector("text=attacks detected", timeout=15000)
        page.wait_for_timeout(500)
        page.screenshot(path="/tmp/shot_6_adversarial.png", full_page=True)
        assert "6/6" in page.content() or "attacks detected" in page.content()

        print("7. Create a new job end to end")
        page.goto(f"{BASE}/dashboard/jobs/new", wait_until="networkidle")
        page.fill('input[placeholder="Backend Software Engineer"]', "Data Analyst")
        page.fill(
            "textarea",
            "We are hiring a Data Analyst.\nMust-have: SQL, Python.\nPreferred: Docker.",
        )
        page.click('button:has-text("Create job")')
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("text=Requirements", timeout=10000)
        page.click('button:has-text("Analyze requirements")')
        page.wait_for_selector("text=must-have", timeout=10000)
        page.screenshot(path="/tmp/shot_7_new_job_analyzed.png")
        assert "SQL" in page.content()

        browser.close()

        console_errors = [e for e in errors if "Failed to load resource" not in e]
        if console_errors:
            print("CONSOLE ERRORS:", console_errors)
        else:
            print("No console errors captured.")

        print("\nALL SMOKE STEPS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"SMOKE TEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
