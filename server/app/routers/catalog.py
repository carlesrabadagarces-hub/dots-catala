from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic import ValidationError

from app.services import catalog_service
from app.services.catalog_service import CatalogError

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


class GenerateRequest(BaseModel):
    description: str = Field(min_length=8, max_length=2000)


@router.get("/sectors")
async def sectors():
    return catalog_service.sectors()


@router.get("")
async def list_catalog(sector: Optional[str] = None, q: str = ""):
    return catalog_service.list_catalog(sector, q)


@router.post("/generate")
async def generate(body: GenerateRequest):
    try:
        return await catalog_service.generate(body.description)
    except CatalogError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail="The generated Dot was not valid.") from exc


@router.post("/{agent_id}/install")
async def install(agent_id: str):
    try:
        return catalog_service.install(agent_id)
    except CatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
