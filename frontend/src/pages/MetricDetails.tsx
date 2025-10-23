import { useParams, useSearchParams } from "react-router-dom";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Mock data for daily chart
const generateDailyData = (metricName: string, period: string = "7d") => {
  const days = period === "7d" ? 7 : period === "14d" ? 14 : 30;
  const data = [];
  
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    
    let value: number;
    let change: number;
    
    // Generate realistic data based on metric type
    switch (metricName) {
      case "total-cost":
        value = 100 + Math.random() * 50; // $100-150
        change = (Math.random() - 0.5) * 20; // ±10%
        break;
      case "average-request-cost":
        value = 0.1 + Math.random() * 0.05; // $0.1-0.15
        change = (Math.random() - 0.5) * 10; // ±5%
        break;
      case "requests-cost":
        value = 450 + Math.random() * 200; // $450-650
        change = (Math.random() - 0.5) * 15; // ±7.5%
        break;
      case "optimization-cost":
        value = 280 + Math.random() * 150; // $280-430
        change = (Math.random() - 0.3) * 20; // mostly positive growth
        break;
      case "total-executions":
        value = 200 + Math.random() * 100; // 200-300
        change = (Math.random() - 0.5) * 20; // ±10%
        break;
      case "total-requests":
        value = 800 + Math.random() * 400; // 800-1200
        change = (Math.random() - 0.5) * 15; // ±7.5%
        break;
      case "data-transferred":
        value = 0.1 + Math.random() * 0.2; // 0.1-0.3 TB
        change = (Math.random() - 0.5) * 25; // ±12.5%
        break;
      case "p5-accuracy":
        value = 85 + Math.random() * 10; // 85-95%
        change = (Math.random() - 0.5) * 5; // ±2.5%
        break;
      case "p95-request-cost":
        value = 0.08 + Math.random() * 0.03; // $0.08-0.11
        change = (Math.random() - 0.5) * 15; // ±7.5%
        break;
      case "p5-efficiency-score":
        value = 70 + Math.random() * 15; // 70-85
        change = (Math.random() - 0.5) * 8; // ±4%
        break;
      case "current-storage-used":
        value = 2.0 + Math.random() * 0.8; // 2.0-2.8 TB
        change = (Math.random() - 0.3) * 10; // mostly positive growth
        break;
      case "optimization-score":
        value = 75 + Math.random() * 15; // 75-90%
        change = (Math.random() - 0.2) * 8; // mostly positive
        break;
      case "resource-efficiency":
        value = 80 + Math.random() * 15; // 80-95%
        change = (Math.random() - 0.3) * 6; // mostly positive
        break;
      case "auto-optimizations":
        value = 35 + Math.random() * 20; // 35-55
        change = (Math.random() - 0.1) * 15; // mostly positive
        break;
      case "optimization-savings":
        value = 250 + Math.random() * 100; // $250-350
        change = (Math.random() - 0.2) * 20; // mostly positive
        break;
      default:
        value = 100;
        change = 0;
    }
    
    data.push({
      date: date.toISOString().split('T')[0],
      displayDate: date.toLocaleDateString('en-US', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
      }),
      value: Number(value.toFixed(2)),
      change: Number(change.toFixed(1))
    });
  }
  
  return data;
};

