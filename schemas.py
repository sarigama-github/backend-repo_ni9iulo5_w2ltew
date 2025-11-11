"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.

Class name lowercased = collection name
- Habit -> "habit"
- RoadmapItem -> "roadmapitem"
- Resource -> "resource"
- Progress -> "progress"
- Message -> "message"
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime

class Habit(BaseModel):
    name: str = Field(..., description="Habit title, e.g., 'Read 30 minutes a day'")
    description: Optional[str] = Field(None, description="Short description or goal context")
    start_date: Optional[date] = Field(None, description="When the habit starts")
    target_days_per_week: int = Field(5, ge=1, le=7, description="Target frequency per week")
    progress: float = Field(0.0, ge=0, le=1, description="Overall completion ratio 0..1")

class RoadmapItem(BaseModel):
    habit_id: str = Field(..., description="Reference to habit _id as string")
    title: str = Field(..., description="Milestone title")
    description: Optional[str] = Field(None)
    order: int = Field(..., ge=0, description="Milestone order index")
    due_date: Optional[date] = Field(None)
    completed: bool = Field(False)

class Resource(BaseModel):
    habit_id: str = Field(..., description="Reference to habit _id as string")
    title: str
    url: str
    type: str = Field("article", description="article|video|course|podcast|tool")
    provider: Optional[str] = None
    notes: Optional[str] = None

class Progress(BaseModel):
    habit_id: str = Field(...)
    note: Optional[str] = None
    image_base64: Optional[str] = Field(None, description="Base64-encoded image payload")
    taken_at: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    habit_id: Optional[str] = None
    role: str = Field(..., description="user|assistant")
    content: str
    image_base64: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
