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
    Trash2,
} from "lucide-react";
import { useState, useEffect } from "react";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { ScoreWeightsSelector } from "@/components/ui/score-weights-selector";
import { useTheme } from "@/hooks/use-theme";
import { providersApi, Provider } from "@/services/providersApi";
import { useToast } from "@/hooks/use-toast";
import { Textarea } from "@/components/ui/textarea";

const Settings = () => {
    const { colorPalettes, selectedPalette, changeTheme } = useTheme();
    const { toast } = useToast();

    const [projectSettings, setProjectSettings] = useState({
        evaluationWeights: {
            quality: 0.5,
            costEfficiency: 0.25,
            timeEfficiency: 0.25,
        },
        qualityThreshold: 85,
        dataRetention: 90,
    });

    const [aiProviders, setAiProviders] = useState<Provider[]>([]);
    const [allProviders, setAllProviders] = useState<Provider[]>([]);
    const [isAddProviderOpen, setIsAddProviderOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [newProvider, setNewProvider] = useState<{
        selectedProviderId: number | null;
        isCustom: boolean;
        name: string;
        displayName: string;
        apiKey: string;
        baseUrl: string;
        models: string;
    }>({
        selectedProviderId: null,
        isCustom: false,
        name: "",
        displayName: "",
        apiKey: "",
        baseUrl: "",
        models: "",
    });

    // Load providers with API keys on mount
    useEffect(() => {
        loadProvidersWithKeys();
    }, []);

    const loadProvidersWithKeys = async () => {
        try {
            const providers = await providersApi.listProvidersWithKeys();
            setAiProviders(providers);
        } catch (error) {
            console.error("Failed to load providers:", error);
            toast({
                title: "Error",
                description: "Failed to load AI providers",
                variant: "destructive",
            });
        }
    };

    const loadAllProviders = async () => {
        try {
            const providers = await providersApi.listProviders();
            setAllProviders(providers);
        } catch (error) {
            console.error("Failed to load all providers:", error);
            toast({
                title: "Error",
                description: "Failed to load provider list",
                variant: "destructive",
            });
        }
    };

    const handleAddProviderClick = async () => {
        setIsAddProviderOpen(true);
        await loadAllProviders();
    };

    const handleProviderSelection = (value: string) => {
        if (value === "custom") {
            setNewProvider({
                selectedProviderId: null,
                isCustom: true,
                name: "",
                displayName: "",
                apiKey: "",
                baseUrl: "",
                models: "",
            });
        } else {
            const providerId = parseInt(value);
            const provider = allProviders.find((p) => p.id === providerId);
            setNewProvider({
                selectedProviderId: providerId,
                isCustom: false,
                name: provider?.name || "",
                displayName: provider?.display_name || "",
                apiKey: "",
                baseUrl: provider?.base_url || "",
                models: "",
            });
        }
    };

    const handleAddProvider = async () => {
        if (!newProvider.apiKey) {
            toast({
                title: "Error",
                description: "API key is required",
                variant: "destructive",
            });
            return;
        }

        setLoading(true);

        try {
            if (newProvider.isCustom) {
                // Create custom provider
                if (
                    !newProvider.name ||
                    !newProvider.displayName ||
                    !newProvider.models
                ) {
                    toast({
                        title: "Error",
                        description:
                            "Name, display name, and models are required for custom providers",
                        variant: "destructive",
                    });
                    setLoading(false);
                    return;
                }

                const modelsList = newProvider.models
                    .split(",")
                    .map((m) => m.trim())
                    .filter((m) => m.length > 0);

                await providersApi.createProvider({
                    name: newProvider.name,
                    display_name: newProvider.displayName,
                    base_url: newProvider.baseUrl || undefined,
                    api_key: newProvider.apiKey,
                    models: modelsList,
                });

                toast({
                    title: "Success",
                    description: "Custom provider added successfully",
                });
            } else if (newProvider.selectedProviderId) {
                // Update existing provider with API key
                await providersApi.updateProvider(
                    newProvider.selectedProviderId,
                    {
                        api_key: newProvider.apiKey,
                    },
                );

                toast({
                    title: "Success",
                    description: "Provider API key added successfully",
                });
            }

            // Reload providers
            await loadProvidersWithKeys();

            // Reset form
            setNewProvider({
                selectedProviderId: null,
                isCustom: false,
                name: "",
                displayName: "",
                apiKey: "",
                baseUrl: "",
                models: "",
            });
            setIsAddProviderOpen(false);
        } catch (error) {
            console.error("Failed to add provider:", error);
            toast({
                title: "Error",
                description:
                    error instanceof Error
                        ? error.message
                        : "Failed to add provider",
                variant: "destructive",
            });
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteProvider = async (providerId: number) => {
        if (!confirm("Are you sure you want to delete this provider?")) {
            return;
        }

        try {
            await providersApi.deleteProvider(providerId);
            toast({
                title: "Success",
                description: "Provider deleted successfully",
            });
            await loadProvidersWithKeys();
        } catch (error) {
            console.error("Failed to delete provider:", error);
            toast({
                title: "Error",
                description:
                    error instanceof Error
                        ? error.message
                        : "Failed to delete provider",
                variant: "destructive",
            });
        }
    };

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
                                <h4 className="font-medium">
                                    Configured Providers
                                </h4>
                                <p className="text-sm text-muted-foreground">
                                    {aiProviders.length} providers available
                                </p>
                            </div>
                            <Dialog
                                open={isAddProviderOpen}
                                onOpenChange={setIsAddProviderOpen}
                            >
                                <DialogTrigger asChild>
                                    <Button
                                        size="sm"
                                        className="gap-2"
                                        onClick={handleAddProviderClick}
                                    >
                                        <Plus className="h-4 w-4" />
                                        Add Provider
                                    </Button>
                                </DialogTrigger>
                                <DialogContent className="sm:max-w-[500px]">
                                    <DialogHeader>
                                        <DialogTitle>
                                            Add AI Provider
                                        </DialogTitle>
                                    </DialogHeader>
                                    <div className="space-y-4 py-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="provider-select">
                                                Provider
                                            </Label>
                                            <Select
                                                onValueChange={
                                                    handleProviderSelection
                                                }
                                                value={
                                                    newProvider.isCustom
                                                        ? "custom"
                                                        : newProvider.selectedProviderId?.toString() ||
                                                          ""
                                                }
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select provider" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {allProviders.map(
                                                        (provider) => (
                                                            <SelectItem
                                                                key={
                                                                    provider.id
                                                                }
                                                                value={provider.id.toString()}
                                                            >
                                                                {
                                                                    provider.display_name
                                                                }
                                                            </SelectItem>
                                                        ),
                                                    )}
                                                    <SelectItem value="custom">
                                                        Custom Provider
                                                    </SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        {newProvider.isCustom && (
                                            <>
                                                <div className="space-y-2">
                                                    <Label htmlFor="provider-name">
                                                        Name (identifier)
                                                    </Label>
                                                    <Input
                                                        id="provider-name"
                                                        value={newProvider.name}
                                                        onChange={(e) =>
                                                            setNewProvider(
                                                                (prev) => ({
                                                                    ...prev,
                                                                    name: e
                                                                        .target
                                                                        .value,
                                                                }),
                                                            )
                                                        }
                                                        placeholder="e.g., my-custom-provider"
                                                    />
                                                </div>

                                                <div className="space-y-2">
                                                    <Label htmlFor="provider-display-name">
                                                        Display Name
                                                    </Label>
                                                    <Input
                                                        id="provider-display-name"
                                                        value={
                                                            newProvider.displayName
                                                        }
                                                        onChange={(e) =>
                                                            setNewProvider(
                                                                (prev) => ({
                                                                    ...prev,
                                                                    displayName:
                                                                        e.target
                                                                            .value,
                                                                }),
                                                            )
                                                        }
                                                        placeholder="e.g., My Custom Provider"
                                                    />
                                                </div>

                                                <div className="space-y-2">
                                                    <Label htmlFor="base-url">
                                                        Base URL
                                                    </Label>
                                                    <Input
                                                        id="base-url"
                                                        value={
                                                            newProvider.baseUrl
                                                        }
                                                        onChange={(e) =>
                                                            setNewProvider(
                                                                (prev) => ({
                                                                    ...prev,
                                                                    baseUrl:
                                                                        e.target
                                                                            .value,
                                                                }),
                                                            )
                                                        }
                                                        placeholder="https://api.example.com/v1"
                                                    />
                                                </div>

                                                <div className="space-y-2">
                                                    <Label htmlFor="models">
                                                        Models (comma-separated)
                                                    </Label>
                                                    <Textarea
                                                        id="models"
                                                        value={
                                                            newProvider.models
                                                        }
                                                        onChange={(e) =>
                                                            setNewProvider(
                                                                (prev) => ({
                                                                    ...prev,
                                                                    models: e
                                                                        .target
                                                                        .value,
                                                                }),
                                                            )
                                                        }
                                                        placeholder="model-1, model-2, model-3"
                                                        rows={3}
                                                    />
                                                    <p className="text-xs text-muted-foreground">
                                                        Enter model names
                                                        separated by commas
                                                    </p>
                                                </div>
                                            </>
                                        )}

                                        <div className="space-y-2">
                                            <Label htmlFor="api-key">
                                                API Key
                                            </Label>
                                            <Input
                                                id="api-key"
                                                type="password"
                                                value={newProvider.apiKey}
                                                onChange={(e) =>
                                                    setNewProvider((prev) => ({
                                                        ...prev,
                                                        apiKey: e.target.value,
                                                    }))
                                                }
                                                placeholder="Enter your API key"
                                            />
                                        </div>
                                    </div>
                                    <div className="flex justify-end gap-2">
                                        <Button
                                            variant="outline"
                                            onClick={() =>
                                                setIsAddProviderOpen(false)
                                            }
                                            disabled={loading}
                                        >
                                            Cancel
                                        </Button>
                                        <Button
                                            onClick={handleAddProvider}
                                            disabled={loading}
                                        >
                                            {loading
                                                ? "Adding..."
                                                : "Add Provider"}
                                        </Button>
                                    </div>
                                </DialogContent>
                            </Dialog>
                        </div>

                        <div className="space-y-3">
                            {aiProviders.map((provider) => {
                                const getDomainFromUrl = (url: string) => {
                                    try {
                                        const urlObj = new URL(url);
                                        return urlObj.hostname;
                                    } catch {
                                        return url;
                                    }
                                };

                                const displayName = provider.base_url
                                    ? getDomainFromUrl(provider.base_url)
                                    : provider.display_name;

                                return (
                                    <div
                                        key={provider.id}
                                        className="p-3 border rounded-lg"
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex-1">
                                                <h5 className="font-medium text-sm">
                                                    {displayName}
                                                </h5>
                                                {provider.models.length > 0 && (
                                                    <p className="text-xs text-muted-foreground">
                                                        {provider.models.length}{" "}
                                                        model
                                                        {provider.models
                                                            .length !== 1
                                                            ? "s"
                                                            : ""}{" "}
                                                        available
                                                    </p>
                                                )}
                                            </div>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() =>
                                                    handleDeleteProvider(
                                                        provider.id,
                                                    )
                                                }
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
                            <span className="text-sm font-medium">
                                Evaluation Weights
                            </span>
                            <ScoreWeightsSelector
                                initialWeights={
                                    projectSettings.evaluationWeights
                                }
                                onWeightsChange={(weights) =>
                                    setProjectSettings((prev) => ({
                                        ...prev,
                                        evaluationWeights: weights,
                                    }))
                                }
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="quality-threshold">
                                Test Quality Score Threshold (%)
                            </Label>
                            <Input
                                id="quality-threshold"
                                name="qualityThreshold"
                                type="number"
                                value={projectSettings.qualityThreshold}
                                onChange={(e) =>
                                    setProjectSettings((prev) => ({
                                        ...prev,
                                        qualityThreshold: parseInt(
                                            e.target.value,
                                        ),
                                    }))
                                }
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
                                Choose a color scheme for your R4U interface.
                                Changes are applied instantly.
                            </p>

                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                                {colorPalettes.map((palette, index) => (
                                    <div
                                        key={palette.name}
                                        className={`p-3 border rounded-lg cursor-pointer transition-all hover:shadow-md ${
                                            selectedPalette === index
                                                ? "ring-2 ring-primary border-primary"
                                                : "border-border hover:border-primary/50"
                                        }`}
                                        onClick={() => changeTheme(index)}
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <h4 className="font-medium text-sm">
                                                    {palette.name}
                                                </h4>
                                                {selectedPalette === index && (
                                                    <CheckCircle className="h-4 w-4 text-primary" />
                                                )}
                                            </div>
                                        </div>
                                        <p className="text-xs text-muted-foreground mb-3">
                                            {palette.description}
                                        </p>

                                        <div className="flex gap-1.5">
                                            {Object.entries(palette.colors)
                                                .slice(0, 4)
                                                .map(([key, value]) => (
                                                    <div
                                                        key={key}
                                                        className="w-6 h-6 rounded-full border border-border/50"
                                                        style={{
                                                            backgroundColor: `hsl(${value})`,
                                                        }}
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
