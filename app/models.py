from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, func
from app.database import Base

class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_ip = Column(String(50), nullable=True)
    prompt = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    cached = Column(Boolean, default=False)
    execution_time_ms = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<RequestLog id={self.id} cached={self.cached} execution_time_ms={self.execution_time_ms}>"
