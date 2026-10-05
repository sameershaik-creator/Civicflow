from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    complaint_id: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int
