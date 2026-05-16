"""Config router — /api/config/* endpoints (Phase 10-A)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.config_service import (
    CONFIG_UPDATE_WHITELIST,
    delete_strategy_preset_by_name,
    get_secrets_status,
    get_strategy_presets_config,
    read_config,
    restore_strategy_defaults,
    update_config,
    update_secrets,
    upsert_strategy_preset,
)

router = APIRouter(prefix="/api/config", tags=["config"])


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class ConfigPatchRequest(BaseModel):
    patch: dict[str, Any]


class SecretsUpdateRequest(BaseModel):
    keys: dict[str, str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
def get_config_endpoint() -> dict[str, Any]:
    """Return current config with secrets masked."""
    config = read_config(mask_secrets=True)
    return {"data": config, "meta": {}}


@router.put("")
def put_config_endpoint(request: ConfigPatchRequest) -> dict[str, Any]:
    """Apply a partial config update (whitelist-only)."""
    try:
        update_config(request.patch)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "WHITELIST_REJECTED", "message": str(exc)}},
        ) from exc
    return {"data": {"updated": True}, "meta": {}}


@router.put("/secrets")
def put_secrets(request: SecretsUpdateRequest) -> dict[str, Any]:
    """Write-only: store API keys in .env.  Never returns key values."""
    try:
        update_secrets(request.keys)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "UNKNOWN_PROVIDER", "message": str(exc)}},
        ) from exc
    return {"data": {"updated": True}, "meta": {}}


@router.get("/secrets/status")
def get_secrets_status_endpoint() -> dict[str, Any]:
    """Return boolean configured status for each API key."""
    status = get_secrets_status()
    return {"data": status, "meta": {}}


@router.get("/strategies")
def get_strategies() -> dict[str, Any]:
    """Return strategy preset list."""
    presets = get_strategy_presets_config()
    return {"data": presets, "meta": {"count": len(presets)}}


class StrategyPresetUpsertRequest(BaseModel):
    preset: dict[str, Any]


@router.post("/strategies", status_code=201)
def upsert_strategy(request: StrategyPresetUpsertRequest) -> dict[str, Any]:
    """Add or update a strategy preset (matched by name)."""
    try:
        upsert_strategy_preset(request.preset)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_PRESET", "message": str(exc)}},
        ) from exc
    name = str(request.preset.get("name", "")).strip()
    return {"data": {"upserted": True, "name": name}, "meta": {}}


@router.post("/strategies/restore")
def restore_strategies() -> dict[str, Any]:
    """Reset strategy presets to defaults."""
    restore_strategy_defaults()
    count = len(get_strategy_presets_config())
    return {"data": {"count": count}, "meta": {}}


@router.delete("/strategies/{name}", status_code=204)
def delete_strategy(name: str) -> None:
    """Delete strategy preset by name. Idempotent — name not found is not an error."""
    delete_strategy_preset_by_name(name)
    return None
