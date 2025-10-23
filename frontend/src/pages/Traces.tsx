import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { TraceHeader } from "@/components/trace/TraceHeader";
import { TraceTable } from "@/components/trace/TraceTable";
import { TraceDetailPanel } from "@/components/trace/TraceDetailPanel";
import { mockTraces } from "@/lib/mock-data/traces";
import { TimePeriod } from "@/lib/types/trace";

const ITEMS_PER_LOAD = 25;

type SortField = 'status' | 'task' | 'type' | 'model' | 'latency' | 'cost' | 'timestamp';
type SortDirection = 'asc' | 'desc';

const Traces = () => {
  // Minimum widths as percentages
  const MIN_LEFT_WIDTH = 30;
  const MIN_RIGHT_WIDTH = 25;

  const [selectedTrace, setSelectedTrace] = useState<string | null>(null);
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("1h");
  const [loadedItems, setLoadedItems] = useState(ITEMS_PER_LOAD);
  const [isLoading, setIsLoading] = useState(false);
  const [sortField, setSortField] = useState<SortField>('timestamp');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  
  // Load initial splitter position from localStorage
  const getInitialSplitterPosition = () => {
    try {
      const saved = localStorage.getItem('traces-splitter-position');
      if (saved) {
        const position = parseFloat(saved);
        // Ensure the saved position respects minimum constraints
        return Math.max(MIN_LEFT_WIDTH, Math.min(100 - MIN_RIGHT_WIDTH, position));
      }
    } catch (error) {
      console.warn('Failed to load splitter position from localStorage:', error);
    }
    return 50; // Default position
  };

  const [splitterPosition, setSplitterPosition] = useState(getInitialSplitterPosition);
  const [isDragging, setIsDragging] = useState(false);
  const observerRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter and sort traces
  const filteredAndSortedTraces = useMemo(() => {
    const now = new Date();
    const timePeriodMs = {
      "5m": 5 * 60 * 1000,
      "15m": 15 * 60 * 1000,
      "1h": 60 * 60 * 1000,
      "4h": 4 * 60 * 60 * 1000,
    }[timePeriod];

    const cutoffTime = new Date(now.getTime() - timePeriodMs);
    const filtered = mockTraces.filter(trace => new Date(trace.timestamp) >= cutoffTime);

    // Sort the filtered traces
    return filtered.sort((a, b) => {
      let aValue: string | number, bValue: string | number;

      switch (sortField) {
        case 'status':
          aValue = a.status;
          bValue = b.status;
          break;
        case 'task':
          aValue = a.taskVersion || '';
          bValue = b.taskVersion || '';
          break;
        case 'type':
          aValue = a.type;
          bValue = b.type;
          break;
        case 'model':
          aValue = a.model;
          bValue = b.model;
          break;
        case 'latency':
          aValue = a.latency;
          bValue = b.latency;
          break;
        case 'cost':
          aValue = a.cost;
          bValue = b.cost;
          break;
        case 'timestamp':
          aValue = new Date(a.timestamp).getTime();
          bValue = new Date(b.timestamp).getTime();
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [timePeriod, sortField, sortDirection]);

  // Get currently loaded traces
  const displayedTraces = filteredAndSortedTraces.slice(0, loadedItems);

  const selectedTraceData = selectedTrace ? mockTraces.find((t) => t.id === selectedTrace) : null;

  // Auto-select first trace when traces are loaded or filtered
  useEffect(() => {
    if (displayedTraces.length > 0 && !selectedTrace) {
      setSelectedTrace(displayedTraces[0].id);
    }
  }, [displayedTraces, selectedTrace]);

  // Load more traces function
  const loadMoreTraces = useCallback(() => {
    if (isLoading || loadedItems >= filteredAndSortedTraces.length) return;
    
    setIsLoading(true);
    // Simulate loading delay
    setTimeout(() => {
      setLoadedItems(prev => Math.min(prev + ITEMS_PER_LOAD, filteredAndSortedTraces.length));
      setIsLoading(false);
    }, 500);
  }, [isLoading, loadedItems, filteredAndSortedTraces.length]);

  // Handle sorting
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMoreTraces();
        }
      },
      { threshold: 0.1 }
    );

    if (observerRef.current) {
      observer.observe(observerRef.current);
    }

    return () => observer.disconnect();
  }, [loadMoreTraces]);

  // Reset loaded items when time period changes
  const handleTimePeriodChange = (period: TimePeriod) => {
    setTimePeriod(period);
    setLoadedItems(ITEMS_PER_LOAD);
    setSelectedTrace(null);
  };

  // Splitter drag handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  // Save splitter position to localStorage
  const saveSplitterPosition = useCallback((position: number) => {
    try {
      localStorage.setItem('traces-splitter-position', position.toString());
    } catch (error) {
      console.warn('Failed to save splitter position to localStorage:', error);
    }
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;
    
    const containerRect = containerRef.current.getBoundingClientRect();
    const newPosition = ((e.clientX - containerRect.left) / containerRect.width) * 100;
    
    // Apply minimum width constraints
    const constrainedPosition = Math.max(
      MIN_LEFT_WIDTH,
      Math.min(100 - MIN_RIGHT_WIDTH, newPosition)
    );
    
    setSplitterPosition(constrainedPosition);
    saveSplitterPosition(constrainedPosition);
  }, [isDragging, MIN_LEFT_WIDTH, MIN_RIGHT_WIDTH, saveSplitterPosition]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add global mouse event listeners when dragging
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div className="flex h-screen flex-col bg-background font-sans">
      <TraceHeader timePeriod={timePeriod} onTimePeriodChange={handleTimePeriodChange} />
      <div ref={containerRef} className="flex flex-1 overflow-hidden">
        {/* Main Table */}
        <div 
          className="flex flex-col border-r border-border"
          style={{ width: `${splitterPosition}%` }}
        >
          <div className="flex-1 overflow-auto">
            <TraceTable 
              traces={displayedTraces} 
              selectedTraceId={selectedTrace} 
              onSelectTrace={setSelectedTrace}
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={handleSort}
            />
            {/* Loading indicator and intersection observer target */}
            <div ref={observerRef} className="h-8 flex items-center justify-center mt-4">
              {isLoading && (
                <div className="text-xs text-muted-foreground">Loading more traces...</div>
              )}
              {!isLoading && loadedItems >= filteredAndSortedTraces.length && filteredAndSortedTraces.length > 0 && (
                <div className="text-xs text-muted-foreground">No more traces to load</div>
              )}
            </div>
          </div>
        </div>

        {/* Splitter */}
        {selectedTraceData && (
          <div
            className="w-1 bg-border hover:bg-border/80 cursor-col-resize flex items-center justify-center group transition-colors"
            onMouseDown={handleMouseDown}
          >
            <div className="w-0.5 h-8 bg-border group-hover:bg-border/60 rounded-full transition-colors" />
          </div>
        )}

        {/* Detail Panel */}
        {selectedTraceData && (
          <div 
            className="overflow-auto border-l border-border"
            style={{ width: `${100 - splitterPosition}%` }}
          >
            <TraceDetailPanel trace={selectedTraceData} />
          </div>
        )}
      </div>
    </div>
  );
};

export default Traces;
