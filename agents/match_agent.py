"""
Match Agent — thay thế phần lọc cứng trong finding-keo.php bằng chấm điểm
% phù hợp giữa 1 user và các kèo/user xung quanh, dựa trên khoảng cách,
sở thích, lịch sử tham gia, giờ giấc.
"""
from crewai import Agent

from tools.keo_tools import (
    get_user_history,
    list_open_invites,
    make_find_nearby_users_tool,
)


def build_match_agent(district: str, activity_type: str = "", llm=None) -> Agent:
    """district BẮT BUỘC truyền (đã có sẵn trong request /match) — được khoá cứng
    vào tool 'Tìm user đang bật radar' bằng closure ngay tại đây, thay vì để LLM
    tự truyền qua tool call. Xem docstring của make_find_nearby_users_tool trong
    tools/keo_tools.py để biết lý do (fix bug district bị LLM bỏ quên -> tool luôn
    trả về danh sách rỗng)."""
    return Agent(
        role="Chuyên gia ghép kèo nhậu",
        goal=(
            "Chấm điểm % phù hợp giữa 1 user với các kèo/user đang mở xung quanh, "
            "dựa trên khoảng cách, khung giờ, loại hoạt động, ngân sách và lịch sử "
            "tham gia — không chỉ đơn thuần sắp xếp theo khoảng cách gần nhất."
        ),
        backstory=(
            "Bạn từng là một 'thổ địa' quen mặt khắp các quán nhậu Sài Gòn, biết "
            "ai hợp nhóm nào, quán nào hợp giờ nào, và luôn ưu tiên trải nghiệm vui "
            "vẻ, an toàn cho người dùng hơn là chỉ nhét cho đủ số lượng."
        ),
        tools=[
            make_find_nearby_users_tool(district=district, activity_type=activity_type),
            list_open_invites,
            get_user_history,
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )