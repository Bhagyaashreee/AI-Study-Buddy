import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  MessageSquare,
  Sparkles,
  BookOpen,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  RotateCw,
  FileText,
  Clock,
  Layers,
  Check
} from 'lucide-react';
import { api, ApiError } from '../services/api';
import { DocumentResponse, ChatMessage, RAGSourceItem, ActiveTab } from '../types';

interface ChatProps {
  initialDocId?: number | null;
  onNavigate: (tab: ActiveTab) => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void;
}

export const Chat: React.FC<ChatProps> = ({ initialDocId, onNavigate, showToast }) => {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch uploaded documents
  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const res = await api.listDocuments();
        setDocuments(res.documents);
        if (initialDocId && res.documents.some((d) => d.id === initialDocId)) {
          setSelectedDocIds([initialDocId]);
        }
      } catch (err) {
        showToast('error', 'Failed to retrieve documents for chat.', 'Connection Error');
      }
    };
    fetchDocs();
  }, [initialDocId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const toggleDocSelection = (id: number) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const selectAllDocs = () => {
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(documents.map((d) => d.id));
    }
  };

  const handleSend = async (textToSend?: string) => {
    const question = (textToSend || inputText).trim();
    if (!question || loading) return;

    if (documents.length === 0) {
      showToast('warning', 'Please upload at least one PDF note before asking questions.', 'No Notes Found');
      return;
    }

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: question,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setLoading(true);

    try {
      const startTime = performance.now();
      const response = await api.askQuestion({
        question,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
        top_k: 4,
      });
      const duration = Math.round(performance.now() - startTime);

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: response.sources,
        duration_ms: response.duration_ms || duration,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error generating response from local LLM.';
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        sender: 'assistant',
        text: `Sorry, I encountered an error: ${msg}. Please ensure Ollama is running with llama3.2:3b.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        error: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
      showToast('error', msg, 'RAG Inference Error');
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (msgId: string) => {
    setExpandedSources((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const retryLastMessage = () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.sender === 'user');
    if (lastUserMsg) {
      handleSend(lastUserMsg.text);
    }
  };

  return (
    <div className="page-wrapper" style={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column', paddingBottom: '1.5rem' }}>
      {/* Document Scope Filter Bar */}
      <div
        className="card"
        style={{
          padding: '0.85rem 1.25rem',
          marginBottom: '1rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <BookOpen size={15} /> SEARCH SCOPE:
          </span>

          <button
            className={`btn btn-sm ${selectedDocIds.length === 0 ? 'btn-primary' : 'btn-outline'}`}
            onClick={selectAllDocs}
            style={{ fontSize: '0.76rem', padding: '0.25rem 0.65rem' }}
          >
            {selectedDocIds.length === 0 ? 'All Documents' : 'Select All'}
          </button>

          {documents.map((doc) => {
            const isSelected = selectedDocIds.includes(doc.id);
            return (
              <button
                key={doc.id}
                onClick={() => toggleDocSelection(doc.id)}
                className={`btn btn-sm ${isSelected ? 'btn-primary' : 'btn-outline'}`}
                style={{
                  fontSize: '0.76rem',
                  padding: '0.25rem 0.65rem',
                  maxWidth: '180px',
                  textOverflow: 'ellipsis',
                  overflow: 'hidden',
                  whiteSpace: 'nowrap',
                }}
                title={doc.original_filename}
              >
                {isSelected && <Check size={12} />}
                {doc.original_filename}
              </button>
            );
          })}
        </div>

        {documents.length === 0 && (
          <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('documents')}>
            <FileText size={14} /> Upload Notes First
          </button>
        )}
      </div>

      {/* Messages Container */}
      <div
        className="card"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
          marginBottom: '1rem',
          background: 'rgba(15, 18, 26, 0.7)',
        }}
      >
        {messages.length === 0 ? (
          <div style={{ margin: 'auto', textAlign: 'center', maxWidth: '520px', padding: '2rem 1rem' }}>
            <div
              style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, rgba(124, 58, 237, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1.25rem auto',
                color: 'var(--primary-400)',
              }}
            >
              <Sparkles size={28} />
            </div>
            <h3 style={{ fontSize: '1.35rem', marginBottom: '0.5rem' }}>
              Ask Questions with Grounded Citations
            </h3>
            <p style={{ fontSize: '0.88rem', marginBottom: '1.5rem', lineHeight: 1.6 }}>
              The local AI retrieves relevant chunks from your uploaded PDFs, builds verified citations with page numbers, and synthesizes answers without fabricating facts.
            </p>

            {documents.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', textAlign: 'left' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600 }}>SUGGESTED PROMPTS:</span>
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ justifyContent: 'flex-start', textAlign: 'left' }}
                  onClick={() => handleSend('Summarize the key concepts covered in these notes.')}
                >
                  💡 "Summarize the key concepts covered in these notes."
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ justifyContent: 'flex-start', textAlign: 'left' }}
                  onClick={() => handleSend('What are the main definitions and formulas I should know?')}
                >
                  📖 "What are the main definitions and formulas I should know?"
                </button>
              </div>
            ) : (
              <button className="btn btn-primary btn-sm" onClick={() => onNavigate('documents')}>
                Upload Your First PDF Note
              </button>
            )}
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === 'user';
            const showSources = expandedSources[msg.id];

            return (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isUser ? 'flex-end' : 'flex-start',
                  maxWidth: '100%',
                }}
              >
                {/* Sender badge & time */}
                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                  <span>{isUser ? 'You' : 'AI Study Buddy'}</span>
                  <span>•</span>
                  <span>{msg.timestamp}</span>
                  {msg.duration_ms !== undefined && msg.duration_ms !== null && msg.duration_ms > 0 && (
                    <>
                      <span>•</span>
                      <span style={{ color: 'var(--primary-400)', display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                        <Clock size={11} /> {msg.duration_ms < 1000 ? '< 0.1s' : `${(msg.duration_ms / 1000).toFixed(1)}s`}
                      </span>
                    </>
                  )}
                </div>

                {/* Message Bubble */}
                <div
                  style={{
                    maxWidth: '82%',
                    padding: '1rem 1.25rem',
                    borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                    background: isUser
                      ? 'linear-gradient(135deg, var(--primary-600) 0%, var(--indigo-500) 100%)'
                      : msg.error
                      ? 'rgba(251, 113, 133, 0.12)'
                      : 'var(--bg-card)',
                    color: isUser ? '#ffffff' : 'var(--text-main)',
                    border: isUser ? 'none' : msg.error ? '1px solid rgba(251, 113, 133, 0.3)' : '1px solid var(--border-card)',
                    boxShadow: 'var(--shadow-sm)',
                    fontSize: '0.92rem',
                    lineHeight: 1.6,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {msg.text}
                </div>

                {/* Citations Accordion (Assistant only) */}
                {!isUser && msg.sources && msg.sources.length > 0 && (
                  <div style={{ marginTop: '0.6rem', maxWidth: '82%', width: '100%' }}>
                    <button
                      onClick={() => toggleSource(msg.id)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--primary-400)',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        padding: '0.2rem 0',
                      }}
                    >
                      <BookOpen size={13} />
                      {showSources ? 'Hide Sources' : `View ${msg.sources.length} Verified Citation${msg.sources.length === 1 ? '' : 's'}`}
                      {showSources ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    </button>

                    {showSources && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                        {msg.sources.map((src, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: '0.75rem',
                              background: 'rgba(21, 25, 36, 0.95)',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: 'var(--radius-md)',
                              fontSize: '0.8rem',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                              <span style={{ fontWeight: 600, color: 'var(--primary-300)' }}>
                                {src.document_name} • Page {src.page_number}
                              </span>
                              <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                                Match: {(src.similarity_score * 100).toFixed(0)}%
                              </span>
                            </div>
                            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic', margin: 0 }}>
                              "{src.excerpt}"
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Loading Bubble */}
        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', maxWidth: '82%' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: '0.3rem' }}>
              AI Study Buddy • Searching notes & generating...
            </div>
            <div
              style={{
                padding: '0.85rem 1.25rem',
                borderRadius: '16px 16px 16px 4px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-card)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
              }}
            >
              <span className="spinner" style={{ width: '1rem', height: '1rem', color: 'var(--primary-400)' }} />
              <span style={{ fontSize: '0.86rem', color: 'var(--text-muted)' }}>
                Querying FAISS vector index & running local llama3.2:3b...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <textarea
            className="textarea"
            rows={2}
            placeholder={
              documents.length === 0
                ? 'Upload notes first to begin asking questions...'
                : 'Ask a question about your study notes... (Press Enter to send)'
            }
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading || documents.length === 0}
            style={{ resize: 'none', paddingRight: '3rem' }}
          />
        </div>

        <button
          className="btn btn-primary"
          style={{ height: '54px', padding: '0 1.35rem' }}
          onClick={() => handleSend()}
          disabled={loading || !inputText.trim() || documents.length === 0}
          title="Send Question"
        >
          {loading ? <span className="spinner" /> : <Send size={18} />}
        </button>

        {messages.some((m) => m.error) && (
          <button
            className="btn btn-secondary"
            style={{ height: '54px', padding: '0 1rem' }}
            onClick={retryLastMessage}
            disabled={loading}
            title="Retry last failed prompt"
          >
            <RotateCw size={17} />
          </button>
        )}
      </div>
    </div>
  );
};
