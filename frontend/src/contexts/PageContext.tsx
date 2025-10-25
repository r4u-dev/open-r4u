import { createContext, useContext, useState, ReactNode } from 'react';

interface PageContextType {
  pageTitle: string | null;
  setPageTitle: (title: string | null) => void;
}

const PageContext = createContext<PageContextType | undefined>(undefined);

export const usePage = () => {
  const context = useContext(PageContext);
  if (context === undefined) {
    // Return a default context instead of throwing an error
    return { pageTitle: null, setPageTitle: () => {} };
  }
  return context;
};

interface PageProviderProps {
  children: ReactNode;
}

export const PageProvider = ({ children }: PageProviderProps) => {
  const [pageTitle, setPageTitle] = useState<string | null>(null);

  return (
    <PageContext.Provider value={{ pageTitle, setPageTitle }}>
      {children}
    </PageContext.Provider>
  );
};
