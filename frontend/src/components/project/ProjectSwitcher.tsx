import { Button } from "@/components/ui/button";
import { Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProjectSwitcherProps {
  onCreateProject: () => void;
  isCollapsed?: boolean;
}

const ProjectSwitcher = ({
  onCreateProject,
  isCollapsed = false,
}: ProjectSwitcherProps) => {
  return (
    <Button
      variant="outline"
      className={cn(
        "px-3 bg-card/50",
        isCollapsed
          ? "justify-center w-full h-10 px-0"
          : "justify-start w-full",
      )}
      disabled
    >
      <div className="flex items-center gap-2">
        <Building2 className="h-4 w-4 text-primary" />
        {!isCollapsed && (
          <span className="font-medium truncate">Default</span>
        )}
      </div>
    </Button>
  );
};

export default ProjectSwitcher;
