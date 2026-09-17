import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useTags, useCreateTag, useDeleteTag } from "../api/tags";
import { Trash2 } from "lucide-react";

interface TagManagerProps {
  open: boolean;
  onClose: () => void;
}

export function TagManager({ open, onClose }: TagManagerProps) {
  const { data: tags } = useTags();
  const createTag = useCreateTag();
  const deleteTag = useDeleteTag();
  
  const [name, setName] = useState("");
  const [color, setColor] = useState("#E2E8F0");

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    createTag.mutate(
      { name, color },
      {
        onSuccess: () => {
          setName("");
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Manage Tags</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleCreate} className="flex gap-2 items-center mb-4">
          <Input 
            type="color" 
            value={color} 
            onChange={(e) => setColor(e.target.value)}
            className="w-12 h-10 p-1"
          />
          <Input 
            value={name} 
            onChange={(e) => setName(e.target.value)}
            placeholder="New tag name"
            maxLength={50}
          />
          <Button type="submit" disabled={createTag.isPending || !name.trim()}>
            Add
          </Button>
        </form>

        <div className="space-y-2 max-h-[300px] overflow-y-auto">
          {tags?.map((tag) => (
            <div key={tag.id} className="flex items-center justify-between p-2 border rounded-md">
              <div className="flex items-center gap-2">
                <div 
                  className="w-4 h-4 rounded-full" 
                  style={{ backgroundColor: tag.color }} 
                />
                <span className="text-sm font-medium">{tag.name}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                onClick={() => deleteTag.mutate(tag.id)}
                disabled={deleteTag.isPending}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
          {tags?.length === 0 && (
            <div className="text-center text-sm text-muted-foreground py-4">
              No tags created yet.
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}