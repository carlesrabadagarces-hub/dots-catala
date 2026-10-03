import httpx
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.schemas.contracts import AppSettingsSchema
from app.services.storage_service import storage_service

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

@router.get("", response_model=AppSettingsSchema)
async def get_settings():
    data = storage_service.get_public_settings()
    return AppSettingsSchema(**data)

@router.post("", response_model=AppSettingsSchema)
async def save_settings(new_settings: AppSettingsSchema):
    data = new_settings.model_dump(exclude_unset=True)
    storage_service.save_settings(data)
    if data.get("model_api_base_url") and data.get("default_model"):
        # New provider: Dots still pointing at the old provider's models would fail with "unknown model".
        storage_service.retarget_bot_models(data.get("model_ids") or [data["default_model"]], data["default_model"])
    return AppSettingsSchema(**storage_service.get_public_settings())


@router.get("/provider-models")
async def provider_models():
    """Ask the saved provider which models it offers right now (Chat Completions style /models)."""
    cfg = storage_service.get_settings()
    key, base = cfg.get("model_api_key"), (cfg.get("model_api_base_url") or "").rstrip("/")
    if not key or not base:
        raise HTTPException(status_code=400, detail="Primer desa l'adreça i la clau del proveïdor.")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"No s'ha pogut contactar amb el proveïdor ({type(exc).__name__}).")
    if res.status_code in (401, 403):
        raise HTTPException(status_code=400, detail="La clau no és vàlida o no té permís.")
    if not res.is_success:
        raise HTTPException(status_code=502, detail=f"El proveïdor ha respost amb l'error {res.status_code}.")
    try:
        items = res.json().get("data") or res.json().get("models") or []
    except ValueError:
        items = []
    ids = sorted({str(i.get("id") or i.get("name", "")).replace("models/", "") for i in items if isinstance(i, dict)} - {""})
    return {"models": ids}
