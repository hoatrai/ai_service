from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    user_id: int
    lat: float
    lng: float
    radius_km: float = 3.0


class RecommendRequest(BaseModel):
    user_id: int
    district: str = ""


class ModerateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    content_type: str = "invite"  # invite | chat_message | profile
