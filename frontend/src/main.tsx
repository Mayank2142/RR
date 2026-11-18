import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter, Route, Routes} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import * as Tooltip from '@radix-ui/react-tooltip';
import App from './App';
import ShortlistWorkspace from './ShortlistWorkspace';
import './styles.css';
import './readability.css';
const queryClient=new QueryClient({defaultOptions:{queries:{staleTime:300000,retry:1}}});
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><Tooltip.Provider delayDuration={250}><BrowserRouter><Routes>
  <Route path="/" element={<ShortlistWorkspace/>}/>
  <Route path="/shortlist" element={<ShortlistWorkspace/>}/>
  <Route path="*" element={<App/>}/>
</Routes></BrowserRouter></Tooltip.Provider></QueryClientProvider></React.StrictMode>);
