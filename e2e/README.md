# E2E Tests – Playwright

## Prerequisites

- Node.js >= 18
- The frontend app must be running at http://localhost:3000
- The backend API must be running at http://localhost:8000

You can spin everything up with Docker:

`ash
docker compose up -d
`

## Setup

`ash
cd e2e
npm install
npx playwright install chromium
`

## Running Tests

`ash
# Headless (CI-friendly)
npx playwright test

# Headed (watch the browser)
npx playwright test --headed

# Single spec
npx playwright test tests/full_user_journey.spec.ts --headed

# View HTML report after run
npx playwright show-report
`

## Test Scenarios

### ull_user_journey.spec.ts
Full end-to-end flow:
1. Register a new account
2. Create a todo item
3. Toggle the todo to completed (verify checkbox + strikethrough)
4. Logout
5. Confirm the protected route redirects to /login

### cross_user_isolation.spec.ts
Cross-user data isolation:
1. Register User A and User B via the API
2. User A creates a private todo
3. User B logs in via a separate browser context
4. Verify that User B's todo list does NOT contain User A's todo

## Environment Variables

| Variable   | Default                    | Description           |
|------------|----------------------------|-----------------------|
| BASE_URL | http://localhost:3000    | Frontend URL          |
| API_URL  | http://localhost:8000    | Backend API URL       |
