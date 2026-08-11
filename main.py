"""
AI Service — chạy độc lập bên cạnh Phoenix/WordPress hiện có.

Kiến trúc:
    Flutter -> Phoenix/WordPress -> AI Service (FastAPI, file này) -> CrewAI agents
                                         |
                                         v
                              gọi ngược vào REST API WordPress
                              (finding-keo/nearby, my-keo, invite/detail...)
                              để lấy dữ liệu thật, không đọc thẳng MySQL.

Chạy dev:
    uvicorn main:app --reload --port 8088

Chạy production (xem README.md phần systemd):
    uvicorn main:app --host 0.0.0.0 --port 8088 --workers 2
"""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from loguru import logger

import crew
from config.settings import get_settings
from schemas import MatchRequest, ModerateRequest, RecommendRequest

settings = get_settings()
app = FastAPI(title="Nhau AI Service", version="0.1.0")


def _check_internal_key(x_internal_key: str | None) -> None:
    """Chặn việc route bị gọi thẳng từ bên ngoài — chỉ Phoenix/WordPress backend
    (giữ key trong biến môi trường của họ) mới gọi được vào AI Service này.
    """
    if not x_internal_key or x_internal_key != settings.ai_service_internal_key:
        raise HTTPException(status_code=401, detail="Thiếu hoặc sai X-Internal-Key")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/match")
def match(req: MatchRequest, x_internal_key: str | None = Header(default=None)) -> dict:
    _check_internal_key(x_internal_key)
    logger.info(f"[/match] user_id={req.user_id} lat={req.lat} lng={req.lng}")
    try:
        result = crew.run_match(req.user_id, req.lat, req.lng, req.radius_km)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[/match] lỗi khi chạy Match Agent")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"success": True, "data": result}


@app.post("/recommend")
def recommend(req: RecommendRequest, x_internal_key: str | None = Header(default=None)) -> dict:
    _check_internal_key(x_internal_key)
    logger.info(f"[/recommend] user_id={req.user_id} district={req.district}")
    try:
        result = crew.run_recommendation(req.user_id, req.district)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[/recommend] lỗi khi chạy Recommendation Agent")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"success": True, "data": result}


@app.post("/moderate")
def moderate(req: ModerateRequest, x_internal_key: str | None = Header(default=None)) -> dict:
    _check_internal_key(x_internal_key)
    logger.info(f"[/moderate] content_type={req.content_type} len={len(req.content)}")
    try:
        result = crew.run_moderation(req.content, req.content_type)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[/moderate] lỗi khi chạy Moderation Agent")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"success": True, "data": result}
