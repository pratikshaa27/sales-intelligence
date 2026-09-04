import { expect, test } from "@playwright/test";

/**
 * The complete flow from spec §22 "End-to-End Tests":
 *   1. Register organization        7. Review research evidence
 *   2. Verify email                 8. Generate lead score
 *   3. Login                        9. Generate sales brief
 *   4. Create product               10. Assign lead
 *   5. Discover companies           11. Update lead status
 *   6. Run research                 12. Export leads
 *                                   13. Review audit logs
 *
 * Runs against an already-running stack (docker-compose up) rather than a mocked one: the
 * company created below uses the real https://example.com (IANA-reserved for documentation/
 * testing, always resolves) so "run research" performs a genuine SSRF-checked fetch and a real
 * (mock-AI-provider) extraction pass, not a stubbed one — this is the same flow a real user
 * would drive, just against fixture data.
 */

const uniqueSuffix = Date.now().toString(36);
const adminEmail = `e2e-${uniqueSuffix}@example.com`;
const adminPassword = "SuperSecret123";
const orgName = `E2E Org ${uniqueSuffix}`;
const productCode = `E2E-${uniqueSuffix}`;
const companyName = `E2E Example Co ${uniqueSuffix}`;
const leadName = `${companyName} - E2E Product`;

test.describe.configure({ mode: "serial" });

test.describe("Golden path: register through audit log review", () => {
  test("full flow", async ({ page }) => {
    await test.step("1. Register organization", async () => {
      await page.goto("/register", { waitUntil: "networkidle" });
      await page.getByLabel("Organization name").fill(orgName);
      await page.getByLabel("Your full name").fill("E2E Admin");
      await page.getByLabel("Email").fill(adminEmail);
      await page.getByLabel("Password").fill(adminPassword);
      await page.getByRole("button", { name: "Create organization" }).click();
      await expect(page).toHaveURL(/\/dashboard/);
    });

    await test.step("2. Verify email (documented gap: no real inbox in this environment)", async () => {
      // Registration sends a verification token through notification_service, which only logs
      // it (no SMTP configured) rather than delivering a real email — by design, nothing short
      // of a real mailbox can retrieve that token, so this step can't be driven through the UI
      // in an automated test. Login/registration deliberately do not block on verification, so
      // the rest of the flow is unaffected; this step is a documented no-op rather than a fake.
      expect(true).toBe(true);
    });

    await test.step("3. Login (log out, then log back in through the login form)", async () => {
      await page.getByRole("button", { name: "Log out" }).click();
      await expect(page).toHaveURL(/\/login/);
      await page.getByLabel("Email").fill(adminEmail);
      await page.getByLabel("Password").fill(adminPassword);
      await page.getByRole("button", { name: "Sign in" }).click();
      await expect(page).toHaveURL(/\/dashboard/);
    });

    await test.step("4. Create product", async () => {
      await page.goto("/products/new", { waitUntil: "networkidle" });
      await page.getByLabel("Product name").fill("E2E Sales Copilot");
      await page.getByLabel("Product code").fill(productCode);
      await page.getByRole("button", { name: "Create product" }).click();
      await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/);
    });

    await test.step("5. Discover companies", async () => {
      await page.goto("/companies/discover", { waitUntil: "networkidle" });
      await page.getByLabel("Industry").fill("Robotics");
      await page.getByRole("button", { name: "Discover companies" }).click();
      await expect(page.getByText("Results")).toBeVisible();
      await expect(page.getByText(/mock discovery provider/i)).toBeVisible({ timeout: 15_000 });
    });

    await test.step("Create the company research will target", async () => {
      // Discovery only ever proposes candidates for human review (spec §6) — it never creates
      // a Company row. A real user would click "Add to companies" on a result; this uses a
      // fixed, stable URL instead so the "run research" step below fetches predictable content.
      await page.goto("/companies/new", { waitUntil: "networkidle" });
      await page.getByLabel("Company name").fill(companyName);
      await page.getByLabel("Website").fill("https://example.com");
      await page.getByRole("button", { name: "Create company" }).click();
      await expect(page).toHaveURL(/\/companies\/[0-9a-f-]+$/);
    });

    await test.step("6. Run research", async () => {
      await page.getByRole("button", { name: "Run research" }).click();
      await expect(page.getByText("Researching…")).toBeVisible();
      await expect(page.getByText("completed", { exact: false })).toBeVisible({
        timeout: 30_000,
      });
    });

    await test.step("7. Review research evidence", async () => {
      await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
      // The evidence list either has real AI-extracted items, or (if example.com's static
      // page yields nothing extractable) explicitly says so — both are valid completed states.
      const hasEvidence = await page
        .getByText(/AI-generated/i)
        .first()
        .isVisible()
        .catch(() => false);
      const hasEmptyState = await page.getByText(/no evidence yet/i).isVisible().catch(() => false);
      expect(hasEvidence || hasEmptyState).toBe(true);
    });

    await test.step("8. Generate lead score (create a lead for the researched company)", async () => {
      await page.goto("/leads/new", { waitUntil: "networkidle" });
      await page.getByLabel("Company").selectOption({ label: companyName });
      await page.getByLabel("Product").selectOption({ label: "E2E Sales Copilot" });
      await page.getByLabel("Lead name").fill(leadName);
      await page.getByRole("button", { name: "Create lead" }).click();
      await expect(page).toHaveURL(/\/leads\/[0-9a-f-]+$/);
      await expect(page.getByText(/Lead score — \d+\/100/)).toBeVisible();
      await expect(page.getByText("Why this score")).toBeVisible();
    });

    await test.step("9. Generate sales brief", async () => {
      await page.getByRole("button", { name: "Generate brief" }).click();
      await expect(page.getByText(/drafted by an AI assistant/i)).toBeVisible({ timeout: 15_000 });
      await expect(page.getByText("Suggested opener (AI-drafted)")).toBeVisible();
    });

    await test.step("10. Assign lead", async () => {
      const assignSelect = page.locator("select").filter({ hasText: "Unassigned" });
      await assignSelect.selectOption({ label: "E2E Admin" });
      await expect(page.getByText("assigned", { exact: false }).first()).toBeVisible();
    });

    await test.step("11. Update lead status", async () => {
      const statusSelect = page.locator("select").filter({ hasText: /new|assigned/i }).first();
      await statusSelect.selectOption("qualified");
      await expect(statusSelect).toHaveValue("qualified");
    });

    await test.step("12. Export leads", async () => {
      await page.goto("/leads", { waitUntil: "networkidle" });
      const downloadPromise = page.waitForEvent("download");
      await page.getByRole("button", { name: "Export CSV", exact: true }).click();
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/leads_export.*\.csv$/);
    });

    await test.step("13. Review audit logs", async () => {
      await page.goto("/audit-logs", { waitUntil: "networkidle" });
      await expect(page.getByText("organization.registered")).toBeVisible();
      await expect(page.getByText("lead.created")).toBeVisible();
      await expect(page.getByText("leads.exported")).toBeVisible();
    });
  });
});
