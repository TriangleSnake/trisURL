import os
import secrets
import shutil
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import Session, select
from sqlalchemy import func
from database import init_db, engine
from models import URL
import mimetypes
from urllib.parse import quote
from routes_auth import router as auth_router
from auth_utils import get_current_user
import secrets
from config import CONFIG

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))
app.include_router(auth_router)
templates = Jinja2Templates(directory="templates")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
init_db()

def check_valid_session(request: Request):
    if "user" not in request.session or "expire" not in request.session:
        return False
    expire_time = datetime.fromisoformat(request.session["expire"])
    if expire_time < datetime.now():
        return False
    return True

def filename_sanitize(filename: str) -> str:
    blacklist = ["..", "/", "\\","\n","\r"]
    for item in blacklist:
        if item in filename:
            return "malicious_filename"
    return filename

def cleanup_expired_entries():
    now = datetime.utcnow()
    with Session(engine) as session:
        expired_urls = session.exec(
            select(URL).where(URL.expires_at != None, URL.expires_at < now, URL.is_expired == False)
        ).all()

        for url in expired_urls:
            if url.file_path and os.path.exists(url.file_path):
                os.remove(url.file_path)
                print(f"已刪除過期檔案: {url.file_path}")

            url.is_expired = True
            session.add(url)

        session.commit()
        if expired_urls:
            print(f"✅ 清除完成，共標記 {len(expired_urls)} 筆為過期")

@app.on_event("startup")
def on_startup():
    cleanup_expired_entries()

@app.get("/")
def dashboard(
    request: Request,
    page_active: int = 1,
    page_expired: int = 1,
    page_size: int = 10
):  
    if CONFIG("DEV") == "true":
        request.session["user"] = {
            "sub": "dev",
            "username": "dev",
            "email": "dev@tris.tw"
        }
        request.session["expire"] = (datetime.now() + timedelta(hours=1)).isoformat()
    
    if not check_valid_session(request):
        return RedirectResponse("/login", status_code=303)

    user = request.session["user"]
    offset_active = (page_active - 1) * page_size
    offset_expired = (page_expired - 1) * page_size

    with Session(engine) as session:
        active_urls = session.exec(
            select(URL)
            .where(URL.is_expired == False)
            .order_by(URL.created_at.desc())
            .offset(offset_active)
            .limit(page_size)
        ).all()

        expired_urls = session.exec(
            select(URL)
            .where(URL.is_expired == True)
            .order_by(URL.created_at.desc())
            .offset(offset_expired)
            .limit(page_size)
        ).all()

        total_active = session.exec(
            select(func.count()).select_from(URL).where(URL.is_expired == False)
        ).one()

        total_expired = session.exec(
            select(func.count()).select_from(URL).where(URL.is_expired == True)
        ).one()

    return templates.TemplateResponse("index.html", {
        "site_name": CONFIG("SITE_NAME"),
        "domain": CONFIG("DOMAIN"),
        "request": request,
        "active_urls": active_urls,
        "expired_urls": expired_urls,
        "page_active": page_active,
        "page_expired": page_expired,
        "page_size": page_size,
        "has_next_active": total_active > page_active * page_size,
        "has_next_expired": total_expired > page_expired * page_size,
        "user": user
    })

@app.post("/shorten")
async def shorten(
    request: Request,
    original_url: str = Form(None),
    file: UploadFile = File(None),
    expires_in_days: int = Form(30)
):
    if not check_valid_session(request):
        return RedirectResponse("/login", status_code=303)
    
    user = get_current_user(request)

    short_code = secrets.token_urlsafe(4)
    url_data = URL(short_code=short_code, created_by=user["username"])

    if original_url:
        if not original_url.startswith(("http://", "https://")):
            original_url = "https://" + original_url
        url_data.original_url = original_url

    elif file and file.filename!="":
        safe_name = f"{short_code}"
        save_path = os.path.join(UPLOAD_DIR, safe_name)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        url_data.file_path = save_path
        url_data.file_name = filename_sanitize(file.filename)

    else:
        return HTMLResponse("<h2>請提供網址或檔案</h2>", status_code=400)

    if expires_in_days != 0:
        url_data.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    else:
        url_data.expires_at = None

    with Session(engine) as session:
        session.add(url_data)
        session.commit()

    return RedirectResponse("/", status_code=303)

@app.get("/{short_code}")
def handle_short_code(short_code: str, request: Request):
    with Session(engine) as session:
        url = session.exec(select(URL).where(URL.short_code == short_code)).first()

        if not url or url.is_expired or (url.file_path and not os.path.exists(url.file_path)):
            return HTMLResponse("<h2>找不到此短網址</h2>", status_code=404)

        if url.file_path:
            mime_type, _ = mimetypes.guess_type(url.file_name or "")
            if mime_type and (mime_type.startswith("image/") or mime_type == "application/pdf"):
                media_type = mime_type
            else:
                media_type = "application/octet-stream"

            quoted_filename = quote(url.file_name)
            if "view" in request.query_params:
                disposition = f"inline; filename*=UTF-8''{quoted_filename}"
            else:
                disposition = f"attachment; filename*=UTF-8''{quoted_filename}"

            return FileResponse(
                url.file_path,
                media_type=media_type,
                filename=url.file_name,
                headers={"Content-Disposition": disposition}
            )

        elif url.original_url:
            return RedirectResponse(url.original_url)

@app.post("/delete/{url_id}")
def delete_url(url_id: int, request: Request):
    if not check_valid_session(request):
        return RedirectResponse("/login", status_code=303)
    user = get_current_user(request)
    with Session(engine) as session:
        url = session.get(URL, url_id)
        if url:
            if url.file_path and os.path.exists(url.file_path):
                os.remove(url.file_path)
            session.delete(url)
            session.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/delete_expired")
def delete_expired(request: Request):
    if not check_valid_session(request):
        return RedirectResponse("/login", status_code=303)
    user = get_current_user(request)
    with Session(engine) as session:
        expired = session.exec(select(URL).where(URL.is_expired == True)).all()
        for url in expired:
            if url.file_path and os.path.exists(url.file_path):
                os.remove(url.file_path)
            session.delete(url)
        session.commit()
    return RedirectResponse("/", status_code=303)