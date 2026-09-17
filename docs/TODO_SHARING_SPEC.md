# Technical Specification: Todo Sharing Feature

## 1. Overview & Objective

- **Feature Summary**: Users can share their todo list with other users, granting either read-only (viewer) or edit (editor) permission. Owners can revoke access at any time.
- **Problem Statement**: Currently todos are completely private. Teams or couples who want to collaborate on shared tasks have no way to do so without sharing credentials -- a serious security antipattern.
- **Target Audience / Roles**:
  - **Owner**: The user who created the todo list. Can share, modify permissions, and revoke.
  - **Editor**: A collaborator who can read AND update todos in a shared list.
  - **Viewer**: A collaborator who can only read todos in a shared list.

---

## 2. User Stories & Acceptance Criteria

### US-1: Share a todo with another user

- **As an** Owner
- **I want to** invite another registered user by email with viewer or editor permission
- **So that** we can collaborate on tasks together

**Acceptance Criteria**:
- [ ] Owner can POST /todos/{todo_id}/shares with {email, permission: "viewer"|"editor"}
- [ ] If the target email does not exist, return 404 with clear error message
- [ ] If owner tries to share with themselves, return 400 "Cannot share with yourself"
- [ ] Duplicate invitations (same todo + same user) return 409 Conflict
- [ ] After sharing, the collaborator can see the todo in their GET /todos response
- [ ] Sharing is immediate -- no email confirmation required in this release

### US-2: View shared todos

- **As a** Viewer or Editor
- **I want to** see todos that have been shared with me alongside my own todos
- **So that** I have a single unified view of all relevant tasks

**Acceptance Criteria**:
- [ ] GET /todos returns the user's own todos PLUS todos shared with them (with permission context)
- [ ] Each TodoResponse includes a `shared_by` field when the todo is not owned by the user
- [ ] Viewer cannot call PUT or DELETE on shared todos (403)
- [ ] Editor can call PUT on shared todos, but cannot DELETE them

### US-3: Revoke access

- **As an** Owner
- **I want to** remove a collaborator's access immediately
- **So that** I can control who sees my data at any time

**Acceptance Criteria**:
- [ ] Owner can DELETE /todos/{todo_id}/shares/{user_id} to revoke
- [ ] After revoke, collaborator no longer sees the todo in GET /todos
- [ ] Redis cache for both the owner and the collaborator is invalidated immediately
- [ ] Collaborator receives 403 on any subsequent request for that todo

### US-4: List collaborators

- **As an** Owner
- **I want to** see who currently has access to a specific todo
- **So that** I can audit and manage permissions

**Acceptance Criteria**:
- [ ] GET /todos/{todo_id}/shares returns list of {user_id, email, permission, shared_at}
- [ ] Only the owner can access this endpoint (403 for others)

---

## 3. Scope

### In-Scope (v1)
- Share individual todos (not entire lists) with specific users by email
- Two permission levels: viewer (read-only) and editor (read + update)
- Owner can revoke any time, immediately effective
- List current collaborators
- Cache invalidation on share and revoke

### Out-of-Scope
- Sharing entire "todo lists" / workspaces (bulk share)
- Email notification when shared/revoked
- Permission escalation by collaborators (Editor cannot invite others)
- Public link sharing
- Time-limited / expiring permissions
- Comment threads on shared todos
- Mobile push notifications

---

## 4. Database Design

### New Table: `todo_shares`

```sql
CREATE TABLE todo_shares (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    todo_id     UUID         NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
    owner_id    UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shared_with UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission  VARCHAR(10)  NOT NULL CHECK (permission IN ('viewer', 'editor')),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

### Constraints & Indexes

```sql
-- Prevent duplicate shares of the same todo to the same user
ALTER TABLE todo_shares ADD CONSTRAINT uq_todo_share UNIQUE (todo_id, shared_with);

-- Prevent self-sharing (enforced at app layer too, but belt-and-suspenders)
ALTER TABLE todo_shares ADD CONSTRAINT ck_no_self_share CHECK (owner_id != shared_with);

