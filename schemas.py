from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    user_id: int
    lat: float
    lng: float
    radius_km: float = 3.0
    # 🔧 FIX: KHÔNG còn bắt buộc — finding-keo/nearby giờ lọc bằng Haversine
    # thật trên lat/lng (xem finding-keo.php::finding_keo_nearby). district
    # cũ dùng để lọc exact-match string, dễ lệch giữa 2 user đứng gần nhau
    # do khác kết quả reverse-geocode -> match luôn rỗng dù có user gần đó.
    # Giữ field lại (optional) chỉ để hiển thị UI / client cũ chưa update.
    district: str = ""
    activity_type: str = ""


class RecommendRequest(BaseModel):
    user_id: int
    district: str = ""


class ModerateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    content_type: str = "invite"  # invite | chat_message | profile