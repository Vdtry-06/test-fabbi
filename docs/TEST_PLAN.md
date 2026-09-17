# Manual Test Plan: Authentication & Authorization -- Todo App

## 1. Scope & Objective

- **Muc tieu**: Xac thuc tinh dung dan cua Authentication (JWT), Authorization (data isolation), va Cache Invalidation sau khi bug fixes Tier 1.
- **Pham vi**: Auth flow, Todo CRUD, Cross-user isolation, Cache behavior, Frontend state management.

## 2. Test Environment & Prerequisites

| Item | Value |
|------|-------|
| Backend URL | http://localhost:8000 |
| Frontend URL | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Test Account A | user_a@test.com / Password@123 |
| Test Account B | user_b@test.com / Password@123 |

**Setup**: Start with `docker compose up -d`, ensure postgres + redis are healthy.

---

## 3. Test Cases Matrix

### MODULE: Authentication

| TC ID | Test Scenario | Preconditions | Test Steps | Expected Result | Priority | Severity |
|-------|---------------|---------------|------------|-----------------|----------|----------|
| TC-AUTH-01 | Register thanh cong | Email chua ton tai | 1. POST /auth/register voi email + password hop le | HTTP 201, tra ve access_token + refresh_token | High | Blocker |
| TC-AUTH-02 | Register voi email da ton tai | User da dang ky | 1. POST /auth/register voi email da dung | HTTP 400 "Email already registered" | High | Major |
| TC-AUTH-03 | Login thanh cong | User da dang ky | 1. POST /auth/login voi credentials dung | HTTP 200, tra ve tokens | High | Blocker |
| TC-AUTH-04 | Login sai mat khau -- Khong leak user existence | User da dang ky | 1. POST /auth/login voi pass sai | HTTP 401 "Invalid email or password" (KHONG noi "user not found") | High | Critical |
| TC-AUTH-05 | Login email khong ton tai -- Tranh enumeration | - | 1. POST /auth/login voi email la | HTTP 401, cung message voi TC-AUTH-04 | High | Critical |
| TC-AUTH-06 | Token het han bi tu choi | Token da expire | 1. Goi API voi expired token | HTTP 401 | High | Critical |
| TC-AUTH-07 | Token bi gia mao (tampered) bi tu choi | - | 1. Modify payload cua JWT | HTTP 401 | High | Critical |
| TC-AUTH-08 | Refresh token de lay access token moi | Valid refresh token | 1. POST /auth/refresh voi refresh_token | HTTP 200, access_token moi | Medium | Major |
| TC-AUTH-09 | Refresh token cua user da bi xoa | User bi xoa khoi DB | 1. POST /auth/refresh voi token cua user da xoa | HTTP 401 "User no longer exists" | Medium | Major |
| TC-AUTH-10 | Logout xoa token phia client | User dang login | 1. Bam Logout tren UI | Redirect ve /login, localStorage khong con token | High | Major |

---

### MODULE: Todo CRUD

| TC ID | Test Scenario | Preconditions | Test Steps | Expected Result | Priority | Severity |
|-------|---------------|---------------|------------|-----------------|----------|----------|
| TC-TODO-01 | Tao todo moi | User da login | 1. POST /todos {title, description} | HTTP 201, completed: false | High | Blocker |
| TC-TODO-02 | Tao todo khong co title | User da login | 1. POST /todos {title: ""} | HTTP 422 validation error | Medium | Major |
| TC-TODO-03 | List todos chi tra ve cua user hien tai | 2 users deu co todos | 1. GET /todos voi token User A | Chi thay todos cua User A | Critical | Blocker |
| TC-TODO-04 | Toggle incomplete -> complete | Todo ton tai | 1. PUT /todos/{id} {completed: true} | HTTP 200, completed: true | High | Major |
| TC-TODO-05 | Toggle complete -> INCOMPLETE (Bug B6 fix) | Todo dang completed | 1. PUT /todos/{id} {completed: false} | HTTP 200, completed: false - PHAI luu duoc | High | Critical |
| TC-TODO-06 | Update title khong xoa description (Partial update) | Todo co description | 1. PUT /todos/{id} {title: "New"} chi | HTTP 200, description giu nguyen | High | Critical |
| TC-TODO-07 | Xoa todo thanh cong | Todo ton tai | 1. DELETE /todos/{id} | HTTP 204, todo khong con trong list | High | Major |
| TC-TODO-08 | Lay todo khong ton tai | - | 1. GET /todos/non-existent-uuid | HTTP 404 | Low | Minor |

