import React, { FC, ReactElement, ReactNode } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";

// Create a new QueryClient instance for each test run
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries for tests to fail faster
      },
    },
    // Silence console errors in tests
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {},
    },
  });

interface TestProvidersProps {
  children: ReactNode;
}

const TestProviders: FC<TestProvidersProps> = ({ children }) => {
  const testQueryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={testQueryClient}>
      <BrowserRouter>
        <ProjectProvider>
          <TooltipProvider>
            {children}
            <Toaster />
          </TooltipProvider>
        </ProjectProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) => render(ui, { wrapper: TestProviders, ...options });

// Re-export everything from testing-library
export * from "@testing-library/react";

// Override the render method with our custom one
export { customRender as render };
