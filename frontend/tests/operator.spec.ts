import { expect, test } from "@playwright/test";

test("operator console requires operator login", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Operator login" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await expect(page.getByText("active seeded operator account")).toBeVisible();
});
