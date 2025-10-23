# Open R4U Frontend

A modern AI system evaluation and monitoring platform built with React, TypeScript, and Vite. This frontend application provides comprehensive tools for managing AI tasks, evaluations, traces, and performance metrics with a beautiful, responsive interface.

## Tech Stack

### Core Framework
- **Vite** - Fast build tool and dev server
- **React 18** - UI library with modern features
- **TypeScript** - Type-safe JavaScript
- **React Router v6** - Client-side routing

### UI & Styling
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality component library
- **Radix UI** - Unstyled, accessible UI primitives
- **Lucide React** - Beautiful icon library
- **next-themes** - Theme management (light/dark mode)

### State Management & Data Fetching
- **TanStack Query** - Server state management
- **React Hook Form** - Form handling with validation
- **Zod** - Schema validation

### Charts & Visualization
- **Recharts** - Composable charting library

### Development Tools
- **ESLint** - Code linting
- **Vitest** - Unit testing framework
- **Testing Library** - React component testing
- **SWC** - Fast TypeScript/JavaScript compiler

## Requirements

- Node.js 18+ (LTS recommended)
- pnpm, npm, or yarn (examples use pnpm)

## Getting Started

1. Install dependencies
   - pnpm install
   - npm install
   - yarn
2. Start the dev server
   - pnpm dev
   - npm run dev
   - yarn dev

## Available Scripts

### Development
- `dev` - Start Vite development server (port 8080)
- `build` - Production build to `dist/`
- `build:dev` - Development-mode build
- `preview` - Preview the production build locally

### Code Quality
- `lint` - Run ESLint on the project
- `lint:fix` - Run ESLint and fix auto-fixable issues
- `type-check` - Run TypeScript type checking

### Testing
- `test` - Run tests in watch mode
- `test:run` - Run tests once
- `test:ui` - Run tests with UI interface
- `test:coverage` - Run tests with coverage report

### CI/CD & Deployment
- `ci:test` - Run full CI test suite (lint + type-check + test + build)
- `ci:build` - CI build command
- `test:ci` - Run tests in CI environment
- `deploy` - Deploy to production
- `setup-aws` - Setup AWS CloudFront deployment

### Security
- `audit` - Run npm audit for security vulnerabilities
- `audit:fix` - Fix security vulnerabilities automatically

### Examples
```bash
# Development
pnpm dev
pnpm build
pnpm preview

# Testing
pnpm test
pnpm test:run
pnpm test:coverage

# Code Quality
pnpm lint
pnpm lint:fix
pnpm type-check

# CI/CD
pnpm ci:test
pnpm deploy
```

## Testing Framework

This project uses **Vitest** as the testing framework with **Testing Library** for React component testing.

### Running Tests

```bash
# Run tests in watch mode (development)
pnpm test

# Run tests once (CI)
pnpm test:run

# Run tests with UI interface
pnpm test:ui

# Run tests with coverage report
pnpm test:coverage
```

### Test Structure

- Tests are located alongside components with `__tests__/` folders
- Test utilities are in `src/test/`
- Configuration is in `vitest.config.ts`

### Writing Tests

- Use `@testing-library/react` for component testing
- Use `@testing-library/user-event` for user interactions
- Use `@testing-library/jest-dom` for custom matchers

## Development Guide

### Architecture
- **Component-based architecture** with feature-specific folders
- **Context-based state management** for global state (ProjectContext)
- **Custom hooks** for reusable logic (forms, themes, toasts)
- **Service layer** for API interactions

### UI Components
- **shadcn/ui components** live under `src/components/ui/` and are composed from Radix UI primitives
- **Tailwind CSS** for styling with utility-first approach
- **Class variance authority** and `clsx` for conditional styling
- **Theme support** with light/dark mode using `next-themes`

### Routing & Navigation
- **React Router v6** handles client-side routing
- **Layout component** provides consistent structure across pages
- **Protected routes** and navigation state management

### Data Management
- **TanStack Query** for server state management and caching
- **React Hook Form** with **Zod validation** for form handling
- **TypeScript** for type safety across the application

### Build & Deployment
- **Vite** for fast development and optimized production builds
- **Manual chunk splitting** for optimal loading performance
- **AWS CloudFront** deployment configuration
- **ESLint** and **TypeScript** for code quality


### Security
```bash
# Check for security vulnerabilities
pnpm audit

# Fix security issues automatically
pnpm audit:fix
```

## Code Quality Standards

### Linting
- **ESLint** with TypeScript support
- **React-specific rules** for hooks and best practices
- **Auto-fix** capability for common issues

```bash
pnpm lint       # Check code style and issues
pnpm lint:fix   # Auto-fix issues where possible
```

### Type Checking
```bash
pnpm type-check # Run TypeScript compiler checks
```

## Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Run** tests and linting: `pnpm ci:test`
5. **Commit** with descriptive messages
6. **Push** to your fork
7. **Submit** a pull request

## License

TBD
