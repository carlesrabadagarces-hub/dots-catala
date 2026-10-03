from urllib.parse import urlparse

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.services.auth_service import auth_service
from app.services.context import current_owner
from app.services import password_login
from app.services.oauth_service import BINDING_COOKIE, OAuthError, oauth_service
from app.services.storage_service import storage_service
from app.services.user_service import SignupError, user_service


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    token: str = Field(min_length=1)


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _session_payload(user):
    return {"authenticated": True, "user": user}


def _base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _signup_open() -> bool:
    return settings.SIGNUP_OPEN not in {"0", "false", "no"}


def _providers():
    return {**oauth_service.enabled(), **password_login.enabled(), "signup": _signup_open(), "local": oauth_service.local_login_allowed(),
            "dev_hint": password_login.dev_mode() and not settings.TEST_MEMBER_PASSWORD and not settings.ADMIN_PASSWORD}


@router.get("/status")
async def auth_status(request: Request):
    user = auth_service.authenticate_request(request)
    return {
        "auth_required": True,
        "authenticated": bool(user),
        "bootstrap_available": auth_service.can_bootstrap(request),
        "user": user,
        "providers": _providers(),
    }


@router.get("/session")
async def establish_session(request: Request, response: Response):
    user = auth_service.authenticate_request(request)
    if not user:
        raise _authentication_error()
    auth_service.set_session_cookie(response, secure=request.url.scheme == "https", user_id=user["id"])
    return _session_payload(user)


@router.post("/login")
async def login(credentials: LoginRequest, request: Request, response: Response):
    if not oauth_service.local_login_allowed() or not auth_service.authenticate_token(credentials.token):
        raise _authentication_error()
    auth_service.set_session_cookie(response, secure=request.url.scheme == "https")
    return _session_payload(auth_service.user)


class PasswordLogin(BaseModel):
    username: str = Field(default="", max_length=60)
    password: str = Field(min_length=1, max_length=200)


@router.post("/login/password")
async def login_password(body: PasswordLogin, request: Request, response: Response):
    key = request.client.host if request.client else "?"
    if password_login.limiter.blocked(key):
        raise HTTPException(status_code=429, detail="Massa intents. Espera un minut.")
    if "@" in body.username:
        account = user_service.verify_password(body.username, body.password)
        if not account:
            password_login.limiter.fail(key)
            raise HTTPException(status_code=401, detail="Correu o contrasenya incorrectes.")
        if account["disabled"]:
            raise HTTPException(status_code=403, detail="Compte suspès.")
        password_login.limiter.clear(key)
        return _start_session(account, request, response)
    kind = password_login.check(body.username, body.password)
    if not kind:
        password_login.limiter.fail(key)
        raise HTTPException(status_code=401, detail="Usuari o contrasenya incorrectes.")
    password_login.limiter.clear(key)
    if kind == "admin":
        user = user_service.upsert_social("admin", "admin", "", "Administrador", role="admin")
    else:
        who = password_login.slug(body.username)
        user = user_service.upsert_social("test", who, "", body.username.strip() or "Provador")
    if user["disabled"]:
        raise HTTPException(status_code=403, detail="Compte suspès.")
    return _start_session(user, request, response)


def _start_session(user, request: Request, response: Response):
    token = current_owner.set(user["id"])
    try:
        storage_service.seed_owner()
    finally:
        current_owner.reset(token)
    auth_service.set_session_cookie(response, secure=request.url.scheme == "https", user_id=user["id"])
    return _session_payload(user)


class Signup(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)
    name: str = Field(default="", max_length=80)


@router.post("/register")
async def register(body: Signup, request: Request, response: Response):
    if not _signup_open():
        raise HTTPException(status_code=403, detail="Ara mateix no s'accepten comptes nous.")
    key = "signup:" + (request.client.host if request.client else "?")
    if password_login.limiter.blocked(key):
        raise HTTPException(status_code=429, detail="Massa intents. Espera un minut.")
    password_login.limiter.fail(key)  # every attempt counts: this is the throttle for account creation
    try:
        user = user_service.register_password(body.email, body.password, body.name)
    except SignupError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _start_session(user, request, response)


@router.post("/logout")
async def logout(request: Request, response: Response):
    auth_service.clear_request_session(request, response)
    return {"authenticated": False}


@router.get("/oauth/{provider}/start")
async def oauth_start(provider: str, request: Request):
    if not oauth_service.enabled().get(provider):
        raise HTTPException(status_code=404, detail="This sign-in method is not configured.")
    url, nonce = oauth_service.authorize_url(provider, _base(request))
    secure = (settings.PUBLIC_BASE_URL or _base(request)).startswith("https")
    response = RedirectResponse(url, status_code=302)
    response.set_cookie(BINDING_COOKIE, oauth_service.binding(nonce), max_age=600, httponly=True,
                        secure=secure, samesite="none" if secure else "lax")
    return response


def _fail(message: str) -> RedirectResponse:
    from urllib.parse import quote

    return RedirectResponse(f"{settings.FRONTEND_URL}/?login_error={quote(message)}", status_code=303)


async def _finish(provider: str, request: Request, code: str, state: str, apple_user=None):
    if not oauth_service.enabled().get(provider):
        raise HTTPException(status_code=404, detail="This sign-in method is not configured.")
    secure = (settings.PUBLIC_BASE_URL or _base(request)).startswith("https")
    try:
        identity = await oauth_service.complete(
            provider, code, state, request.cookies.get(BINDING_COOKIE), _base(request), secure, apple_user)
    except OAuthError as exc:
        return _fail(str(exc))
    admins = {e.strip().lower() for e in settings.ADMIN_EMAILS.split(",") if e.strip()}
    is_admin = identity["email_verified"] and identity["email"].lower() in admins
    user = user_service.upsert_social(provider, identity["sub"], identity["email"], identity["name"],
                                      identity["picture"], identity["email_verified"],
                                      role="admin" if is_admin else "member")
    if is_admin and user["role"] != "admin":
        user = user_service.set_role(user["id"], "admin")
    if user["disabled"]:
        return _fail("Compte suspès.")
    token = current_owner.set(user["id"])
    try:
        storage_service.seed_owner()
    finally:
        current_owner.reset(token)
    response = RedirectResponse(settings.FRONTEND_URL + "/", status_code=303)
    auth_service.set_session_cookie(response, secure=secure, user_id=user["id"])
    response.delete_cookie(BINDING_COOKIE)
    return response


@router.get("/oauth/{provider}/callback")
async def oauth_callback_get(provider: str, request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return _fail("Inici de sessió cancel·lat.")
    return await _finish(provider, request, code, state)


@router.post("/oauth/{provider}/callback")
async def oauth_callback_post(provider: str, request: Request, code: str = Form(""), state: str = Form(""),
                              error: str = Form(""), user: str = Form("")):
    if error or not code:
        return _fail("Inici de sessió cancel·lat.")
    return await _finish(provider, request, code, state, apple_user=user or None)
