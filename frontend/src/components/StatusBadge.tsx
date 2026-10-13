import React from 'react';

interface StatusBadgeProps {
  status: string;
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral';
  pulse?: boolean;
  label?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  pulse = false,
  label,
}) => {
  // Infer variant if not provided
  let computedVariant = variant;
  if (!computedVariant) {
    const s = status.toLowerCase();
    if (s === 'healthy' || s === 'available' || s === 'connected' || s === 'processed' || s === 'easy') {
      computedVariant = 'success';
    } else if (s === 'medium' || s === 'degraded' || s === 'processing') {
      computedVariant = 'warning';
    } else if (s === 'hard' || s === 'unhealthy' || s === 'unavailable' || s === 'disconnected' || s === 'failed') {
      computedVariant = 'danger';
    } else {
      computedVariant = 'neutral';
    }
  }

  return (
    <span className={`badge badge-${computedVariant}`}>
      {pulse && <span className="pulse-dot" />}
      <span>{label || status}</span>
    </span>
  );
};
