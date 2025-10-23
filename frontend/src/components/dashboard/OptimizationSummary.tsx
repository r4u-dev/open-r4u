import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TrendingUp, DollarSign, Zap, Target, ArrowRight, Rocket } from "lucide-react";
import MetricCard from "./MetricCard";
import EmptyState from "./EmptyState";

interface OptimizationMetric {
  title: string;
  value: string;
  change: number;
  trend: "up" | "down" | "stable";
  icon: React.ComponentType<{ className?: string }>;
}

const optimizationMetrics: OptimizationMetric[] = [
  {
    title: "Cost Savings",
    value: "$12.4K",
    change: 23.1,
    trend: "up",
    icon: DollarSign
  },
  {
    title: "Performance Gain",
    value: "18.5%",
    change: 12.3,
    trend: "up",
    icon: Zap
  },
  {
    title: "ROI",
    value: "340%",
    change: 45.2,
    trend: "up",
    icon: TrendingUp
  },
  {
    title: "Accuracy Boost",
    value: "+7.2%",
    change: 15.8,
    trend: "up",
    icon: Target
  }
];

interface OutperformingVersion {
  id: string;
  taskName: string;
  currentAccuracy: number;
  newAccuracy: number;
  costReduction: number;
  speedImprovement: number;
  readyToDeploy: boolean;
}

// For demo - set to empty array to show empty state for new users
const mockOutperformingVersions: OutperformingVersion[] = [];

const OptimizationSummary = () => {
  const hasOptimizations = mockOutperformingVersions.length > 0;

  if (!hasOptimizations) {
    return (
      <div className="space-y-6">
        {/* Empty Optimization Metrics */}
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {optimizationMetrics.map((metric) => (
              <MetricCard
                key={metric.title}
                title={metric.title}
                value="--"
                change={0}
                trend="stable"
                className="opacity-50"
              />
            ))}
          </div>
        </div>

        {/* Empty State for Outperforming Versions */}
        <EmptyState
          icon={Rocket}
          title="Start Optimizing Your AI"
          description="Once you have tasks running, our AI will automatically find optimization opportunities to improve performance and reduce costs."
          actionLabel="Learn About Optimization"
          onAction={() => console.log("Navigate to optimization guide")}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Optimization Metrics */}
      <div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {optimizationMetrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <MetricCard
                key={metric.title}
                title={metric.title}
                value={metric.value}
                change={metric.change}
                trend={metric.trend}
                className="hover:shadow-lg transition-shadow"
              />
            );
          })}
        </div>
      </div>

      {/* Outperforming Versions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-success" />
            Outperforming Task Versions
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {mockOutperformingVersions.map((version) => (
              <div key={version.id} className="p-6 hover:bg-muted/50 transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium text-foreground">{version.taskName}</h3>
                    {version.readyToDeploy && (
                      <Badge className="bg-success-muted text-success border-success/20">
                        Ready to Deploy
                      </Badge>
                    )}
                  </div>
                  <Button 
                    size="sm" 
                    disabled={!version.readyToDeploy}
                    className="gap-2"
                  >
                    Deploy
                    <ArrowRight className="h-3 w-3" />
                  </Button>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Accuracy</span>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">{version.currentAccuracy}%</span>
                      <ArrowRight className="h-3 w-3 text-muted-foreground" />
                      <span className="font-medium text-success">{version.newAccuracy}%</span>
                    </div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Cost Reduction</span>
                    <p className="font-medium text-success">-{version.costReduction}%</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Speed Boost</span>
                    <p className="font-medium text-success">+{version.speedImprovement}%</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Status</span>
                    <p className={`font-medium ${version.readyToDeploy ? "text-success" : "text-warning"}`}>
                      {version.readyToDeploy ? "Ready" : "Testing"}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default OptimizationSummary;