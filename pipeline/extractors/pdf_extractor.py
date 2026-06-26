"""
PDF 文本提取器 (基于 PyMuPDF)
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Iterator
import config


def extract_pdf_text(file_path: str | Path) -> list[dict]:
    """提取 PDF 中每一页的文本和图片信息

    Returns:
        [{"page_num": int, "text": str, "images": int (图片数量)}, ...]
    """
    file_path = Path(file_path)
    doc = fitz.open(str(file_path))
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text()
        # 统计嵌入图片数量
        images = page.get_images(full=True)
        pages.append({
            "page_num": i + 1,
            "text": text.strip(),
            "image_count": len(images),
        })

    doc.close()
    return pages


def extract_pdf_full_text(file_path: str | Path) -> str:
    """提取 PDF 全部文本（合并所有页）"""
    pages = extract_pdf_text(file_path)
    full_text = "\n\n".join(
        f"--- 第{p['page_num']}页 ---\n{p['text']}"
        for p in pages if p["text"].strip()
    )
    return full_text


def extract_pdf_images(file_path: str | Path, output_dir: str | Path = None) -> list[str]:
    """提取 PDF 中所有嵌入图片并保存"""
    file_path = Path(file_path)
    if output_dir is None:
        output_dir = config.EXTRACTED_DIR / file_path.stem / "images"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(file_path))
    saved_paths = []

    for page_num, page in enumerate(doc):
        for img_idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]

            img_path = output_dir / f"page{page_num + 1}_img{img_idx + 1}.{ext}"
            img_path.write_bytes(image_bytes)
            saved_paths.append(str(img_path))

    doc.close()
    return saved_paths


def is_scanned_pdf(file_path: str | Path, text_threshold: int = 100) -> bool:
    """判断 PDF 是否为扫描件（文本量极少）"""
    pages = extract_pdf_text(file_path)
    total_text = sum(len(p["text"]) for p in pages)
    avg_text_per_page = total_text / max(len(pages), 1)
    return avg_text_per_page < text_threshold


def scan_question_files() -> list[dict]:
    """扫描题目目录下所有 PDF 文件，返回文件信息列表"""
    questions_dir = config.QUESTIONS_DIR
    files = []

    for pdf_path in questions_dir.rglob("*.pdf"):
        pages = extract_pdf_text(pdf_path)
        total_chars = sum(len(p["text"]) for p in pages)
        files.append({
            "path": str(pdf_path),
            "relative_path": str(pdf_path.relative_to(questions_dir)),
            "pages": len(pages),
            "total_chars": total_chars,
            "is_scanned": is_scanned_pdf(pdf_path),
        })

    return files


if __name__ == "__main__":
    # 测试：列出所有 PDF 文件信息
    import sys
    sys.path.insert(0, str(config.ROOT_DIR))

    files = scan_question_files()
    for f in files:
        status = "扫描件(需OCR)" if f["is_scanned"] else "文本型"
        print(f"[{status}] {f['relative_path']} ({f['pages']}页, {f['total_chars']}字符)")