import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import EmptyState from "@/components/dashboard/EmptyState";
import MetricCard from "@/components/dashboard/MetricCard";
import { Rocket, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useProject } from "@/contexts/ProjectContext";
import { optimizationsApi } from "@/services/optimizationsApi";
import type { OptimizationDashboardResponse } from "@/lib/types/optimization";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const Optimizations = () => {
  const { activeProject } = useProject();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<OptimizationDashboardResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await optimizationsApi.getDashboardMetrics({ days: 30 });
        if (!mounted) return;
        setData(res.data);
      } catch (e: any) {
        if (!mounted) return;
        setError(e?.message || "Failed to load optimization metrics");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const sortedOutperformers = useMemo(() => {
    if (!data) return [] as NonNullable<OptimizationDashboardResponse>["outperforming_versions"];
    const list = [...data.outperforming_versions];
    list.sort((a, b) => {
      const byTask = a.task_name.localeCompare(b.task_name);
      if (byTask !== 0) return byTask;
      const aScore = a.optimized_score ?? -Infinity;
      const bScore = b.optimized_score ?? -Infinity;
      return bScore - aScore; // highest impl first within task
    });
    return list;
  }, [data]);

  const summaryCards = useMemo(() => {
    const summary = data?.summary;
    return [
      {
        id: "score-boost",
        title: "Score Boost",
        value: summary?.score_boost_percent != null ? `${summary.score_boost_percent.toFixed(1)}%` : "--",
        change: 0,
        trendDirection: (summary?.score_boost_percent != null && summary.score_boost_percent >= 0 ? "up" : "down") as "up" | "down",
        isPositiveChange: true,
      },
      {
        id: "quality-boost",
        title: "Quality Boost",
        value: summary?.quality_boost_percent != null ? `${summary.quality_boost_percent.toFixed(1)}%` : "--",
        change: 0,
        trendDirection: (summary?.quality_boost_percent != null && summary.quality_boost_percent >= 0 ? "up" : "down") as "up" | "down",
        isPositiveChange: true,
      },
      {
        id: "money-saved",
        title: "Money Saved",
        value: summary?.money_saved != null ? `$${Math.round(summary.money_saved).toLocaleString()}` : "--",
        change: 0,
        trendDirection: "up" as const,
        isPositiveChange: true,
      },
      {
        id: "running",
        title: "Running Optimizations",
        value: summary?.running_count != null ? summary.running_count : "--",
        change: 0,
        trendDirection: "stable" as const,
      },
    ];
  }, [data]);

  const renderDelta = (
    value: number | null | undefined,
    type: "score" | "qualityPercent" | "costPercent" | "timeMs",
  ) => {
    if (value == null) return <span>--</span>;
    // Backend deltas are defined so that POSITIVE means improvement for all types
    // (score, quality%, cost%, timeMs). So we treat positive as good uniformly for color/arrow.
    const effective = value; // positive effective means good
    const isPositiveGood = type === "score" || type === "qualityPercent"; // for sign rendering
    const GoodIcon = ArrowUpRight;
    const BadIcon = ArrowDownRight;
    const isZero = Math.abs(value) < 1e-9;
    const isGood = effective > 0;
    const color = isGood ? "text-green-600" : "text-destructive";

    let formatted: string;
    if (type === "qualityPercent" || type === "costPercent") {
      formatted = `${Math.abs(value).toFixed(1)}%`;
    } else if (type === "timeMs") {
      const ms = Math.abs(value);
      formatted = `${ms.toFixed(1)} ms`;
    } else {
      // score
      formatted = `${Math.abs(value).toFixed(2)}`;
    }

    if (isZero) {
      return (
        <span className="inline-flex items-center gap-1 text-muted-foreground">
          <Minus className="h-3.5 w-3.5" />
          {formatted}
        </span>
      );
    }

    const sign = isPositiveGood
      ? (value >= 0 ? "+" : "-")
      : (value >= 0 ? "-" : "+");

    return (
      <span className={`inline-flex items-center gap-1 ${color}`}>
        {isGood ? <GoodIcon className="h-3.5 w-3.5" /> : <BadIcon className="h-3.5 w-3.5" />}
        {sign}{formatted}
      </span>
    );
  };

  if (!activeProject) {
    return (
      <div className="p-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No project selected. Please select a project from the dropdown above.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Optimizations</h1>
          <p className="text-muted-foreground">Discover AI-powered optimizations to improve performance and reduce costs</p>
        </div>
      </div>

      {/* Optimization Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((metric) => (
          <MetricCard
            key={metric.id}
            title={metric.title}
            value={metric.value}
            change={metric.change}
            trendDirection={metric.trendDirection}
            isPositiveChange={metric.isPositiveChange}
            metricType="performance"
            className={loading ? "opacity-50" : undefined}
          />
        ))}
      </div>

      {/* Outperforming Versions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Outperforming Versions</CardTitle>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {(!data || data.outperforming_versions.length === 0) ? (
            <EmptyState
              icon={Rocket}
              title="No optimizations yet"
              description="When optimized versions outperform production, they will appear here."
              actionLabel="Learn About Optimization"
              onAction={() => console.log("Navigate to optimization guide")}
            />
          ) : (
            <TooltipProvider>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Task</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>Score Δ</TableHead>
                    <TableHead>Quality Δ</TableHead>
                    <TableHead>Cost Δ</TableHead>
                    <TableHead>Time Δ</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedOutperformers.map((v) => {
                    const version = v.production_version
                      ? `${v.production_version} → ${v.optimized_version}`
                      : v.optimized_version;
                    const scoreDelta = v.score_delta ?? null;
                    const qualityDelta = v.quality_delta_percent ?? null;
                    const costDelta = v.cost_delta_percent ?? null;
                    const timeDelta = v.time_delta_ms ?? null;
                    return (
                      <TableRow key={`${v.task_id}-${v.optimized_implementation_id}`}>
                        <TableCell className="font-medium">{v.task_name}</TableCell>
                        <TableCell>{version}</TableCell>
                        <TableCell>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="cursor-help">{renderDelta(scoreDelta, "score")}</span>
                            </TooltipTrigger>
                            <TooltipContent>
                              <div className="space-y-1 text-xs">
                                <div>Production: {v.production_score != null ? v.production_score.toFixed(2) : "N/A"}</div>
                                <div>Optimized: {v.optimized_score != null ? v.optimized_score.toFixed(2) : "N/A"}</div>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="cursor-help">{renderDelta(qualityDelta, "qualityPercent")}</span>
                            </TooltipTrigger>
                            <TooltipContent>
                              <div className="space-y-1 text-xs">
                                <div>Production: {v.production_quality != null ? (v.production_quality * 100).toFixed(1) + "%" : "N/A"}</div>
                                <div>Optimized: {v.optimized_quality != null ? (v.optimized_quality * 100).toFixed(1) + "%" : "N/A"}</div>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="cursor-help">{renderDelta(costDelta, "costPercent")}</span>
                            </TooltipTrigger>
                            <TooltipContent>
                              <div className="space-y-1 text-xs">
                                <div>Production: {v.production_cost != null ? `$${v.production_cost.toFixed(6)}` : "N/A"}</div>
                                <div>Optimized: {v.optimized_cost != null ? `$${v.optimized_cost.toFixed(6)}` : "N/A"}</div>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="cursor-help">{renderDelta(timeDelta, "timeMs")}</span>
                            </TooltipTrigger>
                            <TooltipContent>
                              <div className="space-y-1 text-xs">
                                <div>Production: {v.production_time_ms != null ? `${v.production_time_ms.toFixed(1)} ms` : "N/A"}</div>
                                <div>Optimized: {v.optimized_time_ms != null ? `${v.optimized_time_ms.toFixed(1)} ms` : "N/A"}</div>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
                <TableCaption>
                  Showing {sortedOutperformers.length} version(s)
                </TableCaption>
              </Table>
            </TooltipProvider>
          )}
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">How Optimizations Work</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            The optimization feature analyzes your evaluation results to identify potential improvements in:
          </p>
          <ul className="list-disc list-inside space-y-2 ml-4">
            <li>
              <strong>Model Performance:</strong> Finding alternative models that provide better results for your specific use case
            </li>
            <li>
              <strong>Prompt Engineering:</strong> Suggesting prompt modifications to improve accuracy and reduce token usage
            </li>
            <li>
              <strong>Cost Efficiency:</strong> Identifying opportunities to use more cost-effective models without sacrificing quality
            </li>
            <li>
              <strong>Speed Optimization:</strong> Recommending faster models or configurations that meet your latency requirements
            </li>
          </ul>
          <p className="mt-4">
            Create tasks, run evaluations, and check back here to see personalized optimization recommendations.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default Optimizations;
