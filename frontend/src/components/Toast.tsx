import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';
import { ToastNotification } from '../types';

interface ToastContainerProps {
  toasts: ToastNotification[];
  removeToast: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, removeToast }) => {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" role="region" aria-live="polite">
      {toasts.map((toast) => {
        let Icon = Info;
        let borderColor = 'var(--border-card)';
        let iconColor = 'var(--primary-400)';

        if (toast.type === 'success') {
          Icon = CheckCircle2;
          borderColor = 'rgba(52, 211, 153, 0.4)';
          iconColor = 'var(--emerald-400)';
        } else if (toast.type === 'error') {
          Icon = AlertCircle;
          borderColor = 'rgba(251, 113, 133, 0.4)';
          iconColor = 'var(--rose-400)';
        } else if (toast.type === 'warning') {
          Icon = AlertTriangle;
          borderColor = 'rgba(251, 191, 36, 0.4)';
          iconColor = 'var(--amber-400)';
        }

        return (
          <div
            key={toast.id}
            className="toast"
            style={{ borderLeft: `3px solid ${iconColor}`, borderColor }}
          >
            <Icon size={18} color={iconColor} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              {toast.title && (
                <div style={{ fontWeight: 600, fontSize: '0.86rem', color: 'var(--text-main)', marginBottom: '0.15rem' }}>
                  {toast.title}
                </div>
              )}
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', wordBreak: 'break-word' }}>
                {toast.message}
              </div>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-dim)',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center',
              }}
              aria-label="Dismiss toast"
            >
              <X size={15} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
