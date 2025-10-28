import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { 
  LayoutDashboard, 
  CheckSquare, 
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  Rocket
} from "lucide-react";
import { useLocation, Link } from "react-router-dom";

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
  className?: string;
  isMobile?: boolean;
  onMobileMenuClose?: () => void;
}

const navigationItems = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "Traces",
    href: "/traces",
    icon: Activity,
  },
  {
    title: "Tasks",
    href: "/tasks",
    icon: CheckSquare,
  },
  {
    title: "Evaluations",
    href: "/evaluations",
    icon: BarChart3,
  },
  {
    title: "Optimizations",
    href: "/optimizations",
    icon: Rocket,
  },
];

const secondaryItems = [
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
  },
];

const Sidebar = ({ isCollapsed, onToggle, className, isMobile = false, onMobileMenuClose }: SidebarProps) => {
  const location = useLocation();

  const handleNavigationClick = () => {
    // Close mobile menu when navigation item is clicked in mobile view
    if (isMobile && onMobileMenuClose) {
      onMobileMenuClose();
    }
  };


  return (
    <aside
        className={cn(
          "bg-card border-r border-border flex flex-col transition-all duration-300 ease-in-out",
          isCollapsed ? "w-16" : "w-64",
          className
        )}
      >
      {/* Sidebar Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className={cn(
            "flex items-center gap-2 transition-opacity duration-300",
            isCollapsed ? "opacity-0 w-0 overflow-hidden" : "opacity-100",
            isMobile ? "opacity-0 w-0 overflow-hidden" : ""
          )}>
            <div className="w-6 h-6 bg-gradient-to-br from-primary to-primary-hover rounded-md flex items-center justify-center">
              <div className="w-3 h-3 bg-primary-foreground rounded-sm" />
            </div>
            <span className="font-medium text-foreground whitespace-nowrap">R4U</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggle}
            className={cn(
              "hidden lg:flex h-10 w-10 flex-shrink-0",
              isCollapsed ? "-ml-1" : "",
              isMobile ? "hidden" : ""
            )}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>


      {/* Navigation */}
      <nav className="flex-1 p-2 flex flex-col">
        {/* Primary Navigation */}
        <ul className="space-y-1">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            
            return (
              <li key={item.href}>
                {isCollapsed ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link to={item.href} onClick={handleNavigationClick}>
                        <Button
                          variant={isActive ? "secondary" : "ghost"}
                          className={cn(
                            "w-full justify-center h-10 px-0",
                            isActive && "bg-primary/10 text-primary border-primary/20"
                          )}
                        >
                          <Icon className="h-4 w-4 shrink-0" />
                        </Button>
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <p>{item.title}</p>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <Link to={item.href} onClick={handleNavigationClick}>
                    <Button
                      variant={isActive ? "secondary" : "ghost"}
                      className={cn(
                        "w-full justify-start gap-3 h-10 px-3",
                        isActive && "bg-primary/10 text-primary border-primary/20"
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="text-sm font-medium">{item.title}</span>
                    </Button>
                  </Link>
                )}
              </li>
            );
          })}
        </ul>

        {/* Separator */}
        <div className="my-4">
          <div className="h-px bg-border" />
        </div>

        {/* Secondary Navigation */}
        <ul className="space-y-1">
          {secondaryItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;

            return (
              <li key={item.href}>
                {isCollapsed ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link to={item.href} onClick={handleNavigationClick}>
                        <Button
                          variant={isActive ? "secondary" : "ghost"}
                          className={cn(
                            "w-full justify-center h-10 px-0",
                            isActive && "bg-primary/10 text-primary border-primary/20"
                          )}
                        >
                          <Icon className="h-4 w-4 shrink-0" />
                        </Button>
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <p>{item.title}</p>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <Link to={item.href} onClick={handleNavigationClick}>
                    <Button
                      variant={isActive ? "secondary" : "ghost"}
                      className={cn(
                        "w-full justify-start gap-3 h-10 px-3",
                        isActive && "bg-primary/10 text-primary border-primary/20"
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="text-sm font-medium">{item.title}</span>
                    </Button>
                  </Link>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

    </aside>
  );
};

export default Sidebar;