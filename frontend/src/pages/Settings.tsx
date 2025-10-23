import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { 
  Settings as SettingsIcon, 
  Bell, 
  Shield, 
  Database, 
  Zap,
  Mail,
  Smartphone,
  Globe,
  Palette,
  CheckCircle,
  FolderOpen,
  Users,
  UserPlus,
  Target,
  BarChart3,
  Settings2,
  Trash2,
  MoreHorizontal,
  Ban,
  AlertTriangle,
  Plus,
  Cpu,
  Key,
  Link,
  Eye,
  EyeOff
} from "lucide-react";
import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ScoreWeightsSelector } from "@/components/ui/score-weights-selector";
import { useTheme } from "@/hooks/use-theme";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { useProject } from "@/contexts/ProjectContext";
import { getProjectCollaborators, updateProjectCollaborator, removeProjectCollaborator } from "@/lib/api/collaborators";
import { InviteCollaboratorDialog } from "@/components/project/InviteCollaboratorDialog";
import type { ProjectRole, ProjectAccount } from "@/lib/types/collaborator";

interface BlacklistedModel {
  id: string;
  provider: string;
  model: string;
  reason: string;
  blacklistedAt: string;
  blacklistedBy: string;
}

interface UserModel {
  id: string;
  name: string;
  provider: string;
  type: 'known' | 'custom';
  endpoint?: string;
  apiKey?: string;
  description?: string;
  status: 'active' | 'inactive' | 'error';
  lastTested?: string;
  createdAt: string;
  createdBy: string;
}

