import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.services.whatsapp_service import WhatsAppError, whatsapp_service

router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp"])


class ConnectionCreate(BaseModel):
    bot_id: str
    label: str = "WhatsApp"
    phone_number_id: str = Field(min_length=1)
    access_token: str = Field(min_length=1)
    app_secret: str = Field(min_length=1)
    allowed_numbers: List[str] = []


class ConnectionUpdate(BaseModel):
    bot_id: Optional[str] = None
    label: Optional[str] = None
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None
    app_secret: Optional[str] = None
    allowed_numbers: Optional[List[str]] = None
    enabled: Optional[bool] = None


@router.get("/connections")
async def list_connections():
    return whatsapp_service.list_connections()


@router.post("/connections")
async def create_connection(body: ConnectionCreate):
    try:
        return whatsapp_service.create(body.model_dump())
    except WhatsAppError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/connections/{connection_id}")
async def update_connection(connection_id: str, body: ConnectionUpdate):
    try:
        updated = whatsapp_service.update(connection_id, body.model_dump(exclude_unset=True))
    except WhatsAppError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Connection not found")
    return updated


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str):
    if not whatsapp_service.delete(connection_id):
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"status": "ok", "deleted_id": connection_id}


# Public endpoints called by Meta. They are exempt from session auth in main.py
# and protected by the verify token (GET) and the HMAC signature (POST).
@router.get("/webhook/{connection_id}", response_class=PlainTextResponse)
async def verify_webhook(
    connection_id: str,
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
):
    if not whatsapp_service.verify_subscription(connection_id, mode, token):
        raise HTTPException(status_code=403, detail="Verification failed")
    return challenge


@router.post("/webhook/{connection_id}")
async def receive_webhook(connection_id: str, request: Request, background: BackgroundTasks):
    body = await request.body()
    if not whatsapp_service.valid_signature(
        connection_id, body, request.headers.get("x-hub-signature-256")
    ):
        raise HTTPException(status_code=403, detail="Invalid signature")
    try:
        payload: Dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    background.add_task(whatsapp_service.handle_payload, connection_id, payload)
    return {"status": "ok"}
