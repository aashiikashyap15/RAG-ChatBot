import fitz  # PyMuPDF


def load_pdf(filepath: str) -> str:
    """Extract text from PDF with page markers."""
    text = ""
    with fitz.open(filepath) as doc:
        for page_num, page in enumerate(doc):
            page_text = page.get_text().strip()
            if page_text:
                text += f"\n[Page {page_num + 1}]\n{page_text}\n"
    return text


def load_txt(filepath: str) -> str:
    """Read plain text file."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_document(filepath: str) -> str:
    """Auto-detect file type and load."""
    ext = filepath.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return load_pdf(filepath)
    elif ext == "txt":
        return load_txt(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
