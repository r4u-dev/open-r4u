import React, { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Eye, Edit, FileText } from "lucide-react";

interface RequirementsSectionProps {
  requirements: string;
  onRequirementsChange: (value: string) => void;
  errors?: {
    requirements?: string;
  };
}

const RequirementsSection: React.FC<RequirementsSectionProps> = ({
  requirements,
  onRequirementsChange,
  errors = {}
}) => {
  const [activeTab, setActiveTab] = useState<"edit" | "preview">("edit");

  // Enhanced markdown to HTML converter for preview with condensed styling
  const markdownToHtml = (markdown: string): string => {
    // Split into lines for better processing
    const lines = markdown.split('\n');
    const processedLines: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];
      
      // Skip empty lines (will be handled as spacing)
      if (line.trim() === '') {
        processedLines.push('<div class="h-2"></div>');
        continue;
      }
      
      // Headers with condensed spacing using theme-aware classes
      if (line.match(/^#### /)) {
        line = line.replace(/^#### (.*)/, '<h4 class="text-sm font-semibold mt-3 mb-1 text-foreground opacity-80">$1</h4>');
      } else if (line.match(/^### /)) {
        line = line.replace(/^### (.*)/, '<h3 class="text-base font-semibold mt-4 mb-2 text-foreground opacity-90">$1</h3>');
      } else if (line.match(/^## /)) {
        line = line.replace(/^## (.*)/, '<h2 class="text-lg font-semibold mt-5 mb-2 text-foreground">$1</h2>');
      } else if (line.match(/^# /)) {
        line = line.replace(/^# (.*)/, '<h1 class="text-xl font-bold mt-6 mb-3 text-foreground">$1</h1>');
      }
      // Enhanced list handling with better spacing and dark theme support
      else if (line.match(/^- \[ \] /)) {
        line = line.replace(/^- \[ \] (.*)/, '<div class="flex items-start gap-2 ml-4 mb-1 text-sm"><input type="checkbox" disabled class="rounded mt-0.5 flex-shrink-0"> <span class="text-muted-foreground">$1</span></div>');
      } else if (line.match(/^- \[x\] /)) {
        line = line.replace(/^- \[x\] (.*)/, '<div class="flex items-start gap-2 ml-4 mb-1 text-sm"><input type="checkbox" checked disabled class="rounded mt-0.5 flex-shrink-0"> <span class="text-muted-foreground line-through opacity-75">$1</span></div>');
      } else if (line.match(/^- /)) {
        line = line.replace(/^- (.*)/, '<div class="ml-4 mb-1 text-sm text-muted-foreground">• $1</div>');
      } else if (line.match(/^\* /)) {
        line = line.replace(/^\* (.*)/, '<div class="ml-4 mb-1 text-sm text-muted-foreground">• $1</div>');
      } else if (line.match(/^\d+\. /)) {
        line = line.replace(/^(\d+)\. (.*)/, '<div class="ml-4 mb-1 text-sm text-muted-foreground"><span class="font-medium text-foreground">$1.</span> $2</div>');
      }
      // Special handling for User Story format
      else if (line.match(/^\*\*User Story:\*\*/)) {
        line = line.replace(/^\*\*User Story:\*\* (.*)/, '<div class="bg-muted/50 border-l-4 border-border pl-3 py-2 mb-2 text-sm"><span class="font-semibold text-foreground">User Story:</span> <span class="text-foreground">$1</span></div>');
      }
      // Regular paragraph with smaller font
      else {
        line = `<p class="mb-1 text-sm text-foreground leading-relaxed">${line}</p>`;
      }
      
      // Apply inline formatting with better contrast and theme support
      line = line.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-foreground">$1</strong>');
      line = line.replace(/\*(.*?)\*/g, '<em class="italic text-foreground opacity-90">$1</em>');
      line = line.replace(/`([^`]+)`/g, '<code class="bg-muted px-1.5 py-0.5 rounded text-xs font-mono text-foreground opacity-80">$1</code>');
      
      // Handle special keywords in acceptance criteria using theme-aware classes
      line = line.replace(/\b(WHEN|THEN|IF|GIVEN|SHALL|AND|OR)\b/g, '<span class="font-semibold text-foreground opacity-90">$1</span>');
      
      processedLines.push(line);
    }
    
    // Handle code blocks (multi-line) with smaller font and proper theme support
    let html = processedLines.join('');
    html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-muted p-3 rounded-md overflow-x-auto my-3 text-xs"><code class="text-foreground">$1</code></pre>');
    
    return html;
  };

  const validateRequirements = (text: string): string | undefined => {
    if (!text.trim()) {
      return "Requirements are required";
    }
    if (text.trim().length < 20) {
      return "Requirements must be at least 20 characters long";
    }
    if (text.length > 5000) {
      return "Requirements must be less than 5000 characters";
    }
    return undefined;
  };

  const insertTemplate = () => {
    const template = `# Task Requirements

## Introduction
Provide a brief overview of the task, its purpose, and how it fits into the broader system or workflow. Describe the problem this task solves and the value it provides to users or the system.

## Requirements

### Requirement 1
**User Story:** As a [user type], I want to [action/goal], so that I can [benefit/outcome].

#### Acceptance Criteria
1. WHEN [condition] THEN the system SHALL [expected behavior]
2. WHEN [condition] THEN the system SHALL [expected behavior]
3. WHEN [condition] THEN the system SHALL [expected behavior]
4. IF [condition] THEN the system SHALL [expected behavior]
5. GIVEN [precondition] WHEN [action] THEN [expected result]

### Requirement 2
**User Story:** As a [user type], I want to [action/goal], so that I can [benefit/outcome].

#### Acceptance Criteria
1. WHEN [condition] THEN the system SHALL [expected behavior]
2. WHEN [condition] THEN the system SHALL [expected behavior]
3. IF [condition] THEN the system SHALL [expected behavior]
`;

    onRequirementsChange(template);
  };

  const maxLength = 5000;
  const remainingChars = maxLength - requirements.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          Requirements *
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={insertTemplate}
          className="gap-2"
        >
          <FileText className="h-4 w-4" />
          Insert Template
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "edit" | "preview")}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="edit" className="gap-2">
            <Edit className="h-4 w-4" />
            Edit
          </TabsTrigger>
          <TabsTrigger value="preview" className="gap-2">
            <Eye className="h-4 w-4" />
            Preview
          </TabsTrigger>
        </TabsList>

        <TabsContent value="edit" className="space-y-2">
          <Textarea
            placeholder="Define the task requirements using markdown formatting. Include functional requirements, acceptance criteria, and any constraints or assumptions."
          name="requirements"
            value={requirements}
            onChange={(e) => onRequirementsChange(e.target.value)}
            className={`min-h-[300px] resize-none font-mono text-sm ${errors.requirements ? "border-destructive" : ""}`}
            maxLength={maxLength}
          />
          <div className="flex justify-between items-center">
            {errors.requirements && (
              <p className="text-sm text-destructive">{errors.requirements}</p>
            )}
            <div className="flex-1" />
            <p className={`text-xs ${remainingChars < 500 ? 'text-orange-500' : remainingChars < 200 ? 'text-destructive' : 'text-muted-foreground'}`}>
              {remainingChars} characters remaining
            </p>
          </div>
        </TabsContent>

        <TabsContent value="preview" className="space-y-2">
          <div className={`min-h-[300px] p-3 border rounded-md bg-background overflow-y-auto ${errors.requirements ? "border-destructive" : ""}`}>
            {requirements.trim() ? (
              <div 
                className="max-w-none text-sm leading-tight"
                dangerouslySetInnerHTML={{ __html: markdownToHtml(requirements) }}
              />
            ) : (
              <p className="text-muted-foreground italic text-sm">
                No requirements entered yet. Switch to Edit tab to add content.
              </p>
            )}
          </div>
          {errors.requirements && (
            <p className="text-sm text-destructive">{errors.requirements}</p>
          )}
        </TabsContent>
      </Tabs>

      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">
          Use markdown formatting to structure your requirements. Include functional requirements, acceptance criteria, and any constraints.
        </p>
        <div className="text-xs text-muted-foreground space-y-1">
          <p><strong>Markdown tips:</strong></p>
          <ul className="list-disc list-inside space-y-0.5 ml-2">
            <li><code># Header</code> for main sections</li>
            <li><code>**bold**</code> and <code>*italic*</code> for emphasis</li>
            <li><code>- item</code> for bullet lists</li>
            <li><code>- [ ] task</code> for checkboxes</li>
            <li><code>`code`</code> for inline code</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default RequirementsSection;