---

### MODULE: Authorization (Cross-User Isolation)

| TC ID | Test Scenario | Preconditions | Test Steps | Expected Result | Priority | Severity |
|-------|---------------|---------------|------------|-----------------|----------|----------|
| TC-AUTHZ-01 | User B doc todo cua User A | User A co todo ID-X | 1. GET /todos/ID-X voi token User B | HTTP 403 Forbidden | Critical | Blocker |
| TC-AUTHZ-02 | User B sua todo cua User A | User A co todo ID-X | 1. PUT /todos/ID-X voi token User B | HTTP 403 Forbidden | Critical | Blocker |
| TC-AUTHZ-03 | User B xoa todo cua User A | User A co todo ID-X | 1. DELETE /todos/ID-X voi token User B | HTTP 403, todo van con cua User A | Critical | Blocker |
| TC-AUTHZ-04 | User A khong thay todos cua User B trong list | Ca 2 co todos rieng | 1. GET /todos voi token User A | Response chi chua todos cua User A | Critical | Blocker |
| TC-AUTHZ-05 | Goi API khong co token | - | 1. GET /todos khong co header | HTTP 403 | High | Major |

---

### MODULE: Cache Behavior

| TC ID | Test Scenario | Preconditions | Test Steps | Expected Result | Priority | Severity |
|-------|---------------|---------------|------------|-----------------|----------|----------|
| TC-CACHE-01 | Cache moi sau khi tao todo | User da co todos cached | 1. GET /todos 2. POST /todos tao moi 3. GET /todos | Lan 3 thay todo moi, total tang | High | Major |
| TC-CACHE-02 | Cache bi xoa sau khi update | Todo trong cache | 1. GET /todos 2. PUT /todos/{id} doi title 3. GET /todos | Title moi hien thi | High | Major |
| TC-CACHE-03 | Cache bi xoa sau khi delete | Todo trong cache | 1. GET /todos 2. DELETE /todos/{id} 3. GET /todos | Todo da xoa khong con trong list | High | Major |
| TC-CACHE-04 | User A va B co cache rieng biet | Ca 2 co todos | 1. User A GET /todos 2. User A tao todo 3. User B GET /todos | User B nhan cache cua minh | Critical | Blocker |

---

### MODULE: Frontend State Management

| TC ID | Test Scenario | Preconditions | Test Steps | Expected Result | Priority | Severity |
|-------|---------------|---------------|------------|-----------------|----------|----------|
| TC-FE-01 | Sau Logout, React Query cache bi xoa | User A da load todos | 1. Login User A 2. Load todos 3. Logout 4. Login User B | User B khong thay todos cua User A | High | Critical |
| TC-FE-02 | 401 redirect ve login va xoa cache | Token expired | 1. Xoa token 2. Goi API | Redirect /login, khong con du lieu cu | High | Major |

---

## 4. Defect Tracking & Known Limitations

| Bug ID | Severity | Status | Notes |
|--------|----------|--------|-------|
| B1 | Critical | FIXED | JWT expiration now enforced |
| B2 | Critical | FIXED | Cache key scoped per user + page |
| B3 | Critical | FIXED | GET /{id} checks ownership |
| B4 | Critical | FIXED | PUT /{id} checks ownership |
| B5 | Critical | FIXED | DELETE /{id} checks ownership |
| B6 | High | FIXED | exclude_unset=True fixes toggle-to-false |
| B7 | High | FIXED | POST invalidates user cache |
| B8 | High | FIXED | DELETE invalidates user cache |
| B9 | High | FIXED | Login returns 401 consistently |
| B10 | High | FIXED | unique=True added to email |
| B11 | Medium | FIXED | N+1 eliminated |
| B12 | Medium | FIXED | Cache key includes page/size |
| B13 | Medium | FIXED | Refresh validates user existence |
| B14 | Medium | PARTIAL | Logout calls backend but no token blacklist (out of scope) |
| B15 | Medium | FIXED | Frontend queryKey includes page + size |
| B16 | Low | FIXED | Logout clears React Query cache |
| B17 | Low | FIXED | 401 interceptor clears React Query cache |