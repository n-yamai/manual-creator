from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# Image schemas
class ManualImageBase(BaseModel):
    timestamp: Optional[float] = None
    description: Optional[str] = None
    image_type: Optional[str] = "extracted"

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

class ManualRefineRequest(BaseModel):
    instruction: str
    current_content: str
    model_name: Optional[str] = "gemini-3.5-flash"

    model_config = {'protected_namespaces': ()}

class ManualRefineResponse(BaseModel):
    refined_content: str


# Settings & Model schemas
class ApiKeySetRequest(BaseModel):
    api_key: str

class ApiKeyStatusResponse(BaseModel):
    is_set: bool
    masked_key: Optional[str] = None
    using_fallback: bool = False

class ApiKeyAddRequest(BaseModel):
    label: str
    api_key: str

class ApiKeySelectRequest(BaseModel):
    id: str

class ApiKeyItemResponse(BaseModel):
    id: str
    label: str
    masked_key: str
    is_active: bool

class ApiKeysStatusResponse(BaseModel):
    active_id: Optional[str] = None
    active_label: Optional[str] = None
    keys: List[ApiKeyItemResponse] = []
    using_fallback: bool = False
    fallback_masked_key: Optional[str] = None

class AiModelResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    badge: Optional[str] = None
    badgeClass: Optional[str] = None
    available: bool = True


