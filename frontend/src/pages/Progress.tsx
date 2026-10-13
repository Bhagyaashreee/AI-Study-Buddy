import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Award,
  FileText,
  HelpCircle,
  Layers,
  RotateCw,
  TrendingUp,
  Calendar,
  CheckCircle2
} from 'lucide-react';
import { api, ApiError } from '../services/api';
import { StudyProgressResponse, ActiveTab } from '../types';
import { StatusBadge } from '../components/StatusBadge';

interface ProgressProps {
  onNavigate: (tab: ActiveTab) => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void;
}

export const Progress: React.FC<ProgressProps> = ({ onNavigate, showToast }) => {
  const [data, setData] = useState<StudyProgressResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchProgress = async () => {
    try {
      setLoading(true);
      const res = await api.getProgressSummary();
      setData(res);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to load progress analytics.';
      showToast('error', msg, 'Error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProgress();
  }, []);

  // Compute SVG coordinates for Performance History Chart
  const renderTrendChart = () => {
    const history = data?.performance_history || [];
    if (history.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: '3.5rem 1rem', color: 'var(--text-muted)' }}>
          <TrendingUp size={36} style={{ opacity: 0.35, marginBottom: '0.75rem' }} />
          <h4 style={{ marginBottom: '0.35rem' }}>No quiz attempts recorded yet.</h4>
          <p style={{ fontSize: '0.84rem', maxWidth: '360px', margin: '0 auto 1.25rem auto' }}>
            Take practice quizzes to build your historical performance curve.
          </p>
          <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('quizzes')}>
            Start a Practice Quiz
          </button>
        </div>
      );
    }

    const svgWidth = 720;
    const svgHeight = 220;
    const padding = { top: 20, right: 30, bottom: 35, left: 45 };

    const width = svgWidth - padding.left - padding.right;
    const height = svgHeight - padding.top - padding.bottom;

    const points = history.map((item, idx) => {
      const x = padding.left + (history.length === 1 ? width / 2 : (idx / (history.length - 1)) * width);
      const y = padding.top + height - (item.percentage / 100) * height;
      return { x, y, percentage: item.percentage, title: item.quiz_title, date: item.completed_at };
    });

    const pathD = points.reduce((acc, pt, idx) => {
      return idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
    }, '');

    // Area fill under path
    const areaD = points.length > 1
      ? `${pathD} L ${points[points.length - 1].x} ${padding.top + height} L ${points[0].x} ${padding.top + height} Z`
      : '';

    return (
      <div style={{ width: '100%', overflowX: 'auto' }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          style={{ width: '100%', height: 'auto', minWidth: '500px' }}
        >
          {/* Gradient Definition */}
          <defs>
            <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary-600)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="var(--primary-600)" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines & Y-axis labels */}
          {[0, 25, 50, 75, 100].map((pct) => {
            const y = padding.top + height - (pct / 100) * height;
            return (
              <g key={pct}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={svgWidth - padding.right}
                  y2={y}
                  stroke="rgba(255, 255, 255, 0.06)"
                  strokeDasharray="4 4"
                />
                <text
                  x={padding.left - 10}
                  y={y + 4}
                  fill="var(--text-dim)"
                  fontSize="11"
                  textAnchor="end"
                  fontFamily="var(--font-mono)"
                >
                  {pct}%
                </text>
              </g>
            );
          })}

          {/* Area under curve */}
          {areaD && <path d={areaD} fill="url(#areaGradient)" />}

          {/* Curve line */}
          <path
            d={pathD}
            fill="none"
            stroke="var(--primary-500)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data Points */}
          {points.map((pt, idx) => (
            <g key={idx}>
              <circle
                cx={pt.x}
                cy={pt.y}
                r="5"
                fill="var(--bg-app)"
                stroke="var(--primary-400)"
                strokeWidth="2.5"
              />
              <text
                x={pt.x}
                y={pt.y - 10}
                fill="var(--text-main)"
                fontSize="11"
                fontWeight="700"
                textAnchor="middle"
                fontFamily="var(--font-mono)"
              >
                {pt.percentage.toFixed(0)}%
              </text>
              <text
                x={pt.x}
                y={padding.top + height + 18}
                fill="var(--text-dim)"
                fontSize="10"
                textAnchor="middle"
              >
                Attempt {idx + 1}
              </text>
            </g>
          ))}
        </svg>
      </div>
    );
  };

  return (
    <div className="page-wrapper">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h3>Study Progress & Analytics</h3>
          <p style={{ fontSize: '0.84rem' }}>
            Real-time aggregate telemetry computed directly from SQLite database records
          </p>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={fetchProgress} disabled={loading}>
          <RotateCw size={14} className={loading ? 'spinner' : ''} /> Refresh Telemetry
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <span className="spinner" />
        </div>
      ) : (
        <>
          {/* Key Metrics Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600 }}>DOCUMENTS</span>
                <FileText size={16} color="var(--cyan-400)" />
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{data?.total_documents ?? 0}</div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Indexed materials</span>
            </div>

            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600 }}>QUIZZES CREATED</span>
                <HelpCircle size={16} color="var(--primary-400)" />
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{data?.total_quizzes ?? 0}</div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Unique exam sets</span>
            </div>

            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600 }}>COMPLETED ATTEMPTS</span>
                <CheckCircle2 size={16} color="var(--emerald-400)" />
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{data?.total_attempts ?? 0}</div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Finished submissions</span>
            </div>

            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600 }}>AVERAGE SCORE</span>
                <Award size={16} color="var(--emerald-400)" />
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--emerald-400)' }}>
                {(data?.average_quiz_score ?? 0).toFixed(1)}%
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Overall accuracy</span>
            </div>

            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600 }}>FLASHCARDS DUE</span>
                <Layers size={16} color="var(--amber-400)" />
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: (data?.cards_due_for_review ?? 0) > 0 ? 'var(--amber-400)' : 'var(--text-main)' }}>
                {data?.cards_due_for_review ?? 0}
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>of {data?.total_flashcards ?? 0} total cards</span>
            </div>
          </div>

          {/* Quiz Performance Over Time Chart */}
          <div className="card" style={{ marginBottom: '2rem', padding: '1.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', marginBottom: '0.2rem' }}>Quiz Performance Over Time</h3>
                <p style={{ fontSize: '0.82rem' }}>Chronological test accuracy percentage trend</p>
              </div>
              <span className="badge badge-primary">Accuracy (%)</span>
            </div>

            {renderTrendChart()}
          </div>

          {/* Recent Attempts Table */}
          <div className="card" style={{ padding: '1.75rem' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '0.35rem' }}>Recent Quiz Attempts Log</h3>
            <p style={{ fontSize: '0.82rem', marginBottom: '1.25rem' }}>
              Detailed breakdown of recent quiz submissions and grades
            </p>

            {data?.recent_attempts && data.recent_attempts.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-card)', color: 'var(--text-dim)', fontSize: '0.78rem' }}>
                      <th style={{ padding: '0.75rem 1rem' }}>QUIZ TITLE</th>
                      <th style={{ padding: '0.75rem 1rem' }}>DIFFICULTY</th>
                      <th style={{ padding: '0.75rem 1rem' }}>SCORE</th>
                      <th style={{ padding: '0.75rem 1rem' }}>PERCENTAGE</th>
                      <th style={{ padding: '0.75rem 1rem' }}>DATE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_attempts.map((att) => (
                      <tr
                        key={att.attempt_id}
                        style={{ borderBottom: '1px solid var(--border-subtle)' }}
                      >
                        <td style={{ padding: '0.9rem 1rem', fontWeight: 600, color: 'var(--text-main)' }}>
                          {att.quiz_title}
                        </td>
                        <td style={{ padding: '0.9rem 1rem' }}>
                          <StatusBadge status={att.difficulty} />
                        </td>
                        <td style={{ padding: '0.9rem 1rem' }}>
                          {att.score} / {att.total_questions}
                        </td>
                        <td style={{ padding: '0.9rem 1rem', fontWeight: 700, color: att.percentage >= 70 ? 'var(--emerald-400)' : 'var(--amber-400)' }}>
                          {att.percentage.toFixed(0)}%
                        </td>
                        <td style={{ padding: '0.9rem 1rem', color: 'var(--text-dim)', fontSize: '0.82rem' }}>
                          {new Date(att.completed_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-muted)' }}>
                No completed attempts recorded. Complete a quiz to view telemetry here.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
