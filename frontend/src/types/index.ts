// Core TypeScript interfaces matching backend models

export interface DatabaseHealth {
  status: 'connected' | 'disconnected' | string;
  type: string;
}

export interface OllamaHealth {
  status: 'available' | 'unavailable' | string;
  base_url: string;
  target_model: string;
  model_installed: boolean;
  details?: string | null;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy' | string;
  project_name: string;
  version: string;
  environment: string;
  database: DatabaseHealth;
  ollama: OllamaHealth;
  timestamp: string;
}

export interface OllamaStatusResponse {
  status: 'ready' | 'model_missing' | 'offline' | string;
  server_reachable: boolean;
  model_installed: boolean;
  target_model: string;
  available_models: string[];
  message?: string | null;
  timestamp?: string;
}

export interface DocumentResponse {
  id: number;
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  page_count: number;
  status: 'processed' | 'processing' | 'failed' | 'scanned_pdf_no_ocr' | string;
  status_message?: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total_documents: number;
}

export interface DeleteDocumentResponse {
  success: boolean;
  document_id: number;
  message: string;
  chunks_removed: number;
}

export interface RAGSourceItem {
  document_id: number;
  document_name: string;
  page_number: number;
  excerpt: string;
  similarity_score: number;
}

export interface RAGQueryRequest {
  question: string;
  document_ids?: number[] | null;
  top_k?: number | null;
}

export interface RAGQueryResponse {
  answer: string;
  sources: RAGSourceItem[];
  model: string;
  retrieval_count: number;
  duration_ms?: number | null;
  timestamp: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  sources?: RAGSourceItem[];
  duration_ms?: number | null;
  error?: boolean;
}

export interface QuizGenerateRequest {
  document_ids: number[];
  title?: string;
  difficulty?: 'Easy' | 'Medium' | 'Hard';
  num_questions?: number;
}

export interface QuizQuestionPublicResponse {
  id: number;
  quiz_id: number;
  question_text: string;
  options: string[];
  page_reference?: number | null;
}

export interface QuizResponse {
  id: number;
  title: string;
  difficulty: 'Easy' | 'Medium' | 'Hard' | string;
  total_questions: number;
  document_id?: number | null;
  created_at: string;
  questions: QuizQuestionPublicResponse[];
}

export interface QuizListItemResponse {
  id: number;
  title: string;
  difficulty: string;
  total_questions: number;
  document_id?: number | null;
  created_at: string;
  attempts_count: number;
  best_percentage?: number | null;
}

export interface QuizListResponse {
  quizzes: QuizListItemResponse[];
  total_quizzes: number;
}

export interface QuizSubmitRequest {
  answers: Record<string, string>;
}

export interface QuestionResultItem {
  question_id: number;
  question_text: string;
  selected_answer?: string | null;
  correct_answer: string;
  is_correct: boolean;
  explanation?: string | null;
  page_reference?: number | null;
}

export interface QuizSubmitResponse {
  attempt_id: number;
  quiz_id: number;
  score: number;
  total_questions: number;
  percentage: floatNumber;
  completed_at: string;
  results: QuestionResultItem[];
}

type floatNumber = number;

export interface QuizAttemptResponse {
  id: number;
  quiz_id: number;
  score: number;
  total_questions: number;
  percentage: number;
  completed_at: string;
}

export interface FlashcardGenerateRequest {
  document_ids: number[];
  num_cards?: number;
}

export interface FlashcardResponse {
  id: number;
  document_id?: number | null;
  document_name?: string | null;
  question: string;
  answer: string;
  difficulty_rating: string;
  page_reference?: number | null;
  review_count: number;
  last_reviewed_at?: string | null;
  next_review_at?: string | null;
  is_due: boolean;
  created_at: string;
}

export interface FlashcardListResponse {
  flashcards: FlashcardResponse[];
  total_cards: number;
}

export interface FlashcardReviewRequest {
  rating: 'Easy' | 'Medium' | 'Hard';
}

export interface FlashcardReviewResponse {
  id: number;
  difficulty_rating: string;
  review_count: number;
  last_reviewed_at: string;
  next_review_at: string;
  interval_days: number;
  message: string;
}

export interface RecentAttemptItem {
  attempt_id: number;
  quiz_id: number;
  quiz_title: string;
  difficulty: string;
  score: number;
  total_questions: number;
  percentage: number;
  completed_at: string;
}

export interface PerformanceHistoryItem {
  attempt_id: number;
  quiz_title: string;
  percentage: number;
  completed_at: string;
}

export interface StudyProgressResponse {
  total_documents: number;
  total_quizzes: number;
  total_attempts: number;
  average_quiz_score: number;
  total_flashcards: number;
  cards_due_for_review: number;
  recent_attempts: RecentAttemptItem[];
  performance_history: PerformanceHistoryItem[];
}

export type ActiveTab = 'dashboard' | 'documents' | 'chat' | 'quizzes' | 'flashcards' | 'progress';

export interface ToastNotification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title?: string;
  message: string;
}
