"""
Recommendation Agent — thay thế rule cứng trong keo-priority-sort.php
(đang live > sắp diễn ra > còn xa, không cá nhân hoá) bằng gợi ý theo
từng user cụ thể: sở thích, khu vực hay lui tới, bạn bè, lịch sử xem/join.
"""
from crewai import Agent

from tools.keo_tools import list_open_invites, get_invite_detail, get_user_history


def build_recommendation_agent(llm=None) -> Agent:
    return Agent(
        role="Chuyên gia gợi ý kèo & nội dung cá nhân hoá",
        goal=(
            "Từ danh sách kèo đang mở và hồ sơ/lịch sử của 1 user, chọn ra top kèo "
            "phù hợp nhất để hiển thị ưu tiên cho user đó — khác nhau giữa từng người, "
            "không phải một thứ tự cứng áp dụng chung cho tất cả."
        ),
        backstory=(
            "Bạn giống một người bạn thân hiểu gu nhậu của từng người: ai thích quán "
            "yên tĩnh, ai thích đông vui, ai hay đi khu nào giờ nào, để gợi ý đúng gu "
            "thay vì chỉ đẩy kèo đang hot lên đầu cho tất cả mọi người."
        ),
        tools=[list_open_invites, get_invite_detail, get_user_history],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
