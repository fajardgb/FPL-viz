"""
pdf.py — assemble a report's chart PNGs into a single downloadable PDF.
Pure Pillow, no HTML/WeasyPrint/system-library dependency.
"""
from pathlib import Path

from PIL import Image

from app import cache


def _pdf_path(league_id: int, gw: int) -> Path:
    return cache.report_output_dir(league_id, gw) / "report.pdf"


def build_pdf(league_id: int, gw: int, chart_names: list[str]) -> Path:
    save_dir = cache.report_output_dir(league_id, gw)
    out_path = _pdf_path(league_id, gw)

    pages = []
    cover = save_dir / "cover.png"
    if cover.exists():
        pages.append(Image.open(cover).convert("RGB"))
    for name in chart_names:
        pages.append(Image.open(save_dir / name).convert("RGB"))

    if not pages:
        raise ValueError("No charts available to build a PDF from.")

    first, rest = pages[0], pages[1:]
    first.save(out_path, save_all=True, append_images=rest)
    return out_path


async def get_or_build_pdf(league_id: int, gw: int, chart_names: list[str], ttl) -> Path:
    path = _pdf_path(league_id, gw)
    key = cache.make_key(league_id, gw, "pdf_built")
    if cache.get(key) and path.exists():
        return path
    build_pdf(league_id, gw, chart_names)
    cache.set(key, True, ttl)
    return path
