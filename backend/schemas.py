from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# Image schemas
class ManualImageBase(BaseModel):
    timestamp: float
    description: Optional[str] = None

class ManualImageCreate(ManualImageBase):
    image_path: str

class ExtractFrameRequest(BaseModel):
    timestamp: float
    description: Optional[str] = None


class ManualImageResponse(ManualImageBase):
    id: int
    manual_id: int
    image_path: str
    created_at: datetime

    class Config:
        from_attributes = True

# Manual schemas
class ManualBase(BaseModel):
    title: str
    content: Optional[str] = None

class ManualCreate(ManualBase):
    video_path: Optional[str] = None

class ManualUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class ManualResponse(ManualBase):
    id: int
    video_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ManualDetailResponse(ManualResponse):
    images: List[ManualImageResponse] = []

    class Config:
        from_attributes = True

class GenerateRequest(BaseModel):
    title: str
    prompt_instruction: Optional[str] = None
