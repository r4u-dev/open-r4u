import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";

interface NotificationBellProps {
  hasNotifications?: boolean;
  className?: string;
  onClick?: () => void;
}

const NotificationBell = ({ 
  hasNotifications = true, 
  className,
  onClick 
}: NotificationBellProps) => {
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative p-2 rounded-md hover:bg-accent transition-all duration-200 group",
        className
      )}
      aria-label={hasNotifications ? "You have new notifications" : "No new notifications"}
    >
      <Bell 
        className={cn(
          "h-4 w-4 transition-all duration-300",
          hasNotifications && "animate-pulse text-primary",
          "group-hover:scale-110"
        )} 
      />
      
      {hasNotifications && (
        <>
          {/* Animated notification dot */}
          <div className="absolute -top-0.5 -right-0.5 h-3 w-3 bg-primary rounded-full animate-pulse border-2 border-background shadow-sm">
            <span className="sr-only">New notifications</span>
          </div>
          
          {/* Subtle glow effect */}
          <div className="absolute -top-1 -right-1 h-4 w-4 bg-primary/20 rounded-full animate-ping" />
          
          {/* Ring animation */}
          <div className="absolute inset-0 rounded-md">
            <div className={cn(
              "absolute inset-0 rounded-md border-2 border-primary/30",
              "animate-ping",
              "opacity-0 group-hover:opacity-100 transition-opacity duration-300"
            )} />
          </div>
        </>
      )}
    </button>
  );
};

export default NotificationBell;
