import React from 'react';
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  HelpCircle,
  Layers,
  BarChart3,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Database
} from 'lucide-react';
import { ActiveTab, HealthResponse, OllamaStatusResponse } from '../types';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
  cardsDueCount: number;
  health: HealthResponse | null;
  ollamaStatus: OllamaStatusResponse | null;
  loadingHealth: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  collapsed,
  setCollapsed,
  mobileOpen,
  setMobileOpen,
  cardsDueCount,
  health,
  ollamaStatus,
  loadingHealth,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'documents', label: 'My Documents', icon: FileText },
    { id: 'chat', label: 'AI Study Chat', icon: MessageSquare },
    { id: 'quizzes', label: 'Quiz Center', icon: HelpCircle },
    { id: 'flashcards', label: 'Flashcards', icon: Layers, badge: cardsDueCount > 0 ? cardsDueCount : undefined },
    { id: 'progress', label: 'Study Progress', icon: BarChart3 },
  ];

  const handleNavClick = (tabId: ActiveTab) => {
    setActiveTab(tabId);
    if (mobileOpen) setMobileOpen(false);
  };

  const isDbReady = health?.database.status === 'connected';

  let dbStatusLabel = 'Checking';
  let dbStatusColor = 'var(--text-dim)';
  if (!loadingHealth || health) {
    if (isDbReady) {
      dbStatusLabel = 'Online';
      dbStatusColor = 'var(--emerald-400)';
    } else {
      dbStatusLabel = 'Offline';
      dbStatusColor = 'var(--rose-400)';
    }
  }

  let ollamaStatusLabel = 'Checking';
  let ollamaStatusColor = 'var(--text-dim)';
  if (!loadingHealth || ollamaStatus) {
    if (ollamaStatus?.status === 'ready' || (ollamaStatus?.server_reachable && ollamaStatus?.model_installed)) {
      ollamaStatusLabel = 'Ready';
      ollamaStatusColor = 'var(--emerald-400)';
    } else if (ollamaStatus?.status === 'model_missing' || (ollamaStatus?.server_reachable && !ollamaStatus?.model_installed)) {
      ollamaStatusLabel = 'Missing';
      ollamaStatusColor = 'var(--amber-400)';
    } else {
      ollamaStatusLabel = 'Offline';
      ollamaStatusColor = 'var(--rose-400)';
    }
  }

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="modal-backdrop"
          style={{ zIndex: 90 }}
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        style={{
          width: collapsed ? '80px' : '260px',
          minWidth: collapsed ? '80px' : '260px',
          height: '100vh',
          backgroundColor: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-card)',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width var(--transition-normal)',
          zIndex: 95,
          position: mobileOpen ? 'fixed' : 'relative',
          left: 0,
          top: 0,
        }}
      >
        {/* Brand Header */}
        <div
          style={{
            padding: collapsed ? '1.25rem 0.5rem' : '1.25rem 1.25rem',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'space-between',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', overflow: 'hidden' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: 'var(--radius-md)',
                background: 'linear-gradient(135deg, var(--primary-600) 0%, var(--indigo-500) 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 12px var(--primary-glow)',
                flexShrink: 0,
              }}
            >
              <Sparkles size={20} color="#ffffff" />
            </div>
            {!collapsed && (
              <div>
                <h1 style={{ fontSize: '1.05rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-main)', whiteSpace: 'nowrap' }}>
                  AI Study Buddy
                </h1>
                <p style={{ fontSize: '0.72rem', color: 'var(--primary-400)', fontWeight: 500 }}>
                  100% Local AI (₹0)
                </p>
              </div>
            )}
          </div>

          {!collapsed && (
            <button
              className="btn btn-outline btn-sm"
              style={{ padding: '0.3rem', borderRadius: 'var(--radius-sm)' }}
              onClick={() => setCollapsed(true)}
              title="Collapse sidebar"
            >
              <ChevronLeft size={16} />
            </button>
          )}
        </div>

        {/* Collapsed expand toggle */}
        {collapsed && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '0.5rem 0' }}>
            <button
              className="btn btn-outline btn-sm"
              style={{ padding: '0.3rem', borderRadius: 'var(--radius-sm)' }}
              onClick={() => setCollapsed(false)}
              title="Expand sidebar"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}

        {/* Navigation items */}
        <nav style={{ padding: '1rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.35rem', flex: 1, overflowY: 'auto' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id as ActiveTab)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.85rem',
                  padding: collapsed ? '0.75rem 0' : '0.75rem 1rem',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  borderRadius: 'var(--radius-md)',
                  border: isActive ? '1px solid var(--border-highlight)' : '1px solid transparent',
                  background: isActive ? 'rgba(124, 58, 237, 0.15)' : 'transparent',
                  color: isActive ? 'var(--primary-300)' : 'var(--text-muted)',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                  position: 'relative',
                  width: '100%',
                }}
                title={collapsed ? item.label : undefined}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                    e.currentTarget.style.color = 'var(--text-main)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = 'var(--text-muted)';
                  }
                }}
              >
                <Icon size={19} color={isActive ? 'var(--primary-400)' : 'currentColor'} />
                {!collapsed && (
                  <span style={{ flex: 1, textAlign: 'left', whiteSpace: 'nowrap' }}>
                    {item.label}
                  </span>
                )}
                {!collapsed && item.badge !== undefined && (
                  <span
                    style={{
                      background: 'var(--primary-600)',
                      color: '#ffffff',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      padding: '0.1rem 0.45rem',
                      borderRadius: 'var(--radius-full)',
                    }}
                  >
                    {item.badge}
                  </span>
                )}
                {collapsed && item.badge !== undefined && (
                  <span
                    style={{
                      position: 'absolute',
                      top: '4px',
                      right: '12px',
                      width: '8px',
                      height: '8px',
                      background: 'var(--primary-500)',
                      borderRadius: '50%',
                    }}
                  />
                )}
              </button>
            );
          })}
        </nav>

        {/* System Health Status Footer Card */}
        {!collapsed && (
          <div
            style={{
              padding: '1rem',
              margin: '0.75rem',
              backgroundColor: 'rgba(13, 16, 24, 0.8)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-card)',
              fontSize: '0.78rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                System Core
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Local</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
                  <Database size={13} /> SQLite DB
                </span>
                <span style={{ color: dbStatusColor, fontWeight: 600 }}>
                  {dbStatusLabel}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
                  <Cpu size={13} /> llama3.2:3b
                </span>
                <span style={{ color: ollamaStatusColor, fontWeight: 600 }}>
                  {ollamaStatusLabel}
                </span>
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
};
