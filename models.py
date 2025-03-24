from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class URL(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    original_url: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    short_code: str
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None   # 過期時間（None 表示永不過期）
    is_expired: bool = Field(default=False) # 是否已被清除處理（如刪除檔案）
