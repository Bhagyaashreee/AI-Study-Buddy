import io
import re
import logging
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger("ai_study_buddy.pdf")


class PDFProcessingException(Exception):
    """Base exception for PDF processing."""
    pass


class PDFCorruptedError(PDFProcessingException):
    """Raised when a PDF cannot be opened or parsed."""
    pass


class PDFEmptyError(PDFProcessingException):
    """Raised when a PDF has zero pages or content."""
    pass


class PDFScannedNoOCRError(PDFProcessingException):
    """Raised when a PDF contains no extractable text (image-only or scanned)."""
    pass


class PDFService:
    """Zero-cost local PDF text extraction and chunking service using PyPDF."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans excessive whitespace while preserving paragraph flow."""
        if not text:
            return ""
        # Standardize line breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace non-breaking spaces and tabs with regular space
        text = text.replace("\xa0", " ").replace("\t", " ")
        # Collapse multiple horizontal spaces into a single space
        text = re.sub(r"[ ]{2,}", " ", text)
        # Collapse 3 or more newlines into 2 (paragraphs)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def extract_text_by_pages(self, file_content: bytes) -> Tuple[List[Dict[str, Any]], int, bool]:
        """Extracts text page by page from raw PDF bytes.
        Returns:
            Tuple of:
            - pages_data: list of dicts with {"page_number": int, "text": str}
            - page_count: total page count
            - is_scanned_or_empty: True if document contains no extractable text
        """
        if not file_content:
            raise PDFEmptyError("The uploaded file is empty (0 bytes).")

        # Verify PDF magic bytes '%PDF-'
        if not file_content.startswith(b"%PDF-"):
            raise PDFCorruptedError("Invalid PDF format: file does not have a valid PDF header.")

        try:
            reader = PdfReader(io.BytesIO(file_content))
        except (PdfReadError, Exception) as exc:
            logger.error(f"Failed to read PDF: {exc}")
            raise PDFCorruptedError("Failed to parse PDF document. The file may be encrypted or corrupted.") from exc

        page_count = len(reader.pages)
        if page_count == 0:
            raise PDFEmptyError("PDF contains 0 pages.")

        pages_data: List[Dict[str, Any]] = []
        total_extracted_chars = 0

        for i, page in enumerate(reader.pages):
            page_num = i + 1  # 1-based page number
            try:
                page_text = page.extract_text() or ""
            except Exception as page_exc:
                logger.warning(f"Error extracting text from page {page_num}: {page_exc}")
                page_text = ""

            cleaned = self.clean_text(page_text)
            if cleaned:
                pages_data.append({
                    "page_number": page_num,
                    "text": cleaned
                })
                total_extracted_chars += len(cleaned)

        # Scanned PDF detection heuristic:
        # If total characters extracted across all pages is fewer than 30, it is likely an image-only scan
        is_scanned_or_empty = total_extracted_chars < 30

        return pages_data, page_count, is_scanned_or_empty

    def chunk_document(
        self,
        pages_data: List[Dict[str, Any]],
        chunk_size: int = 600,
        chunk_overlap: int = 100
    ) -> List[Dict[str, Any]]:
        """Splits page text into overlapping chunks, maintaining 1-based page numbers.
        Returns list of dicts:
        [{"chunk_index": int, "page_number": int, "content": str, "char_count": int}]
        """
        if chunk_size <= chunk_overlap:
            chunk_overlap = chunk_size // 4

        chunks: List[Dict[str, Any]] = []
        chunk_index = 0

        for page in pages_data:
            page_num = page["page_number"]
            text = page["text"]

            if not text:
                continue

            # If text fits in a single chunk, keep it intact
            if len(text) <= chunk_size:
                chunks.append({
                    "chunk_index": chunk_index,
                    "page_number": page_num,
                    "content": text,
                    "char_count": len(text)
                })
                chunk_index += 1
                continue

            # Split by paragraph/sentences when possible, otherwise sliding character window
            start = 0
            text_len = len(text)

            while start < text_len:
                end = min(start + chunk_size, text_len)
                
                # If we're not at the very end of the text, try to break on whitespace or punctuation
                if end < text_len:
                    # Look for sentence boundary or newline in the last 20% of the chunk window
                    window_cutoff = start + int(chunk_size * 0.8)
                    breakpoint = -1
                    for delim in ["\n\n", ".\n", ". ", "? ", "! ", "\n", " "]:
                        pos = text.rfind(delim, window_cutoff, end)
                        if pos != -1:
                            breakpoint = pos + len(delim)
                            break
                    if breakpoint != -1:
                        end = breakpoint

                chunk_content = text[start:end].strip()
                if chunk_content:
                    chunks.append({
                        "chunk_index": chunk_index,
                        "page_number": page_num,
                        "content": chunk_content,
                        "char_count": len(chunk_content)
                    })
                    chunk_index += 1

                # Advance window with overlap
                if end >= text_len:
                    break
                start = max(start + 1, end - chunk_overlap)

        return chunks


pdf_service = PDFService()
