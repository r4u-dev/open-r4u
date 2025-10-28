import React from "react";
import { Button } from "@/components/ui/button";
import { Menu } from "lucide-react";
import { cn } from "@/lib/utils";

interface HeaderProps {
  onToggleSidebar: () => void;
  mobileMenuOpen?: boolean;
  className?: string;
}

const Header = ({ onToggleSidebar, mobileMenuOpen = false, className }: HeaderProps) => {
  return (
    <header className={cn("h-16 border-b border-border bg-card/90 sm:bg-card/95 backdrop-blur-sm sticky top-0 z-50", className)}>
      <div className="flex items-center justify-between h-full px-4 sm:px-6">
        <div className="flex items-center gap-3 sm:gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleSidebar}
            className="lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          {/* Right side content can be added here in the future */}
        </div>
      </div>
    </header>
  );
};

export default Header;