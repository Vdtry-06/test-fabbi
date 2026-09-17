import { useState } from "react";
import { Plus, LogOut, Tags, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { useTodos } from "../api/todos";
import { TodoList } from "./TodoList";
import { TodoForm } from "./TodoForm";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { TagManager } from "@/features/tags/components/TagManager";
import { useTags } from "@/features/tags/api/tags";

export function TodoPage() {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showTagManager, setShowTagManager] = useState(false);
  
  // Filters state
  const [keyword, setKeyword] = useState("");
  const [status, setStatus] = useState<boolean | undefined>(undefined);
  const [tagId, setTagId] = useState<string | undefined>(undefined);

  const { data, isLoading, error } = useTodos({ keyword, status, tag_id: tagId });
  const { data: tags } = useTags();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-muted/40">
      <header className="bg-card border-b">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Todo App</h1>
            {user && (
              <p className="text-sm text-muted-foreground">{user.email}</p>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <Card>
          <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-lg">My Todos</CardTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowTagManager(true)}>
                <Tags className="h-4 w-4 mr-1" />
                Manage Tags
              </Button>
              <Button size="sm" onClick={() => setShowCreateForm(true)}>
                <Plus className="h-4 w-4 mr-1" />
                Add Todo
              </Button>
            </div>
          </CardHeader>
          <Separator />
          <CardContent className="pt-4">
            
            {/* Filter Bar */}
            <div className="flex flex-col sm:flex-row gap-2 mb-6">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search todos..."
                  className="pl-9"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                />
              </div>
              <select
                className="flex h-10 w-full sm:w-[150px] items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={status === undefined ? "" : status ? "true" : "false"}
                onChange={(e) => {
                  const val = e.target.value;
                  setStatus(val === "" ? undefined : val === "true");
                }}
              >
                <option value="">All Status</option>
                <option value="false">Active</option>
                <option value="true">Completed</option>
              </select>
              <select
                className="flex h-10 w-full sm:w-[150px] items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={tagId || ""}
                onChange={(e) => setTagId(e.target.value || undefined)}
              >
                <option value="">All Tags</option>
                {tags?.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>

            {isLoading && (
              <div className="text-center py-12 text-muted-foreground">
                Loading todos...
              </div>
            )}

            {error && (
              <div className="text-center py-12 text-destructive">
                Failed to load todos. Please try again.
              </div>
            )}

            {data && <TodoList todos={data.items} />}

            {data && data.total > 0 && (
              <div className="mt-4 text-center text-sm text-muted-foreground">
                Showing {data.items.length} of {data.total} todos
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      <TodoForm
        mode="create"
        open={showCreateForm}
        onClose={() => setShowCreateForm(false)}
      />

      <TagManager 
        open={showTagManager} 
        onClose={() => setShowTagManager(false)} 
      />
    </div>
  );
}