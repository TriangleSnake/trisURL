from fastapi import Request, HTTPException, status
from config import CONFIG
def get_current_user(request: Request):
    if CONFIG("DEV"):
        return {
            "sub": "dev",
            "email": "dev@tris.tw",
            "username": "dev"
        }
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登入")
    return user