import React from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ShortlistWorkspace from './ShortlistWorkspace';

const client = new QueryClient({defaultOptions: {queries: {retry: false, staleTime: Infinity}}});
createRoot(document.getElementById('root')!).render(
  <React.StrictMode><QueryClientProvider client={client}><ShortlistWorkspace/></QueryClientProvider></React.StrictMode>
);
