import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  Search,
  MessageSquare,
  HelpCircle,
  Layers,
  Info
} from 'lucide-react';
import { api, ApiError } from '../services/api';
import { DocumentResponse, ActiveTab } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';

interface DocumentsProps {
  onNavigate: (tab: ActiveTab, docId?: number) => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void;
}

export const Documents: React.FC<DocumentsProps> = ({ onNavigate, showToast }) => {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedDoc, setSelectedDoc] = useState<DocumentResponse | null>(null);
  const [docToDelete, setDocToDelete] = useState<DocumentResponse | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const res = await api.listDocuments();
      setDocuments(res.documents);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to retrieve documents.';
      showToast('error', msg, 'Connection Error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showToast('error', 'Only PDF files are supported.', 'Invalid File Type');
      return;
    }

    try {
      setUploading(true);
      const newDoc = await api.uploadDocument(file);
      showToast('success', `"${newDoc.original_filename}" processed (${newDoc.page_count} pages, ${newDoc.chunk_count} chunks).`, 'Upload Successful');
      fetchDocuments();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error uploading PDF.';
      showToast('error', msg, 'Upload Failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const confirmDelete = async () => {
    if (!docToDelete) return;
    try {
      setDeleting(true);
      await api.deleteDocument(docToDelete.id);
      showToast('success', `"${docToDelete.original_filename}" and its vector index chunks were deleted.`, 'Document Removed');
      setDocToDelete(null);
      if (selectedDoc?.id === docToDelete.id) setSelectedDoc(null);
      fetchDocuments();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to delete document.';
      showToast('error', msg, 'Delete Error');
    } finally {
      setDeleting(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const filteredDocs = documents.filter((doc) =>
    doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="page-wrapper">
      {/* Upload Dropzone */}
      <div
        className="card"
        style={{
          marginBottom: '2rem',
          border: dragActive ? '2px dashed var(--primary-500)' : '2px dashed var(--border-card)',
          backgroundColor: dragActive ? 'rgba(124, 58, 237, 0.08)' : 'var(--bg-surface)',
          padding: '2.5rem 1.5rem',
          textAlign: 'center',
          cursor: uploading ? 'wait' : 'pointer',
          transition: 'all var(--transition-normal)',
        }}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFileUpload(e.target.files[0]);
            }
          }}
        />

        {uploading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <span className="spinner" style={{ width: '2rem', height: '2rem' }} />
            <div>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>Extracting & Indexing PDF...</h3>
              <p style={{ fontSize: '0.85rem' }}>
                PyPDF extracting text • SentenceTransformers generating embeddings • FAISS updating
              </p>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '54px',
                height: '54px',
                borderRadius: '50%',
                background: 'rgba(124, 58, 237, 0.14)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--primary-400)',
                marginBottom: '0.25rem',
              }}
            >
              <Upload size={24} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: '0.35rem' }}>
                Drop your PDF study notes here, or <span style={{ color: 'var(--primary-400)' }}>browse files</span>
              </h3>
              <p style={{ fontSize: '0.82rem' }}>
                Supports standard text PDFs up to 50 MB. Preserves page numbers and generates overlapping chunks.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Document Library Header & Filter */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.25rem' }}>
        <div>
          <h3>Uploaded Documents ({documents.length})</h3>
          <p style={{ fontSize: '0.82rem' }}>All materials indexed locally in FAISS vector store</p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: '260px' }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
            <input
              type="text"
              className="input"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '36px', fontSize: '0.85rem' }}
            />
          </div>
        </div>
      </div>

      {/* Documents Table / Grid */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <span className="spinner" />
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
          <FileText size={40} style={{ opacity: 0.35, marginBottom: '0.75rem' }} />
          <h4 style={{ marginBottom: '0.35rem' }}>
            {searchQuery ? 'No documents match your search.' : 'No study notes uploaded yet.'}
          </h4>
          <p style={{ fontSize: '0.85rem', maxWidth: '400px', margin: '0 auto 1.25rem auto' }}>
            Upload a lecture slide deck, textbook chapter, or research paper in PDF format to get started.
          </p>
          <button className="btn btn-primary btn-sm" onClick={() => fileInputRef.current?.click()}>
            <Upload size={14} /> Upload First PDF
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {filteredDocs.map((doc) => (
            <div
              key={doc.id}
              className="card"
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '1rem',
                padding: '1.15rem 1.35rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', minWidth: '240px', flex: 1 }}>
                <div
                  style={{
                    padding: '0.65rem',
                    borderRadius: 'var(--radius-md)',
                    background: doc.status === 'processed' ? 'rgba(52, 211, 153, 0.12)' : 'rgba(251, 191, 36, 0.12)',
                    color: doc.status === 'processed' ? 'var(--emerald-400)' : 'var(--amber-400)',
                  }}
                >
                  <FileText size={22} />
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.94rem', color: 'var(--text-main)', wordBreak: 'break-word' }}>
                    {doc.original_filename}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '2px', display: 'flex', gap: '0.85rem', flexWrap: 'wrap' }}>
                    <span>{doc.page_count} page{doc.page_count === 1 ? '' : 's'}</span>
                    <span>•</span>
                    <span>{doc.chunk_count} chunks</span>
                    <span>•</span>
                    <span>{formatFileSize(doc.file_size_bytes)}</span>
                    <span>•</span>
                    <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              {/* Status & Actions */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                <StatusBadge status={doc.status} />

                {/* Quick study actions with this document */}
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onNavigate('chat', doc.id)}
                  title="Ask questions using this document"
                >
                  <MessageSquare size={14} /> Chat
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onNavigate('quizzes', doc.id)}
                  title="Generate quiz from this document"
                >
                  <HelpCircle size={14} /> Quiz
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onNavigate('flashcards', doc.id)}
                  title="Generate flashcards from this document"
                >
                  <Layers size={14} /> Flashcards
                </button>

                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => setDocToDelete(doc)}
                  title="Delete document and remove from FAISS"
                  style={{ padding: '0.4rem 0.6rem' }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!docToDelete}
        onClose={() => setDocToDelete(null)}
        title="Confirm Document Deletion"
        footer={
          <>
            <button className="btn btn-secondary btn-sm" onClick={() => setDocToDelete(null)} disabled={deleting}>
              Cancel
            </button>
            <button className="btn btn-danger btn-sm" onClick={confirmDelete} disabled={deleting}>
              {deleting ? <span className="spinner" /> : <Trash2 size={14} />} Delete Document
            </button>
          </>
        }
      >
        <p style={{ fontSize: '0.9rem', marginBottom: '0.75rem' }}>
          Are you sure you want to delete <strong>{docToDelete?.original_filename}</strong>?
        </p>
        <div style={{ fontSize: '0.82rem', color: 'var(--rose-400)', background: 'rgba(251, 113, 133, 0.08)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
          This will permanently remove the uploaded PDF, delete all {docToDelete?.chunk_count} chunk embeddings from the FAISS vector index, and cascade clean-up in SQLite.
        </div>
      </Modal>
    </div>
  );
};
