from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Manual(Base):
    __tablename__ = "manuals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=True)  # Markdown text
    video_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = relationship("ManualImage", back_populates="manual", cascade="all, delete-orphan")

class ManualImage(Base):
    __tablename__ = "manual_images"

    id = Column(Integer, primary_key=True, index=True)
    manual_id = Column(Integer, ForeignKey("manuals.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(String, nullable=False)
    timestamp = Column(Float, nullable=False)  # Timestamp in seconds where the image was extracted
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    manual = relationship("Manual", back_populates="images")
