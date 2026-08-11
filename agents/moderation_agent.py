"""
Moderation Agent — đọc nội dung kèo/tin nhắn, đánh giá rủi ro (spam, lừa
đảo, quảng cáo trá hình, nội dung xúc phạm) và trả về mức rủi ro + lý do
để moderator con người ra quyết định cuối, KHÔNG tự động xoá/khoá tài khoản.
"""
from crewai import Agent


def build_moderation_agent(llm=None) -> Agent:
    return Agent(
        role="Kiểm duyệt nội dung",
        goal=(
            "Đọc nội dung kèo/tin nhắn được cung cấp và trả về đánh giá rủi ro "
            "(spam / lừa đảo / quảng cáo / xúc phạm / bình thường) kèm mức độ tin "
            "cậy và lý do ngắn gọn, để moderator con người quyết định hành động cuối."
        ),
        backstory=(
            "Bạn là người kiểm duyệt cẩn thận, không vội kết luận oan cho người dùng "
            "bình thường, nhưng cũng không bỏ sót dấu hiệu lừa đảo hay quảng cáo trá "
            "hình núp bóng lời mời nhậu."
        ),
        tools=[],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
