import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Pencil, Trash2, Tag as TagIcon, X } from "lucide-react";
import type { Todo } from "../api/todos";
import { useTags } from "@/features/tags/api/tags";
import { useAddTagToTodo, useRemoveTagFromTodo } from "../api/todos";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface TodoItemProps {
  todo: Todo;
  index: number;
  onToggle: (todo: Todo) => void;
  onEdit: (todo: Todo) => void;
  onDelete: (id: string) => void;
  isSelected: boolean;
  onSelect: (id: string, selected: boolean) => void;
}

export function TodoItem({ todo, onToggle, onEdit, onDelete, isSelected, onSelect }: TodoItemProps) {
  const { data: allTags } = useTags();
  const addTag = useAddTagToTodo();
  const removeTag = useRemoveTagFromTodo();

  const handleAddTag = (tagId: string) => {
    addTag.mutate({ todo_id: todo.id, tag_id: tagId });
  };

  const handleRemoveTag = (tagId: string) => {
    removeTag.mutate({ todo_id: todo.id, tag_id: tagId });
  };

  // Filter out tags that are already added
  const availableTags = allTags?.filter(t => !todo.tags?.find(tt => tt.id === t.id)) || [];

  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg border transition-colors group ${isSelected ? 'bg-accent/30 border-primary' : 'bg-card hover:bg-accent/50'}`}>
      
      <Checkbox
        checked={isSelected}
        onCheckedChange={(c) => onSelect(todo.id, !!c)}
        className="data-[state=checked]:bg-primary rounded-[4px]"
      />

      <Checkbox
        id={`todo-${todo.id}`}
        checked={todo.completed}
        onCheckedChange={() => onToggle(todo)}
        className="rounded-full"
      />

      <div className="flex-1 min-w-0">
        <label
          htmlFor={`todo-${todo.id}`}
          className={`text-sm font-medium cursor-pointer ${
            todo.completed ? "line-through text-muted-foreground" : ""
          }`}
        >
          {todo.title}
        </label>
        {todo.description && (
          <p className="text-xs text-muted-foreground mt-0.5 truncate">
            {todo.description}
          </p>
        )}
        
        {todo.tags && todo.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {todo.tags.map(tag => (
              <div 
                key={tag.id} 
                className="flex items-center text-[10px] font-medium px-1.5 py-0.5 rounded gap-1"
                style={{ backgroundColor: tag.color + '40', color: '#333' }}
              >
                {tag.name}
                <button 
                  onClick={() => handleRemoveTag(tag.id)} 
                  className="hover:bg-black/10 rounded-full p-0.5"
                  disabled={removeTag.isPending}
                >
                  <X className="w-2 h-2" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <TagIcon className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {availableTags.length === 0 ? (
              <div className="p-2 text-xs text-muted-foreground">No tags available</div>
            ) : (
              availableTags.map(tag => (
                <DropdownMenuItem key={tag.id} onClick={() => handleAddTag(tag.id)}>
                  <div className="w-2 h-2 rounded-full mr-2" style={{ backgroundColor: tag.color }} />
                  {tag.name}
                </DropdownMenuItem>
              ))
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => onEdit(todo)}
        >
          <Pencil className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-destructive hover:text-destructive"
          onClick={() => onDelete(todo.id)}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}