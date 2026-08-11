from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    user_id: int
    lat: float
    lng: float
    radius_km: float = 3.0
    # 🆕 BẮT BUỘC để find_nearby_users hoạt động — route WordPress phía sau
    # (finding-keo/nearby) lọc theo quận/huyện trước, không nhận lat/lng
    # trực tiếp. Thiếu field này, Agent gọi tool sẽ luôn ra danh sách rỗng.
    district: str = ""
    activity_type: str = ""


class RecommendRequest(BaseModel):
    user_id: int
    district: str = ""


class ModerateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    content_type: str = "invite"  # invite | chat_message | profile
