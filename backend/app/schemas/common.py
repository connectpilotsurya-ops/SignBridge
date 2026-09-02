from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ORMBase(BaseModel):
    model_config = {"from_attributes": True}


class Timestamped(ORMBase):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TextChunk(ORMBase):
    """One unit of parsed resume text with full forensic metadata.

    This is the thing that makes anti-gaming detection possible — a plain
    `text.extract()` throws exactly this information away.
    """
    text: str
    page: int
    font_size: float
    font_name: str = ""
    color_hex: str = "#000000"
    bg_color_hex: str = "#FFFFFF"
    x: float
    y: float
    width: float = 0.0
    height: float = 0.0
    block_type: str = "text"
    section: str = "unknown"
    visibility: str = "visible"  # enums.Visibility value
