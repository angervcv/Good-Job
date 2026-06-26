"""
文档处理流水线编排器
负责扫描文件、提取文本、解析题目、分类、入库的完整流程
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.db.connection import get_cursor
from data.db.queries import insert_question
from pipeline.extractors.pdf_extractor import extract_pdf_full_text, scan_question_files, is_scanned_pdf
from pipeline.extractors.docx_extractor import extract_docx_full_text, extract_docx_with_tables, scan_docx_files
from pipeline.extractors.image_extractor import ocr_image, scan_image_files
from pipeline.parser import parse_text_blocks, enrich_question
from pipeline.classifier import auto_classify, get_category_id


def process_all_files(use_llm: bool = True) -> dict:
    """处理所有文档文件，提取并入库题目

    Args:
        use_llm: 是否使用 LLM 进行解析（关闭则仅用规则）

    Returns:
        处理统计信息
    """
    stats = {
        "pdf_files": 0,
        "docx_files": 0,
        "image_files": 0,
        "extracted_chars": 0,
        "parsed_questions": 0,
        "inserted_questions": 0,
        "skipped_files": [],
        "errors": [],
    }

    print("=" * 60)
    print("GoodJob 文档处理流水线")
    print(f"开始时间: {datetime.now()}")
    print("=" * 60)

    # Step 1: 扫描 PDF 文件
    print("\n[Step 1/5] 扫描 PDF 文件...")
    pdf_files = scan_question_files()
    print(f"  找到 {len(pdf_files)} 个 PDF 文件")

    for pdf in pdf_files:
        stats["pdf_files"] += 1
        rel_path = pdf["relative_path"]
        print(f"\n  处理 PDF: {rel_path}")

        # 跳过扫描件（标记为需 OCR）
        if pdf["is_scanned"]:
            msg = f"跳过扫描件(需OCR): {rel_path}"
            print(f"    {msg}")
            stats["skipped_files"].append(msg)
            continue

        # 跳过纯知识点文档（非题目）
        if _is_knowledge_doc(rel_path):
            msg = f"跳过知识点文档: {rel_path}"
            print(f"    {msg}")
            stats["skipped_files"].append(msg)
            continue

        try:
            text = extract_pdf_full_text(pdf["path"])
            stats["extracted_chars"] += len(text)
            print(f"    提取 {len(text)} 字符")

            if use_llm:
                questions = parse_text_blocks(text, source=rel_path)
                print(f"    解析出 {len(questions)} 道题目")

                for q in questions:
                    q = enrich_question(q)
                    q_id = _insert_parsed_question(q, source_file=rel_path)
                    if q_id:
                        stats["inserted_questions"] += 1

                stats["parsed_questions"] += len(questions)
            else:
                print(f"    (LLM 解析已禁用，跳过)")
        except Exception as e:
            msg = f"PDF 处理失败 {rel_path}: {e}"
            print(f"    [错误] {msg}")
            stats["errors"].append(msg)

    # Step 2: 扫描 DOCX 文件
    print("\n[Step 2/5] 扫描 DOCX 文件...")
    docx_files = scan_docx_files()
    print(f"  找到 {len(docx_files)} 个 DOCX 文件")

    for docx in docx_files:
        stats["docx_files"] += 1
        rel_path = docx["relative_path"]
        print(f"\n  处理 DOCX: {rel_path}")

        if _is_knowledge_doc(rel_path):
            msg = f"跳过知识点文档: {rel_path}"
            print(f"    {msg}")
            stats["skipped_files"].append(msg)
            continue

        try:
            text = extract_docx_with_tables(docx["path"])
            stats["extracted_chars"] += len(text)
            print(f"    提取 {len(text)} 字符")

            if use_llm:
                questions = parse_text_blocks(text, source=rel_path)
                print(f"    解析出 {len(questions)} 道题目")

                for q in questions:
                    q = enrich_question(q)
                    q_id = _insert_parsed_question(q, source_file=rel_path)
                    if q_id:
                        stats["inserted_questions"] += 1

                stats["parsed_questions"] += len(questions)
            else:
                print(f"    (LLM 解析已禁用，跳过)")
        except Exception as e:
            msg = f"DOCX 处理失败 {rel_path}: {e}"
            print(f"    [错误] {msg}")
            stats["errors"].append(msg)

    # Step 3: 扫描 JPG/PNG 图片
    print("\n[Step 3/5] 扫描图片文件...")
    img_files = scan_image_files()
    print(f"  找到 {len(img_files)} 个图片文件")

    for img in img_files:
        stats["image_files"] += 1
        rel_path = img["relative_path"]
        print(f"\n  处理图片: {rel_path}")

        try:
            text = ocr_image(img["path"])
            stats["extracted_chars"] += len(text)
            print(f"    OCR 提取 {len(text)} 字符")

            if text and use_llm:
                questions = parse_text_blocks(text, source=rel_path)
                print(f"    解析出 {len(questions)} 道题目")

                for q in questions:
                    q = enrich_question(q)
                    q_id = _insert_parsed_question(q, source_file=rel_path)
                    if q_id:
                        stats["inserted_questions"] += 1

                stats["parsed_questions"] += len(questions)
            elif not text:
                print(f"    OCR 未提取到文本，可尝试手动录入")
                stats["skipped_files"].append(f"OCR无文本: {rel_path}")
        except Exception as e:
            msg = f"图片处理失败 {rel_path}: {e}"
            print(f"    [错误] {msg}")
            stats["errors"].append(msg)

    # Step 4: 统计
    print("\n" + "=" * 60)
    print(f"[Step 4/5] 处理完成统计")
    print(f"  PDF 文件: {stats['pdf_files']}")
    print(f"  DOCX 文件: {stats['docx_files']}")
    print(f"  图片文件: {stats['image_files']}")
    print(f"  提取字符: {stats['extracted_chars']}")
    print(f"  解析题目: {stats['parsed_questions']}")
    print(f"  入库题目: {stats['inserted_questions']}")
    print(f"  跳过文件: {len(stats['skipped_files'])}")
    print(f"  错误: {len(stats['errors'])}")

    # 打印错误和跳过
    if stats["skipped_files"]:
        print(f"\n  跳过的文件:")
        for s in stats["skipped_files"]:
            print(f"    - {s}")
    if stats["errors"]:
        print(f"\n  错误:")
        for e in stats["errors"]:
            print(f"    - {e}")

    return stats


def _insert_parsed_question(q: dict, source_file: str) -> int | None:
    """将解析后的题目字典插入数据库"""
    try:
        question_text = q.get("question_text", "")
        if not question_text or len(question_text) < 10:
            return None

        # 处理 options（如果是选择题）
        options = q.get("options")
        if options and isinstance(options, list):
            options = json.dumps(options, ensure_ascii=False)

        # 处理 keywords
        keywords = q.get("keywords", [])
        if isinstance(keywords, list):
            keywords = ",".join(keywords)

        return insert_question(
            question_type=q.get("question_type", "short_answer"),
            question_text=question_text,
            category_id=q.get("category_id"),
            answer_text=q.get("answer_text", ""),
            explanation=q.get("explanation", ""),
            keywords=keywords,
            difficulty=q.get("difficulty", 3),
            title=q.get("title", ""),
            options=options,
            is_ai_generated=0,
            source_file=source_file,
        )
    except Exception as e:
        print(f"    [入库失败] {e}")
        return None


def _is_knowledge_doc(relative_path: str) -> bool:
    """判断文件是否为知识点文档（非题目）"""
    knowledge_indicators = [
        "知识点",
        "BCD工艺综述",
        "精通开关电源设计笔记",
        "栅电荷测试方法研究",
        "UIS_开关_反向恢复",
        "可靠性测试",
        "MOSFET开关过程",
        "功率MOS器件UIS失效",
        "问题总结",
    ]
    return any(ind in relative_path for ind in knowledge_indicators)


def run_dry_run() -> dict:
    """干运行：仅扫描统计，不实际解析"""
    print("=" * 60)
    print("GoodJob 文档扫描 (干运行)")
    print("=" * 60)

    pdf_files = scan_question_files()
    docx_files = scan_docx_files()
    img_files = scan_image_files()

    result = {
        "pdf_files": pdf_files,
        "docx_files": docx_files,
        "image_files": img_files,
        "total_files": len(pdf_files) + len(docx_files) + len(img_files),
    }

    print(f"\nPDF 文件: {len(pdf_files)}")
    for f in pdf_files:
        status = "扫描件(需OCR)" if f["is_scanned"] else "文本型"
        print(f"  [{status}] {f['relative_path']} ({f['pages']}页, {f['total_chars']}字符)")

    print(f"\nDOCX 文件: {len(docx_files)}")
    for f in docx_files:
        print(f"  {f['relative_path']} ({f['paragraphs']}段, {f['total_chars']}字符)")

    print(f"\n图片文件: {len(img_files)}")
    for f in img_files:
        print(f"  {f['relative_path']}")

    print(f"\n总计: {result['total_files']} 个文件")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GoodJob 文档处理流水线")
    parser.add_argument("--dry-run", action="store_true", help="仅扫描文件，不实际处理")
    parser.add_argument("--no-llm", action="store_true", help="不使用 LLM 解析")
    args = parser.parse_args()

    if args.dry_run:
        run_dry_run()
    else:
        process_all_files(use_llm=not args.no_llm)