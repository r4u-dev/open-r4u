import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Loader2, Pencil, X, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { testCasesApi, TestCase } from "@/services/testCasesApi";

const TestCaseDetail = () => {
  const { taskId, testCaseId } = useParams<{ taskId: string; testCaseId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTab = searchParams.get("tab") || "overview";
  const [tc, setTc] = useState<TestCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editDesc, setEditDesc] = useState(false);
  const [editArgs, setEditArgs] = useState(false);
  const [editExp, setEditExp] = useState(false);
  const [descValue, setDescValue] = useState("");
  const [argsValue, setArgsValue] = useState("{}");
  const [expValue, setExpValue] = useState("");
  const [descSubmitting, setDescSubmitting] = useState(false);
  const [argsSubmitting, setArgsSubmitting] = useState(false);
  const [expSubmitting, setExpSubmitting] = useState(false);
  const [descError, setDescError] = useState<string | null>(null);
  const [argsError, setArgsError] = useState<string | null>(null);
  const [expError, setExpError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      if (!testCaseId) return;
      try {
        setLoading(true);
        setError(null);
        const res = await testCasesApi.getTestCase(String(testCaseId));
        const data = res.data as any;
        setTc(data);
        setDescValue(data.description || "");
        setArgsValue(JSON.stringify((data as any).arguments ?? {}, null, 2));
        setExpValue(JSON.stringify(data.expected_output ?? [], null, 2));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load test case");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [testCaseId]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Loading test case...</p>
        </div>
      </div>
    );
  }

  if (error || !tc) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">{error || "Test case not found"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col -m-6 bg-background font-sans">
      <div className="px-6 pt-6 pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Test Case {tc.id}</h1>
            <p className="text-muted-foreground">Belongs to task {taskId}</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="w-full p-4 space-y-4">
          <div className="border border-border rounded-lg p-4">
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs text-muted-foreground">Description</div>
              {!editDesc ? (
                <Button variant="outline" size="icon" onClick={() => { setEditDesc(true); setDescError(null); setDescValue(tc.description || ""); }} aria-label="Edit description">
                  <Pencil className="h-4 w-4" />
                </Button>
              ) : (
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="icon" onClick={() => { setEditDesc(false); setDescError(null); setDescValue(tc.description || ""); }} disabled={descSubmitting} aria-label="Cancel description edit">
                    <X className="h-4 w-4" />
                  </Button>
                  <Button size="icon" onClick={async () => {
                    if (!testCaseId) return;
                    try {
                      setDescSubmitting(true);
                      setDescError(null);
                      const res = await testCasesApi.patchTestCase(String(testCaseId), { description: descValue || undefined } as any);
                      const updated = res.data as any;
                      setTc(updated);
                      setDescValue(updated.description || "");
                      setEditDesc(false);
                    } catch (e) {
                      setDescError(e instanceof Error ? e.message : "Failed to update description");
                    } finally {
                      setDescSubmitting(false);
                    }
                  }} disabled={descSubmitting} aria-label="Save description">
                    {descSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  </Button>
                </div>
              )}
            </div>
            {!editDesc ? (
              <div className="text-sm">{tc.description || "—"}</div>
            ) : (
              <Textarea rows={2} value={descValue} onChange={(e) => setDescValue(e.target.value)} />
            )}
            {descError && <div className="text-xs text-destructive mt-2">{descError}</div>}
          </div>

          <div className="border border-border rounded-lg p-4">
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs text-muted-foreground">Arguments</div>
              {!editArgs ? (
                <Button variant="outline" size="icon" onClick={() => { setEditArgs(true); setArgsError(null); setArgsValue(JSON.stringify((tc as any).arguments ?? {}, null, 2)); }} aria-label="Edit arguments">
                  <Pencil className="h-4 w-4" />
                </Button>
              ) : (
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="icon" onClick={() => { setEditArgs(false); setArgsError(null); setArgsValue(JSON.stringify((tc as any).arguments ?? {}, null, 2)); }} disabled={argsSubmitting} aria-label="Cancel arguments edit">
                    <X className="h-4 w-4" />
                  </Button>
                  <Button size="icon" onClick={async () => {
                    if (!testCaseId) return;
                    try {
                      setArgsSubmitting(true);
                      setArgsError(null);
                      const parsed = JSON.parse(argsValue || "{}");
                      const res = await testCasesApi.patchTestCase(String(testCaseId), { arguments: parsed } as any);
                      const updated = res.data as any;
                      setTc(updated);
                      setArgsValue(JSON.stringify((updated as any).arguments ?? {}, null, 2));
                      setEditArgs(false);
                    } catch (e) {
                      setArgsError(e instanceof Error ? e.message : "Failed to update arguments (must be valid JSON)");
                    } finally {
                      setArgsSubmitting(false);
                    }
                  }} disabled={argsSubmitting} aria-label="Save arguments">
                    {argsSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  </Button>
                </div>
              )}
            </div>
            {!editArgs ? (
              <pre className="bg-muted p-3 rounded text-xs overflow-auto">{JSON.stringify((tc as any).arguments ?? {}, null, 2)}</pre>
            ) : (
              <Textarea rows={10} className="font-mono text-xs" value={argsValue} onChange={(e) => setArgsValue(e.target.value)} />
            )}
            {argsError && <div className="text-xs text-destructive mt-2">{argsError}</div>}
          </div>

          <div className="border border-border rounded-lg p-4">
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs text-muted-foreground">Expected Output</div>
              {!editExp ? (
                <Button variant="outline" size="icon" onClick={() => { setEditExp(true); setExpError(null); setExpValue(JSON.stringify(tc.expected_output ?? [], null, 2)); }} aria-label="Edit expected output">
                  <Pencil className="h-4 w-4" />
                </Button>
              ) : (
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="icon" onClick={() => { setEditExp(false); setExpError(null); setExpValue(JSON.stringify(tc.expected_output ?? [], null, 2)); }} disabled={expSubmitting} aria-label="Cancel expected output edit">
                    <X className="h-4 w-4" />
                  </Button>
                  <Button size="icon" onClick={async () => {
                    if (!testCaseId) return;
                    try {
                      setExpSubmitting(true);
                      setExpError(null);
                      const expectedArray = JSON.parse(expValue || "[]");
                      const res = await testCasesApi.patchTestCase(String(testCaseId), { expected_output: expectedArray } as any);
                      const updated = res.data as any;
                      setTc(updated);
                      setExpValue(JSON.stringify(updated.expected_output ?? [], null, 2));
                      setEditExp(false);
                    } catch (e) {
                      setExpError(e instanceof Error ? e.message : "Failed to update expected output");
                    } finally {
                      setExpSubmitting(false);
                    }
                  }} disabled={expSubmitting} aria-label="Save expected output">
                    {expSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  </Button>
                </div>
              )}
            </div>
            {!editExp ? (
              <pre className="bg-muted p-3 rounded text-xs overflow-auto">{JSON.stringify(tc.expected_output ?? [], null, 2)}</pre>
            ) : (
              <Textarea rows={6} className="font-mono text-xs" value={expValue} onChange={(e) => setExpValue(e.target.value)} />
            )}
            {expError && <div className="text-xs text-destructive mt-2">{expError}</div>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TestCaseDetail;


