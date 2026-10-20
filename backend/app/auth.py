"""Single-owner login. Sessions are intentionally local to one server process."""
import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import deque
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parents[1] / ".env", encoding="utf-8-sig")
router = APIRouter(prefix="/auth", tags=["auth"])
SESSION_SECONDS = 12 * 60 * 60
LOGIN_LIMIT = 5
LOGIN_WINDOW = 60
_lock = threading.Lock()
_sessions: dict[str, tuple[float, str]] = {}
_attempts: deque[float] = deque()


def credentials():
    username = os.getenv("APP_USERNAME", "")
    password = os.getenv("APP_PASSWORD", "")
    if not username or not password:
        raise HTTPException(503, "Chưa cấu hình APP_USERNAME và APP_PASSWORD trên backend.")
    return username, password


def fingerprint(username, password):
    return hashlib.sha256((username + "\0" + password).encode()).hexdigest()


def token_key(token):
    return hashlib.sha256(token.encode()).hexdigest()


def bearer(request):
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    return token if scheme.lower() == "bearer" else ""


def valid_session(token):
    username, password = credentials()
    now = time.monotonic()
    with _lock:
        expired = [key for key, (expires, _) in _sessions.items() if expires <= now]
        for key in expired:
            del _sessions[key]
        session = _sessions.get(token_key(token))
        return bool(session and hmac.compare_digest(session[1], fingerprint(username, password)))


async def require_login(request: Request, call_next):
    public = (
        request.method == "OPTIONS"
        or (request.method == "GET" and request.url.path == "/health")
        or (request.method == "POST" and request.url.path == "/auth/login")
    )
    if not public:
        try:
            if not valid_session(bearer(request)):
                return JSONResponse({"detail": "Vui lòng đăng nhập lại."}, status_code=401,
                                    headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"})
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    response = await call_next(request)
    if request.url.path.startswith("/auth"):
        response.headers["Cache-Control"] = "no-store"
    return response


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=1024)


@router.post("/login")
def login(body: Login):
    username, password = credentials()
    now = time.monotonic()
    with _lock:
        while _attempts and _attempts[0] <= now - LOGIN_WINDOW:
            _attempts.popleft()
        if len(_attempts) >= LOGIN_LIMIT:
            raise HTTPException(429, "Thử đăng nhập quá nhiều lần. Vui lòng chờ một phút.",
                                headers={"Retry-After": str(max(1, int(LOGIN_WINDOW - (now - _attempts[0])) + 1))})
        _attempts.append(now)
        user_ok = hmac.compare_digest(body.username.encode(), username.encode())
        password_ok = hmac.compare_digest(body.password.encode(), password.encode())
        if not (user_ok and password_ok):
            raise HTTPException(401, "Tên đăng nhập hoặc mật khẩu không đúng.")
        token = secrets.token_urlsafe(48)
        # Bound memory even if the owner repeatedly logs in without logging out.
        for key in [key for key, (expires, _) in _sessions.items() if expires <= now]:
            del _sessions[key]
        if len(_sessions) >= 20:
            del _sessions[min(_sessions, key=lambda key: _sessions[key][0])]
        _sessions[token_key(token)] = (now + SESSION_SECONDS, fingerprint(username, password))
    return {"access_token": token, "token_type": "bearer", "expires_in": SESSION_SECONDS}


@router.get("/session")
def session():
    return {"username": credentials()[0]}


@router.post("/logout")
def logout(request: Request):
    with _lock:
        _sessions.pop(token_key(bearer(request)), None)
    return {"ok": True}
