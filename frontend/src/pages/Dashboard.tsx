import React, { useEffect, useState } from 'react';
import {
  FileText,
  HelpCircle,
  Layers,
  Award,
  Upload,
  MessageSquare,
  Play,
  RotateCw,
  Server,
  Cpu,
  AlertCircle,
  TrendingUp,
  ArrowRight
} from 'lucide-react';
import { api, ApiError } from '../services/api';
import { StudyProgressResponse, HealthResponse, OllamaStatusResponse, ActiveTab } from '../types';
import { StatusBadge } from '../components/StatusBadge';

interface DashboardProps {
  onNavigate: (tab: ActiveTab) => void;
  health: HealthResponse | null;
  ollamaStatus: OllamaStatusResponse | null;
  loadingHealth: boolean;
  onRefreshHealth: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  onNavigate,
  health,
  ollamaStatus,
  loadingHealth,
  onRefreshHealth,
}) => {
  const [progress, setProgress] = useState<StudyProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProgress = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getProgressSummary();
      setProgress(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Failed to load progress summary: ${err.message}`);
      } else {
        setError('Cannot reach FastAPI backend at ' + api.getBaseUrl());
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProgress();
  }, []);

  const isServerHealthy = health?.status === 'healthy';
  const isOllamaReady = ollamaStatus?.status === 'ready' || (ollamaStatus?.server_reachable && ollamaStatus?.model_installed);
  const isOllamaMissing = ollamaStatus?.status === 'model_missing' || (ollamaStatus?.server_reachable && !ollamaStatus?.model_installed);

  return (
    <div className="page-wrapper">
      {/* Backend & AI Connection Alert Banner if Degraded */}
      {!loadingHealth && (!isServerHealthy || !isOllamaReady) && (
        <div
          className="card"
          style={{
            marginBottom: '1.75rem',
            background: 'rgba(251, 191, 36, 0.08)',
            borderColor: 'rgba(251, 191, 36, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <AlertCircle size={22} color="var(--amber-400)" />
            <div>
              <h4 style={{ fontSize: '0.95rem', color: 'var(--amber-400)' }}>
                {!isServerHealthy
                  ? 'FastAPI Backend Disconnected'
                  : isOllamaMissing
                  ? 'Ollama Model Needs Download'
                  : 'Ollama Service Unreachable'}
              </h4>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                {!isServerHealthy
                  ? `Ensure uvicorn is running: .\\.venv\\Scripts\\uvicorn app.main:app --port 8000`
                  : isOllamaMissing
                  ? `Target model '${ollamaStatus?.target_model || 'llama3.2:3b'}' is missing. Pull it in terminal: ollama pull ${ollamaStatus?.target_model || 'llama3.2:3b'}`
                  : `Ensure Ollama is running at http://localhost:11434 (run: ollama serve).`}
              </p>
            </div>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => {
              fetchProgress();
              onRefreshHealth();
            }}
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Hero Welcome & Quick Actions */}
      <div
        className="card card-glow-top"
        style={{
          marginBottom: '2rem',
          padding: '2rem',
          background: 'linear-gradient(135deg, rgba(21, 25, 36, 0.9) 0%, rgba(15, 18, 26, 0.95) 100%)',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1.5rem' }}>
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span className="badge badge-primary">Zero-Cost AI Learning</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>• 100% Offline Capable</span>
            </div>
            <h1 style={{ fontSize: '1.75rem', marginBottom: '0.5rem' }}>
              Welcome back to AI Study Buddy
            </h1>
            <p style={{ maxWidth: '650px', fontSize: '0.92rem' }}>
              Upload your textbooks or lecture notes to chat with verified page citations, generate custom quizzes, and reinforce mastery with spaced repetition flashcards.
            </p>
          </div>

          {/* Quick Actions Grid */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            <button
              className="btn btn-primary"
              onClick={() => onNavigate('documents')}
              id="action-upload-notes"
            >
              <Upload size={16} /> Upload Notes
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => onNavigate('chat')}
              id="action-ask-ai"
            >
              <MessageSquare size={16} /> Ask AI
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => onNavigate('quizzes')}
              id="action-create-quiz"
            >
              <Play size={16} /> Practice Quiz
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => onNavigate('flashcards')}
              id="action-review-cards"
            >
              <RotateCw size={16} /> Review Cards
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        {/* Total Documents */}
        <div className="card" onClick={() => onNavigate('documents')} style={{ cursor: 'pointer' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600 }}>DOCUMENTS</span>
            <div style={{ padding: '0.45rem', borderRadius: 'var(--radius-md)', background: 'rgba(56, 189, 248, 0.12)', color: 'var(--cyan-400)' }}>
              <FileText size={18} />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '0.25rem' }}>
            {loading ? '—' : progress?.total_documents ?? 0}
          </div>
          <p style={{ fontSize: '0.78rem' }}>Uploaded PDF materials</p>
        </div>

        {/* Quizzes & Attempts */}
        <div className="card" onClick={() => onNavigate('quizzes')} style={{ cursor: 'pointer' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600 }}>QUIZZES & ATTEMPTS</span>
            <div style={{ padding: '0.45rem', borderRadius: 'var(--radius-md)', background: 'rgba(124, 58, 237, 0.14)', color: 'var(--primary-400)' }}>
              <HelpCircle size={18} />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '0.25rem' }}>
            {loading ? '—' : `${progress?.total_quizzes ?? 0} / ${progress?.total_attempts ?? 0}`}
          </div>
          <p style={{ fontSize: '0.78rem' }}>
            {progress?.total_attempts ?? 0} completed attempt{(progress?.total_attempts ?? 0) === 1 ? '' : 's'}
          </p>
        </div>

        {/* Average Quiz Score */}
        <div className="card" onClick={() => onNavigate('progress')} style={{ cursor: 'pointer' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600 }}>AVERAGE SCORE</span>
            <div style={{ padding: '0.45rem', borderRadius: 'var(--radius-md)', background: 'rgba(52, 211, 153, 0.12)', color: 'var(--emerald-400)' }}>
              <Award size={18} />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '0.25rem' }}>
            {loading ? '—' : `${(progress?.average_quiz_score ?? 0).toFixed(1)}%`}
          </div>
          <p style={{ fontSize: '0.78rem' }}>Overall test accuracy</p>
        </div>

        {/* Flashcards & Due */}
        <div className="card" onClick={() => onNavigate('flashcards')} style={{ cursor: 'pointer' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600 }}>FLASHCARDS DUE</span>
            <div style={{ padding: '0.45rem', borderRadius: 'var(--radius-md)', background: 'rgba(251, 191, 36, 0.12)', color: 'var(--amber-400)' }}>
              <Layers size={18} />
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span style={{ fontSize: '1.85rem', fontWeight: 800, color: (progress?.cards_due_for_review ?? 0) > 0 ? 'var(--amber-400)' : 'var(--text-main)' }}>
              {loading ? '—' : progress?.cards_due_for_review ?? 0}
            </span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>
              / {progress?.total_flashcards ?? 0} total
            </span>
          </div>
          <p style={{ fontSize: '0.78rem' }}>
            {(progress?.cards_due_for_review ?? 0) > 0 ? 'Cards awaiting review today' : 'All caught up!'}
          </p>
        </div>
      </div>

      {/* Activity & Performance Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Recent Quiz Activity */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3>Recent Quiz Activity</h3>
            <button className="btn btn-outline btn-sm" onClick={() => onNavigate('quizzes')}>
              View All <ArrowRight size={14} />
            </button>
          </div>

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
              <span className="spinner" />
            </div>
          ) : progress?.recent_attempts && progress.recent_attempts.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {progress.recent_attempts.slice(0, 4).map((att) => (
                <div
                  key={att.attempt_id}
                  style={{
                    padding: '0.85rem 1rem',
                    background: 'rgba(255, 255, 255, 0.02)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ minWidth: 0, flex: 1, marginRight: '1rem' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-main)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {att.quiz_title}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                      {new Date(att.completed_at).toLocaleDateString()} • {att.score}/{att.total_questions} questions correct
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <StatusBadge status={att.difficulty} />
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: att.percentage >= 70 ? 'var(--emerald-400)' : 'var(--amber-400)',
                      }}
                    >
                      {att.percentage.toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-muted)' }}>
              <HelpCircle size={32} style={{ opacity: 0.35, marginBottom: '0.75rem' }} />
              <p style={{ fontSize: '0.88rem', marginBottom: '1rem' }}>No quizzes taken yet.</p>
              <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('quizzes')}>
                Create Practice Quiz
              </button>
            </div>
          )}
        </div>

        {/* System Architecture Details */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3>Local AI System Status</h3>
            <span className="badge badge-success">Zero-Cost Offline</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.02)' }}>
              <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', background: 'rgba(124, 58, 237, 0.15)', color: 'var(--primary-400)' }}>
                <Cpu size={20} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>Ollama Local LLM</div>
                <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)' }}>
                  Model: {ollamaStatus?.target_model || 'llama3.2:3b'} (
                  {loadingHealth && !ollamaStatus
                    ? 'Checking...'
                    : isOllamaReady
                    ? 'Ready'
                    : isOllamaMissing
                    ? 'Model Missing'
                    : 'Offline'}
                  )
                </div>
              </div>
              <StatusBadge
                status={
                  loadingHealth && !ollamaStatus
                    ? 'Processing'
                    : isOllamaReady
                    ? 'Ready'
                    : isOllamaMissing
                    ? 'Warning'
                    : 'Offline'
                }
                label={
                  loadingHealth && !ollamaStatus
                    ? 'Checking'
                    : isOllamaReady
                    ? 'Ready'
                    : isOllamaMissing
                    ? 'Missing'
                    : 'Offline'
                }
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.02)' }}>
              <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', background: 'rgba(56, 189, 248, 0.12)', color: 'var(--cyan-400)' }}>
                <Server size={20} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>FastAPI Backend</div>
                <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)' }}>
                  Port: 8000 • Database: SQLite (local)
                </div>
              </div>
              <StatusBadge status={health?.database.status === 'connected' ? 'Connected' : 'Disconnected'} />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.02)' }}>
              <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', background: 'rgba(52, 211, 153, 0.12)', color: 'var(--emerald-400)' }}>
                <TrendingUp size={20} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>Vector Embeddings & FAISS</div>
                <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)' }}>
                  all-MiniLM-L6-v2 (384-dim) • Local Index
                </div>
              </div>
              <span className="badge badge-success">Optimized</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