-- Performance indexes
CREATE INDEX idx_todo_shares_todo_id       ON todo_shares(todo_id);
CREATE INDEX idx_todo_shares_shared_with   ON todo_shares(shared_with);
CREATE INDEX idx_todo_shares_owner_id      ON todo_shares(owner_id);
```

### Impact on existing tables
- `todos`: No structural change. `user_id` continues to mean "owner".
- The new `todo_shares` table is purely additive.

---

## 5. API Contracts & Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/todos/{todo_id}/shares | Share a todo with a user | Owner only |
| GET | /api/v1/todos/{todo_id}/shares | List collaborators of a todo | Owner only |
| PATCH | /api/v1/todos/{todo_id}/shares/{user_id} | Update permission of a collaborator | Owner only |
| DELETE | /api/v1/todos/{todo_id}/shares/{user_id} | Revoke a collaborator's access | Owner only |

### POST /api/v1/todos/{todo_id}/shares

**Request Body**:
```json
{
  "email": "collaborator@example.com",
  "permission": "editor"
}
```

**Responses**:
| Code | Condition |
|------|-----------|
| 201 | Share created successfully |
| 400 | Self-sharing attempt |
| 403 | Requester is not the owner |
| 404 | Todo not found OR target user not found |
| 409 | Already shared with this user |

**Response Body (201)**:
```json
{
  "id": "uuid",
  "todo_id": "uuid",
  "shared_with_email": "collaborator@example.com",
  "permission": "editor",
  "created_at": "2026-09-17T00:00:00Z"
}
```

### GET /api/v1/todos/{todo_id}/shares

**Response Body (200)**:
```json
{
  "collaborators": [
    {
      "user_id": "uuid",
      "email": "collab@example.com",
      "permission": "viewer",
      "shared_at": "2026-09-17T00:00:00Z"
    }
  ]
}
```

### PATCH /api/v1/todos/{todo_id}/shares/{user_id}

**Request Body**:
```json
{ "permission": "viewer" }
```
Returns 200 with updated share object or 403/404.

### DELETE /api/v1/todos/{todo_id}/shares/{user_id}

Returns 204 No Content on success, 403 if not owner, 404 if share not found.

---

## 6. Business Logic & Security

### Authorization Matrix

| Action | Owner | Editor | Viewer | Unauthenticated |
|--------|-------|--------|--------|-----------------|
| Read todo | YES | YES | YES | NO |
| Update todo | YES | YES | NO (403) | NO |
| Delete todo | YES | NO (403) | NO (403) | NO |
| Share todo | YES | NO (403) | NO (403) | NO |
| Revoke share | YES | NO (403) | NO (403) | NO |
| List shares | YES | NO (403) | NO (403) | NO |

### Edge Cases

| Case | Handling |
|------|----------|
| Owner tries to share with themselves | 400 "Cannot share with yourself" |
| Sharing with email that does not exist | 404 "User not found" |
| Duplicate share (same todo + same user) | 409 "Already shared with this user" |
| Owner deletes todo | CASCADE removes all shares automatically |
| Owner account deleted | CASCADE removes their todos and all shares |
| Editor updates todo while owner revokes simultaneously | Last-write-wins; revoke takes effect on next request |
| Collaborator tries to re-share with another user | 403 "Only the owner can share this todo" |

---

## 7. GET /todos Behavior After Sharing

The existing `GET /todos` must be extended to return both owned AND shared todos:

```python
# Pseudocode for modified query
owned = SELECT * FROM todos WHERE user_id = current_user.id
shared = SELECT t.*, ts.permission, u.email AS shared_by_email
         FROM todos t
         JOIN todo_shares ts ON ts.todo_id = t.id
         JOIN users u ON u.id = t.user_id
         WHERE ts.shared_with = current_user.id
result = owned UNION shared ORDER BY created_at DESC
```

`TodoResponse` gains two optional fields:
```json
{
  "is_shared": true,
  "permission": "editor",
  "shared_by_email": "owner@example.com"
}
```

---

## 8. Caching & Invalidation Strategy

### Cache Key Structure

```
todos:list:{user_id}:{page}:{size}   -- per user, existing pattern
```

### Invalidation Triggers

| Event | Cache Keys to Invalidate |
|-------|--------------------------|
| Owner shares a todo | `todos:list:{shared_with}:*` (collaborator now has new visible todo) |
| Owner updates a shared todo | `todos:list:{owner_id}:*` + `todos:list:{each_collaborator}:*` |
| Owner revokes access | `todos:list:{revoked_user_id}:*` (immediately effective) |
| Owner deletes a shared todo | `todos:list:{owner_id}:*` + `todos:list:{each_collaborator}:*` |

### Implementation

Use Redis `SCAN` + `DEL` pattern (same as current `_invalidate_user_todo_cache`).
Wrap share/revoke operations in a transaction: DB commit first, then cache invalidation.

---

## 9. Migration Plan

1. Create `b2c3d4e5f6a7_add_todo_shares.py` Alembic migration (additive, zero downtime).
2. Deploy with feature flag disabled.
3. Run migration on production.
4. Enable feature flag.
5. No data backfill required (new table starts empty).