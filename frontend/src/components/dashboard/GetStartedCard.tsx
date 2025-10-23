import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Play, BookOpen } from "lucide-react";
import { useNavigate } from "react-router-dom";

const GetStartedCard = () => {
  const navigate = useNavigate();

  const task = {
    id: 1,
    title: "Create Your First Task",
    description: "Set up an AI task to start tracking performance and get insights",
    icon: Play,
    action: "Create Task",
  };

  const handleCreateTask = () => {
    navigate("/tasks/new");
  };

  return (
    <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          Welcome to R4U
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 sm:space-y-6">
        <p className="text-muted-foreground text-sm sm:text-base">
          Get started by creating your first AI task:
        </p>
        
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-3 sm:p-4 rounded-lg border transition-all duration-200 bg-background/50 border-border/50 hover:border-primary/30">
          {/* Progress indicator */}
          <div className="w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 flex-shrink-0 bg-primary/10">
            <Play className="h-4 w-4 text-primary" />
          </div>

          <div className="flex-1 min-w-0">
            <h4 className="font-medium transition-colors text-sm sm:text-base text-foreground">
              {task.title}
            </h4>
            <p className="text-xs sm:text-sm transition-colors mt-1 text-muted-foreground">
              {task.description}
            </p>
          </div>

          {/* Action button */}
          <div className="flex justify-end sm:justify-start">
            <div className="flex items-center gap-2 flex-shrink-0">
              <Button
                size="sm"
                variant="outline"
                onClick={handleCreateTask}
                className="text-xs sm:text-sm"
              >
                {task.action}
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default GetStartedCard;