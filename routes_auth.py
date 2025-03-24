from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from auth import oauth
from auth import config
router = APIRouter()

@router.get("/login")
async def login(request: Request):
    redirect_url = config("REDIRECT_URL")
    return await oauth.synology.authorize_redirect(request, redirect_url)

@router.get("/relay", name="auth_callback")
async def auth_callback(request: Request):
    token = await oauth.synology.authorize_access_token(request)
    user = await oauth.synology.userinfo(token=token)

    if not user:
        raise HTTPException(status_code=400, detail="無法取得使用者資訊")

    request.session["user"] = user

    return RedirectResponse("/")

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")