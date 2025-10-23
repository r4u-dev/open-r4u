import React from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

interface BasicInfoSectionProps {
  name: string;
  description: string;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  errors?: {
    name?: string;
    description?: string;
  };
}

const BasicInfoSection: React.FC<BasicInfoSectionProps> = ({
  name,
  description,
  onNameChange,
  onDescriptionChange,
  errors = {}
}) => {
  const maxDescriptionLength = 500;
  const remainingChars = maxDescriptionLength - description.length;

  return (
    <div className="space-y-6">
      {/* Task Name */}
      <div className="space-y-2">
        <Label htmlFor="task-name" className="text-sm font-medium">
          Task Name *
        </Label>
        <Input
          id="task-name"
          name="taskName"
          type="text"
          placeholder="Enter a descriptive name for your task"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          className={errors.name ? "border-destructive" : ""}
          maxLength={100}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name}</p>
        )}
        <p className="text-xs text-muted-foreground">
          Choose a clear, descriptive name that explains what this task accomplishes
        </p>
      </div>

      {/* Task Description */}
      <div className="space-y-2">
        <Label htmlFor="task-description" className="text-sm font-medium">
          Description *
        </Label>
        <Textarea
          id="task-description"
          name="taskDescription"
          placeholder="Provide a detailed description of what this task should accomplish, including its purpose and expected outcomes"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          className={`min-h-[120px] resize-none ${errors.description ? "border-destructive" : ""}`}
          maxLength={maxDescriptionLength}
        />
        <div className="flex justify-between items-center">
          {errors.description && (
            <p className="text-sm text-destructive">{errors.description}</p>
          )}
          <div className="flex-1" />
          <p className={`text-xs ${remainingChars < 50 ? 'text-orange-500' : remainingChars < 20 ? 'text-destructive' : 'text-muted-foreground'}`}>
            {remainingChars} characters remaining
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          Explain the task's purpose, expected behavior, and any important context
        </p>
      </div>


    </div>
  );
};

export default BasicInfoSection;