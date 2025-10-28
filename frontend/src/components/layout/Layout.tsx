import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Header from "./Header";
import Sidebar from "./Sidebar";
import { useProject } from "@/contexts/ProjectContext";
import { usePage } from "@/contexts/PageContext";
import NoProjectsModal from "../project/NoProjectsModal";
import LoadingOverlay from "../project/LoadingOverlay";
import { cn } from "@/lib/utils";

interface Breadcrumb {
  label: string;
  to?: string;
  isCurrentPage?: boolean;
}

const Layout = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [noProjectsModalOpen, setNoProjectsModalOpen] = useState(false);
  const location = useLocation();
  const { hasNoProjects, isLoading } = useProject();
  const { pageTitle } = usePage();

  const getBreadcrumbs = () => {
    const pathname = location.pathname;
    const search = new URLSearchParams(location.search);

    // Handle metric details route
    if (pathname.startsWith('/metrics/')) {
      const metricId = pathname.split('/').pop();
      const metricNames: Record<string, string> = {
        "total-cost": "Total Cost",
        "average-request-cost": "Average Request Cost",
        "requests-cost": "Usage Cost",
        "optimization-cost": "Optimization Cost",
        "total-executions": "Total Executions",
        "total-requests": "Total Requests",
        "data-transferred": "Data Transferred",
        "current-storage-used": "Current Storage Used",
        "p5-accuracy": "P5 Accuracy",
        "p95-request-cost": "P95 Request Cost",
        "p5-efficiency-score": "P5 Efficiency Score",
        "optimization-score": "Optimization Score",
        "resource-efficiency": "Resource Efficiency",
        "auto-optimizations": "Auto Optimizations",
        "optimization-savings": "Optimization Savings"
      };
      const metricName = metricNames[metricId || ""] || "Metric Details";
      return [
        { label: 'Dashboard', to: '/' },
        { label: metricName, isCurrentPage: true }
      ];
    }


    // Handle nested routes first
    if (pathname === '/tasks/new') {
      return [
        { label: 'Tasks', to: '/tasks' },
        { label: 'Create Task', isCurrentPage: true }
      ];
    }

    // Handle task detail page
    if (pathname.startsWith('/tasks/') && pathname !== '/tasks/new') {
      return [
        { label: 'Tasks', to: '/tasks' },
        { label: pageTitle || 'Task Details', isCurrentPage: true }
      ];
    }

    // Handle evaluation detail page with optional task_id back-link
    if (pathname.match(/^\/evaluations\/[^/]+$/)) {
      const taskId = search.get('task_id');
      const crumbs = [] as Array<{ label: string; to?: string; isCurrentPage?: boolean }>;
      if (taskId) {
        crumbs.push({ label: 'Tasks', to: '/tasks' });
        crumbs.push({ label: 'Task', to: `/tasks/${taskId}?tab=evaluations` });
      }
      crumbs.push({ label: 'Evaluation', isCurrentPage: true });
      return crumbs;
    }

    // Handle main routes
    switch (pathname) {
      case '/':
        return [{ label: 'Dashboard', isCurrentPage: true }];
      case '/traces':
        return [{ label: 'Traces', isCurrentPage: true }];
      case '/tasks':
        return [{ label: 'Tasks', isCurrentPage: true }];
      case '/evaluations':
        return [{ label: 'Evaluations', isCurrentPage: true }];
      case '/optimizations':
        return [{ label: 'Optimizations', isCurrentPage: true }];
      case '/settings':
        return [{ label: 'Settings', isCurrentPage: true }];
      default: {
        // Fallback for any unmatched routes
        const pathSegments = pathname.split('/').filter(Boolean);
        if (pathSegments.length > 0) {
          const lastSegment = pathSegments[pathSegments.length - 1];
          const capitalizedLabel = lastSegment.charAt(0).toUpperCase() + lastSegment.slice(1);
          return [{ label: capitalizedLabel, isCurrentPage: true }];
        }
        return [{ label: 'Dashboard', isCurrentPage: true }];
      }
    }
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen);
  };



  // Show no projects modal only after API call completes and there are no projects
  useEffect(() => {
    if (hasNoProjects && !isLoading) {
      setNoProjectsModalOpen(true);
    } else {
      setNoProjectsModalOpen(false);
    }
  }, [hasNoProjects, isLoading]);

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={toggleMobileMenu}
        />
      )}

      {/* Sidebar */}
      <Sidebar
        isCollapsed={sidebarCollapsed}
        onToggle={toggleSidebar}
        isMobile={mobileMenuOpen}
        onMobileMenuClose={() => setMobileMenuOpen(false)}
        className={cn(
          "fixed left-0 top-0 z-50 h-full",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      />

      {/* Main content */}
      <div className={cn(
        "min-h-screen flex flex-col transition-all duration-300 ease-in-out",
        sidebarCollapsed ? "lg:ml-16" : "lg:ml-64"
      )}>
        <Header
          onToggleSidebar={toggleMobileMenu}
          mobileMenuOpen={mobileMenuOpen}
          breadcrumbs={getBreadcrumbs()}
        />
        
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>


      {/* Loading Overlay */}
      <LoadingOverlay open={isLoading} />

      {/* No Projects Modal */}
      <NoProjectsModal
        open={noProjectsModalOpen}
        onOpenChange={setNoProjectsModalOpen}
      />
    </div>
  );
};

export default Layout;