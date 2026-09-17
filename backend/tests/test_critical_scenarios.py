"""Critical scenario tests for Tier 2A.

Covers:
1. Expired / tampered JWT rejection
2. Authorization boundary - User A cannot read/update/delete User B's todos
3. Boolean toggle: completed=true -> false persists correctly
4. Partial update: title update does not erase description
5. Cache invalidation on create/update/delete
"""

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


# ── helpers ──────────────────────────────────────────────────────────────────

async def register_user(client: AsyncClient, email: str, password: str = "Password@123") -> str:
    """Register a user and return access_token."""
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


async def create_todo_for(
    client: AsyncClient,
    token: str,
    title: str = "My Todo",
    description: str | None = "Some description",
) -> dict:
    res = await client.post(
        "/api/v1/todos",
        json={"title": title, "description": description},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()


# ── 1. JWT token scenarios ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_expired_token_rejected(client: AsyncClient):
    """Expired JWT access token must be rejected with 401."""
    # Create a token that expired 1 second in the past
    expired_token = create_access_token(
        data={"sub": str(uuid.uuid4())},
        expires_delta=timedelta(seconds=-1),
    )
    res = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


@pytest.mark.asyncio
async def test_tampered_token_rejected(client: AsyncClient):
    """A JWT with an invalid signature must be rejected with 401."""
    tampered = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWtlIn0.badsignature"
    res = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


@pytest.mark.asyncio
async def test_no_token_rejected(client: AsyncClient):
    """Requests without any Authorization header must be rejected with 403."""
    res = await client.get("/api/v1/todos")
    assert res.status_code in (401, 403)


# ── 2. Authorization boundary ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_cannot_read_other_users_todo(client: AsyncClient):
    """User B must receive 403/404 when trying to read User A's todo."""
    token_a = await register_user(client, "user_a_read@example.com")
    token_b = await register_user(client, "user_b_read@example.com")

    todo = await create_todo_for(client, token_a, "Secret Todo A")
    todo_id = todo["id"]

    res = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code in (403, 404), (
        f"User B should not access User A's todo, got {res.status_code}"
    )


@pytest.mark.asyncio
async def test_user_cannot_update_other_users_todo(client: AsyncClient):
    """User B must receive 403/404 when trying to update User A's todo."""
    token_a = await register_user(client, "user_a_update@example.com")
    token_b = await register_user(client, "user_b_update@example.com")

    todo = await create_todo_for(client, token_a, "A's Private Todo")
    todo_id = todo["id"]

    res = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Hacked by B"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code in (403, 404), (
        f"User B should not update User A's todo, got {res.status_code}"
    )


@pytest.mark.asyncio
async def test_user_cannot_delete_other_users_todo(client: AsyncClient):
    """User B must receive 403/404 when trying to delete User A's todo."""
    token_a = await register_user(client, "user_a_delete@example.com")
    token_b = await register_user(client, "user_b_delete@example.com")

    todo = await create_todo_for(client, token_a, "A's Todo to Protect")
    todo_id = todo["id"]

    res = await client.delete(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code in (403, 404), (
        f"User B should not delete User A's todo, got {res.status_code}"
    )

    # Confirm it still exists for User A
    get_res = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert get_res.status_code == 200


# ── 3. Boolean toggle: completed true -> false ────────────────────────────────


@pytest.mark.asyncio
async def test_toggle_completed_false_persists(client: AsyncClient):
    """Setting completed=false after completed=true must be saved correctly."""
    token = await register_user(client, "toggle@example.com")
    todo = await create_todo_for(client, token, "Toggle Me")
    todo_id = todo["id"]

    # Mark as completed
    res = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"completed": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["completed"] is True

    # Toggle back to incomplete
    res2 = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"completed": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    assert res2.json()["completed"] is False, (
        "completed=False must persist but got True"
    )


# ── 4. Partial update: title update must not erase description ────────────────


@pytest.mark.asyncio
async def test_partial_update_title_preserves_description(client: AsyncClient):
    """Updating only the title must not erase the existing description."""
    token = await register_user(client, "partial@example.com")
    todo = await create_todo_for(client, token, "Original Title", "Keep this description")
    todo_id = todo["id"]

    res = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "New Title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "New Title"
    assert data["description"] == "Keep this description", (
        f"Description was erased! Got: {data['description']}"
    )


# ── 5. Cache invalidation ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_invalidated_on_create(client: AsyncClient):
    """After creating a todo, the list cache must be invalidated (new item visible)."""
    token = await register_user(client, "cache_create@example.com")

    # Warm the cache with first request
    list_res1 = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res1.status_code == 200
    initial_count = list_res1.json()["total"]

    # Create a new todo (should invalidate cache)
    await create_todo_for(client, token, "Cache Busting Todo")

    # New request must reflect the new count
    list_res2 = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res2.status_code == 200
    assert list_res2.json()["total"] == initial_count + 1, (
        "Cache was not invalidated after create — new todo not in list"
    )


@pytest.mark.asyncio
async def test_cache_invalidated_on_update(client: AsyncClient):
    """After updating a todo, the list must reflect the update."""
    token = await register_user(client, "cache_update@example.com")
    todo = await create_todo_for(client, token, "Before Update")
    todo_id = todo["id"]

    await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "After Update"},
        headers={"Authorization": f"Bearer {token}"},
    )

    list_res = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    titles = [item["title"] for item in list_res.json()["items"]]
    assert "After Update" in titles, "Updated title not visible — stale cache?"


@pytest.mark.asyncio
async def test_cache_invalidated_on_delete(client: AsyncClient):
    """After deleting a todo, the list must not include the deleted item."""
    token = await register_user(client, "cache_delete@example.com")
    todo = await create_todo_for(client, token, "To Be Deleted")
    todo_id = todo["id"]

    # Warm list cache
    await client.get("/api/v1/todos", headers={"Authorization": f"Bearer {token}"})

    # Delete
    del_res = await client.delete(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204

    # List must not contain deleted item
    list_res = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    ids = [item["id"] for item in list_res.json()["items"]]
    assert todo_id not in ids, "Deleted todo still visible — cache not invalidated"
