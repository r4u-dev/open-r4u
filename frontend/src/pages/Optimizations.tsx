import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import EmptyState from "@/components/dashboard/EmptyState";
import MetricCard from "@/components/dashboard/MetricCard";
import { Rocket, TrendingUp, DollarSign, Zap, Target } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useProject } from "@/contexts/ProjectContext";

const optimizationMetrics = [
  {
    title: "Cost Savings",
    value: "--",
    change: 0,
    trend: "stable" as const,
    icon: DollarSign
  },
  {
    title: "Performance Gain",
    value: "--",
    change: 0,
    trend: "stable" as const,
    icon: Zap
  },
  {
    title: "ROI",
    value: "--",
    change: 0,
    trend: "stable" as const,
    icon: TrendingUp
  },
  {
    title: "Accuracy Boost",
    value: "--",
    change: 0,
    trend: "stable" as const,
    icon: Target
  }
];

const Optimizations = () => {
  const { activeProject } = useProject();
  const navigate = useNavigate();

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

      {/* Optimization Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {optimizationMetrics.map((metric) => (
          <MetricCard
            key={metric.title}
            title={metric.title}
            value={metric.value}
            change={metric.change}
            trend={metric.trend}
            className="opacity-50"
          />
        ))}
      </div>

      {/* Empty State */}
      <Card>
        <CardContent className="pt-6">
          <EmptyState
            icon={Rocket}
            title="Start Optimizing Your AI"
            description="Once you have tasks running with evaluations, our AI will automatically find optimization opportunities to improve performance and reduce costs."
            actionLabel="Learn About Optimization"
            onAction={() => console.log("Navigate to optimization guide")}
          />
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
