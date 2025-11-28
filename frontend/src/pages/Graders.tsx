import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Plus, MoreHorizontal, Pencil, Trash2, Check, X } from "lucide-react";
import { format } from "date-fns";

import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useProject } from "@/contexts/ProjectContext";
import { gradersApi, GraderListItem } from "@/services/gradersApi";
import { useToast } from "@/hooks/use-toast";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const Graders = () => {
    const { activeProject } = useProject();
    const projectId = activeProject?.id ? Number(activeProject.id) : null;
    const navigate = useNavigate();
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [graderToDelete, setGraderToDelete] = useState<GraderListItem | null>(null);

    const { data: graders, isLoading } = useQuery({
        queryKey: ["graders", projectId],
        queryFn: () => gradersApi.listByProject(projectId!),
        enabled: !!projectId,
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => gradersApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["graders", projectId] });
            toast({
                title: "Grader deleted",
                description: "The grader has been successfully deleted.",
            });
            setGraderToDelete(null);
        },
        onError: (error) => {
            toast({
                title: "Error",
                description: "Failed to delete grader. Please try again.",
                variant: "destructive",
            });
            console.error("Failed to delete grader:", error);
        },
    });

    const handleDeleteConfirm = () => {
        if (graderToDelete) {
            deleteMutation.mutate(graderToDelete.id);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Graders</h1>
                    <p className="text-muted-foreground">
                        Manage LLM-based graders for evaluating your tasks.
                    </p>
                </div>
                <Button onClick={() => navigate("/graders/new")}>
                    <Plus className="mr-2 h-4 w-4" />
                    Create Grader
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>All Graders</CardTitle>
                    <CardDescription>
                        List of all graders configured for this project.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {graders?.data && graders.data.length > 0 ? (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Name</TableHead>
                                    <TableHead>Description</TableHead>
                                    <TableHead>Score Type</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Created At</TableHead>
                                    <TableHead className="w-[70px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {graders.data.map((grader) => (
                                    <TableRow key={grader.id}>
                                        <TableCell className="font-medium">
                                            <Link
                                                to={`/graders/${grader.id}`}
                                                className="hover:underline text-primary"
                                            >
                                                {grader.name}
                                            </Link>
                                        </TableCell>
                                        <TableCell className="max-w-[300px] truncate">
                                            {grader.description || "-"}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline">{grader.score_type}</Badge>
                                        </TableCell>
                                        <TableCell>
                                            {grader.is_active ? (
                                                <Badge variant="default" className="bg-green-500 hover:bg-green-600">
                                                    <Check className="mr-1 h-3 w-3" /> Active
                                                </Badge>
                                            ) : (
                                                <Badge variant="secondary">
                                                    <X className="mr-1 h-3 w-3" /> Inactive
                                                </Badge>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {format(new Date(grader.created_at), "MMM d, yyyy")}
                                        </TableCell>
                                        <TableCell>
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button variant="ghost" className="h-8 w-8 p-0">
                                                        <span className="sr-only">Open menu</span>
                                                        <MoreHorizontal className="h-4 w-4" />
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuItem
                                                        onClick={() => navigate(`/graders/${grader.id}`)}
                                                    >
                                                        <Pencil className="mr-2 h-4 w-4" />
                                                        Edit
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem
                                                        className="text-destructive focus:text-destructive"
                                                        onClick={() => setGraderToDelete(grader)}
                                                    >
                                                        <Trash2 className="mr-2 h-4 w-4" />
                                                        Delete
                                                    </DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    ) : (
                        <div className="text-center py-10">
                            <p className="text-muted-foreground mb-4">No graders found.</p>
                            <Button variant="outline" onClick={() => navigate("/graders/new")}>
                                Create your first grader
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            <AlertDialog
                open={!!graderToDelete}
                onOpenChange={(open) => !open && setGraderToDelete(null)}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. This will permanently delete the grader
                            "{graderToDelete?.name}" and all associated grades.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDeleteConfirm}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
};

export default Graders;
