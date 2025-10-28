import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { RefreshCw, Filter } from "lucide-react";

interface EvaluationHeaderProps {
    onRefresh: () => void;
    isRefreshing?: boolean;
}

export function EvaluationHeader({ onRefresh, isRefreshing }: EvaluationHeaderProps) {
    return (
        <header className="flex h-12 items-center justify-between border-b border-border bg-card px-4 gap-4">
            {/* Left: Search */}
            <div className="flex items-center gap-2 flex-1 max-w-md">
                <div className="relative flex-1">
                    <Search className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
                    <Input 
                        placeholder="Search evaluations..." 
                        className="h-8 bg-card pl-7 text-xs border-border focus:border-primary" 
                    />
                </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-8"
                    onClick={onRefresh}
                    disabled={isRefreshing}
                >
                    <RefreshCw className={`h-3 w-3 mr-1 ${isRefreshing ? 'animate-spin' : ''}`} />
                    Refresh
                </Button>
                <Button variant="ghost" size="sm" className="h-8">
                    <Filter className="h-3 w-3 mr-1" />
                    Filter
                </Button>
            </div>
        </header>
    );
}

