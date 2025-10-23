import React, { useState, useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Code, 
  Eye, 
  FileJson, 
  CheckCircle, 
  XCircle, 
  Copy,
  RefreshCw 
} from "lucide-react";

interface SchemaSectionProps {
  inputSchema: object;
  outputSchema: object;
  onInputSchemaChange: (value: object) => void;
  onOutputSchemaChange: (value: object) => void;
  errors?: {
    inputSchema?: string;
    outputSchema?: string;
  };
}

const SchemaSection: React.FC<SchemaSectionProps> = ({
  inputSchema,
  outputSchema,
  onInputSchemaChange,
  onOutputSchemaChange,
  errors = {}
}) => {
  const [inputSchemaText, setInputSchemaText] = useState(() => 
    JSON.stringify(inputSchema, null, 2)
  );
  const [outputSchemaText, setOutputSchemaText] = useState(() => 
    JSON.stringify(outputSchema, null, 2)
  );
  const [inputSchemaValid, setInputSchemaValid] = useState(true);
  const [outputSchemaValid, setOutputSchemaValid] = useState(true);
  const [activeTab, setActiveTab] = useState<"input" | "output">("input");

  const validateAndUpdateSchema = useCallback((
    text: string, 
    isInput: boolean
  ) => {
    try {
      const parsed = JSON.parse(text);
      if (isInput) {
        setInputSchemaValid(true);
        onInputSchemaChange(parsed);
      } else {
        setOutputSchemaValid(true);
        onOutputSchemaChange(parsed);
      }
    } catch (error) {
      if (isInput) {
        setInputSchemaValid(false);
      } else {
        setOutputSchemaValid(false);
      }
    }
  }, [onInputSchemaChange, onOutputSchemaChange]);

  const handleInputSchemaChange = (value: string) => {
    setInputSchemaText(value);
    validateAndUpdateSchema(value, true);
  };

  const handleOutputSchemaChange = (value: string) => {
    setOutputSchemaText(value);
    validateAndUpdateSchema(value, false);
  };

  const insertTemplate = (isInput: boolean) => {
    const inputTemplate = {
      type: "object",
      properties: {
        text: {
          type: "string",
          description: "Input text to process"
        },
        options: {
          type: "object",
          properties: {
            format: {
              type: "string",
              enum: ["json", "text", "markdown"],
              default: "text"
            }
          }
        }
      },
      required: ["text"]
    };

    const outputTemplate = {
      type: "object",
      properties: {
        result: {
          type: "string",
          description: "Processed result"
        },
        confidence: {
          type: "number",
          minimum: 0,
          maximum: 1,
          description: "Confidence score of the result"
        },
        metadata: {
          type: "object",
          properties: {
            processingTime: {
              type: "number",
              description: "Processing time in milliseconds"
            },
            model: {
              type: "string",
              description: "Model used for processing"
            }
          }
        }
      },
      required: ["result"]
    };

    const template = isInput ? inputTemplate : outputTemplate;
    const formattedTemplate = JSON.stringify(template, null, 2);
    
    if (isInput) {
      handleInputSchemaChange(formattedTemplate);
    } else {
      handleOutputSchemaChange(formattedTemplate);
    }
  };

  const formatSchema = (isInput: boolean) => {
    try {
      const text = isInput ? inputSchemaText : outputSchemaText;
      const parsed = JSON.parse(text);
      const formatted = JSON.stringify(parsed, null, 2);
      
      if (isInput) {
        handleInputSchemaChange(formatted);
      } else {
        handleOutputSchemaChange(formatted);
      }
    } catch (error) {
      // Invalid JSON, don't format
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const generateExample = (schema: Record<string, unknown>): unknown => {
    const generateFromSchema = (schemaObj: Record<string, unknown>): unknown => {
      if (!schemaObj || typeof schemaObj !== 'object') return null;
      type JSONSchemaLike = {
        type?: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object';
        enum?: unknown[];
        default?: unknown;
        items?: Record<string, unknown>;
        properties?: Record<string, Record<string, unknown>>;
      };
      const s = schemaObj as JSONSchemaLike;
      switch (s.type) {
        case 'string':
          if (s.enum) return s.enum[0];
          return s.default || "example string";
        case 'number':
          return s.default || 42;
        case 'integer':
          return s.default || 1;
        case 'boolean':
          return s.default || true;
        case 'array':
          if (s.items) {
            return [generateFromSchema(s.items as Record<string, unknown>)];
          }
          return [];
        case 'object':
          if (s.properties && typeof s.properties === 'object') {
            const result: Record<string, unknown> = {};
            Object.keys(s.properties as Record<string, unknown>).forEach(key => {
              const properties = s.properties as Record<string, Record<string, unknown>>;
              result[key] = generateFromSchema(properties[key]);
            });
            return result;
          }
          return {};
        default:
          return null;
      }
    };

    return generateFromSchema(schema);
  };

  const renderSchemaEditor = (
    isInput: boolean,
    text: string,
    isValid: boolean,
    onChange: (value: string) => void,
    error?: string
  ) => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {isInput ? 'Input' : 'Output'} Schema *
          </span>
          <Badge variant={isValid ? "default" : "destructive"} className="gap-1">
            {isValid ? (
              <>
                <CheckCircle className="h-3 w-3" />
                Valid
              </>
            ) : (
              <>
                <XCircle className="h-3 w-3" />
                Invalid
              </>
            )}
          </Badge>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => insertTemplate(isInput)}
            className="gap-2"
          >
            <FileJson className="h-4 w-4" />
            Template
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => formatSchema(isInput)}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Format
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => copyToClipboard(text)}
            className="gap-2"
          >
            <Copy className="h-4 w-4" />
            Copy
          </Button>
        </div>
      </div>

      <Textarea
        placeholder={`Enter JSON schema for ${isInput ? 'input' : 'output'} data structure...`}
        name={isInput ? 'inputSchema' : 'outputSchema'}
        value={text}
        onChange={(e) => onChange(e.target.value)}
        className={`min-h-[200px] resize-none font-mono text-sm ${
          error || !isValid ? "border-destructive" : ""
        }`}
      />

      {(error || !isValid) && (
        <p className="text-sm text-destructive">
          {error || "Invalid JSON schema format"}
        </p>
      )}

      {isValid && text.trim() && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Eye className="h-4 w-4" />
              Example Data
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto">
              <code>
                {JSON.stringify(generateExample(JSON.parse(text) as Record<string, unknown>), null, 2)}
              </code>
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "input" | "output")}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="input" className="gap-2">
            <Code className="h-4 w-4" />
            Input Schema
          </TabsTrigger>
          <TabsTrigger value="output" className="gap-2">
            <Code className="h-4 w-4" />
            Output Schema
          </TabsTrigger>
        </TabsList>

        <TabsContent value="input">
          {renderSchemaEditor(
            true,
            inputSchemaText,
            inputSchemaValid,
            handleInputSchemaChange,
            errors.inputSchema
          )}
        </TabsContent>

        <TabsContent value="output">
          {renderSchemaEditor(
            false,
            outputSchemaText,
            outputSchemaValid,
            handleOutputSchemaChange,
            errors.outputSchema
          )}
        </TabsContent>
      </Tabs>

      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">
          Define JSON schemas to specify the structure and validation rules for input and output data.
        </p>
        <div className="text-xs text-muted-foreground space-y-1">
          <p><strong>Schema tips:</strong></p>
          <ul className="list-disc list-inside space-y-0.5 ml-2">
            <li>Use <code>type</code> to specify data types (string, number, object, array)</li>
            <li>Add <code>description</code> fields to document properties</li>
            <li>Use <code>required</code> array to specify mandatory fields</li>
            <li>Set <code>enum</code> for restricted value lists</li>
            <li>Add validation with <code>minimum</code>, <code>maximum</code>, <code>pattern</code></li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default SchemaSection;