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

import math

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


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Khoảng cách thẳng giữa 2 toạ độ (km) — dùng để lọc thêm theo radius_km
    ở phía Python, vì endpoint finding-keo/nearby chỉ lọc theo district (không
    hỗ trợ bán kính), nhưng mỗi row trong bảng wp_finding_keo có sẵn lat/lng
    (xem finding_keo_on() trong finding-keo.php) nên vẫn lọc lại được.
    """
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4))
def get_nearby_users(
    lat: float,
    lng: float,
    radius_km: float = 3.0,
    district: str = "",
    activity_type: str = "",
) -> list[dict]:
    """Gọi custom/v1/finding-keo/nearby — danh sách user đang bật radar quanh 1 toạ độ.

    🔧 FIX: route thật (finding_keo_nearby() trong finding-keo.php) lọc theo
    `district` (BẮT BUỘC — thiếu thì trả success:false luôn) và `activity_type`
    (optional), KHÔNG nhận lat/lng/radius_km — trước đây hàm này gửi nhầm
    lat/lng/radius_km lên route, route luôn trả "Missing district" -> luôn
    ra danh sách rỗng dù có user thật đang bật radar gần đó.
    Giờ gửi đúng `district`, rồi TỰ lọc lại theo `radius_km` ở phía Python
    bằng khoảng cách haversine tính từ lat/lng có sẵn trong mỗi row trả về
    (mỗi row của bảng wp_finding_keo có lat/lng riêng, xem finding_keo_on()).
    """
    if not district:
        logger.warning("[wp_api_client] get_nearby_users thiếu district -> route sẽ trả rỗng, bỏ qua gọi")
        return []

    with _client() as client:
        params: dict[str, str] = {"district": district}
        if activity_type:
            params["activity_type"] = activity_type
        resp = client.get("/wp-json/custom/v1/finding-keo/nearby", params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success", True):
            logger.warning(f"[wp_api_client] finding-keo/nearby trả lỗi: {data.get('message')}")
            return []
        users = data.get("data", data if isinstance(data, list) else [])

    # Lọc lại theo bán kính thật (route chỉ lọc theo quận, quận có thể rộng
    # hơn radius_km nhiều) — bỏ qua row nào thiếu lat/lng thay vì loại hết.
    filtered = []
    for u in users:
        u_lat, u_lng = u.get("lat"), u.get("lng")
        if u_lat in (None, "", 0) or u_lng in (None, "", 0):
            filtered.append(u)  # thiếu toạ độ -> không lọc được, giữ lại thay vì mất user
            continue
        try:
            dist = _haversine_km(lat, lng, float(u_lat), float(u_lng))
        except (TypeError, ValueError):
            filtered.append(u)
            continue
        if dist <= radius_km:
            u["distance_km"] = round(dist, 2)
            filtered.append(u)

    return filtered


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4))
def get_open_invites(district: str | None = None, per_page: int = 30) -> list[dict]:
    """Lấy danh sách kèo đang mở qua nhau/v1/shop-feed (route CÔNG KHAI, không cần
    JWT/consumer key — cùng nguồn dữ liệu shop_page.dart đang dùng thật).

    🔧 FIX: TRƯỚC ĐÂY gọi nhau/v1/my-keo — SAI 2 lớp:
      1. my-keo.php tự đọc get_current_user_id() và trả 401 'not_logged_in'
         nếu không có JWT. _client() ở file này không hề gắn Authorization
         header (tham số jwt không được truyền ở bất kỳ chỗ gọi nào) -> mọi
         request đều 401 -> safe_call() nuốt lỗi -> luôn trả [] -> Recommendation
         Agent không có kèo nào để xếp hạng -> /invite/recommend luôn rỗng.
      2. Kể cả có JWT, my-keo CHỈ trả kèo của ĐÚNG 1 user đang đăng nhập
         (host hoặc đã join) — không phải danh sách "tất cả kèo đang mở"
         cần để so sánh/xếp hạng giữa nhiều lựa chọn.

    shop-feed không lọc theo `district` dạng chuỗi (chỉ có lat/lng/radius_km),
    nên KHÔNG lọc cứng ở đây — trả full list (đã sort theo priority/live/sắp
    diễn ra) kèm field 'address' để Agent tự đọc và ưu tiên đúng khu vực nếu
    task có nhắc district, tương tự cách LLM tự suy luận reason. Tránh lặp
    lại bug "LLM quên truyền district" từng gặp ở find_nearby_users bằng
    cách không bắt buộc LLM tự lọc số liệu, chỉ cần đọc text.
    """
    with _client() as client:
        params = {"page": 1, "per_page": min(per_page, 30)}
        resp = client.get("/wp-json/nhau/v1/shop-feed", params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success", True):
            logger.warning(f"[wp_api_client] shop-feed trả lỗi: {data.get('message')}")
            return []
        items = data.get("data", [])

    # Chuẩn hoá field cho gọn — Agent chỉ cần vừa đủ để xếp hạng + gọi tiếp
    # get_invite_detail(invite_id). Giữ 'address' nguyên văn để LLM tự đọc
    # khu vực (thay cho lọc district cứng mà shop-feed không hỗ trợ).
    normalized = []
    for it in items:
        invite = it.get("invite") or {}
        normalized.append({
            "invite_id": invite.get("invite_id"),
            "product_id": it.get("id"),
            "pub_name": it.get("pub_name", ""),
            "address": it.get("address", ""),
            "time": it.get("time", ""),
            "slots": it.get("slots", 0),
            "joined_count": it.get("joined", 0),
            "priority": it.get("priority"),
            "lat": it.get("lat"),
            "lng": it.get("lng"),
        })
    return normalized


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