import React, { useState, useEffect, useCallback } from 'react';
import { api } from './services/api';
import {
  ActiveTab,
  HealthResponse,
  OllamaStatusResponse,
  ToastNotification
} from './types';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ToastContainer } from './components/Toast';

import { Dashboard } from './pages/Dashboard';
import { Documents } from './pages/Documents';
import { Chat } from './pages/Chat';
import { Quizzes } from './pages/Quizzes';
import { Flashcards } from './pages/Flashcards';
import { Progress } from './pages/Progress';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard');
  const [targetDocId, setTargetDocId] = useState<number | null>(null);

  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);

  // System Health state
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatusResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(false);

  // Due flashcards count
  const [cardsDueCount, setCardsDueCount] = useState<number>(0);

  // Toasts
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  const addToast = useCallback((
    type: 'success' | 'error' | 'warning' | 'info',
    message: string,
    title?: string
  ) => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, type, message, title }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Fetch health and Ollama status
  const checkSystemHealth = useCallback(async () => {
    setLoadingHealth(true);
    try {
      const [hRes, oRes] = await Promise.allSettled([
        api.getHealth(),
        api.getOllamaStatus(),
      ]);

      if (hRes.status === 'fulfilled') {
        setHealth(hRes.value);
      } else {
        setHealth(null);
      }

      if (oRes.status === 'fulfilled') {
        setOllamaStatus(oRes.value);
      } else {
        setOllamaStatus(null);
      }
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  // Fetch due count
  const checkDueCount = useCallback(async () => {
    try {
      const dueRes = await api.getDueFlashcards();
      setCardsDueCount(dueRes.total_cards);
    } catch {
      // Ignore if offline
    }
  }, []);

  useEffect(() => {
    checkSystemHealth();
    checkDueCount();

    // Periodic heartbeat every 30 seconds
    const interval = setInterval(() => {
      checkSystemHealth();
      checkDueCount();
    }, 30000);

    return () => clearInterval(interval);
  }, [checkSystemHealth, checkDueCount]);

  const handleNavigate = (tab: ActiveTab, docId?: number) => {
    if (docId !== undefined) {
      setTargetDocId(docId);
    } else {
      setTargetDocId(null);
    }
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="app-container">
      {/* Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => handleNavigate(tab)}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        cardsDueCount={cardsDueCount}
        health={health}
        ollamaStatus={ollamaStatus}
        loadingHealth={loadingHealth}
      />

      {/* Main Content Area */}
      <div className="main-content">
        <Header
          activeTab={activeTab}
          mobileOpen={mobileOpen}
          setMobileOpen={setMobileOpen}
          health={health}
          ollamaStatus={ollamaStatus}
          loadingHealth={loadingHealth}
          onRefreshHealth={() => {
            checkSystemHealth();
            checkDueCount();
          }}
        />

        {/* View Routing */}
        <main style={{ flex: 1 }}>
          {activeTab === 'dashboard' && (
            <Dashboard
              onNavigate={handleNavigate}
              health={health}
              ollamaStatus={ollamaStatus}
              loadingHealth={loadingHealth}
              onRefreshHealth={() => {
                checkSystemHealth();
                checkDueCount();
              }}
            />
          )}

          {activeTab === 'documents' && (
            <Documents
              onNavigate={handleNavigate}
              showToast={addToast}
            />
          )}

          {activeTab === 'chat' && (
            <Chat
              initialDocId={targetDocId}
              onNavigate={handleNavigate}
              showToast={addToast}
            />
          )}

          {activeTab === 'quizzes' && (
            <Quizzes
              initialDocId={targetDocId}
              onNavigate={handleNavigate}
              showToast={addToast}
            />
          )}

          {activeTab === 'flashcards' && (
            <Flashcards
              initialDocId={targetDocId}
              onNavigate={handleNavigate}
              showToast={addToast}
              onRefreshDueCount={checkDueCount}
            />
          )}

          {activeTab === 'progress' && (
            <Progress
              onNavigate={handleNavigate}
              showToast={addToast}
            />
          )}
        </main>
      </div>

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </div>
  );
};

export default App;