const Settings = () => {
  const { colorPalettes, selectedPalette, changeTheme } = useTheme();
  const { activeProject } = useProject();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [projectSettings, setProjectSettings] = useState({
    name: "AI Performance Optimization",
    evaluationWeights: {
      accuracy: 0.5,
      costEfficiency: 0.25,
      timeEfficiency: 0.25
    },
    accuracyThreshold: 85,
    autoRetry: true,
    maxRetries: 3,
    dataRetention: 90
  });

  // Fetch collaborators from backend (now includes name and email fields)
  const { data: collaborators = [], isLoading: collaboratorsLoading } = useQuery({
    queryKey: ["collaborators", activeProject?.id],
    queryFn: () => activeProject?.id ? getProjectCollaborators(activeProject.id) : Promise.resolve([]),
    enabled: !!activeProject?.id,
  });

  // Since we removed authentication, assume user has full permissions
  const isOwner = true;
  const isAdmin = true;
  const canManageMembers = true;

  // Update collaborator role mutation
  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: ProjectRole }) => {
      if (!activeProject?.id) throw new Error("No active project");
      return updateProjectCollaborator(activeProject.id, userId, { role });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collaborators", activeProject?.id] });
      toast({
        title: "Role updated",
        description: "Collaborator role has been updated successfully",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to update role",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Remove collaborator mutation
  const removeMutation = useMutation({
    mutationFn: (userId: string) => {
      if (!activeProject?.id) throw new Error("No active project");
      return removeProjectCollaborator(activeProject.id, userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collaborators", activeProject?.id] });
      toast({
        title: "Member removed",
        description: "Collaborator has been removed from the project",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to remove member",
        description: error.message,
        variant: "destructive",
      });
    },
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

  const [userModels, setUserModels] = useState<UserModel[]>([
    {
      id: "1",
      name: "Custom GPT-4",
      provider: "OpenAI",
      type: "known",
      status: "active",
      lastTested: "2024-02-25",
      createdAt: "2024-01-15",
      createdBy: "John Smith"
    },
    {
      id: "2",
      name: "Internal Claude Model",
      provider: "Custom",
      type: "custom",
      endpoint: "https://internal-ai.company.com/v1/chat/completions",
      status: "active",
      lastTested: "2024-02-24",
      createdAt: "2024-02-01",
      createdBy: "Sarah Johnson",
      description: "Internal Claude model hosted on company infrastructure"
    },
    {
      id: "3",
      name: "Local Llama Model",
      provider: "Custom",
      type: "custom",
      endpoint: "http://localhost:8080/v1/completions",
      status: "error",
      lastTested: "2024-02-20",
      createdAt: "2024-02-10",
      createdBy: "Mike Chen",
      description: "Local Llama model for development and testing"
    }
  ]);

  const [showApiKeys, setShowApiKeys] = useState<{[key: string]: boolean}>({});

  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    sms: false,
    alerts: true
  });

  const [performance, setPerformance] = useState({
    autoOptimization: true,
    costOptimization: true
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground">Configure your R4U preferences and system settings</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Project Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5" />
              Project Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="project-name">Project Name</Label>
              <Input
                id="project-name"
                name="projectName"
                value={projectSettings.name}
                onChange={(e) => setProjectSettings(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter project name"
              />
            </div>


            <div className="space-y-4">
              <span className="text-sm font-medium">Evaluation Weights</span>
              <ScoreWeightsSelector
                onWeightsChange={(weights) => setProjectSettings(prev => ({ ...prev, evaluationWeights: weights }))}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="accuracy-threshold">Accuracy Threshold (%)</Label>
                <Input
                  id="accuracy-threshold"
                name="accuracyThreshold"
                  type="number"
                  value={projectSettings.accuracyThreshold}
                  onChange={(e) => setProjectSettings(prev => ({ ...prev, accuracyThreshold: parseInt(e.target.value) }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max-retries">Max Retries</Label>
                <Input
                  id="max-retries"
                name="maxRetries"
                  type="number"
                  value={projectSettings.maxRetries}
                  onChange={(e) => setProjectSettings(prev => ({ ...prev, maxRetries: parseInt(e.target.value) }))}
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Auto Retry Failed Tasks</Label>
                <p className="text-sm text-muted-foreground">Automatically retry failed tasks</p>
              </div>
              <Switch
                checked={projectSettings.autoRetry}
                onCheckedChange={(checked) => setProjectSettings(prev => ({ ...prev, autoRetry: checked }))}
              />
            </div>
          </CardContent>
        </Card>

        {/* Team Management */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Team Members
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">Active Collaborators</h4>
                <p className="text-sm text-muted-foreground">
                  {collaboratorsLoading ? "Loading..." : `${collaborators.length} team member${collaborators.length !== 1 ? 's' : ''}`}
                </p>
              </div>
              {activeProject?.id && canManageMembers && (
                <InviteCollaboratorDialog projectId={activeProject.id} isOwner={isOwner} />
              )}
            </div>

            {collaboratorsLoading ? (
              <div className="text-center py-8 text-muted-foreground">Loading collaborators...</div>
            ) : collaborators.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No collaborators yet. Invite team members to get started.
              </div>
            ) : (
              <div className="space-y-3">
                {collaborators.map((collaborator) => {
                  const isCollaboratorOwner = collaborator.role === 'owner';
                  const canModifyThisUser = canManageMembers && !isCollaboratorOwner && (
                    // Only owners can manage admins
                    isOwner || collaborator.role !== 'admin'
                  );

                  return (
                    <div key={collaborator.account_id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback>
                            {collaborator.account.name 
                              ? collaborator.account.name.split(' ').map(n => n[0]).join('').toUpperCase()
                              : collaborator.account.email.charAt(0).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-sm">
                              {collaborator.account.name}
                            </p>
                            <Badge 
                              variant={
                                collaborator.role === 'owner' ? 'default' :
                                collaborator.role === 'admin' ? 'default' : 
                                collaborator.role === 'editor' ? 'secondary' : 
                                'outline'
                              } 
                              className="text-xs"
                            >
                              {collaborator.role}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground">{collaborator.account.email}</p>
                        </div>
                      </div>
                      {canModifyThisUser ? (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {/* Only owners can promote to admin or demote admins */}
                            {isOwner && (
                              <DropdownMenuItem 
                                onClick={() => updateRoleMutation.mutate({ 
                                  userId: collaborator.account_id, 
                                  role: collaborator.role === 'admin' ? 'editor' : 'admin' 
                                })}
                              >
                                {collaborator.role === 'admin' ? 'Make Editor' : 'Make Admin'}
                              </DropdownMenuItem>
                            )}
                            {/* Anyone with canManageMembers can change editor/viewer roles */}
                            {collaborator.role !== 'admin' && collaborator.role !== 'viewer' && (
                              <DropdownMenuItem 
                                onClick={() => updateRoleMutation.mutate({ 
                                  userId: collaborator.account_id, 
                                  role: 'viewer' 
                                })}
                              >
                                Make Viewer
                              </DropdownMenuItem>
                            )}
                            {collaborator.role !== 'admin' && collaborator.role !== 'editor' && (
                              <DropdownMenuItem 
                                onClick={() => updateRoleMutation.mutate({ 
                                  userId: collaborator.account_id, 
                                  role: 'editor' 
                                })}
                              >
                                Make Editor
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem 
                              className="text-destructive"
                              onClick={() => removeMutation.mutate(collaborator.account_id)}
                            >
                              Remove Member
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      ) : (
                        <div className="w-9 h-9" />
                      )}
                    </div>
                  );
                })}
              </div>
            )}
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

        {/* AI Models */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              AI Models
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">Configured Models</h4>
                <p className="text-sm text-muted-foreground">{userModels.length} models available</p>
              </div>
              <Button size="sm" className="gap-2">
                <Plus className="h-4 w-4" />
                Add Model
              </Button>
            </div>

            <div className="space-y-3">
              {userModels.map((model) => (
                <div key={model.id} className="p-3 border rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <h5 className="font-medium text-sm">{model.name}</h5>
                      <Badge variant={model.status === 'active' ? 'default' : model.status === 'error' ? 'destructive' : 'secondary'}>
                        {model.status}
                      </Badge>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>Test Model</DropdownMenuItem>
                        <DropdownMenuItem>Edit Configuration</DropdownMenuItem>
                        <DropdownMenuItem className="text-destructive">
                          Remove Model
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <p className="text-xs text-muted-foreground">{model.provider} • {model.type}</p>
                  {model.endpoint && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Link className="h-3 w-3" />
                      {model.endpoint}
                    </div>
                  )}
                  {model.apiKey && (
                    <div className="flex items-center gap-2">
                      <Key className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">
                        {showApiKeys[model.id] ? model.apiKey : '••••••••••••••••'}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowApiKeys(prev => ({ ...prev, [model.id]: !prev[model.id] }))}
                      >
                        {showApiKeys[model.id] ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <div>
                  <span className="text-sm font-medium">Email Notifications</span>
                  <p className="text-sm text-muted-foreground">Receive updates via email</p>
                </div>
              </div>
              <Switch 
                checked={notifications.email}
                onCheckedChange={(checked) => setNotifications(prev => ({ ...prev, email: checked }))}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Smartphone className="h-4 w-4 text-muted-foreground" />
                <div>
                  <span className="text-sm font-medium">Push Notifications</span>
                  <p className="text-sm text-muted-foreground">Browser push notifications</p>
                </div>
              </div>
              <Switch 
                checked={notifications.push}
                onCheckedChange={(checked) => setNotifications(prev => ({ ...prev, push: checked }))}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                <div>
                  <span className="text-sm font-medium">System Alerts</span>
                  <p className="text-sm text-muted-foreground">Critical system notifications</p>
                </div>
              </div>
              <Switch 
                checked={notifications.alerts}
                onCheckedChange={(checked) => setNotifications(prev => ({ ...prev, alerts: checked }))}
              />
            </div>
          </CardContent>
        </Card>

        {/* Performance Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-sm font-medium">Auto Optimization</span>
                <p className="text-sm text-muted-foreground">Automatically optimize performance</p>
              </div>
              <Switch 
                checked={performance.autoOptimization}
                onCheckedChange={(checked) => setPerformance(prev => ({ ...prev, autoOptimization: checked }))}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-sm font-medium">Cost Optimization</span>
                <p className="text-sm text-muted-foreground">Optimize for cost efficiency</p>
              </div>
              <Switch 
                checked={performance.costOptimization}
                onCheckedChange={(checked) => setPerformance(prev => ({ ...prev, costOptimization: checked }))}
              />
            </div>

          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Settings;