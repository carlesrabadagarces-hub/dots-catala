from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.services import usage_service
from app.services.context import current_owner
from app.services.user_service import user_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_admin(request: Request) -> dict:
    user = getattr(request.state, "user", None) or {}
    if user.get("role") not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Només per a administradors.")
    return user


class UserControls(BaseModel):
    disabled: Optional[bool] = None
    token_limit: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    clear_token_limit: bool = False


@router.get("/stats")
async def stats(request: Request, days: int = Query(30, ge=1, le=365)):
    _require_admin(request)
    return usage_service.stats(days)


@router.patch("/users/{user_id}")
async def update_user(user_id: str, body: UserControls, request: Request):
    admin = _require_admin(request)
    target = user_service.get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuari no trobat.")
    if target["role"] in {"admin", "owner"} and body.disabled:
        raise HTTPException(status_code=400, detail="No es pot suspendre un administrador.")
    if user_id == admin.get("id") and body.disabled:
        raise HTTPException(status_code=400, detail="No et pots suspendre a tu mateix.")
    limit = "keep"
    if body.clear_token_limit:
        limit = None
    elif body.token_limit is not None:
        limit = body.token_limit or None
    return user_service.set_controls(user_id, body.disabled, limit)
