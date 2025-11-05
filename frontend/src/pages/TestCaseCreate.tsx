import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { testCasesApi } from "@/services/testCasesApi";

const TestCaseCreate = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const [searchParams] = useSearchParams();
  const returnTab = searchParams.get("tab") || "overview";
  const navigate = useNavigate();

  const [form, setForm] = useState<{ description: string; arguments: string; expected_output: string }>({ description: "", arguments: "{}", expected_output: "[]" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!taskId) return;
    try {
      setSubmitting(true);
      setError(null);
      const argsObj = JSON.parse(form.arguments || "{}");
      const expectedArray = JSON.parse(form.expected_output || "[]");
      await testCasesApi.createTestCase({
        task_id: String(taskId),
        description: form.description || undefined,
        arguments: argsObj,
        expected_output: expectedArray,
      } as any);
      navigate(`/tasks/${taskId}?tab=${returnTab}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create test case");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col -m-6 bg-background font-sans">
      <div className="px-6 pt-6 pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Create Test Case</h1>
            <p className="text-muted-foreground">For task {taskId}</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="w-full p-4 space-y-6">
          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">Description</div>
            <Input id="tc-desc" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          </div>

          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">Arguments</div>
            <Textarea id="tc-args" rows={12} className="font-mono text-xs" value={form.arguments} onChange={(e) => setForm((f) => ({ ...f, arguments: e.target.value }))} />
          </div>

          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">Expected Output</div>
            <Textarea id="tc-exp" rows={8} className="font-mono text-xs" value={form.expected_output} onChange={(e) => setForm((f) => ({ ...f, expected_output: e.target.value }))} />
          </div>

          {error && <div className="text-sm text-destructive">{error}</div>}

          <div className="flex justify-end gap-2 pt-1">
            <Button variant="outline" onClick={() => navigate(`/tasks/${taskId}?tab=${returnTab}`)} disabled={submitting}>Cancel</Button>
            <Button onClick={handleCreate} disabled={submitting}>{submitting ? (<><Loader2 className="h-4 w-4 animate-spin" /> Creating...</>) : 'Create'}</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TestCaseCreate;


