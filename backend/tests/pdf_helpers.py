"""Helper utilities for generating authentic test PDFs in memory."""
import io
from typing import List


def generate_test_pdf(pages: List[str]) -> bytes:
    """Generates standard PDF 1.4 bytes containing specified text on each page."""
    obj_id = 3
    page_objs = []
    stream_objs = []
    page_refs = []

    for text in pages:
        p_id = obj_id
        s_id = obj_id + 1
        obj_id += 2
        page_refs.append(f"{p_id} 0 R")

        # Escape parenthesis for PDF string literals
        escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content = f"BT /F1 12 Tf 50 700 Td ({escaped_text}) Tj ET".encode("latin1", errors="replace")
        
        stream_data = (
            f"{s_id} 0 obj\n<< /Length {len(content)} >>\nstream\n".encode("latin1")
            + content
            + b"\nendstream\nendobj\n"
        )
        page_data = (
            f"{p_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {s_id} 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
            f"/BaseFont /Helvetica >> >> >> >>\nendobj\n"
        ).encode("latin1")

        page_objs.append((p_id, page_data))
        stream_objs.append((s_id, stream_data))

    catalog = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    kids = " ".join(page_refs)
    pages_obj = f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>\nendobj\n".encode("latin1")

    body = [catalog, pages_obj]
    for _, p_data in page_objs:
        body.append(p_data)
    for _, s_data in stream_objs:
        body.append(s_data)

    out = b"%PDF-1.4\n"
    offsets = [0]
    curr = len(out)
    for b in body:
        offsets.append(curr)
        out += b
        curr = len(out)

    xref_offset = len(out)
    out += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("latin1")
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode("latin1")
    out += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1")

    return out
