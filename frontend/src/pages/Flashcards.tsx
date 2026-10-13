import React, { useState, useEffect } from 'react';
import {
  Layers,
  Sparkles,
  RotateCcw,
  ArrowRight,
  ArrowLeft,
  Trash2,
  Calendar,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Plus
} from 'lucide-react';
import { api, ApiError } from '../services/api';
import {
  DocumentResponse,
  FlashcardResponse,
  ActiveTab
} from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';

interface FlashcardsProps {
  initialDocId?: number | null;
  onNavigate: (tab: ActiveTab) => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void;
  onRefreshDueCount: () => void;
}

export const Flashcards: React.FC<FlashcardsProps> = ({
  initialDocId,
  onNavigate,
  showToast,
  onRefreshDueCount,
}) => {
  const [cards, setCards] = useState<FlashcardResponse[]>([]);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [mode, setMode] = useState<'due' | 'all'>('due');

  // Study card index & flip state
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [isFlipped, setIsFlipped] = useState<boolean>(false);
  const [reviewing, setReviewing] = useState<boolean>(false);

  // Generation Modal State
  const [isGenerateOpen, setIsGenerateOpen] = useState<boolean>(false);
  const [genDocIds, setGenDocIds] = useState<number[]>([]);
  const [genNumCards, setGenNumCards] = useState<number>(5);
  const [generating, setGenerating] = useState<boolean>(false);
  const [generationElapsed, setGenerationElapsed] = useState<number>(0);

  // Delete Modal
  const [cardToDelete, setCardToDelete] = useState<FlashcardResponse | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);

  const fetchCardsAndDocs = async (currentMode: 'due' | 'all') => {
    try {
      setLoading(true);
      const [cardsRes, docsRes] = await Promise.all([
        currentMode === 'due' ? api.getDueFlashcards() : api.listFlashcards(),
        api.listDocuments(),
      ]);
      setCards(cardsRes.flashcards);
      setDocuments(docsRes.documents);
      setCurrentIndex(0);
      setIsFlipped(false);

      if (initialDocId && docsRes.documents.some((d) => d.id === initialDocId)) {
        setGenDocIds([initialDocId]);
        setIsGenerateOpen(true);
      }
    } catch (err) {
      showToast('error', 'Failed to retrieve flashcards.', 'Error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCardsAndDocs(mode);
  }, [mode, initialDocId]);

  // Keyboard navigation for power users
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isGenerateOpen || !!cardToDelete) return;

      if (e.code === 'Space') {
        e.preventDefault();
        setIsFlipped((prev) => !prev);
      } else if (e.key === 'ArrowRight' && currentIndex < cards.length - 1) {
        handleNext();
      } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
        handlePrev();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFlipped, currentIndex, cards.length, isGenerateOpen, cardToDelete]);

  const handleNext = () => {
    setIsFlipped(false);
    setCurrentIndex((prev) => Math.min(cards.length - 1, prev + 1));
  };

  const handlePrev = () => {
    setIsFlipped(false);
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  };

  const handleReview = async (rating: 'Easy' | 'Medium' | 'Hard') => {
    if (cards.length === 0 || reviewing) return;
    const currentCard = cards[currentIndex];

    try {
      setReviewing(true);
      const res = await api.reviewFlashcard(currentCard.id, rating);
      showToast(
        'success',
        `Scheduled for review in ${res.interval_days} day${res.interval_days === 1 ? '' : 's'}.`,
        `Marked as ${rating}`
      );
      onRefreshDueCount();

      // In 'due' mode, remove this card from the queue
      if (mode === 'due') {
        const nextCards = cards.filter((c) => c.id !== currentCard.id);
        setCards(nextCards);
        setIsFlipped(false);
        if (currentIndex >= nextCards.length) {
          setCurrentIndex(Math.max(0, nextCards.length - 1));
        }
      } else {
        // In 'all' mode, advance to next
        if (currentIndex < cards.length - 1) {
          handleNext();
        } else {
          setIsFlipped(false);
        }
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error recording review.';
      showToast('error', msg, 'Review Failed');
    } finally {
      setReviewing(false);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (generating) return;
    if (genDocIds.length === 0) {
      showToast('warning', 'Please select at least one document.', 'Selection Required');
      return;
    }

    let timer: any = null;
    try {
      setGenerating(true);
      setGenerationElapsed(0);
      timer = setInterval(() => {
        setGenerationElapsed((prev) => prev + 1);
      }, 1000);

      const res = await api.generateFlashcards({
        document_ids: genDocIds,
        num_cards: genNumCards,
      });
      showToast('success', `Generated ${res.flashcards.length} smart flashcards!`, 'Cards Created');
      setIsGenerateOpen(false);
      onRefreshDueCount();
      fetchCardsAndDocs(mode);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to generate flashcards.';
      showToast('error', msg, 'Generation Failed');
    } finally {
      if (timer) clearInterval(timer);
      setGenerating(false);
      setGenerationElapsed(0);
    }
  };


  const handleDeleteCard = async () => {
    if (!cardToDelete) return;
    try {
      setDeleting(true);
      await api.deleteFlashcard(cardToDelete.id);
      showToast('success', 'Flashcard deleted.', 'Removed');
      setCardToDelete(null);
      onRefreshDueCount();
      const updated = cards.filter((c) => c.id !== cardToDelete.id);
      setCards(updated);
      setIsFlipped(false);
      if (currentIndex >= updated.length) {
        setCurrentIndex(Math.max(0, updated.length - 1));
      }
    } catch (err) {
      showToast('error', 'Failed to delete flashcard.', 'Error');
    } finally {
      setDeleting(false);
    }
  };

  const toggleGenDoc = (id: number) => {
    setGenDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const currentCard = cards[currentIndex];

  return (
    <div className="page-wrapper" style={{ maxWidth: '850px' }}>
      {/* Top Header & Mode Toggle */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
        <div>
          <h3>Spaced Flashcards</h3>
          <p style={{ fontSize: '0.84rem' }}>
            Lightweight Leitner-style active recall grounded in your notes
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Due vs All Mode Switch */}
          <div style={{ display: 'flex', background: 'var(--bg-surface)', padding: '3px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
            <button
              className={`btn btn-sm ${mode === 'due' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setMode('due')}
              style={{ padding: '0.35rem 0.85rem', fontSize: '0.8rem' }}
            >
              Due Today
            </button>
            <button
              className={`btn btn-sm ${mode === 'all' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setMode('all')}
              style={{ padding: '0.35rem 0.85rem', fontSize: '0.8rem' }}
            >
              All Cards
            </button>
          </div>

          <button className="btn btn-primary" onClick={() => setIsGenerateOpen(true)}>
            <Plus size={16} /> New Cards
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <span className="spinner" />
        </div>
      ) : cards.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
          <Layers size={44} style={{ opacity: 0.35, marginBottom: '0.75rem' }} />
          <h4 style={{ marginBottom: '0.35rem' }}>
            {mode === 'due' ? 'No cards due for review today!' : 'No flashcards generated yet.'}
          </h4>
          <p style={{ fontSize: '0.85rem', maxWidth: '420px', margin: '0 auto 1.5rem auto' }}>
            {mode === 'due'
              ? 'Great job! You are all caught up on scheduled reviews. You can view all cards or generate more.'
              : 'Generate question-answer pairs from your uploaded PDF notes to begin spaced repetition.'}
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem' }}>
            {mode === 'due' && (
              <button className="btn btn-secondary btn-sm" onClick={() => setMode('all')}>
                View All Cards
              </button>
            )}
            <button className="btn btn-primary btn-sm" onClick={() => setIsGenerateOpen(true)}>
              <Sparkles size={14} /> Generate Flashcards
            </button>
          </div>
        </div>
      ) : (
        <div>
          {/* Card Meta & Counter Bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <span>Card {currentIndex + 1} of {cards.length}</span>
              {currentCard.document_name && (
                <span className="badge badge-neutral" style={{ fontSize: '0.74rem' }}>
                  <BookOpen size={11} /> {currentCard.document_name}
                  {currentCard.page_reference ? ` (p. ${currentCard.page_reference})` : ''}
                </span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.76rem', color: 'var(--text-dim)' }}>Reviews: {currentCard.review_count}</span>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => setCardToDelete(currentCard)}
                title="Delete this card"
                style={{ padding: '0.3rem 0.5rem', color: 'var(--rose-400)' }}
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          {/* 3D Flip Card Scene */}
          <div className="flashcard-scene" onClick={() => setIsFlipped(!isFlipped)}>
            <div className={`flashcard-card ${isFlipped ? 'flipped' : ''}`}>
              {/* Front Face: Question */}
              <div className="flashcard-face flashcard-front">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="badge badge-primary">QUESTION</span>
                  <span style={{ fontSize: '0.76rem', color: 'var(--text-dim)' }}>Click or press Space to flip</span>
                </div>

                <div style={{ margin: 'auto', textAlign: 'center', width: '100%', padding: '1rem 0' }}>
                  <h3 style={{ fontSize: '1.4rem', lineHeight: 1.45, fontWeight: 600 }}>
                    {currentCard.question}
                  </h3>
                </div>

                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--primary-400)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    <RotateCcw size={14} /> Click card to reveal answer
                  </span>
                </div>
              </div>

              {/* Back Face: Answer */}
              <div className="flashcard-face flashcard-back">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="badge badge-success">ANSWER</span>
                  <span style={{ fontSize: '0.76rem', color: 'var(--text-dim)' }}>Click to flip back</span>
                </div>

                <div style={{ margin: 'auto', textAlign: 'center', width: '100%', padding: '1rem 0' }}>
                  <p style={{ fontSize: '1.15rem', lineHeight: 1.6, color: 'var(--text-main)', whiteSpace: 'pre-wrap' }}>
                    {currentCard.answer}
                  </p>
                </div>

                {currentCard.page_reference ? (
                  <div style={{ display: 'flex', justifyContent: 'center', fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                    Source: Page {currentCard.page_reference}
                  </div>
                ) : <div />}
              </div>
            </div>
          </div>

          {/* Review Buttons (Rating Recall) */}
          <div style={{ marginTop: '1.75rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {isFlipped ? (
              <div className="card" style={{ padding: '1.15rem 1.5rem', background: 'rgba(21, 25, 36, 0.95)' }}>
                <div style={{ textAlign: 'center', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.85rem' }}>
                  How well did you remember this answer?
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleReview('Hard')}
                    disabled={reviewing}
                    title="Repeat tomorrow"
                  >
                    Hard <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>(1d)</span>
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleReview('Medium')}
                    disabled={reviewing}
                    title="Review in ~2 days"
                    style={{ borderColor: 'rgba(251, 191, 36, 0.3)' }}
                  >
                    Medium <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>(+2d)</span>
                  </button>
                  <button
                    className="btn btn-success"
                    onClick={() => handleReview('Easy')}
                    disabled={reviewing}
                    title="Review in ~4 days"
                  >
                    Easy <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>(+4d)</span>
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button
                  className="btn btn-outline"
                  onClick={handlePrev}
                  disabled={currentIndex === 0}
                >
                  <ArrowLeft size={16} /> Previous
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => setIsFlipped(true)}
                >
                  <RotateCcw size={15} /> Reveal Answer
                </button>
                <button
                  className="btn btn-outline"
                  onClick={handleNext}
                  disabled={currentIndex === cards.length - 1}
                >
                  Next <ArrowRight size={16} />
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Generate Flashcards Modal */}
      <Modal
        isOpen={isGenerateOpen}
        onClose={() => !generating && setIsGenerateOpen(false)}
        title="Generate AI Flashcards"
        footer={
          <>
            <button className="btn btn-secondary btn-sm" onClick={() => setIsGenerateOpen(false)} disabled={generating}>
              Cancel
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleGenerate}
              disabled={generating || genDocIds.length === 0}
              id="generate-flashcards-btn"
            >
              {generating ? (
                <>
                  <span className="spinner" style={{ width: '14px', height: '14px', marginRight: '6px' }} />
                  Generating ({generationElapsed}s)...
                </>
              ) : (
                <>
                  <Sparkles size={14} /> Generate Cards
                </>
              )}
            </button>
          </>
        }
      >
        {generating && (
          <div
            id="flashcard-generation-loading-banner"
            style={{
              padding: '1.1rem 1.25rem',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, rgba(124, 58, 237, 0.12) 0%, rgba(59, 130, 246, 0.08) 100%)',
              border: '1px solid rgba(124, 58, 237, 0.35)',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              boxShadow: '0 4px 12px rgba(124, 58, 237, 0.1)',
            }}
          >
            <span
              className="spinner"
              style={{
                width: '26px',
                height: '26px',
                borderWidth: '2.5px',
                borderTopColor: '#a855f7',
                flexShrink: 0,
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>Generating {genNumCards} Flashcards with Local AI...</span>
                <span
                  style={{
                    fontSize: '0.75rem',
                    padding: '0.15rem 0.5rem',
                    borderRadius: '12px',
                    background: 'rgba(168, 85, 247, 0.2)',
                    color: '#c084fc',
                    fontWeight: 700,
                  }}
                >
                  {generationElapsed}s elapsed
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                llama3.2:3b local inference active • 100% private, strictly ₹0 cost
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleGenerate}>
          <div className="form-group">
            <label className="form-label">Select Source Documents *</label>
            {documents.length === 0 ? (
              <p style={{ fontSize: '0.82rem', color: 'var(--rose-400)' }}>
                No documents found. Please upload a PDF first.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', maxHeight: '160px', overflowY: 'auto' }}>
                {documents.map((doc) => {
                  const isChecked = genDocIds.includes(doc.id);
                  return (
                    <label
                      key={doc.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.65rem',
                        fontSize: '0.85rem',
                        cursor: 'pointer',
                        padding: '0.45rem 0.65rem',
                        borderRadius: 'var(--radius-sm)',
                        background: isChecked ? 'rgba(124, 58, 237, 0.12)' : 'transparent',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleGenDoc(doc.id)}
                        disabled={generating}
                      />
                      <span>{doc.original_filename} ({doc.chunk_count} chunks)</span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">Number of Flashcards</label>
            <select
              className="select"
              value={genNumCards}
              onChange={(e) => setGenNumCards(Number(e.target.value))}
              disabled={generating}
            >
              <option value={3}>3 Cards (Quick recap)</option>
              <option value={5}>5 Cards (Standard set)</option>
              <option value={10}>10 Cards (Deep study)</option>
            </select>
          </div>
        </form>
      </Modal>

      {/* Delete Flashcard Modal */}
      <Modal
        isOpen={!!cardToDelete}
        onClose={() => setCardToDelete(null)}
        title="Delete Flashcard"
        footer={
          <>
            <button className="btn btn-secondary btn-sm" onClick={() => setCardToDelete(null)} disabled={deleting}>
              Cancel
            </button>
            <button className="btn btn-danger btn-sm" onClick={handleDeleteCard} disabled={deleting}>
              {deleting ? <span className="spinner" /> : <Trash2 size={14} />} Delete
            </button>
          </>
        }
      >
        <p style={{ fontSize: '0.9rem' }}>
          Are you sure you want to delete this flashcard?
        </p>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontStyle: 'italic' }}>
          "{cardToDelete?.question}"
        </p>
      </Modal>
    </div>
  );
};
