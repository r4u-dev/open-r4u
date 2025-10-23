import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import MetricCard from "@/components/dashboard/MetricCard";

const Dashboard = () => {
  const [timePeriod, setTimePeriod] = useState("7d");
  const navigate = useNavigate();
  
  // Check if user is new (no tasks exist)  
  const isNewUser = false; // This would come from your data/API

  // Helper function to get duration text
  const getDurationText = (period: string) => {
    switch (period) {
      case "7d": return "last 7 days";
      case "14d": return "last 14 days";
      case "30d": return "last 30 days";
      default: return "last 7 days";
    }
  };

  // Helper function to get mock data based on duration
  const getMockData = (baseValue: number, change: number, period: string) => {
    const multiplier = period === "7d" ? 1 : period === "14d" ? 1.8 : 3.5;
    return {
      value: Math.round(baseValue * multiplier),
      change: change + (period === "14d" ? 2 : period === "30d" ? 5 : 0)
    };
  };

  // Handle metric card click
  const handleMetricClick = (metricId: string) => {
    navigate(`/metrics/${metricId}?period=${timePeriod}`);
  };


  // Financial Metrics
  const financialMetrics = [
    {
      id: "total-cost",
      title: "Total Cost",
      baseValue: 847,
      unit: "$",
      baseChange: -12.4,
      trendDirection: "down" as const, // Value decreased
      isPositiveChange: true, // Cost reduction is positive
      type: "total" as const,
      description: `Total spend in the ${getDurationText(timePeriod)}`
    },
    {
      id: "requests-cost",
      title: "Usage Cost",
      baseValue: 523,
      unit: "$",
      baseChange: -8.7,
      trendDirection: "down" as const, // Value decreased
      isPositiveChange: true, // Cost reduction is positive
      type: "total" as const,
      description: `Total cost for API requests in the ${getDurationText(timePeriod)}`
    },
    {
      id: "optimization-cost",
      title: "Optimization Cost",
      baseValue: 324,
      unit: "$",
      baseChange: 15.3,
      trendDirection: "up" as const, // Value increased
      isPositiveChange: false, // Cost increase is negative
      type: "total" as const,
      description: `Total cost for optimization processes in the ${getDurationText(timePeriod)}`
    },
    {
      id: "average-request-cost",
      title: "Average Request Cost",
      baseValue: 0.124,
      unit: "$",
      baseChange: -5.2,
      trendDirection: "down" as const, // Value decreased
      isPositiveChange: true, // Cost reduction is positive
      type: "average" as const,
      description: "Average cost per API request"
    }
  ];

  // Usage Metrics
  const usageMetrics = [
    {
      id: "total-requests",
      title: "Total Requests",
      baseValue: 6847,
      baseChange: 12.3,
      trendDirection: "up" as const, // Value increased
      isPositiveChange: undefined, // Neutral - usage increase is neither good nor bad
      type: "total" as const,
      description: `Total API requests in the ${getDurationText(timePeriod)}`
    },
    {
      id: "total-executions",
      title: "Total Executions",
      baseValue: 2195,
      baseChange: 15.2,
      trendDirection: "up" as const, // Value increased
      isPositiveChange: undefined, // Neutral - execution increase is neither good nor bad
      type: "total" as const,
      description: `Total task executions in the ${getDurationText(timePeriod)}`
    },
    {
      id: "data-transferred",
      title: "Data Transferred",
      baseValue: 1.2,
      unit: "TB",
      baseChange: 8.5,
      trendDirection: "up" as const, // Value increased
      isPositiveChange: undefined, // Neutral - data transfer increase is neither good nor bad
      type: "total" as const,
      description: `Total data transferred in the ${getDurationText(timePeriod)}`
    },
    {
      id: "current-storage-used",
      title: "Current Storage Used",
      baseValue: 2.4,
      unit: "TB",
      baseChange: 0,
      trendDirection: "stable" as const, // Value unchanged
      isPositiveChange: undefined, // Neutral - no change
      type: "total" as const,
      description: "Current storage usage"
    }
  ];

  // Performance Metrics
  const performanceMetrics = [
    {
      id: "p5-accuracy",
      title: "P5 Accuracy",
      baseValue: 87.2,
      unit: "%",
      baseChange: 3.1,
      trendDirection: "up" as const, // Value increased
      isPositiveChange: true, // Higher accuracy is positive
      type: "percentile" as const,
      description: "95% of tasks achieve better than this accuracy"
    },
    {
      id: "p95-request-cost",
      title: "P95 Request Cost",
      baseValue: 0.089,
      baseChange: -8.2,
      trendDirection: "down" as const, // Value decreased
      isPositiveChange: true, // Cost reduction is positive
      type: "percentile" as const,
      description: "95% of requests cost less than this amount"
    },
    {
      id: "p5-efficiency-score",
      title: "P5 Efficiency Score",
      baseValue: 72.8,
      baseChange: -2.4,
      trendDirection: "down" as const, // Value decreased
      isPositiveChange: false, // Lower efficiency is negative
      type: "percentile" as const,
      description: "95% of tasks achieve better than this efficiency"
    }
  ];

  // Optimization Metrics
  const optimizationMetrics = [
    {
      id: "optimization-score",
      title: "Optimization Score",
      baseValue: 78.5,
      unit: "%",
      baseChange: 5.2,
      trendDirection: "up" as const, // Value increased
      isPositiveChange: undefined, // Neutral - optimization metrics are complex to interpret
      type: "percentage" as const,
      description: "Overall system optimization effectiveness"
    },
    {
      id: "resource-efficiency",
      title: "Resource Efficiency",
      baseValue: 85.3,
      unit: "%",
      baseChange: 3.1,
      trendDirection: "up" as const, // Value increased
      isPositiveChange: undefined, // Neutral - efficiency metrics are complex to interpret
      type: "percentage" as const,
      description: "Efficiency of resource utilization"
    },
    {
      id: "auto-optimizations",
      title: "Auto Optimizations",
      baseValue: 42,
      baseChange: 12.5,
      trendDirection: "up" as const, // Value increased
      isPositiveChange: undefined, // Neutral - more optimizations could be good or bad
      type: "total" as const,
      description: `Automatic optimizations applied in the ${getDurationText(timePeriod)}`
    },
    {
      id: "optimization-savings",
      title: "Optimization Savings",
      baseValue: 287,
      unit: "$",
      baseChange: 18.7,
      trendDirection: "up" as const, // Value increased
      isPositiveChange: undefined, // Neutral - savings increase is complex to interpret
      type: "total" as const,
      description: `Total savings from optimizations in the ${getDurationText(timePeriod)}`
    }
  ];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">AI System Dashboard</h1>
          <p className="text-muted-foreground">Monitor and optimize your AI agentic systems</p>
        </div>
        <div className="flex items-center gap-3">
          {!isNewUser && (
            <>
              <Select value={timePeriod} onValueChange={setTimePeriod}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                  <SelectItem value="14d">Last 14 days</SelectItem>
                  <SelectItem value="30d">Last 30 days</SelectItem>
                </SelectContent>
              </Select>
              <Button>Export Report</Button>
            </>
          )}
        </div>
      </div>


      {/* Financial Overview Section */}
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-primary rounded-full animate-pulse" />
          <h2 className="text-xl font-semibold text-foreground">Financial Overview</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {financialMetrics.map((metric) => {
            const dynamicData = getMockData(metric.baseValue, metric.baseChange, timePeriod);
            const formattedValue = metric.unit === "$"
              ? `$${dynamicData.value.toLocaleString()}`
              : metric.type === "average"
                ? `$${dynamicData.value.toFixed(3)}`
                : `$${dynamicData.value.toLocaleString()}`;
            return (
              <MetricCard
                key={metric.id}
                title={metric.title}
                value={isNewUser ? "--" : formattedValue}
                unit={metric.unit === "$" ? undefined : metric.unit}
                change={isNewUser ? 0 : dynamicData.change}
                trendDirection={isNewUser ? "stable" : metric.trendDirection}
                isPositiveChange={isNewUser ? undefined : metric.isPositiveChange}
                description={metric.description}
                onClick={() => !isNewUser && handleMetricClick(metric.id)}
                className={`transition-all duration-200 ${
                  isNewUser ? "opacity-50" : ""
                }`}
                metricType="financial"
              />
            );
          })}
        </div>
      </div>

      {/* Usage Overview Section */}
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
          <h2 className="text-xl font-semibold text-foreground">Usage Overview</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {usageMetrics.map((metric) => {
            const dynamicData = getMockData(metric.baseValue, metric.baseChange, timePeriod);
            const formattedValue = metric.unit === "TB"
              ? `${dynamicData.value.toFixed(1)}`
              : dynamicData.value.toLocaleString();
            return (
              <MetricCard
                key={metric.id}
                title={metric.title}
                value={isNewUser ? "--" : formattedValue}
                unit={metric.unit === "$" ? undefined : metric.unit}
                change={isNewUser ? 0 : dynamicData.change}
                trendDirection={isNewUser ? "stable" : metric.trendDirection}
                isPositiveChange={isNewUser ? undefined : metric.isPositiveChange}
                description={metric.description}
                onClick={() => !isNewUser && handleMetricClick(metric.id)}
                className={`transition-all duration-200 ${
                  isNewUser ? "opacity-50" : ""
                }`}
                metricType="usage"
              />
            );
          })}
        </div>
      </div>

      {/* Performance Overview Section */}
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-warning rounded-full animate-pulse" />
          <h2 className="text-xl font-semibold text-foreground">Performance Overview</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {performanceMetrics.map((metric) => {
            const dynamicData = getMockData(metric.baseValue, metric.baseChange, timePeriod);
            const formattedValue = metric.unit === "%"
              ? `${dynamicData.value.toFixed(2)}`
              : metric.baseValue < 1
                ? `$${dynamicData.value.toFixed(3)}`
                : dynamicData.value.toFixed(1);
            return (
              <MetricCard
                key={metric.id}
                title={metric.title}
                value={isNewUser ? "--" : formattedValue}
                unit={metric.unit === "$" ? undefined : metric.unit}
                change={isNewUser ? 0 : dynamicData.change}
                trendDirection={isNewUser ? "stable" : metric.trendDirection}
                isPositiveChange={isNewUser ? undefined : metric.isPositiveChange}
                description={metric.description}
                onClick={() => !isNewUser && handleMetricClick(metric.id)}
                className={`transition-all duration-200 ${
                  isNewUser ? "opacity-50" : ""
                }`}
                metricType="performance"
              />
            );
          })}
        </div>
      </div>


      {/* Optimization Overview Section */}
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
          <h2 className="text-xl font-semibold text-foreground">Optimization Overview</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {optimizationMetrics.map((metric) => {
            const dynamicData = getMockData(metric.baseValue, metric.baseChange, timePeriod);
            const formattedValue = metric.unit === "%"
              ? `${dynamicData.value.toFixed(2)}`
              : metric.unit === "$"
                ? `$${dynamicData.value.toLocaleString()}`
                : dynamicData.value.toLocaleString();

            return (
              <MetricCard
                key={metric.id}
                title={metric.title}
                value={isNewUser ? "--" : formattedValue}
                unit={metric.unit === "$" ? undefined : metric.unit}
                change={isNewUser ? 0 : dynamicData.change}
                trendDirection={isNewUser ? "stable" : metric.trendDirection}
                isPositiveChange={isNewUser ? undefined : metric.isPositiveChange}
                description={metric.description}
                onClick={() => !isNewUser && handleMetricClick(metric.id)}
                className={`transition-all duration-200 ${
                  isNewUser ? "opacity-50" : ""
                }`}
                metricType="optimization"
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;