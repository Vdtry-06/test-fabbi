import { test, expect, BrowserContext } from '@playwright/test';

// ─── helpers ─────────────────────────────────────────────────────────────────

const BASE_API = process.env.API_URL || 'http://localhost:8000';

async function apiRegister(email: string, password: string) {
  const res = await fetch(${BASE_API}/api/v1/auth/register, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(Register failed: );
  return res.json() as Promise<{ access_token: string }>;
}

async function apiCreateTodo(token: string, title: string) {
  const res = await fetch(${BASE_API}/api/v1/todos, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: Bearer ,
    },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(Create todo failed: );
  return res.json();
}

function uniqueEmail(prefix: string) {
  return ${prefix}_@e2e-test.local;
}

// ─── Scenario 2: Cross-User Data Isolation ───────────────────────────────────

test.describe('Scenario 2 – Cross-User Data Isolation', () => {
  test(
    'User A creates a private todo; User B logs in and must NOT see it',
    async ({ browser }) => {
      const emailA = uniqueEmail('user_a_isolation');
      const emailB = uniqueEmail('user_b_isolation');
      const password = 'Isolation@123';
      const privateTitle = PRIVATE-;

      // ── Step 1: Register both users via API ────────────────────────────
      const { access_token: tokenA } = await apiRegister(emailA, password);
      await apiRegister(emailB, password);

      // ── Step 2: User A creates a private todo via API ──────────────────
      await apiCreateTodo(tokenA, privateTitle);

      // ── Step 3: User B logs in via UI in a separate browser context ────
      const ctxB: BrowserContext = await browser.newContext();
      const pageB = await ctxB.newPage();

      await pageB.goto('/login');
      await pageB.getByLabel('Email').fill(emailB);
      await pageB.getByLabel('Password').fill(password);
      await pageB.getByRole('button', { name: /sign in/i }).click();

      // Wait for redirect to dashboard
      await expect(pageB).toHaveURL('/');

      // ── Step 4: User B's todo list must NOT contain User A's todo ──────
      await pageB.waitForLoadState('networkidle');

      // Check that the private title is NOT visible anywhere on the page
      const bodyText = await pageB.locator('body').innerText();
      expect(bodyText).not.toContain(privateTitle);

      // Also confirm via page locator
      await expect(pageB.getByText(privateTitle)).not.toBeVisible();

      await ctxB.close();
    }
  );
});
