from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import auth, bots, models, chat, approvals, upload, settings as settings_router, connectors, audit, computers, whatsapp, catalog, admin
from app.services.auth_service import auth_service
from app.services.context import current_owner
from app.services.computer_provider import computer_provider
from app.services.storage_service import storage_service

app = FastAPI(
    title="Open Dots API",
    description="Open-source alternative to OpenAI Dots: self-hosted AI workspace API with a configurable inference adapter",
    version="1.0.0"
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_API_PATHS = {
    "/api/v1/health",
    "/api/v1/auth/status",
    "/api/v1/auth/session",
    "/api/v1/auth/login",
    "/api/v1/auth/login/password",
    "/api/v1/auth/logout",
}
PUBLIC_API_PREFIXES = ("/api/v1/whatsapp/webhook/", "/api/v1/auth/oauth/")


@app.middleware("http")
async def require_authentication(request: Request, call_next):
    path = request.url.path
    if (
        request.method == "OPTIONS"
        or not path.startswith("/api/v1")
        or path in PUBLIC_API_PATHS
        or path.startswith(PUBLIC_API_PREFIXES)
    ):
        return await call_next(request)

    user = auth_service.authenticate_request(request)
    if not user:
        origin = request.headers.get("origin", "")
        cors_headers = {}
        if origin in settings.CORS_ORIGINS:
            cors_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Headers": request.headers.get("access-control-request-headers", "*"),
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "Vary": "Origin",
            }
        return JSONResponse(
            {"detail": "Authentication is required."},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer", **cors_headers},
        )
    if user.get("disabled"):
        return JSONResponse({"detail": "Compte suspès."}, status_code=403)
    request.state.user = user
    token = current_owner.set(user["id"])
    try:
        return await call_next(request)
    finally:
        current_owner.reset(token)

app.include_router(auth.router)
app.include_router(bots.router)
app.include_router(models.router)
app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(approvals.router)
app.include_router(settings_router.router)
app.include_router(connectors.router)
app.include_router(audit.router)
app.include_router(computers.router)
app.include_router(whatsapp.router)
app.include_router(catalog.router)
app.include_router(admin.router)


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "online",
        "service": "Open Dots FastAPI Backend",
        "provider": "configured inference endpoint",
        "computer_provider": computer_provider.provider_name,
        "default_model": storage_service.get_settings().get("default_model") or settings.DEFAULT_MODEL
    }
