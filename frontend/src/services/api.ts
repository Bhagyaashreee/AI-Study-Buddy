import {
  HealthResponse,
  OllamaStatusResponse,
  DocumentResponse,
  DocumentListResponse,
  DeleteDocumentResponse,
  RAGQueryRequest,
  RAGQueryResponse,
  QuizGenerateRequest,
  QuizResponse,
  QuizListResponse,
  QuizSubmitResponse,
  QuizAttemptResponse,
  FlashcardGenerateRequest,
  FlashcardListResponse,
  FlashcardReviewResponse,
  StudyProgressResponse,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    let data: unknown = null;
    try {
      data = await response.json();
      if (typeof data === 'object' && data !== null && 'detail' in data) {
        const detail = (data as { detail: unknown }).detail;
        if (typeof detail === 'string') {
          errorDetail = detail;
        } else if (Array.isArray(detail)) {
          errorDetail = detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(', ');
        }
      }
    } catch {
      // Fallback to status text
    }
    throw new ApiError(errorDetail, response.status, data);
  }
  return response.json();
}

export const api = {
  getBaseUrl(): string {
    return BASE_URL;
  },

  // 1. Health & AI Status
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${BASE_URL}/api/health`);
    return handleResponse<HealthResponse>(res);
  },

  async getOllamaStatus(): Promise<OllamaStatusResponse> {
    const res = await fetch(`${BASE_URL}/api/ai/status`);
    return handleResponse<OllamaStatusResponse>(res);
  },

  // 2. Documents
  async listDocuments(): Promise<DocumentListResponse> {
    const res = await fetch(`${BASE_URL}/api/documents`);
    return handleResponse<DocumentListResponse>(res);
  },

  async getDocument(id: number): Promise<DocumentResponse> {
    const res = await fetch(`${BASE_URL}/api/documents/${id}`);
    return handleResponse<DocumentResponse>(res);
  },

  async uploadDocument(file: File): Promise<DocumentResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/api/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<DocumentResponse>(res);
  },

  async deleteDocument(id: number): Promise<DeleteDocumentResponse> {
    const res = await fetch(`${BASE_URL}/api/documents/${id}`, {
      method: 'DELETE',
    });
    return handleResponse<DeleteDocumentResponse>(res);
  },

  // 3. RAG Chat
  async askQuestion(payload: RAGQueryRequest): Promise<RAGQueryResponse> {
    const res = await fetch(`${BASE_URL}/api/chat/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<RAGQueryResponse>(res);
  },

  // 4. Quizzes
  async generateQuiz(payload: QuizGenerateRequest): Promise<QuizResponse> {
    const res = await fetch(`${BASE_URL}/api/quizzes/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<QuizResponse>(res);
  },

  async listQuizzes(): Promise<QuizListResponse> {
    const res = await fetch(`${BASE_URL}/api/quizzes`);
    return handleResponse<QuizListResponse>(res);
  },

  async getQuiz(quizId: number): Promise<QuizResponse> {
    const res = await fetch(`${BASE_URL}/api/quizzes/${quizId}`);
    return handleResponse<QuizResponse>(res);
  },

  async submitQuiz(quizId: number, answers: Record<string, string>): Promise<QuizSubmitResponse> {
    const res = await fetch(`${BASE_URL}/api/quizzes/${quizId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
    });
    return handleResponse<QuizSubmitResponse>(res);
  },

  async getQuizAttempts(quizId: number): Promise<QuizAttemptResponse[]> {
    const res = await fetch(`${BASE_URL}/api/quizzes/${quizId}/attempts`);
    return handleResponse<QuizAttemptResponse[]>(res);
  },

  // 5. Flashcards
  async generateFlashcards(payload: FlashcardGenerateRequest): Promise<FlashcardListResponse> {
    const res = await fetch(`${BASE_URL}/api/flashcards/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<FlashcardListResponse>(res);
  },

  async listFlashcards(documentId?: number): Promise<FlashcardListResponse> {
    const url = documentId !== undefined
      ? `${BASE_URL}/api/flashcards?document_id=${documentId}`
      : `${BASE_URL}/api/flashcards`;
    const res = await fetch(url);
    return handleResponse<FlashcardListResponse>(res);
  },

  async getDueFlashcards(): Promise<FlashcardListResponse> {
    const res = await fetch(`${BASE_URL}/api/flashcards/due`);
    return handleResponse<FlashcardListResponse>(res);
  },

  async reviewFlashcard(
    flashcardId: number,
    rating: 'Easy' | 'Medium' | 'Hard'
  ): Promise<FlashcardReviewResponse> {
    const res = await fetch(`${BASE_URL}/api/flashcards/${flashcardId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating }),
    });
    return handleResponse<FlashcardReviewResponse>(res);
  },

  async deleteFlashcard(flashcardId: number): Promise<{ message: string; flashcard_id: number }> {
    const res = await fetch(`${BASE_URL}/api/flashcards/${flashcardId}`, {
      method: 'DELETE',
    });
    return handleResponse<{ message: string; flashcard_id: number }>(res);
  },

  // 6. Progress
  async getProgressSummary(): Promise<StudyProgressResponse> {
    const res = await fetch(`${BASE_URL}/api/progress/summary`);
    return handleResponse<StudyProgressResponse>(res);
  },
};
