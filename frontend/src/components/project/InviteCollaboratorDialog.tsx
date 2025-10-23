import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { addProjectCollaborator } from "@/lib/api/collaborators";
import type { ProjectRole } from "@/lib/types/collaborator";
import { UserPlus } from "lucide-react";

interface InviteCollaboratorDialogProps {
  projectId: string;
  isOwner?: boolean; // Whether the current user is the owner
}

export function InviteCollaboratorDialog({ projectId, isOwner = false }: InviteCollaboratorDialogProps) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ProjectRole>("editor");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const inviteMutation = useMutation({
    mutationFn: async () => {
      // Note: Backend expects account_id, but UI typically works with email
      // This assumes backend will handle email-to-account_id lookup
      // or we need to add an endpoint to search users by email first
      return addProjectCollaborator(projectId, {
        email, // This may need adjustment based on backend implementation
        role,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collaborators", projectId] });
      toast({
        title: "Collaborator invited",
        description: `Successfully invited ${email} as ${role}`,
      });
      setOpen(false);
      setEmail("");
      setRole("editor");
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to invite collaborator",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      toast({
        title: "Email required",
        description: "Please enter a valid email address",
        variant: "destructive",
      });
      return;
    }
    inviteMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-2">
          <UserPlus className="h-4 w-4" />
          Invite Member
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Invite Team Member</DialogTitle>
            <DialogDescription>
              Add a new member to your project. They'll receive an invitation email.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="colleague@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="role">Role</Label>
              <Select value={role} onValueChange={(value) => setRole(value as ProjectRole)}>
                <SelectTrigger id="role">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="viewer">Viewer - Read-only access</SelectItem>
                  <SelectItem value="editor">Editor - Can edit and create</SelectItem>
                  {isOwner && (
                    <SelectItem value="admin">Admin - Full control</SelectItem>
                  )}
                </SelectContent>
              </Select>
              {!isOwner && (
                <p className="text-xs text-muted-foreground">
                  Only project owners can invite admins
                </p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={inviteMutation.isPending}>
              {inviteMutation.isPending ? "Inviting..." : "Send Invitation"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
