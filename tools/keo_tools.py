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

    🔧 FIX: `district` KHÔNG còn bắt buộc — route WordPress phía sau
    (finding-keo/nearby) giờ lọc bằng khoảng cách thật (Haversine trên lat/lng),
    không còn so khớp chuỗi district nữa (trước đây 2 user đứng gần nhau vẫn có
    thể bị reverse-geocode ra 2 chuỗi district khác nhau -> exact match luôn
    rỗng dù có user thật rất gần). Chỉ cần lat/lng + radius_km là đủ.
    `activity_type` (optional) lọc thêm theo loại hoạt động đang tìm (vd "nhậu bia",
    "cafe") nếu cần khớp đúng sở thích/loại kèo, để trống nếu muốn thấy mọi loại.

    ⚠️ Giữ lại hàm này (module-level, đủ 5 tham số) để backward-compat cho nơi nào
    còn import trực tiếp. Nhưng KHÔNG gắn hàm này cho match_agent nữa — dùng
    `make_find_nearby_users_tool(district, activity_type)` bên dưới thay thế, vì
    LLM (gpt-4o-mini) hay quên truyền các tham số phụ (structured tool-calling bị
    giới hạn bởi args_schema, không phải tự do). Xem crew.py run_match để biết
    chỗ gọi factory.
    """
    users = wp.safe_call(wp.get_nearby_users, lat, lng, radius_km, district, activity_type, default=[])
    return json.dumps(users, ensure_ascii=False)


def make_find_nearby_users_tool(district: str, activity_type: str = "", exclude_user_id: int | None = None):
    """Factory tạo tool 'Tìm user đang bật radar gần một toạ độ' cho MỘT request cụ
    thể, khoá cứng `district`/`activity_type` bằng closure ngay tại thời điểm build
    agent (biết trước từ context của request, không cần LLM tự suy ra).

    Khác với `find_nearby_users` ở trên: tool trả về từ factory này CHỈ có
    `lat`, `lng`, `radius_km` trong args_schema — LLM không hề nhìn thấy (và do đó
    không thể quên truyền) `district`/`activity_type`.

    🔧 FIX (lọc theo khoảng cách thay vì district): trước đây route WordPress
    phía sau (finding-keo/nearby) lọc BẮT BUỘC bằng `fk.district = %s` (so khớp
    chuỗi) — 2 user đứng gần nhau vẫn ra 2 chuỗi district khác nhau tuỳ máy
    (lệch ranh giới quận, khác fallback locality/subAdministrativeArea) nên
    match luôn rỗng dù có người thật gần đó. Route giờ đã đổi sang Haversine
    trên lat/lng (giống spiritwebs/v1/nearby-deals), `district` chỉ còn dùng để
    hiển thị UI, không còn quyết định có match được hay không.

    🆕 `exclude_user_id`: loại chính user đang gọi /match ra khỏi kết quả trước khi
    trả về LLM. Phát hiện qua test thật với 2 user online: user tự bật radar ở
    đúng toạ độ mình đứng -> distance_km=0.0 -> lọt qua bộ lọc bán kính -> Agent
    match user với chính họ, score 100% ("Cùng tổ chức kèo"). Lọc ở code, không
    dựa vào Task description nhắc Agent "đừng tự match với chính mình" — cùng lý
    do với fix district: LLM hay bỏ sót instruction dạng phủ định/edge-case.

    Dùng trong build_match_agent(district=..., exclude_user_id=user_id) thay vì
    tool module-level phía trên.
    """

    @tool("Tìm user đang bật radar gần một toạ độ")
    def find_nearby_users_bound(lat: float, lng: float, radius_km: float = 3.0) -> str:
        """Trả về JSON danh sách user đang online/bật finding-keo trong bán kính
        radius_km quanh (lat, lng), đã tự động lọc theo đúng quận/huyện của user
        hiện tại và tự động loại chính user đang tìm kiếm ra khỏi kết quả. Dùng
        khi cần tìm người để ghép vào 1 kèo."""
        users = wp.safe_call(
            wp.get_nearby_users, lat, lng, radius_km, district, activity_type, default=[]
        )
        if exclude_user_id is not None:
            users = [u for u in users if str(u.get("user_id")) != str(exclude_user_id)]
        return json.dumps(users, ensure_ascii=False)

    return find_nearby_users_bound


@tool("Lấy danh sách kèo đang mở")
def list_open_invites(district: str = "") -> str:
    """Trả về JSON danh sách kèo (invite) đang ở trạng thái open (nguồn: shop-feed,
    đã sort sẵn theo độ hot/sắp diễn ra).

    ⚠️ `district` KHÔNG lọc cứng được ở đây — endpoint gốc (nhau/v1/shop-feed)
    chỉ hỗ trợ lọc theo lat/lng/radius_km, không nhận tên quận/huyện dạng chuỗi
    (khác với 'Tìm user đang bật radar...'). Nếu cần ưu tiên đúng khu vực, tự đọc
    field 'address' của từng kèo trong kết quả trả về thay vì trông chờ tool này
    tự lọc theo `district` truyền vào.
    """
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