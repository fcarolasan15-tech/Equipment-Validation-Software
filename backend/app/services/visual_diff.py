from pathlib import Path
from app.config import settings


def compare_pdfs(baseline_pdf: Path, generated_pdf: Path) -> float:
    try:
        from pdf2image import convert_from_path
        from PIL import Image, ImageChops
        import math

        baseline_pages = convert_from_path(str(baseline_pdf), dpi=settings.pdf_render_dpi)
        generated_pages = convert_from_path(str(generated_pdf), dpi=settings.pdf_render_dpi)

        total_pixels = 0
        diff_pixels = 0

        for b_page, g_page in zip(baseline_pages, generated_pages):
            b_gray = b_page.convert("L")
            g_gray = g_page.convert("L")

            if b_gray.size != g_gray.size:
                g_gray = g_gray.resize(b_gray.size)

            diff = ImageChops.difference(b_gray, g_gray)
            w, h = diff.size
            total_pixels += w * h
            for pixel in diff.getdata():
                if pixel > 10:
                    diff_pixels += 1

        return diff_pixels / total_pixels if total_pixels > 0 else 0.0
    except Exception as e:
        return -1.0