const MetricDetails = () => {
  const { metricId } = useParams<{ metricId: string }>();
  const [searchParams] = useSearchParams();
  const period = searchParams.get("period") || "7d";
  
  // Helper function to get duration text
  const getDurationText = (period: string) => {
    switch (period) {
      case "7d": return "last 7 days";
      case "14d": return "last 14 days";
      case "30d": return "last 30 days";
      default: return "last 7 days";
    }
  };
  
  // Map metric IDs to display names
  const metricNames: Record<string, { title: string; unit: string; description: string }> = {
    "total-cost": { title: "Total Cost", unit: "$", description: `Total spend in the ${getDurationText(period)}` },
    "average-request-cost": { title: "Average Request Cost", unit: "$", description: "Average cost per API request" },
    "requests-cost": { title: "Usage Cost", unit: "$", description: `Total cost for API requests in the ${getDurationText(period)}` },
    "optimization-cost": { title: "Optimization Cost", unit: "$", description: `Total cost for optimization processes in the ${getDurationText(period)}` },
    "total-executions": { title: "Total Executions", unit: "", description: `Total task executions in the ${getDurationText(period)}` },
    "total-requests": { title: "Total Requests", unit: "", description: `Total API requests in the ${getDurationText(period)}` },
    "data-transferred": { title: "Data Transferred", unit: "TB", description: `Total data transferred in the ${getDurationText(period)}` },
    "current-storage-used": { title: "Current Storage Used", unit: "TB", description: "Current storage usage" },
    "p5-accuracy": { title: "P5 Accuracy", unit: "%", description: "95% of tasks achieve better than this accuracy" },
    "p95-request-cost": { title: "P95 Request Cost", unit: "$", description: "95% of requests cost less than this amount" },
    "p5-efficiency-score": { title: "P5 Efficiency Score", unit: "", description: "95% of tasks achieve better than this efficiency" },
    "optimization-score": { title: "Optimization Score", unit: "%", description: "Overall system optimization effectiveness" },
    "resource-efficiency": { title: "Resource Efficiency", unit: "%", description: "Efficiency of resource utilization" },
    "auto-optimizations": { title: "Auto Optimizations", unit: "", description: `Automatic optimizations applied in the ${getDurationText(period)}` },
    "optimization-savings": { title: "Optimization Savings", unit: "$", description: `Total savings from optimizations in the ${getDurationText(period)}` }
  };
  
  const metric = metricNames[metricId || ""];
  const dailyData = generateDailyData(metricId || "", "30d"); // Always show 30 days for chart
  
  if (!metric) {
    return (
      <div className="space-y-6">
        <div className="text-center py-12">
          <h1 className="text-2xl font-bold text-foreground mb-2">Metric Not Found</h1>
          <p className="text-muted-foreground">The requested metric could not be found.</p>
        </div>
      </div>
    );
  }
  
  const currentValue = dailyData[dailyData.length - 1];
  const previousValue = dailyData[dailyData.length - 2];
  const change = previousValue ? ((currentValue.value - previousValue.value) / previousValue.value) * 100 : 0;
  const trend = change > 0 ? "up" : change < 0 ? "down" : "stable";
  
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor = trend === "up" ? "text-success" : trend === "down" ? "text-destructive" : "text-muted-foreground";
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">{metric.title}</h1>
        <p className="text-sm text-muted-foreground">{metric.description}</p>
      </div>
      
      {/* Current Value Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Current Value
            <TrendIcon className={cn("h-4 w-4", trendColor)} />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2">
            <div className="text-3xl font-bold text-foreground">
              {metric.unit === "$"
                ? `$${currentValue.value.toLocaleString()}`
                : metric.unit === "%"
                  ? currentValue.value.toFixed(2)
                  : currentValue.value.toLocaleString()}
            </div>
            {metric.unit && metric.unit !== "$" && (
              <span className="text-lg text-muted-foreground">{metric.unit}</span>
            )}
          </div>
          <p className={cn("text-sm mt-2", trendColor)}>
            {change > 0 ? "+" : ""}{change.toFixed(2)}% from yesterday
          </p>
        </CardContent>
      </Card>
      
      {/* Daily Trend */}
      <Card>
        <CardHeader>
          <CardTitle className="block sm:hidden">Daily Trend (last 7 days)</CardTitle>
          <CardTitle className="hidden sm:block">Daily Trend (last 30 days)</CardTitle>
        </CardHeader>
        <CardContent className="p-2 sm:p-6">
          {/* Mobile Table View */}
          <div className="block sm:hidden">
            <div className="space-y-2">
              {dailyData.slice(-7).reverse().map((day, index) => {
                const globalIndex = dailyData.length - 1 - index;
                const dayChange = globalIndex > 0 ? ((day.value - dailyData[globalIndex - 1].value) / dailyData[globalIndex - 1].value) * 100 : 0;
                const dayTrend = dayChange > 0 ? "up" : dayChange < 0 ? "down" : "stable";
                const dayTrendColor = dayTrend === "up" ? "text-success" : dayTrend === "down" ? "text-destructive" : "text-muted-foreground";
                return (
                  <div key={day.date} className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                    <div className="flex-1">
                      <div className="font-medium text-sm">{day.displayDate}</div>
                      <div className="text-xs text-muted-foreground">{day.date}</div>
                    </div>
                    <div className="text-right flex-1">
                      <div className="font-semibold text-sm">
                        {metric.unit === "$"
                          ? `$${day.value.toLocaleString()}`
                          : metric.unit === "%"
                            ? `${day.value.toFixed(2)}`
                            : day.value.toLocaleString()}
                      </div>
                      {globalIndex > 0 && (
                        <div className={cn("text-xs", dayTrendColor)}>
                          {dayChange > 0 ? "+" : ""}{dayChange.toFixed(2)}%
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Desktop Chart View */}
          <div className="hidden sm:block h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis 
                  dataKey="displayDate" 
                  tick={{ fontSize: 10 }}
                  tickLine={{ stroke: 'hsl(var(--muted-foreground))' }}
                  axisLine={{ stroke: 'hsl(var(--muted-foreground))' }}
                />
                <YAxis 
                  tick={{ fontSize: 10 }}
                  tickLine={{ stroke: 'hsl(var(--muted-foreground))' }}
                  axisLine={{ stroke: 'hsl(var(--muted-foreground))' }}
                  tickFormatter={(value) =>
                    metric.unit === "$"
                      ? `$${value.toLocaleString()}`
                      : metric.unit === "%"
                        ? value.toFixed(2)
                        : value.toLocaleString()
                  }
                />
                <Tooltip 
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      const index = dailyData.findIndex(d => d.displayDate === label);
                      const dayChange = index > 0 ? ((data.value - dailyData[index - 1].value) / dailyData[index - 1].value) * 100 : 0;
                      
                      return (
                        <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
                          <p className="font-medium">{label}</p>
                          <p className="text-sm">
                            <span className="font-semibold">
                              {metric.unit === "$"
                                ? `$${data.value.toLocaleString()}`
                                : metric.unit === "%"
                                  ? data.value.toFixed(2)
                                  : data.value.toLocaleString()}
                            </span>
                          </p>
                          {index > 0 && (
                            <p className={cn("text-xs", 
                              dayChange > 0 ? "text-success" : 
                              dayChange < 0 ? "text-destructive" : 
                              "text-muted-foreground"
                            )}>
                              {dayChange > 0 ? "+" : ""}{dayChange.toFixed(2)}% from previous day
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="hsl(var(--primary))" 
                  strokeWidth={2}
                  dot={{ fill: 'hsl(var(--primary))', strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, stroke: 'hsl(var(--primary))', strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

    </div>
  );
};

export default MetricDetails;
