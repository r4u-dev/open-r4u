import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Palette,
  CheckCircle,
  Target,
  Plus,
  Server,
  Link,
  Trash2
} from "lucide-react";
import { useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ScoreWeightsSelector } from "@/components/ui/score-weights-selector";
import { useTheme } from "@/hooks/use-theme";

interface BlacklistedModel {
  id: string;
  provider: string;
  model: string;
  reason: string;
  blacklistedAt: string;
  blacklistedBy: string;
}

interface AIProvider {
  id: string;
  name: string;
  type: 'openai' | 'anthropic' | 'google' | 'cohere' | 'mistral' | 'groq' | 'together' | 'replicate' | 'huggingface' | 'azure' | 'aws' | 'custom';
  apiKey?: string;
  baseUrl?: string;
  description?: string;
  status: 'active' | 'inactive' | 'error';
  lastTested?: string;
  createdAt: string;
  createdBy: string;
}

const Settings = () => {
  const { colorPalettes, selectedPalette, changeTheme } = useTheme();

  const [projectSettings, setProjectSettings] = useState({
    evaluationWeights: {
      quality: 0.5,
      costEfficiency: 0.25,
      timeEfficiency: 0.25
    },
    qualityThreshold: 85,
    dataRetention: 90
  });


  const [blacklistedModels, setBlacklistedModels] = useState<BlacklistedModel[]>([
    {
      id: "1",
      provider: "OpenAI",
      model: "GPT-3.5-turbo-instruct",
      reason: "legal",
      blacklistedAt: "2024-02-15",
      blacklistedBy: "John Smith"
    },
    {
      id: "2",
      provider: "Anthropic",
      model: "Claude-2.0",
      reason: "performance",
      blacklistedAt: "2024-02-20",
      blacklistedBy: "Mike Chen"
    }
  ]);

  const [aiProviders, setAiProviders] = useState<AIProvider[]>([
    {
      id: "1",
      name: "OpenAI GPT-4",
      type: "openai",
      status: "active",
      lastTested: "2024-02-25",
      createdAt: "2024-01-15",
      createdBy: "John Smith"
    },
    {
      id: "2",
      name: "Anthropic Claude",
      type: "anthropic",
      status: "active",
      lastTested: "2024-02-24",
      createdAt: "2024-02-01",
      createdBy: "Sarah Johnson"
    },
    {
      id: "3",
      name: "Custom OpenAI Compatible",
      type: "custom",
      baseUrl: "https://internal-ai.company.com/v1",
      status: "error",
      lastTested: "2024-02-20",
      createdAt: "2024-02-10",
      createdBy: "Mike Chen",
      description: "Internal OpenAI-compatible API"
    }
  ]);

  const [isAddProviderOpen, setIsAddProviderOpen] = useState(false);
  const [newProvider, setNewProvider] = useState({
    type: 'openai' as 'openai' | 'anthropic' | 'google' | 'cohere' | 'mistral' | 'groq' | 'together' | 'replicate' | 'huggingface' | 'azure' | 'aws' | 'custom',
    apiKey: '',
    baseUrl: ''
  });


  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* AI Providers */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              AI Providers
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">Configured Providers</h4>
                <p className="text-sm text-muted-foreground">{aiProviders.length} providers available</p>
              </div>
              <Dialog open={isAddProviderOpen} onOpenChange={setIsAddProviderOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" className="gap-2">
                    <Plus className="h-4 w-4" />
                    Add Provider
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[425px]">
                  <DialogHeader>
                    <DialogTitle>Add AI Provider</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="provider-type">Provider</Label>
                      <Select value={newProvider.type} onValueChange={(value: 'openai' | 'anthropic' | 'google' | 'cohere' | 'mistral' | 'groq' | 'together' | 'replicate' | 'huggingface' | 'azure' | 'aws' | 'custom') => setNewProvider(prev => ({ ...prev, type: value }))}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select provider" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="openai">OpenAI</SelectItem>
                          <SelectItem value="anthropic">Anthropic</SelectItem>
                          <SelectItem value="google">Google (Gemini)</SelectItem>
                          <SelectItem value="cohere">Cohere</SelectItem>
                          <SelectItem value="mistral">Mistral AI</SelectItem>
                          <SelectItem value="groq">Groq</SelectItem>
                          <SelectItem value="together">Together AI</SelectItem>
                          <SelectItem value="replicate">Replicate</SelectItem>
                          <SelectItem value="huggingface">Hugging Face</SelectItem>
                          <SelectItem value="azure">Azure OpenAI</SelectItem>
                          <SelectItem value="aws">AWS Bedrock</SelectItem>
                          <SelectItem value="custom">Custom (OpenAI Compatible)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="api-key">API Key</Label>
                      <Input
                        id="api-key"
                        type="password"
                        value={newProvider.apiKey}
                        onChange={(e) => setNewProvider(prev => ({ ...prev, apiKey: e.target.value }))}
                        placeholder="Enter your API key"
                      />
                    </div>

                    {newProvider.type === 'custom' && (
                      <div className="space-y-2">
                        <Label htmlFor="base-url">Base URL</Label>
                        <Input
                          id="base-url"
                          value={newProvider.baseUrl}
                          onChange={(e) => setNewProvider(prev => ({ ...prev, baseUrl: e.target.value }))}
                          placeholder="https://api.example.com/v1"
                        />
                      </div>
                    )}

                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setIsAddProviderOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={() => {
                      const providerNames = {
                        openai: 'OpenAI',
                        anthropic: 'Anthropic',
                        google: 'Google (Gemini)',
                        cohere: 'Cohere',
                        mistral: 'Mistral AI',
                        groq: 'Groq',
                        together: 'Together AI',
                        replicate: 'Replicate',
                        huggingface: 'Hugging Face',
                        azure: 'Azure OpenAI',
                        aws: 'AWS Bedrock',
                        custom: 'Custom (OpenAI Compatible)'
                      };
                      const provider: AIProvider = {
                        id: Date.now().toString(),
                        name: providerNames[newProvider.type],
                        type: newProvider.type,
                        apiKey: newProvider.apiKey,
                        baseUrl: newProvider.type === 'custom' ? newProvider.baseUrl : undefined,
                        status: 'active',
                        createdAt: new Date().toISOString().split('T')[0],
                        createdBy: 'Current User'
                      };
                      setAiProviders(prev => [...prev, provider]);
                      setNewProvider({ type: 'openai', apiKey: '', baseUrl: '' });
                      setIsAddProviderOpen(false);
                    }}>
                      Add Provider
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <div className="space-y-3">
              {aiProviders.map((provider) => {
                const providerNames = {
                  openai: 'OpenAI',
                  anthropic: 'Anthropic',
                  google: 'Google (Gemini)',
                  cohere: 'Cohere',
                  mistral: 'Mistral AI',
                  groq: 'Groq',
                  together: 'Together AI',
                  replicate: 'Replicate',
                  huggingface: 'Hugging Face',
                  azure: 'Azure OpenAI',
                  aws: 'AWS Bedrock',
                  custom: 'Custom (OpenAI Compatible)'
                };

                const getDomainFromUrl = (url: string) => {
                  try {
                    const urlObj = new URL(url);
                    return urlObj.hostname;
                  } catch {
                    return url;
                  }
                };

                const displayName = provider.type === 'custom' && provider.baseUrl
                  ? getDomainFromUrl(provider.baseUrl)
                  : providerNames[provider.type];

                return (
                  <div key={provider.id} className="p-3 border rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <h5 className="font-medium text-sm">{displayName}</h5>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setAiProviders(prev => prev.filter(p => p.id !== provider.id))}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Evaluation */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Evaluation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-4">
              <span className="text-sm font-medium">Evaluation Weights</span>
              <ScoreWeightsSelector
                initialWeights={projectSettings.evaluationWeights}
                onWeightsChange={(weights) => setProjectSettings(prev => ({ ...prev, evaluationWeights: weights }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="quality-threshold">Test Quality Score Threshold (%)</Label>
              <Input
                id="quality-threshold"
                name="qualityThreshold"
                type="number"
                value={projectSettings.qualityThreshold}
                onChange={(e) => setProjectSettings(prev => ({ ...prev, qualityThreshold: parseInt(e.target.value) }))}
              />
            </div>
          </CardContent>
        </Card>

        {/* Appearance Settings */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              Appearance & Theme
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <Label>Color Palette</Label>
              <p className="text-sm text-muted-foreground">
                Choose a color scheme for your R4U interface. Changes are applied instantly.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {colorPalettes.map((palette, index) => (
                  <div
                    key={palette.name}
                    className={`p-3 border rounded-lg cursor-pointer transition-all hover:shadow-md ${
                      selectedPalette === index ? 'ring-2 ring-primary border-primary' : 'border-border hover:border-primary/50'
                    }`}
                    onClick={() => changeTheme(index)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-sm">{palette.name}</h4>
                        {selectedPalette === index && (
                          <CheckCircle className="h-4 w-4 text-primary" />
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">{palette.description}</p>

                    <div className="flex gap-1.5">
                      {Object.entries(palette.colors).slice(0, 4).map(([key, value]) => (
                        <div
                          key={key}
                          className="w-6 h-6 rounded-full border border-border/50"
                          style={{ backgroundColor: `hsl(${value})` }}
                          title={`${key}: ${value}`}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
};

export default Settings;