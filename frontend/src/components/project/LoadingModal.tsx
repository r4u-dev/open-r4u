import { Loader2, Building2 } from "lucide-react";

interface LoadingOverlayProps {
  open: boolean;
}

const LoadingOverlay = ({ open }: LoadingOverlayProps) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="flex flex-col items-center space-y-4">
        <div className="w-16 h-16 bg-gradient-to-br from-primary/20 to-primary/10 rounded-full flex items-center justify-center">
          <Building2 className="h-8 w-8 text-primary" />
        </div>
        <div className="text-center">
          <h3 className="text-lg font-semibold text-foreground">
            Loading Projects
          </h3>
          <p className="text-sm text-muted-foreground">
            Please wait while we load your projects...
          </p>
        </div>
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    </div>
  );
};

export default LoadingOverlay;
