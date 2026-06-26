"""
图片 OCR 提取器 (基于 pytesseract + Pillow)
用于手机拍摄的试卷照片（JPG/PNG）
"""

from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import config


def preprocess_image(image: Image.Image) -> Image.Image:
    """图像预处理：灰度化 + 增强对比度 + 锐化 + 放大"""
    # 转为灰度
    img = image.convert("L")
    # 对比度增强
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    # 锐度增强
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    # 二值化 (大津法阈值)
    img = img.point(lambda x: 255 if x > 140 else 0, "1")
    return img


def ocr_image(
    file_path: str | Path,
    preprocess: bool = True,
    lang: str = "chi_sim+eng",
) -> str:
    """对单张图片进行 OCR 识别

    Args:
        file_path: 图片路径
        preprocess: 是否预处理
        lang: 识别语言 (chi_sim=简体中文, eng=英文)

    Returns:
        识别出的文本
    """
    file_path = Path(file_path)
    img = Image.open(str(file_path))

    if img.width < 1000 or img.height < 1000:
        # 低分辨率图片放大 2 倍
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)

    if preprocess:
        img = preprocess_image(img)

    try:
        text = pytesseract.image_to_string(img, lang=lang)
    except pytesseract.TesseractError:
        # 如果中文包不可用，退回到英文
        text = pytesseract.image_to_string(img, lang="eng")

    return text.strip()


def ocr_images_in_dir(
    dir_path: str | Path,
    extensions: tuple = (".jpg", ".jpeg", ".png", ".bmp"),
) -> list[dict]:
    """对目录下所有图片文件进行 OCR"""
    dir_path = Path(dir_path)
    results = []

    for ext in extensions:
        for img_path in dir_path.rglob(f"*{ext}"):
            try:
                text = ocr_image(img_path)
                results.append({
                    "path": str(img_path),
                    "text": text,
                    "char_count": len(text),
                })
            except Exception as e:
                print(f"  [警告] OCR 失败 {img_path}: {e}")
                results.append({
                    "path": str(img_path),
                    "text": "",
                    "char_count": 0,
                    "error": str(e),
                })

    return results


def scan_image_files() -> list[dict]:
    """扫描题目目录下所有图片文件"""
    questions_dir = config.QUESTIONS_DIR
    image_extensions = (".jpg", ".jpeg", ".png", ".bmp")

    files = []
    for ext in image_extensions:
        for img_path in questions_dir.rglob(f"*{ext}"):
            files.append({
                "path": str(img_path),
                "relative_path": str(img_path.relative_to(questions_dir)),
                "ext": ext,
            })

    return files


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(config.ROOT_DIR))

    files = scan_image_files()
    print(f"共找到 {len(files)} 个图片文件:")
    for f in files:
        print(f"  {f['relative_path']}")