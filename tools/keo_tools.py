"""
CrewAI tools — lớp mỏng để Agent "gọi được" dữ liệu thật từ WordPress qua
wp_api_client.py. Mỗi tool trả về text/JSON string vì LLM chỉ đọc được text.
"""
from __future__ import annotations

import json

from crewai.tools import tool

from tools import wp_api_client as wp


@tool("Tìm user đang bật radar gần một toạ độ")
def find_nearby_users(lat: float, lng: float, radius_km: float = 3.0, district: str = "", activity_type: str = "") -> str:
    """Trả về JSON danh sách user đang online/bật finding-keo trong bán kính radius_km
    quanh (lat, lng). Dùng khi cần tìm người để ghép vào 1 kèo.

    🔧 BẮT BUỘC truyền `district` (quận/huyện, vd "Bình Thạnh") — route WordPress
    phía sau lọc theo district trước, radius_km chỉ lọc TIẾP trong kết quả đó.
    Thiếu district sẽ luôn trả về danh sách rỗng.
    `activity_type` (optional) lọc thêm theo loại hoạt động đang tìm (vd "nhậu bia",
    "cafe") nếu cần khớp đúng sở thích/loại kèo, để trống nếu muốn thấy mọi loại.
    """
    users = wp.safe_call(wp.get_nearby_users, lat, lng, radius_km, district, activity_type, default=[])
    return json.dumps(users, ensure_ascii=False)


@tool("Lấy danh sách kèo đang mở")
def list_open_invites(district: str = "") -> str:
    """Trả về JSON danh sách kèo (invite) đang ở trạng thái open, có thể lọc theo quận."""
    invites = wp.safe_call(wp.get_open_invites, district or None, default=[])
    return json.dumps(invites, ensure_ascii=False)


@tool("Lấy chi tiết 1 kèo")
def get_invite_detail(invite_id: int) -> str:
    """Trả về JSON chi tiết 1 invite theo invite_id: giờ bắt đầu, số chỗ còn, loại
    hoạt động, toạ độ quán..."""
    detail = wp.safe_call(wp.get_invite_detail, invite_id, default={})
    return json.dumps(detail, ensure_ascii=False)


@tool("Lấy lịch sử/độ uy tín của user")
def get_user_history(user_id: int) -> str:
    """Trả về JSON thống kê của 1 user: số kèo đã tham gia, trust rating, loại hoạt
    động hay tham gia... dùng để cá nhân hoá gợi ý thay vì chỉ so khoảng cách."""
    stats = wp.safe_call(wp.get_user_stats, user_id, default={})
    return json.dumps(stats, ensure_ascii=False)


@tool("Lấy lịch sử của nhiều user cùng lúc")
def get_users_history_bulk(user_ids: list[int]) -> str:
    """Trả về JSON thống kê của nhiều user cùng lúc (tránh gọi tuần tự chậm khi cần
    chấm điểm 1 danh sách ứng viên)."""
    stats = wp.safe_call(wp.get_user_stats_bulk, user_ids, default={})
    return json.dumps(stats, ensure_ascii=False)
