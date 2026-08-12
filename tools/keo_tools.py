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

    ⚠️ Giữ lại hàm này (module-level, đủ 5 tham số) để backward-compat cho nơi nào
    còn import trực tiếp. Nhưng KHÔNG gắn hàm này cho match_agent nữa — dùng
    `make_find_nearby_users_tool(district, activity_type)` bên dưới thay thế, vì
    LLM (gpt-4o-mini) hay quên truyền `district` dù docstring có ghi "BẮT BUỘC"
    (structured tool-calling bị giới hạn bởi args_schema, không phải tự do —
    LLM chỉ tuân theo những gì nó THẤY trong schema, không phải những gì đọc
    trong prompt). Xem crew.py run_match để biết chỗ gọi factory.
    """
    users = wp.safe_call(wp.get_nearby_users, lat, lng, radius_km, district, activity_type, default=[])
    return json.dumps(users, ensure_ascii=False)


def make_find_nearby_users_tool(district: str, activity_type: str = ""):
    """Factory tạo tool 'Tìm user đang bật radar gần một toạ độ' cho MỘT request cụ
    thể, khoá cứng `district`/`activity_type` bằng closure ngay tại thời điểm build
    agent (biết trước từ context của request, không cần LLM tự suy ra).

    Khác với `find_nearby_users` ở trên: tool trả về từ factory này CHỈ có
    `lat`, `lng`, `radius_km` trong args_schema — LLM không hề nhìn thấy (và do đó
    không thể quên truyền) `district`/`activity_type`. Đây là fix triệt để cho bug
    "district thiếu -> WordPress route finding-keo/nearby luôn trả rỗng".

    Dùng trong build_match_agent(district=...) thay vì tool module-level phía trên.
    """

    @tool("Tìm user đang bật radar gần một toạ độ")
    def find_nearby_users_bound(lat: float, lng: float, radius_km: float = 3.0) -> str:
        """Trả về JSON danh sách user đang online/bật finding-keo trong bán kính
        radius_km quanh (lat, lng), đã tự động lọc theo đúng quận/huyện của user
        hiện tại. Dùng khi cần tìm người để ghép vào 1 kèo."""
        users = wp.safe_call(
            wp.get_nearby_users, lat, lng, radius_km, district, activity_type, default=[]
        )
        return json.dumps(users, ensure_ascii=False)

    return find_nearby_users_bound


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