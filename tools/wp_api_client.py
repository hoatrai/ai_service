"""
Client gọi thẳng vào các route REST đã có sẵn trong plugin custom-api-core
(namespace `nhau/v1` và `custom/v1`) — KHÔNG đọc thẳng MySQL, để tránh app
Flutter và AI Service đá dữ liệu chéo nhau / trùng logic validate.

Các route tham chiếu (đọc trực tiếp từ code plugin lúc viết file này):
  - GET  custom/v1/finding-keo/nearby   (finding-keo.php)
  - GET  nhau/v1/my-keo                 (my-keo.php)
  - GET  nhau/v1/invite/detail          (invite-api.php)
  - GET  nhau/v1/user-stats/{user_id}   (invite-api.php)
  - POST nhau/v1/user-stats-bulk        (invite-api.php)
"""
from __future__ import annotations

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import get_settings

settings = get_settings()

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _client(jwt: str | None = None) -> httpx.Client:
    headers = {"Content-Type": "application/json"}
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    return httpx.Client(base_url=settings.wordpress_base_url, headers=headers, timeout=_TIMEOUT)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4))
def get_nearby_users(lat: float, lng: float, radius_km: float = 3.0) -> list[dict]:
    """Gọi custom/v1/finding-keo/nearby — danh sách user đang bật radar quanh 1 toạ độ.

    Lưu ý: route hiện tại trong finding-keo.php lọc theo district/hoạt động, KHÔNG
    tự tính khoảng cách km hay điểm phù hợp — việc đó là phần AI Service này thêm vào.
    """
    with _client() as client:
        resp = client.get(
            "/wp-json/custom/v1/finding-keo/nearby",
            params={"lat": lat, "lng": lng, "radius_km": radius_km},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("users", data if isinstance(data, list) else [])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4))
def get_open_invites(district: str | None = None) -> list[dict]:
    """Lấy danh sách kèo đang mở. Dùng nhau/v1/my-keo hoặc /wc/v3/products tuỳ triển khai
    thực tế — ở đây gọi endpoint chung, anh chỉnh lại cho khớp response thật của site.
    """
    with _client() as client:
        params = {"status": "open"}
        if district:
            params["district"] = district
        resp = client.get("/wp-json/nhau/v1/my-keo", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("invites", data if isinstance(data, list) else [])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4))
def get_invite_detail(invite_id: int) -> dict:
    with _client() as client:
        resp = client.get("/wp-json/nhau/v1/invite/detail", params={"invite_id": invite_id})
        resp.raise_for_status()
        return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4))
def get_user_stats(user_id: int) -> dict:
    """nhau/v1/user-stats/{user_id} — lịch sử tham gia kèo, trust rating... dùng để
    cá nhân hoá matching (thay vì chỉ lọc theo khoảng cách/quận như hiện tại).
    """
    with _client() as client:
        resp = client.get(f"/wp-json/nhau/v1/user-stats/{user_id}")
        resp.raise_for_status()
        return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4))
def get_user_stats_bulk(user_ids: list[int]) -> dict:
    with _client() as client:
        resp = client.post("/wp-json/nhau/v1/user-stats-bulk", json={"user_ids": user_ids})
        resp.raise_for_status()
        return resp.json()


def safe_call(fn, *args, default=None, **kwargs):
    """Bọc lỗi mạng/HTTP để 1 nguồn dữ liệu lỗi không làm sập cả agent."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[wp_api_client] {fn.__name__} thất bại: {exc}")
        return default
