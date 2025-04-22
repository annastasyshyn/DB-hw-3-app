from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from pathlib import Path

from app.routers import passenger_router, ticketing_router, admin_router
from app.database.config import ensure_activity_log_table_exists

app = FastAPI(title="Tariffs & Exemptions Management System")

templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(passenger_router.router, prefix="/passenger", tags=["Passenger"])
app.include_router(ticketing_router.router, prefix="/ticketing", tags=["Ticketing Staff"])
app.include_router(admin_router.router, prefix="/admin", tags=["Transport Administrator"])

@app.on_event("startup")
async def startup_event():
    ensure_activity_log_table_exists()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "title": "Tariffs & Exemptions System"}
    )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)