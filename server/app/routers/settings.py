from fastapi import APIRouter
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
