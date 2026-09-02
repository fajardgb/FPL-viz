"""
main.py — FastAPI app: the league-ID/GW form, the generated report, and the
PDF export. Rate-limited per IP since this is a public tool that fans out to
the FPL API on arbitrary league IDs.
"""
from pathlib import Path

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import cache, fpl_client, pdf as pdf_module, report
from app.fpl_client import FPLError

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="FPL League Reports")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
cache.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(cache.OUTPUT_DIR)), name="reports")


@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    current_gw = await report.get_current_gw()
    return templates.TemplateResponse(
        "form.html", {"request": request, "current_gw": current_gw, "error": None}
    )


@app.post("/report", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def make_report(request: Request, league_id: str = Form(...), gw: str = Form(...)):
    try:
        data = await report.build_report(league_id, gw)
    except FPLError as exc:
        current_gw = await report.get_current_gw()
        return templates.TemplateResponse(
            "form.html",
            {"request": request, "current_gw": current_gw, "error": str(exc)},
            status_code=400,
        )
    return templates.TemplateResponse("report.html", {"request": request, **data})


@app.get("/report/{league_id}/{gw}/pdf")
@limiter.limit("10/minute")
async def report_pdf(request: Request, league_id: str, gw: str):
    try:
        data = await report.build_report(league_id, gw)

        async with httpx.AsyncClient() as client:
            bootstrap = await report._get_bootstrap(client)
        event_info = fpl_client.get_event_info(bootstrap, data["gw"])
        ttl = cache.gw_ttl(event_info)

        pdf_path = await pdf_module.get_or_build_pdf(
            data["league_id"], data["gw"], data["chart_names"], ttl
        )
    except FPLError as exc:
        current_gw = await report.get_current_gw()
        return templates.TemplateResponse(
            "form.html",
            {"request": request, "current_gw": current_gw, "error": str(exc)},
            status_code=400,
        )
    filename = f"{data['league_name']}_GW{data['gw']}.pdf".replace(" ", "_")
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
