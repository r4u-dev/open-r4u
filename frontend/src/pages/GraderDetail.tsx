import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Save, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useProject } from "@/contexts/ProjectContext";
import { gradersApi, ScoreType } from "@/services/gradersApi";

const formSchema = z.object({
    name: z.string().min(1, "Name is required").max(255),
    description: z.string().optional(),
    prompt: z.string().min(1, "Prompt is required"),
    score_type: z.nativeEnum(ScoreType),
    model: z.string().min(1, "Model is required"),
    temperature: z.number().min(0).max(2).optional(),
    max_output_tokens: z.number().min(1),
    is_active: z.boolean(),
});

type FormValues = z.infer<typeof formSchema>;

const GraderDetail = () => {
    const { activeProject } = useProject();
    const projectId = activeProject?.id ? Number(activeProject.id) : null;
    const { graderId } = useParams();
    const navigate = useNavigate();
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const isEditMode = !!graderId;

    const { data: grader, isLoading: isLoadingGrader } = useQuery({
        queryKey: ["grader", graderId],
        queryFn: () => gradersApi.get(Number(graderId)),
        enabled: isEditMode,
    });

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            description: "",
            prompt: "",
            score_type: ScoreType.float,
            model: "gpt-4o",
            temperature: 0.0,
            max_output_tokens: 1000,
            is_active: true,
        },
    });

    useEffect(() => {
        if (grader?.data) {
            form.reset({
                name: grader.data.name,
                description: grader.data.description || "",
                prompt: grader.data.prompt,
                score_type: grader.data.score_type,
                model: grader.data.model,
                temperature: grader.data.temperature || 0.0,
                max_output_tokens: grader.data.max_output_tokens,
                is_active: grader.data.is_active,
            });
        }
    }, [grader, form]);

    const createMutation = useMutation({
        mutationFn: (data: FormValues) =>
            gradersApi.create({
                project_id: projectId!,
                name: data.name,
                prompt: data.prompt,
                score_type: data.score_type,
                model: data.model,
                max_output_tokens: data.max_output_tokens,
                is_active: data.is_active,
                description: data.description || null,
                temperature: data.temperature || null,
                reasoning: null,
                response_schema: null,
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["graders", projectId] });
            toast({
                title: "Grader created",
                description: "The grader has been successfully created.",
            });
            navigate("/graders");
        },
        onError: (error) => {
            toast({
                title: "Error",
                description: "Failed to create grader. Please try again.",
                variant: "destructive",
            });
            console.error("Failed to create grader:", error);
        },
    });

    const updateMutation = useMutation({
        mutationFn: (data: FormValues) =>
            gradersApi.update(Number(graderId), data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["graders", projectId] });
            queryClient.invalidateQueries({ queryKey: ["grader", graderId] });
            toast({
                title: "Grader updated",
                description: "The grader has been successfully updated.",
            });
            navigate("/graders");
        },
        onError: (error) => {
            toast({
                title: "Error",
                description: "Failed to update grader. Please try again.",
                variant: "destructive",
            });
            console.error("Failed to update grader:", error);
        },
    });

    const onSubmit = (data: FormValues) => {
        if (isEditMode) {
            updateMutation.mutate(data);
        } else {
            createMutation.mutate(data);
        }
    };

    if (isEditMode && isLoadingGrader) {
        return (
            <div className="flex items-center justify-center h-full">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => navigate("/graders")}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">
                        {isEditMode ? "Edit Grader" : "Create Grader"}
                    </h1>
                    <p className="text-muted-foreground">
                        {isEditMode
                            ? "Update the configuration for this grader."
                            : "Configure a new LLM-based grader."}
                    </p>
                </div>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                    <Card>
                        <CardHeader>
                            <CardTitle>General Information</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <FormField
                                control={form.control}
                                name="name"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Name</FormLabel>
                                        <FormControl>
                                            <Input placeholder="e.g. Accuracy Grader" {...field} />
                                        </FormControl>
                                        <FormDescription>
                                            A unique name for this grader.
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="description"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Description</FormLabel>
                                        <FormControl>
                                            <Textarea
                                                placeholder="Describe what this grader evaluates..."
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="is_active"
                                render={({ field }) => (
                                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                                        <div className="space-y-0.5">
                                            <FormLabel className="text-base">Active Status</FormLabel>
                                            <FormDescription>
                                                Enable or disable this grader for evaluations.
                                            </FormDescription>
                                        </div>
                                        <FormControl>
                                            <Switch
                                                checked={field.value}
                                                onCheckedChange={field.onChange}
                                            />
                                        </FormControl>
                                    </FormItem>
                                )}
                            />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>LLM Configuration</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="model"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Model</FormLabel>
                                            <FormControl>
                                                <Input placeholder="e.g. gpt-4o" {...field} />
                                            </FormControl>
                                            <FormDescription>
                                                The LLM model ID to use.
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="score_type"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Score Type</FormLabel>
                                            <Select
                                                onValueChange={field.onChange}
                                                defaultValue={field.value}
                                            >
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select a score type" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value={ScoreType.float}>
                                                        Float (0.0 - 1.0)
                                                    </SelectItem>
                                                    <SelectItem value={ScoreType.boolean}>
                                                        Boolean (True/False)
                                                    </SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormDescription>
                                                The type of score returned by the grader.
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <FormField
                                control={form.control}
                                name="temperature"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Temperature: {field.value}</FormLabel>
                                        <FormControl>
                                            <Slider
                                                min={0}
                                                max={2}
                                                step={0.1}
                                                value={[field.value || 0]}
                                                onValueChange={(vals) => field.onChange(vals[0])}
                                            />
                                        </FormControl>
                                        <FormDescription>
                                            Controls randomness (0 = deterministic, 2 = creative).
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="max_output_tokens"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Max Output Tokens</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number"
                                                {...field}
                                                onChange={(e) => field.onChange(Number(e.target.value))}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Prompt</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <FormField
                                control={form.control}
                                name="prompt"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>System Prompt</FormLabel>
                                        <FormControl>
                                            <Textarea
                                                className="font-mono min-h-[300px]"
                                                placeholder="You are an expert evaluator..."
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormDescription>
                                            The prompt used to instruct the LLM how to grade. You can use
                                            variables like {"{{task_arguments}}"}, {"{{expected_output}}"}, and
                                            {"{{actual_output}}"}.
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </CardContent>
                    </Card>

                    <div className="flex justify-end">
                        <Button
                            type="submit"
                            disabled={createMutation.isPending || updateMutation.isPending}
                        >
                            {(createMutation.isPending || updateMutation.isPending) && (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            )}
                            {isEditMode ? "Update Grader" : "Create Grader"}
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
};

export default GraderDetail;
