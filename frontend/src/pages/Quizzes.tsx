import React, { useState, useEffect } from 'react';
import {
  HelpCircle,
  Play,
  CheckCircle2,
  XCircle,
  Award,
  BookOpen,
  ArrowRight,
  ArrowLeft,
  RotateCw,
  Plus,
  Clock,
  Sparkles,
  Check
} from 'lucide-react';
import { api, ApiError } from '../services/api';
import {
  DocumentResponse,
  QuizListItemResponse,
  QuizResponse,
  QuizSubmitResponse,
  QuizAttemptResponse,
  ActiveTab
} from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';

interface QuizzesProps {
  initialDocId?: number | null;
  onNavigate: (tab: ActiveTab) => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void;
}

export const Quizzes: React.FC<QuizzesProps> = ({ initialDocId, onNavigate, showToast }) => {
  const [quizzes, setQuizzes] = useState<QuizListItemResponse[]>([]);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Generation Modal State
  const [isGenerateOpen, setIsGenerateOpen] = useState<boolean>(false);
  const [genTitle, setGenTitle] = useState<string>('');
  const [genDocIds, setGenDocIds] = useState<number[]>([]);
  const [genDifficulty, setGenDifficulty] = useState<'Easy' | 'Medium' | 'Hard'>('Medium');
  const [genNumQuestions, setGenNumQuestions] = useState<number>(3);
  const [generating, setGenerating] = useState<boolean>(false);
  const [generationElapsed, setGenerationElapsed] = useState<number>(0);

  // Active Quiz Solving State
  const [activeQuiz, setActiveQuiz] = useState<QuizResponse | null>(null);
  const [currentQIndex, setCurrentQIndex] = useState<number>(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [quizResult, setQuizResult] = useState<QuizSubmitResponse | null>(null);

  // Past Attempts Modal State
  const [viewingAttemptsQuiz, setViewingAttemptsQuiz] = useState<QuizListItemResponse | null>(null);
  const [attemptsList, setAttemptsList] = useState<QuizAttemptResponse[]>([]);
  const [loadingAttempts, setLoadingAttempts] = useState<boolean>(false);

  // Load quizzes and documents
  const fetchData = async () => {
    try {
      setLoading(true);
      const [qRes, dRes] = await Promise.all([
        api.listQuizzes(),
        api.listDocuments(),
      ]);
      setQuizzes(qRes.quizzes);
      setDocuments(dRes.documents);

      if (initialDocId && dRes.documents.some((d) => d.id === initialDocId)) {
        setGenDocIds([initialDocId]);
        setIsGenerateOpen(true);
      }
    } catch (err) {
      showToast('error', 'Failed to load quizzes or documents.', 'Connection Error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [initialDocId]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (genDocIds.length === 0) {
      showToast('warning', 'Please select at least one document to generate from.', 'Document Required');
      return;
    }

    let timer: any = null;
    try {
      setGenerating(true);
      setGenerationElapsed(0);
      timer = setInterval(() => {
        setGenerationElapsed((prev) => prev + 1);
      }, 1000);

      const newQuiz = await api.generateQuiz({
        document_ids: genDocIds,
        title: genTitle.trim() || undefined,
        difficulty: genDifficulty,
        num_questions: genNumQuestions,
      });

      showToast('success', `Generated "${newQuiz.title}" with ${newQuiz.questions.length} questions.`, 'Quiz Ready');
      setIsGenerateOpen(false);
      setGenTitle('');
      fetchData();

      // Launch newly generated quiz immediately
      startQuiz(newQuiz.id);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error generating quiz with local AI.';
      showToast('error', msg, 'Generation Failed');
    } finally {
      if (timer) clearInterval(timer);
      setGenerating(false);
      setGenerationElapsed(0);
    }
  };

  const startQuiz = async (quizId: number) => {
    try {
      setLoading(true);
      const fullQuiz = await api.getQuiz(quizId);
      setActiveQuiz(fullQuiz);
      setCurrentQIndex(0);
      setSelectedAnswers({});
      setQuizResult(null);
    } catch (err) {
      showToast('error', 'Failed to load quiz questions.', 'Error');
    } finally {
      setLoading(false);
    }
  };

  const handleOptionSelect = (questionId: number, option: string) => {
    setSelectedAnswers((prev) => ({
      ...prev,
      [String(questionId)]: option,
    }));
  };

  const handleSubmitQuiz = async () => {
    if (!activeQuiz) return;
    try {
      setSubmitting(true);
      const result = await api.submitQuiz(activeQuiz.id, selectedAnswers);
      setQuizResult(result);
      showToast('success', `Quiz scored! You scored ${result.score}/${result.total_questions} (${result.percentage.toFixed(0)}%).`, 'Quiz Submitted');
      fetchData(); // Refresh attempt counts
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to submit quiz.';
      showToast('error', msg, 'Submission Error');
    } finally {
      setSubmitting(false);
    }
  };

  const viewAttempts = async (quizItem: QuizListItemResponse) => {
    setViewingAttemptsQuiz(quizItem);
    try {
      setLoadingAttempts(true);
      const list = await api.getQuizAttempts(quizItem.id);
      setAttemptsList(list);
    } catch (err) {
      showToast('error', 'Failed to load previous attempts.', 'Error');
    } finally {
      setLoadingAttempts(false);
    }
  };

  const toggleGenDoc = (id: number) => {
    setGenDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  // ----------------------------------------------------
  // VIEW 1: Active Quiz Player / Result Breakdown
  // ----------------------------------------------------
  if (activeQuiz) {
    const questions = activeQuiz.questions;
    const currentQ = questions[currentQIndex];
    const totalQ = questions.length;
    const answeredCount = Object.keys(selectedAnswers).length;

    return (
      <div className="page-wrapper" style={{ maxWidth: '850px' }}>
        {/* Back / Navigation Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <button
            className="btn btn-outline btn-sm"
            onClick={() => {
              setActiveQuiz(null);
              setQuizResult(null);
            }}
          >
            <ArrowLeft size={15} /> Back to Quiz Center
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <StatusBadge status={activeQuiz.difficulty} />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {activeQuiz.total_questions} Questions
            </span>
          </div>
        </div>

        {/* Header */}
        <div className="card card-glow-top" style={{ marginBottom: '1.75rem', padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.45rem', marginBottom: '0.35rem' }}>{activeQuiz.title}</h2>
          <p style={{ fontSize: '0.84rem' }}>
            {quizResult
              ? 'Results scored by FastAPI backend. Review your score and detailed explanations below.'
              : 'Answer each question grounded in your uploaded study notes. Your score is graded on the backend.'}
          </p>
        </div>

        {/* Result Summary Banner (if submitted) */}
        {quizResult && (
          <div
            className="card"
            style={{
              marginBottom: '1.75rem',
              background: quizResult.percentage >= 70
                ? 'linear-gradient(135deg, rgba(52, 211, 153, 0.12) 0%, rgba(16, 185, 129, 0.05) 100%)'
                : 'linear-gradient(135deg, rgba(251, 191, 36, 0.12) 0%, rgba(245, 158, 11, 0.05) 100%)',
              borderColor: quizResult.percentage >= 70 ? 'rgba(52, 211, 153, 0.35)' : 'rgba(251, 191, 36, 0.35)',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1.25rem',
              padding: '1.5rem 2rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
              <div
                style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  background: quizResult.percentage >= 70 ? 'rgba(52, 211, 153, 0.2)' : 'rgba(251, 191, 36, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: quizResult.percentage >= 70 ? 'var(--emerald-400)' : 'var(--amber-400)',
                }}
              >
                <Award size={30} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.35rem', marginBottom: '0.2rem' }}>
                  {quizResult.score} / {quizResult.total_questions} Correct ({quizResult.percentage.toFixed(0)}%)
                </h3>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-main)' }}>
                  {quizResult.percentage >= 80
                    ? 'Excellent mastery of these study materials!'
                    : quizResult.percentage >= 60
                    ? 'Good effort! Review the citations below to reinforce concepts.'
                    : 'Consider reviewing your notes before re-attempting.'}
                </p>
              </div>
            </div>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setSelectedAnswers({});
                setQuizResult(null);
                setCurrentQIndex(0);
              }}
            >
              <RotateCw size={14} /> Retake Quiz
            </button>
          </div>
        )}

        {/* Question Review or Solving View */}
        {!quizResult ? (
          // Active Solving: Question Card
          <div className="card" style={{ padding: '2rem' }}>
            {/* Progress Bar */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.45rem' }}>
                <span>Question {currentQIndex + 1} of {totalQ}</span>
                <span>{answeredCount} of {totalQ} answered</span>
              </div>
              <div style={{ width: '100%', height: '6px', background: 'var(--border-card)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${((currentQIndex + 1) / totalQ) * 100}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, var(--primary-600), var(--indigo-500))',
                    borderRadius: 'var(--radius-full)',
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
            </div>

            {/* Question Text */}
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', lineHeight: 1.4 }}>
              {currentQ.question_text}
            </h3>

            {/* Options */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '2rem' }}>
              {currentQ.options.map((opt, oIdx) => {
                const isSelected = selectedAnswers[String(currentQ.id)] === opt;
                const optionLetter = String.fromCharCode(65 + oIdx);

                return (
                  <button
                    key={oIdx}
                    onClick={() => handleOptionSelect(currentQ.id, opt)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem',
                      padding: '1rem 1.25rem',
                      borderRadius: 'var(--radius-md)',
                      background: isSelected ? 'rgba(124, 58, 237, 0.16)' : 'rgba(255, 255, 255, 0.02)',
                      border: isSelected ? '1px solid var(--primary-500)' : '1px solid var(--border-card)',
                      color: isSelected ? 'var(--text-main)' : 'var(--text-muted)',
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: '0.92rem',
                      transition: 'all var(--transition-fast)',
                    }}
                  >
                    <span
                      style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        background: isSelected ? 'var(--primary-600)' : 'rgba(255, 255, 255, 0.06)',
                        color: isSelected ? '#ffffff' : 'var(--text-muted)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        fontSize: '0.8rem',
                        flexShrink: 0,
                      }}
                    >
                      {optionLetter}
                    </span>
                    <span style={{ flex: 1 }}>{opt}</span>
                  </button>
                );
              })}
            </div>

            {/* Navigation Buttons */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                className="btn btn-outline"
                onClick={() => setCurrentQIndex((prev) => Math.max(0, prev - 1))}
                disabled={currentQIndex === 0}
              >
                <ArrowLeft size={16} /> Previous
              </button>

              {currentQIndex < totalQ - 1 ? (
                <button
                  className="btn btn-primary"
                  onClick={() => setCurrentQIndex((prev) => Math.min(totalQ - 1, prev + 1))}
                >
                  Next <ArrowRight size={16} />
                </button>
              ) : (
                <button
                  className="btn btn-primary"
                  onClick={handleSubmitQuiz}
                  disabled={submitting || answeredCount === 0}
                >
                  {submitting ? <span className="spinner" /> : <CheckCircle2 size={16} />}
                  Submit Quiz
                </button>
              )}
            </div>
          </div>
        ) : (
          // Post-Submission Graded Results List
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {quizResult.results.map((res, idx) => {
              const isCorrect = res.is_correct;
              return (
                <div
                  key={res.question_id}
                  className="card"
                  style={{
                    padding: '1.5rem',
                    borderLeft: `4px solid ${isCorrect ? 'var(--emerald-400)' : 'var(--rose-400)'}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: '0.75rem' }}>
                    <h4 style={{ fontSize: '1.05rem', lineHeight: 1.4 }}>
                      {idx + 1}. {res.question_text}
                    </h4>
                    <span className={`badge badge-${isCorrect ? 'success' : 'danger'}`}>
                      {isCorrect ? 'Correct (+1)' : 'Incorrect (0)'}
                    </span>
                  </div>

                  {/* Answers chosen vs correct */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', marginBottom: '0.85rem', fontSize: '0.88rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: isCorrect ? 'var(--emerald-400)' : 'var(--rose-400)' }}>
                      {isCorrect ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                      <span>Your Answer: <strong>{res.selected_answer || 'No answer selected'}</strong></span>
                    </div>

                    {!isCorrect && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--emerald-400)', marginLeft: '1.45rem' }}>
                        <span>Correct Answer: <strong>{res.correct_answer}</strong></span>
                      </div>
                    )}
                  </div>

                  {/* Explanation & Page Reference */}
                  {res.explanation && (
                    <div style={{ padding: '0.85rem', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)', fontSize: '0.82rem' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.2rem' }}>
                        Explanation:
                      </div>
                      <p style={{ color: 'var(--text-muted)', marginBottom: res.page_reference ? '0.35rem' : 0 }}>
                        {res.explanation}
                      </p>
                      {res.page_reference && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--primary-400)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <BookOpen size={12} /> Reference: Page {res.page_reference}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // ----------------------------------------------------
  // VIEW 2: Quiz Center List & Generator
  // ----------------------------------------------------
  return (
    <div className="page-wrapper">
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
        <div>
          <h3>Practice Quizzes ({quizzes.length})</h3>
          <p style={{ fontSize: '0.84rem' }}>
            AI generated multiple-choice practice exams graded on the backend
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setIsGenerateOpen(true)}>
          <Plus size={16} /> Generate New Quiz
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <span className="spinner" />
        </div>
      ) : quizzes.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
          <HelpCircle size={44} style={{ opacity: 0.35, marginBottom: '0.75rem' }} />
          <h4 style={{ marginBottom: '0.35rem' }}>No practice quizzes generated yet.</h4>
          <p style={{ fontSize: '0.85rem', maxWidth: '420px', margin: '0 auto 1.5rem auto' }}>
            Select one or more uploaded notes to create a grounded multiple-choice quiz with customizable difficulty.
          </p>
          <button className="btn btn-primary btn-sm" onClick={() => setIsGenerateOpen(true)}>
            <Sparkles size={14} /> Create Your First Quiz
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.25rem' }}>
          {quizzes.map((quiz) => (
            <div key={quiz.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.75rem' }}>
                  <StatusBadge status={quiz.difficulty} />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    {quiz.total_questions} Questions
                  </span>
                </div>

                <h4 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', lineHeight: 1.35 }}>
                  {quiz.title}
                </h4>

                <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '1.25rem', display: 'flex', gap: '0.65rem' }}>
                  <span>Created {new Date(quiz.created_at).toLocaleDateString()}</span>
                  <span>•</span>
                  <span>{quiz.attempts_count} attempt{quiz.attempts_count === 1 ? '' : 's'}</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
                {quiz.best_percentage !== null && quiz.best_percentage !== undefined ? (
                  <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--emerald-400)' }}>
                    Best: {quiz.best_percentage.toFixed(0)}%
                  </span>
                ) : (
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-dim)' }}>Not attempted</span>
                )}

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {quiz.attempts_count > 0 && (
                    <button
                      className="btn btn-outline btn-sm"
                      onClick={() => viewAttempts(quiz)}
                      title="View past attempts history"
                    >
                      <Clock size={13} />
                    </button>
                  )}
                  <button className="btn btn-primary btn-sm" onClick={() => startQuiz(quiz.id)}>
                    <Play size={13} /> Start Quiz
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Generation Modal */}
      <Modal
        isOpen={isGenerateOpen}
        onClose={() => !generating && setIsGenerateOpen(false)}
        title="Generate AI Quiz"
        footer={
          <>
            <button className="btn btn-secondary btn-sm" onClick={() => setIsGenerateOpen(false)} disabled={generating}>
              Cancel
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleGenerate}
              disabled={generating || genDocIds.length === 0}
              id="generate-quiz-btn"
            >
              {generating ? (
                <>
                  <span className="spinner" style={{ width: '14px', height: '14px', marginRight: '6px' }} />
                  Generating ({generationElapsed}s)...
                </>
              ) : (
                <>
                  <Sparkles size={14} /> Generate Quiz
                </>
              )}
            </button>
          </>
        }
      >
        {generating && (
          <div
            id="quiz-generation-loading-banner"
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
                <span>Generating {genNumQuestions} Questions with Local AI...</span>
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
            <label className="form-label">Quiz Title (Optional)</label>
            <input
              type="text"
              className="input"
              placeholder="e.g., Biology Midterm Practice"
              value={genTitle}
              onChange={(e) => setGenTitle(e.target.value)}
              disabled={generating}
            />
          </div>

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
                      <span>{doc.original_filename} ({doc.page_count} pages)</span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Difficulty</label>
              <select
                className="select"
                value={genDifficulty}
                onChange={(e) => setGenDifficulty(e.target.value as 'Easy' | 'Medium' | 'Hard')}
                disabled={generating}
              >
                <option value="Easy">Easy (Core definitions)</option>
                <option value="Medium">Medium (Application & concepts)</option>
                <option value="Hard">Hard (Analysis & details)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Number of Questions</label>
              <select
                className="select"
                value={genNumQuestions}
                onChange={(e) => setGenNumQuestions(Number(e.target.value))}
                disabled={generating}
              >
                <option value={3}>3 Questions (Fast - Recommended)</option>
                <option value={5}>5 Questions (Standard)</option>
                <option value={10}>10 Questions (Comprehensive)</option>
                <option value={15}>15 Questions (Exam length)</option>
              </select>
            </div>
          </div>
        </form>
      </Modal>

      {/* Past Attempts History Modal */}
      <Modal
        isOpen={!!viewingAttemptsQuiz}
        onClose={() => setViewingAttemptsQuiz(null)}
        title={`Attempt History: ${viewingAttemptsQuiz?.title || 'Quiz'}`}
        footer={
          <button className="btn btn-secondary btn-sm" onClick={() => setViewingAttemptsQuiz(null)}>
            Close
          </button>
        }
      >
        {loadingAttempts ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
            <span className="spinner" />
          </div>
        ) : attemptsList.length === 0 ? (
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No completed attempts on record.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {attemptsList.map((att) => (
              <div
                key={att.id}
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>
                    Score: {att.score}/{att.total_questions} ({att.percentage.toFixed(0)}%)
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    Completed on {new Date(att.completed_at).toLocaleString()}
                  </div>
                </div>
                <span
                  style={{
                    fontWeight: 700,
                    fontSize: '0.95rem',
                    color: att.percentage >= 70 ? 'var(--emerald-400)' : 'var(--amber-400)',
                  }}
                >
                  {att.percentage.toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
};
