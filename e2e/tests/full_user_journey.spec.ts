import { test, expect, Page } from '@playwright/test';

// ─── helpers ─────────────────────────────────────────────────────────────────

const BASE_API = process.env.API_URL || 'http://localhost:8000';

/** Register a fresh user directly via API and return tokens. */
async function apiRegister(email: string, password: string) {
  const res = await fetch(${BASE_API}/api/v1/auth/register, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(Register failed: );
  return res.json() as Promise<{ access_token: string; refresh_token: string }>;
}

/** Helper to generate a unique e-mail per test run. */
function uniqueEmail(prefix: string) {
  return ${prefix}_@e2e-test.local;
}

// ─── Scenario 1: Full User Journey ───────────────────────────────────────────

test.describe('Scenario 1 – Full User Journey', () => {
  test('Register → Login → Create todo → Toggle completion → Verify UI → Logout', async ({
    page,
  }) => {
    const email = uniqueEmail('journey');
    const password = 'Journey@123';

    // ── Step 1: Register ───────────────────────────────────────────────────
    await page.goto('/register');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill(password);
    await page.getByRole('button', { name: /sign up/i }).click();

    // Should redirect to the dashboard after registration
    await expect(page).toHaveURL('/');

    // ── Step 2: Create a todo ──────────────────────────────────────────────
    await page.getByRole('button', { name: /add todo/i }).click();

    const todoTitle = E2E Todo ;
    await page.getByPlaceholder(/title/i).fill(todoTitle);
    await page.getByRole('button', { name: /create|save|add/i }).last().click();

    // The new todo should appear in the list
    await expect(page.getByText(todoTitle)).toBeVisible();

    // ── Step 3: Toggle completion ──────────────────────────────────────────
    const todoItem = page.locator('[class*="flex items-center"]').filter({ hasText: todoTitle }).first();
    const checkbox = todoItem.getByRole('checkbox');

    await expect(checkbox).not.toBeChecked();
    await checkbox.click();
    await expect(checkbox).toBeChecked();

    // The title should appear with line-through when completed
    await expect(todoItem.getByText(todoTitle)).toHaveClass(/line-through/);

    // ── Step 4: Logout ─────────────────────────────────────────────────────
    await page.getByRole('button', { name: /logout/i }).click();

    // Should redirect to /login
    await expect(page).toHaveURL(/login/);

    // ── Step 5: Confirm todos not accessible after logout ──────────────────
    await page.goto('/');
    await expect(page).toHaveURL(/login/); // ProtectedRoute should redirect
  });
});
