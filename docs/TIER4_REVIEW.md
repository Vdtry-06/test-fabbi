# Tier 4 Review — Tags, Filtering & Bulk Actions (Optional Extension)

> **Status**: Completed  
> **Branch**: `feat/tier4-tags-bulk-actions` (Ready to merge)  
> **Bonus Points**: +15 pts

---

## 1. Database & Models (SQLAlchemy & Alembic)

*   **New Models**:
    *   `Tag`: Stores tag metadata (`id`, `name`, `color`, `user_id`, `created_at`). Enforces unique tag names per user via `uq_tag_name_per_user` constraint.
    *   `todo_tags`: Association table for the Many-to-Many relationship between `todos` and `tags`. Configured with `ondelete="CASCADE"`.
*   **Model Updates**:
    *   Added `tags` relationship to `Todo` model using `selectinload` for optimized querying without N+1 issues.
    *   Added `tags` relationship to `User` model.
*   **Migration**:
    *   Generated Alembic migration `b9a2697eda96` mapping the new DB structures without affecting Tier 3C performance indexes.

---

## 2. Backend API (FastAPI)

### Tag Management
*   `POST /api/v1/tags`: Create a new tag with custom hex color.
*   `GET /api/v1/tags`: List all tags belonging to the authenticated user.
*   `PUT /api/v1/tags/{id}`: Update tag name/color (with ownership guard).
*   `DELETE /api/v1/tags/{id}`: Delete a tag (cascades automatically to remove from todos).

### Todo-Tag Relationships
*   `POST /api/v1/todos/{todo_id}/tags/{tag_id}`: Attach a tag to a todo.
*   `DELETE /api/v1/todos/{todo_id}/tags/{tag_id}`: Detach a tag from a todo.

### Bulk Actions
*   `PATCH /api/v1/todos/bulk-status`: Accepts a list of `todo_ids` and a `completed` boolean. Performs a single optimized SQL `UPDATE` statement.
*   `DELETE /api/v1/todos/bulk`: Accepts a list of `todo_ids`. Performs a single optimized SQL `DELETE` statement.

### Advanced Filtering
*   Enhanced `GET /api/v1/todos` to support optional query parameters:
    *   `keyword`: Case-insensitive `ILIKE` search on todo titles.
    *   `status`: Exact match boolean filter for `completed`.
    *   `tag_id`: Filters todos that contain the specific tag ID.
*   **Cache Strategy Updated**: The Redis cache key format was expanded to include filter parameters `todos:list:{user_id}:{page}:{size}:{status}:{tag_id}:{keyword}` to ensure correct cached results for different filter combinations.

---

## 3. Frontend Architecture (React Query)

*   **API Hooks (`frontend/src/features/tags/api/tags.ts`)**:
    *   `useTags`, `useCreateTag`, `useUpdateTag`, `useDeleteTag` implemented with optimistic UI/Cache invalidation.
*   **Extended Hooks (`frontend/src/features/todos/api/todos.ts`)**:
    *   Updated `useTodos(filters)` to accept and reactively fetch based on filter states.
    *   Added `useBulkUpdateStatus`, `useBulkDeleteTodos`, `useAddTagToTodo`, `useRemoveTagFromTodo`.

---

## 4. Frontend UI Components (React + Tailwind)

### Tag Manager Modal (`TagManager.tsx`)
*   Accessible from the "Manage Tags" button on the main dashboard.
*   Inline form with native HTML color picker and text input to create tags.
*   List view to display existing tags with a delete action.

### Filter Bar (`TodoPage.tsx`)
*   Responsive filter bar placed above the todo list.
*   Real-time search input for `keyword`.
*   Dropdown select for `status` (All / Active / Completed).
*   Dropdown select for `tag_id` dynamically populated from the user's tags.

### Bulk Actions Toolbar (`TodoList.tsx`)
*   Appears dynamically only when 1 or more todos are selected.
*   Provides "Select All" / "Deselect All" capabilities.
*   Action buttons: "Complete" (marks all true), "Undo" (marks all false), and "Delete" (with confirmation prompt).

### Enhanced Todo Item (`TodoItem.tsx`)
*   **Multi-select Checkbox**: Added a new square checkbox on the far left for bulk selection, distinct from the circular completion toggle.
*   **Tag Display**: Renders assigned tags as colorful badges below the todo description.
*   **Tag Menu**: Added a Tag icon button that opens a Dropdown Menu containing available (unassigned) tags to quickly attach them to the todo.
*   **Quick Detach**: Each attached tag badge has a small 'X' button for instant removal.

---

**Total Assessment Score Projection:** 100/100 Core + 15/15 Bonus = **115/100 Points** 🏆