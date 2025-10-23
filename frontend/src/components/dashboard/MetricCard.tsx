import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  trend?: "up" | "down" | "stable";
  trendDirection?: "up" | "down" | "stable"; // Actual direction of change
  isPositiveChange?: boolean; // Whether the change is perceived as positive
  unit?: string;
  description?: string;
  className?: string;
  onClick?: () => void;
  metricType?: "performance" | "financial" | "usage" | "optimization";
}

const MetricCard = ({
  title,
  value,
  change,
  trend,
  trendDirection,
  isPositiveChange,
  unit,
  description,
  className,
  onClick,
  metricType
}: MetricCardProps) => {
  // Use trendDirection for icon, fallback to trend if not provided
  const direction = trendDirection || trend;
  const TrendIcon = direction === "up" ? TrendingUp : direction === "down" ? TrendingDown : Minus;
  
  // Color logic: Only performance metrics show positive/negative colors
  // For other metrics, use neutral colors regardless of change perception
  const trendColor = metricType === "performance" && isPositiveChange !== undefined
    ? (isPositiveChange ? "text-success" : "text-destructive")
    : "text-muted-foreground";

  return (
    <Card
      className={cn("hover:shadow-md transition-shadow", onClick && "cursor-pointer hover:shadow-lg", className)}
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {direction && (
          <TrendIcon className={cn("h-4 w-4", trendColor)} />
        )}
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold text-foreground">
            {value}
          </div>
          {unit && (
            <span className="text-sm text-muted-foreground">{unit}</span>
          )}
        </div>
        {change !== undefined && (
          <p className={cn("text-xs mt-1", trendColor)}>
            {change > 0 ? "+" : ""}{change.toFixed(2)}% from last period
          </p>
        )}
        {description && (
          <p className="text-xs text-muted-foreground mt-1">
            {description}
          </p>
        )}
      </CardContent>
    </Card>
  );
};

export default MetricCard;