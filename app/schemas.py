from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class SummarizeRequest(BaseModel):
    text: str = Field(
        ..., 
        min_length=10, 
        max_length=5000, 
        description="The source text to summarize (between 10 and 5000 characters)."
    )

class SummarizeResponse(BaseModel):
    summary: str
    cached: bool
    execution_time_ms: float

class RequestLogSchema(BaseModel):
    id: int
    client_ip: Optional[str]
    prompt: str
    summary: str
    cached: bool
    execution_time_ms: float
    timestamp: datetime

    class Config:
        from_attributes = True

class HealthCheckResponse(BaseModel):
    status: str
    database: str
    redis: str
    version: str
    timestamp: datetime
