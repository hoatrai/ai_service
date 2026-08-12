"""
Lắp Agent + Task thành Crew cho từng use-case (match / recommend / moderate).
Mỗi hàm ở đây nhận input thô (dict) từ FastAPI route, build Task tương ứng,
chạy kickoff() và ép output về JSON để trả cho Phoenix/WordPress.
"""
from __future__ import annotations

import json
import re

from crewai import Crew, Process, Task
from loguru import logger

from agents.match_agent import build_match_agent
from agents.moderation_agent import build_moderation_agent
from agents.recommendation_agent import build_recommendation_agent


def _parse_json_output(raw: str) -> dict | list:
    """LLM đôi khi bọc JSON trong ```json ... ``` — bóc ra trước khi parse.

    🆕 FIX: trước đây chỉ bóc fence khi nó nằm Ở ĐẦU chuỗi
    (text.startswith("```")). Thực tế LLM nhiều lúc chỉ dính dư fence ở
    CUỐI (vd '{"matches": []}\n```' — JSON hợp lệ nhưng có "```" thừa ở
    cuối) -> startswith("```") = False -> không bóc -> json.loads() lỗi ->
    rơi về {"raw": raw} thay vì JSON thật (gặp đúng case này ở /match).
    Giờ bóc fence ở CẢ 2 đầu bằng regex, không phụ thuộc chuỗi bắt đầu
    bằng gì.
    """
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"[crew] Output không phải JSON hợp lệ, trả raw text: {raw[:200]}")
        return {"raw": raw}


def run_match(
    user_id: int,
    lat: float,
    lng: float,
    radius_km: float = 3.0,
    district: str = "",
    activity_type: str = "",
) -> dict | list:
    # district/activity_type được khoá cứng vào tool "Tìm user đang bật radar..."
    # ngay tại đây (closure trong make_find_nearby_users_tool), agent không còn
    # tham số district để tự truyền/tự quên nữa -> khỏi cần nhắc trong Task nữa.
    agent = build_match_agent(district=district, activity_type=activity_type)
    task = Task(
        description=(
            f"User_id={user_id} đang ở toạ độ lat={lat}, lng={lng}, quận/huyện='{district}'. "
            f"Gọi tool 'Tìm user đang bật radar gần một toạ độ' với lat/lng ở trên và "
            f"radius_km={radius_km} để lấy danh sách ứng viên xung quanh (tool đã tự lọc "
            f"đúng quận/huyện '{district}' rồi, không cần truyền lại). Sau đó lọc trong bán "
            f"kính {radius_km}km bằng lat/lng của từng ứng viên (đã có sẵn trong kết quả tool). "
            "Chấm điểm % phù hợp cho từng ứng viên dựa trên khoảng cách, khung giờ, "
            "loại hoạt động và lịch sử tham gia (gọi tool lấy lịch sử nếu cần)."
        ),
        expected_output=(
            'CHỈ trả JSON dạng: {"matches": [{"invite_id": <int|null>, '
            '"candidate_user_id": <int|null>, "score": <0-100>, "reason": "<ngắn gọn>"}]}. '
            "Không markdown, không giải thích ngoài JSON."
        ),
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
    result = crew.kickoff()
    return _parse_json_output(result.raw)


def run_recommendation(user_id: int, district: str = "") -> dict | list:
    agent = build_recommendation_agent()
    task = Task(
        description=(
            f"Gợi ý top kèo phù hợp nhất cho user_id={user_id}"
            + (f" tại khu vực {district}" if district else "")
            + ". Lấy danh sách kèo đang mở và lịch sử user bằng tool, rồi xếp hạng "
            "theo mức độ phù hợp với sở thích/thói quen của riêng user này."
        ),
        expected_output=(
            'CHỈ trả JSON dạng: {"recommendations": [{"invite_id": <int>, '
            '"score": <0-100>, "reason": "<ngắn gọn>"}]}, tối đa 5 kèo, sắp xếp giảm dần '
            "theo score. Không markdown, không giải thích ngoài JSON."
        ),
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
    result = crew.kickoff()
    return _parse_json_output(result.raw)


def run_moderation(content: str, content_type: str = "invite") -> dict | list:
    agent = build_moderation_agent()
    task = Task(
        description=(
            f"Đánh giá nội dung loại '{content_type}' sau đây có vi phạm không:\n"
            f"---\n{content}\n---"
        ),
        expected_output=(
            'CHỈ trả JSON dạng: {"risk_level": "none|low|medium|high", '
            '"category": "spam|scam|ads|abusive|normal", "confidence": <0-1>, '
            '"reason": "<ngắn gọn>"}. Không markdown, không giải thích ngoài JSON.'
        ),
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
    result = crew.kickoff()
    return _parse_json_output(result.raw)