"""
Match Agent — thay thế phần lọc cứng trong finding-keo.php bằng chấm điểm
% phù hợp giữa 1 user và các kèo/user xung quanh, dựa trên khoảng cách,
sở thích, lịch sử tham gia, giờ giấc.
"""
from crewai import Agent

from tools.keo_tools import find_nearby_users, list_open_invites, get_user_history


def build_match_agent(llm=None) -> Agent:
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
        tools=[find_nearby_users, list_open_invites, get_user_history],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
