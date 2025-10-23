import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "@/components/theme-provider";
import Layout from "./components/layout/Layout";
import Dashboard from "./pages/Dashboard";
import MetricDetails from "./pages/MetricDetails";
import Tasks from "./pages/Tasks";
import TaskDetail from "./pages/TaskDetail";
import EvaluationDetail from "./pages/EvaluationDetail";
import CreateTask from "./pages/CreateTask";
import Traces from "./pages/Traces";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";
import { ProjectProvider } from "./contexts/ProjectContext";

const queryClient = new QueryClient();

const App = () => (
    <QueryClientProvider client={queryClient}>
        <ThemeProvider>
            <TooltipProvider>
                <Toaster />
                <ProjectProvider>
                        <BrowserRouter
                            future={{
                                v7_startTransition: true,
                                v7_relativeSplatPath: true,
                            }}
                        >
                            <Routes>
                                {/* Main application routes */}
                                <Route path="/" element={<Layout />}>
                                    <Route index element={<Dashboard />} />
                                    <Route
                                        path="metrics/:metricId"
                                        element={<MetricDetails />}
                                    />
                                    <Route path="tasks" element={<Tasks />} />
                                    <Route
                                        path="tasks/:taskId"
                                        element={<TaskDetail />}
                                    />
                                    <Route
                                        path="evaluations/:evaluationId"
                                        element={<EvaluationDetail />}
                                    />
                                    <Route
                                        path="tasks/new"
                                        element={<CreateTask />}
                                    />
                                    <Route
                                        path="traces"
                                        element={<Traces />}
                                    />
                                    <Route
                                        path="settings"
                                        element={<Settings />}
                                    />
                                </Route>
                                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                                <Route path="*" element={<NotFound />} />
                            </Routes>
                        </BrowserRouter>
                    </ProjectProvider>
            </TooltipProvider>
        </ThemeProvider>
    </QueryClientProvider>
);

export default App;
