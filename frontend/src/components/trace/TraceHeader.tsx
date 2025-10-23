import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { TimePeriod } from "@/lib/types/trace";

interface TraceHeaderProps {
  timePeriod: TimePeriod;
  onTimePeriodChange: (period: TimePeriod) => void;
}

export function TraceHeader({ timePeriod, onTimePeriodChange }: TraceHeaderProps) {
  const timePeriods = [
    { value: "5m" as const, label: "Last 5 minutes" },
    { value: "15m" as const, label: "Last 15 minutes" },
    { value: "1h" as const, label: "Last 1 hour" },
    { value: "4h" as const, label: "Last 4 hours" },
  ];

  return (
    <header className="flex h-12 items-center justify-between border-b border-border bg-card px-4 gap-4">
      {/* Left: Search */}
      <div className="flex items-center gap-2 flex-1 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search traces..." className="h-8 bg-card pl-7 text-xs border-border focus:border-primary" />
        </div>
      </div>

      {/* Right: Time Period Selector */}
      <div className="flex items-center gap-2">
        <select
          value={timePeriod}
          onChange={(e) => onTimePeriodChange(e.target.value as TimePeriod)}
          className="h-8 px-2 bg-card text-xs rounded border border-border text-card-foreground cursor-pointer hover:bg-accent hover:text-accent-foreground focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none focus:bg-accent focus:text-accent-foreground transition-colors"
        >
          {timePeriods.map((period) => (
            <option key={period.value} value={period.value}>
              {period.label}
            </option>
          ))}
        </select>
      </div>
    </header>
  );
}
