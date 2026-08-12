"""
Test khoá chặt bug: district thiếu trong tool call -> finding-keo/nearby luôn
trả rỗng.

Chạy: pytest tests/test_find_nearby_users_tool.py -v
(chạy từ thư mục ai_service/, không cần OPENAI_API_KEY hay WordPress thật vì
wp_api_client.get_nearby_users được mock hoàn toàn.)
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from agents.match_agent import build_match_agent
from tools.keo_tools import make_find_nearby_users_tool


@pytest.fixture
def fake_wp_call():
    """Mock wp.get_nearby_users, ghi lại đúng những gì nó thực sự nhận được."""
    captured = {}

    def _fake(lat, lng, radius_km, district, activity_type):
        captured.update(
            lat=lat, lng=lng, radius_km=radius_km,
            district=district, activity_type=activity_type,
        )
        return [{"user_id": 1, "distance_km": 0.8}]

    with patch("tools.wp_api_client.get_nearby_users", _fake):
        yield captured


def test_llm_khong_the_thay_district_trong_schema():
    """Đây là điểm mấu chốt: LLM chỉ tuân theo args_schema, không tuân theo
    docstring. Nếu district còn xuất hiện ở đây, bug có thể tái diễn."""
    t = make_find_nearby_users_tool(district="Bình Thạnh")
    visible_args = set(t.args_schema.model_fields.keys())
    assert visible_args == {"lat", "lng", "radius_km"}, (
        f"LEAK: LLM đang thấy {visible_args - {'lat', 'lng', 'radius_km'}} "
        "-> có thể quên truyền như bug cũ."
    )


def test_district_van_duoc_gui_dung_xuong_wordpress(fake_wp_call):
    """Giả lập đúng cách CrewAI sẽ gọi: LLM chỉ gửi lat/lng/radius_km."""
    t = make_find_nearby_users_tool(district="Bình Thạnh", activity_type="nhậu bia")

    # Đây là tool-call y hệt như log lỗi gốc: THIẾU district (vì giờ LLM
    # không còn tham số này để truyền nữa) -> vẫn phải work.
    result = t.run(lat=10.6945, lng=106.7032, radius_km=3.0)

    assert fake_wp_call["district"] == "Bình Thạnh"
    assert fake_wp_call["activity_type"] == "nhậu bia"
    assert fake_wp_call["lat"] == 10.6945
    assert json.loads(result) != []  # không còn rỗng như log cũ


def test_moi_request_co_district_rieng_khong_dinh_nhau(fake_wp_call):
    """Đảm bảo 2 request song song (weekend peak traffic) không bị lẫn
    district của nhau do đóng closure sai (bug kinh điển: loop variable
    capture / shared state)."""
    t1 = make_find_nearby_users_tool(district="Quận 1")
    t2 = make_find_nearby_users_tool(district="Bình Thạnh")

    t1.run(lat=10.77, lng=106.70, radius_km=2.0)
    assert fake_wp_call["district"] == "Quận 1"

    t2.run(lat=10.80, lng=106.71, radius_km=2.0)
    assert fake_wp_call["district"] == "Bình Thạnh"


def test_build_match_agent_bat_buoc_co_district():
    """district giờ là positional bắt buộc trong build_match_agent — build
    thiếu phải lỗi ngay lúc code chứ không lỗi ngầm lúc LLM chạy."""
    with pytest.raises(TypeError):
        build_match_agent()  # thiếu district/user_id -> phải raise, không được chạy ngầm


def test_user_tu_bien_mat_khoi_ket_qua_tim_kiem_cua_chinh_minh(fake_wp_call):
    """Bug phát hiện qua test thật (user_id=59 tự match với chính mình, score
    100%) vì user tự bật radar ở đúng toạ độ mình đứng -> distance_km=0.0 ->
    lọt qua bộ lọc bán kính. Tool phải tự loại user đó, không dựa vào LLM."""

    def _fake_with_self(lat, lng, radius_km, district, activity_type):
        return [
            {"user_id": "59", "display_name": "muoiotchanh", "distance_km": 0.0},
            {"user_id": "112", "display_name": "hanhnhi", "distance_km": 1.73},
        ]

    with patch("tools.wp_api_client.get_nearby_users", _fake_with_self):
        t = make_find_nearby_users_tool(district="Quận 3", exclude_user_id=59)
        result = json.loads(t.run(lat=10.78, lng=106.68, radius_km=5.0))

    result_ids = {u["user_id"] for u in result}
    assert "59" not in result_ids, "User tự xuất hiện trong kết quả tìm kiếm của chính họ!"
    assert "112" in result_ids  # vẫn giữ đúng những user khác