import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import Layout from '../Layout';
import { Project } from '@/lib/types/project';
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

// Default project for testing
const defaultProject: Project = {
  id: 'test-project-1',
  name: 'Test Project',
  owner_id: 'test-user-1',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

// Default project context mock
const defaultProjectContext = {
  projects: [defaultProject],
  activeProject: defaultProject,
  isLoading: false,
  error: null,
  hasNoProjects: false,
  refetchProjects: vi.fn(),
  addProject: vi.fn(),
  switchProject: vi.fn(),
};

// Mock the ProjectContext with default project
vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => defaultProjectContext,
  ProjectProvider: ({ children }: { children: React.ReactNode }) => children,
}));

describe('Layout Integration', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  it('should render the layout with header and sidebar', async () => {
    render(<Layout />);

    // Check if the header is rendered
    const header = screen.getByRole('banner');
    expect(header).toBeInTheDocument();

    // Check if the main content is rendered
    const mainContent = screen.getByTestId('main-content');
    expect(mainContent).toBeInTheDocument();
  });

  // Note: The "no projects modal" test is moved to a separate test file
  // since it requires a different mock setup that conflicts with the default project mock
});