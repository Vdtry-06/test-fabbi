import { useState } from "react";
import { TodoItem } from "./TodoItem";
import { TodoForm } from "./TodoForm";
import type { Todo } from "../api/todos";
import { useDeleteTodo, useToggleTodo, useBulkUpdateStatus, useBulkDeleteTodos } from "../api/todos";
import { Button } from "@/components/ui/button";
import { CheckSquare, Square, Trash2, Check } from "lucide-react";

interface TodoListProps {
  todos: Todo[];
}

export function TodoList({ todos }: TodoListProps) {
  const [editingTodo, setEditingTodo] = useState<Todo | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  
  const deleteTodo = useDeleteTodo();
  const toggleTodo = useToggleTodo();
  const bulkUpdate = useBulkUpdateStatus();
  const bulkDelete = useBulkDeleteTodos();

  const handleToggle = (todo: Todo) => {
    toggleTodo.mutate(todo);
  };

  const handleEdit = (todo: Todo) => {
    setEditingTodo(todo);
  };

  const handleDelete = (id: string) => {
    deleteTodo.mutate(id);
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const handleSelect = (id: string, selected: boolean) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (selected) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const selectAll = () => setSelectedIds(new Set(todos.map(t => t.id)));
  const deselectAll = () => setSelectedIds(new Set());

  const handleBulkComplete = (completed: boolean) => {
    bulkUpdate.mutate({ todo_ids: Array.from(selectedIds), completed }, {
      onSuccess: () => setSelectedIds(new Set())
    });
  };

  const handleBulkDelete = () => {
    if (confirm("Are you sure you want to delete selected todos?")) {
      bulkDelete.mutate({ todo_ids: Array.from(selectedIds) }, {
        onSuccess: () => setSelectedIds(new Set())
      });
    }
  };

  if (todos.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p className="text-lg">No todos found</p>
      </div>
    );
  }

  return (
    <>
      {todos.length > 0 && (
        <div className="flex items-center justify-between mb-4 bg-muted/30 p-2 rounded-md border">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={selectedIds.size === todos.length ? deselectAll : selectAll}>
              {selectedIds.size === todos.length ? <CheckSquare className="w-4 h-4 mr-2" /> : <Square className="w-4 h-4 mr-2" />}
              {selectedIds.size > 0 ? `${selectedIds.size} selected` : "Select All"}
            </Button>
          </div>
          
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => handleBulkComplete(true)}>
                <Check className="w-4 h-4 mr-1 text-green-600" /> Complete
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleBulkComplete(false)}>
                <CheckSquare className="w-4 h-4 mr-1 text-gray-500" /> Undo
              </Button>
              <Button variant="destructive" size="sm" onClick={handleBulkDelete}>
                <Trash2 className="w-4 h-4 mr-1" /> Delete
              </Button>
            </div>
          )}
        </div>
      )}

      <div className="space-y-2">
        {todos.map((todo, index) => (
          <TodoItem
            key={index}
            todo={todo}
            index={index}
            onToggle={handleToggle}
            onEdit={handleEdit}
            onDelete={handleDelete}
            isSelected={selectedIds.has(todo.id)}
            onSelect={handleSelect}
          />
        ))}
      </div>

      {editingTodo && (
        <TodoForm
          mode="edit"
          todo={editingTodo}
          open={!!editingTodo}
          onClose={() => setEditingTodo(null)}
        />
      )}
    </>
  );
}