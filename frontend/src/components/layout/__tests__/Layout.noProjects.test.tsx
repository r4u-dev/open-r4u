import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import Layout from '../Layout';
import React from 'react';

// Mock the Outlet component since we're testing layout integration
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    Outlet: () => <div data-testid="main-content">Main Content</div>,
    useLocation: () => ({ pathname: '/' })
  };
});

// Mock the ProjectContext with no projects
vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    hasNoProjects: true,
    isLoading: false,
    projects: [],
    activeProject: null,
    error: null,
    refetchProjects: vi.fn(),
    addProject: vi.fn(),
    switchProject: vi.fn(),
  }),
  ProjectProvider: ({ children }: { children: React.ReactNode }) => children,
}));

describe('Layout - No Projects Modal', () => {
  it('should show no projects modal when there are no projects', async () => {
    render(<Layout />);

    // Wait for the modal to appear
    await waitFor(() => {
      expect(screen.getByText('Welcome to R4U!')).toBeInTheDocument();
    });

    // Check that the modal content is displayed
    expect(screen.getByText("A project is required to continue. Let's create your first project to get started with AI system management and optimization.")).toBeInTheDocument();
    expect(screen.getByLabelText('Project Name *')).toBeInTheDocument();
    expect(screen.getByText('Create Your First Project')).toBeInTheDocument();
    // Verify description field is not present
    expect(screen.queryByLabelText('Description')).not.toBeInTheDocument();
  });
});
