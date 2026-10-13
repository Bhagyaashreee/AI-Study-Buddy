import React from 'react';
import { Menu, RefreshCw, Server, Cpu, CheckCircle2, AlertCircle } from 'lucide-react';
import { ActiveTab, HealthResponse, OllamaStatusResponse } from '../types';

interface HeaderProps {
  activeTab: ActiveTab;
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
  health: HealthResponse | null;
  ollamaStatus: OllamaStatusResponse | null;
  loadingHealth: boolean;
  onRefreshHealth: () => void;
}

const titles: Record<ActiveTab, { title: string; subtitle: string }> = {
  dashboard: { title: 'Study Dashboard', subtitle: 'Overview of your learning progress and system status' },
  documents: { title: 'Document Vault', subtitle: 'Upload and manage PDF notes, slides, and textbooks' },
  chat: { title: 'RAG Study Chat', subtitle: 'Chat with your uploaded materials backed by page citations' },
  quizzes: { title: 'Quiz Center', subtitle: 'Generate, solve, and analyze multiple-choice practice exams' },
  flashcards: { title: 'Spaced Flashcards', subtitle: 'Reinforce memory with active recall and interval schedules' },
  progress: { title: 'Study Analytics', subtitle: 'Visual metrics, quiz accuracy, and retention tracking' },
};

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  mobileOpen,
  setMobileOpen,
  health,
  ollamaStatus,
  loadingHealth,
  onRefreshHealth,
}) => {
  const current = titles[activeTab] || { title: 'AI Study Buddy', subtitle: '' };

  const isServerHealthy = health?.status === 'healthy';

  let ollamaState: 'loading' | 'ready' | 'missing' | 'offline' = 'loading';
  if (!loadingHealth || ollamaStatus) {
    if (ollamaStatus?.status === 'ready' || (ollamaStatus?.server_reachable && ollamaStatus?.model_installed)) {
      ollamaState = 'ready';
    } else if (ollamaStatus?.status === 'model_missing' || (ollamaStatus?.server_reachable && !ollamaStatus?.model_installed)) {
      ollamaState = 'missing';
    } else {
      ollamaState = 'offline';
    }
  }

  const ollamaStyles = {
    ready: {
      bg: 'rgba(52, 211, 153, 0.12)',
      border: '1px solid rgba(52, 211, 153, 0.3)',
      color: 'var(--emerald-400)',
      label: 'llama3.2:3b (Ready)',
      icon: <CheckCircle2 size={13} />,
      title: 'Ollama local inference engine is ready and model is installed.',
    },
    missing: {
      bg: 'rgba(251, 191, 36, 0.12)',
      border: '1px solid rgba(251, 191, 36, 0.3)',
      color: 'var(--amber-400)',
      label: 'llama3.2:3b (Missing)',
      icon: <AlertCircle size={13} />,
      title: 'Ollama is online, but llama3.2:3b is not pulled yet (run: ollama pull llama3.2:3b).',
    },
    offline: {
      bg: 'rgba(251, 113, 133, 0.12)',
      border: '1px solid rgba(251, 113, 133, 0.3)',
      color: 'var(--rose-400)',
      label: 'llama3.2:3b (Offline)',
      icon: <AlertCircle size={13} />,
      title: 'Ollama service is unreachable at http://localhost:11434. Ensure Ollama is running.',
    },
    loading: {
      bg: 'rgba(255, 255, 255, 0.05)',
      border: '1px solid var(--border-subtle)',
      color: 'var(--text-dim)',
      label: 'llama3.2:3b (Checking...)',
      icon: <span className="spinner" style={{ width: '11px', height: '11px' }} />,
      title: 'Checking Ollama status...',
    },
  }[ollamaState];

  return (
    <header
      style={{
        padding: '1.1rem 2rem',
        backgroundColor: 'var(--bg-glass)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        borderBottom: '1px solid var(--border-card)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button
          className="btn btn-outline btn-sm"
          style={{ display: 'inline-flex' }}
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle mobile menu"
        >
          <Menu size={18} />
        </button>

        <div>
          <h2>{current.title}</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {current.subtitle}
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        {/* Backend status pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            padding: '0.35rem 0.75rem',
            borderRadius: 'var(--radius-full)',
            fontSize: '0.78rem',
            fontWeight: 500,
            background: loadingHealth && !health
              ? 'rgba(255, 255, 255, 0.05)'
              : isServerHealthy
              ? 'rgba(52, 211, 153, 0.1)'
              : 'rgba(251, 113, 133, 0.1)',
            border: loadingHealth && !health
              ? '1px solid var(--border-subtle)'
              : isServerHealthy
              ? '1px solid rgba(52, 211, 153, 0.25)'
              : '1px solid rgba(251, 113, 133, 0.25)',
            color: loadingHealth && !health
              ? 'var(--text-dim)'
              : isServerHealthy
              ? 'var(--emerald-400)'
              : 'var(--rose-400)',
          }}
          title={health ? `FastAPI: ${health.status} (${health.environment})` : 'Connecting to backend...'}
        >
          <Server size={14} />
          <span>Backend</span>
          {loadingHealth && !health ? (
            <span className="spinner" style={{ width: '11px', height: '11px' }} />
          ) : isServerHealthy ? (
            <CheckCircle2 size={13} />
          ) : (
            <AlertCircle size={13} />
          )}
        </div>

        {/* Ollama local model status pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            padding: '0.35rem 0.75rem',
            borderRadius: 'var(--radius-full)',
            fontSize: '0.78rem',
            fontWeight: 500,
            background: ollamaStyles.bg,
            border: ollamaStyles.border,
            color: ollamaStyles.color,
          }}
          title={ollamaStyles.title}
        >
          <Cpu size={14} />
          <span>{ollamaStyles.label}</span>
          {ollamaStyles.icon}
        </div>

        {/* Refresh button */}
        <button
          className="btn btn-outline btn-sm"
          onClick={onRefreshHealth}
          disabled={loadingHealth}
          title="Refresh connection status"
          style={{ padding: '0.45rem 0.6rem' }}
        >
          <RefreshCw size={14} className={loadingHealth ? 'spinner' : ''} />
        </button>
      </div>
    </header>
  );
};
