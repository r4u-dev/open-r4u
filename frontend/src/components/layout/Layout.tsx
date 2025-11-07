import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import { useProject } from "@/contexts/ProjectContext";
import NoProjectsModal from "../project/NoProjectsModal";
import LoadingOverlay from "../project/LoadingOverlay";
import { Button } from "@/components/ui/button";
import { Menu } from "lucide-react";
import { cn } from "@/lib/utils";

const Layout = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [noProjectsModalOpen, setNoProjectsModalOpen] = useState(false);
  const { hasNoProjects, isLoading } = useProject();

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
        {/* Floating mobile menu button */}
        {!mobileMenuOpen && (
          <Button
            variant="default"
            size="icon"
            onClick={toggleMobileMenu}
            className="fixed top-4 left-4 z-30 lg:hidden h-10 w-10"
          >
            <Menu className="h-5 w-5" />
          </Button>
        )}
        
        <main className="flex-1 p-6 pt-16 lg:pt-6">
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