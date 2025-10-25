import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

interface JsonSchemaViewerProps {
  schema: Record<string, any>;
  title: string;
}

interface PropertyViewerProps {
  propKey: string;
  value: any;
  required?: boolean;
  level?: number;
}

const PropertyViewer = ({ propKey, value, required = false, level = 0 }: PropertyViewerProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Use a more controlled indentation approach with reduced spacing
  const getIndentClass = (level: number) => {
    switch (level) {
      case 0: return "ml-0";
      case 1: return "ml-2";
      case 2: return "ml-4";
      case 3: return "ml-6";
      case 4: return "ml-8";
      default: return "ml-10"; // Cap at a reasonable maximum
    }
  };

  const indentClass = getIndentClass(level);

  const getTypeBadge = (type: any, items?: any) => {
    if (Array.isArray(type)) {
      return type.join(" | ");
    }
    
    // Handle array types with items
    if (type === "array" && items) {
      if (items.type) {
        return `${items.type}[]`;
      }
      if (Array.isArray(items)) {
        return `${items.join(" | ")}[]`;
      }
      if (items.properties) {
        return "object[]";
      }
      return "array[]";
    }
    
    return type;
  };

  const getTypeColor = (type: any) => {
    const typeStr = Array.isArray(type) ? type[0] : type;
    switch (typeStr) {
      case "string":
        return "text-muted-foreground";
      case "integer":
      case "number":
        return "text-muted-foreground";
      case "boolean":
        return "text-muted-foreground";
      case "array":
        return "text-muted-foreground";
      case "object":
        return "text-muted-foreground";
      default:
        return "text-muted-foreground";
    }
  };

  const renderValue = (val: any, currentLevel: number = 0) => {
    if (val === null || val === undefined) {
      return <span className="text-muted-foreground italic">null</span>;
    }

    if (typeof val === "string") {
      return <span className="text-foreground">"{val}"</span>;
    }

    if (typeof val === "number" || typeof val === "boolean") {
      return <span className="text-foreground">{String(val)}</span>;
    }

    if (Array.isArray(val)) {
      if (val.length === 0) {
        return <span className="text-muted-foreground">[]</span>;
      }
      
      return (
        <div className="ml-2">
          <span className="text-muted-foreground">[</span>
          {val.map((item, index) => (
            <div key={index} className="ml-2">
              {renderValue(item, currentLevel + 1)}
              {index < val.length - 1 && <span className="text-muted-foreground">,</span>}
            </div>
          ))}
          <span className="text-muted-foreground">]</span>
        </div>
      );
    }

    if (typeof val === "object") {
      const entries = Object.entries(val);
      if (entries.length === 0) {
        return <span className="text-muted-foreground">{}</span>;
      }

      return (
        <div className="ml-2">
          <span className="text-muted-foreground">{"{"}</span>
          {entries.map(([key, itemValue], index) => (
            <div key={key} className="ml-2">
              <span className="text-primary font-mono">"{key}"</span>
              <span className="text-muted-foreground">: </span>
              {renderValue(itemValue, currentLevel + 1)}
              {index < entries.length - 1 && <span className="text-muted-foreground">,</span>}
            </div>
          ))}
          <span className="text-muted-foreground">{"}"}</span>
        </div>
      );
    }

    return <span className="text-foreground">{String(val)}</span>;
  };


  const shouldShowExpandButton = (val: any) => {
    // Only show expand button for objects with properties
    if (val?.properties && typeof val.properties === "object" && Object.keys(val.properties).length > 0) {
      return true;
    }
    
    // Show expand for arrays that contain objects (not simple types)
    if (val?.type === "array" && val?.items?.properties) {
      return true;
    }
    
    // Show expand for arrays that contain arrays (nested arrays)
    if (val?.type === "array" && val?.items?.type === "array") {
      return true;
    }
    
    // Don't show expand for simple types like string, number, boolean, or arrays of simple types
    return false;
  };

  return (
    <div className={`${indentClass} mb-2`}>
      <div className="flex items-center gap-0.5 flex-wrap">
        <div className="w-3 flex justify-center">
          {shouldShowExpandButton(value) ? (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="hover:text-primary transition-colors"
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
            </button>
          ) : null}
        </div>
        
        <span className="font-mono text-foreground font-semibold" style={{ color: 'inherit' }}>{propKey}</span>
        
        {value?.type && (
          <span className={`px-1.5 py-0.5 rounded text-xs ${getTypeColor(value.type)}`}>
            {getTypeBadge(value.type, value.items)}
          </span>
        )}
        
        {required && (
          <span className="px-1.5 py-0.5 text-muted-foreground text-xs">
            required
          </span>
        )}

        {value?.enum && (
          <span className="px-1.5 py-0.5 text-muted-foreground text-xs">
            enum
          </span>
        )}

        {value?.pattern && (
          <span className="px-1.5 py-0.5 text-muted-foreground text-xs">
            pattern
          </span>
        )}

        {value?.minimum !== undefined && (
          <span className="px-1.5 py-0.5 text-muted-foreground text-xs">
            min: {value.minimum}
          </span>
        )}

        {value?.maximum !== undefined && (
          <span className="px-1.5 py-0.5 text-muted-foreground text-xs">
            max: {value.maximum}
          </span>
        )}
      </div>

      {value?.description && (
        <div className="text-muted-foreground text-xs ml-6 mt-0">
          {value.description}
        </div>
      )}

      {isExpanded && (
        <div className="ml-1 mt-2 border-l border-border pl-1">
          {/* Show properties if it's an object with properties */}
          {value?.properties && (
            <div>
                {Object.entries(value.properties).map(([key, propValue]: [string, any]) => (
                  <PropertyViewer
                    key={key}
                    propKey={key}
                    value={propValue}
                    required={value?.required?.includes(key)}
                    level={level + 1}
                  />
                ))}
            </div>
          )}

          {/* Show array item properties directly */}
          {value?.items && value?.items?.properties && (
            <div>
                {Object.entries(value.items.properties).map(([key, propValue]: [string, any]) => (
                  <PropertyViewer
                    key={key}
                    propKey={key}
                    value={propValue}
                    required={value.items?.required?.includes(key)}
                    level={level + 1}
                  />
                ))}
              </div>
          )}

          {/* Show enum values for simple types */}
          {value?.enum && !value?.properties && (
            <div>
              <div className="text-muted-foreground text-xs font-medium mb-1">Allowed Values:</div>
              <div className="flex gap-1 flex-wrap">
                {value.enum.map((enumValue: any, index: number) => (
                  <span key={index} className="px-1.5 py-0.5 text-muted-foreground text-xs">
                    {String(enumValue)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Show pattern for simple types */}
          {value?.pattern && !value?.properties && (
            <div>
              <div className="text-muted-foreground text-xs font-medium mb-1">Pattern:</div>
              <div className="font-mono text-xs">
                {value.pattern}
              </div>
            </div>
          )}

          {/* Show constraints for simple types */}
          {(value?.minLength || value?.maxLength || value?.minimum || value?.maximum) && !value?.properties && (
            <div>
              <div className="text-muted-foreground text-xs font-medium mb-1">Constraints:</div>
              <div>
                {value.minLength && (
                  <div className="text-xs">Min length: {value.minLength}</div>
                )}
                {value.maxLength && (
                  <div className="text-xs">Max length: {value.maxLength}</div>
                )}
                {value.minimum && (
                  <div className="text-xs">Minimum: {value.minimum}</div>
                )}
                {value.maximum && (
                  <div className="text-xs">Maximum: {value.maximum}</div>
                )}
              </div>
            </div>
          )}

          {/* Show default value for simple types */}
          {value?.default !== undefined && !value?.properties && (
            <div>
              <div className="text-muted-foreground text-xs font-medium mb-1">Default:</div>
              <div className="font-mono text-xs">
                {renderValue(value.default)}
              </div>
            </div>
          )}

          {/* Show example for simple types */}
          {value?.example && !value?.properties && (
            <div>
              <div className="text-muted-foreground text-xs font-medium mb-1">Example:</div>
              <div className="font-mono text-xs">
                {renderValue(value.example)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const JsonSchemaViewer = ({ schema, title }: JsonSchemaViewerProps) => {
  if (!schema?.properties) {
    return (
      <div className="text-xs space-y-2">
        <h3 className="font-semibold text-sm">{title}</h3>
        <div className="text-muted-foreground">No properties defined</div>
      </div>
    );
  }

  return (
    <div className="text-xs space-y-2">
      <div className="text-muted-foreground mb-1 text-xs">{title}</div>
      <div>
        <div>
          {Object.entries(schema.properties).map(([key, prop]: [string, any]) => (
            <PropertyViewer
              key={key}
              propKey={key}
              value={prop}
              required={schema.required?.includes(key)}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
