import time
from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
import httpx
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Depends, HTTPException, Request, Security, status
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.security.api_key import APIKeyHeader
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.logger import logger
from app.models import RequestLog
from app.redis_client import (
    get_redis_client,
    get_cached_summary,
    set_cached_summary,
    is_rate_limited,
)
from app.schemas import (
    SummarizeRequest,
    SummarizeResponse,
    RequestLogSchema,
    HealthCheckResponse,
)

# Create Database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security: Optional API Key checking
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if settings.API_SECRET_KEY:
        if not api_key or api_key != settings.API_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API Key.",
            )
    return api_key

# Middleware: Request Logging & Execution Time Tracking
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    duration = time.time() - start_time
    duration_ms = round(duration * 1000, 2)
    
    logger.info(
        "HTTP Request Processed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "client_ip": request.client.host if request.client else "unknown",
            "duration_ms": duration_ms
        }
    )
    return response

# Endpoint: Health Check
@app.get("/health", response_model=HealthCheckResponse, status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    redis_status = "connected"
    
    # Check Database Connection
    try:
        db.execute(Base.metadata.tables[RequestLog.__tablename__].select().limit(1))
    except Exception as e:
        logger.error("Health check - database connection failed", extra={"error": str(e)})
        db_status = "disconnected"
        
    # Check Redis Connection
    try:
        redis_conn = get_redis_client()
        redis_conn.ping()
    except Exception as e:
        logger.error("Health check - Redis connection failed", extra={"error": str(e)})
        redis_status = "disconnected"
        
    is_healthy = db_status == "connected" and redis_status == "connected"
    
    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": db_status,
                "redis": redis_status,
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc)
            }
        )
        
    return {
        "status": "healthy",
        "database": db_status,
        "redis": redis_status,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc)
    }

# Endpoint: Summarize (AI/LLM Gateway with caching)
@app.post(
    f"{settings.API_V1_STR}/summarize",
    response_model=SummarizeResponse,
    dependencies=[Depends(verify_api_key)]
)
async def summarize_text(
    request: Request,
    payload: SummarizeRequest,
    db: Session = Depends(get_db)
):
    start_time = time.time()
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Rate Limiting Check (Limit to 15 requests per minute)
    if is_rate_limited(client_ip, limit=15, window_sec=60):
        logger.warning("Rate limit exceeded for client", extra={"client_ip": client_ip})
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 15 requests per minute."
        )

    text_to_summarize = payload.text.strip()
    
    # 2. Check Cache
    cached_summary = get_cached_summary(text_to_summarize)
    if cached_summary:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        # Log cache-hit metadata to Postgres
        log_entry = RequestLog(
            client_ip=client_ip,
            prompt=text_to_summarize,
            summary=cached_summary,
            cached=True,
            execution_time_ms=duration_ms
        )
        db.add(log_entry)
        db.commit()
        
        return {
            "summary": cached_summary,
            "cached": True,
            "execution_time_ms": duration_ms
        }

    # 3. Cache Miss: Run Inference (Query Hugging Face or Mock Fallback)
    summary_text = ""
    if settings.HF_API_TOKEN:
        try:
            # Query Hugging Face API
            headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}
            api_url = f"https://api-inference.huggingface.co/models/{settings.HF_MODEL_ID}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json={"inputs": text_to_summarize, "parameters": {"max_length": 150, "min_length": 30}}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        summary_text = result[0].get("summary_text", "")
                
                if not summary_text:
                    logger.error(
                        "Hugging Face API returned empty response or error", 
                        extra={"status_code": response.status_code, "response": response.text}
                    )
        except Exception as e:
            logger.error("Error communicating with Hugging Face API", extra={"error": str(e)})

    # Fallback to deterministic NLP summary if Hugging Face is not configured or fails
    if not summary_text:
        # Simulate LLM inference delay (e.g., 500ms)
        time.sleep(0.5)
        # Mock NLP extractive summarization (first sentence + metadata sentence)
        sentences = text_to_summarize.split(".")
        first_sentence = sentences[0].strip() if sentences else text_to_summarize
        summary_text = f"[Offline AI Model] Summary: {first_sentence}. (Original length: {len(text_to_summarize)} chars)"

    duration_ms = round((time.time() - start_time) * 1000, 2)

    # 4. Save to Database
    log_entry = RequestLog(
        client_ip=client_ip,
        prompt=text_to_summarize,
        summary=summary_text,
        cached=False,
        execution_time_ms=duration_ms
    )
    db.add(log_entry)
    db.commit()

    # 5. Cache summary in Redis (TTL = 1 Hour)
    set_cached_summary(text_to_summarize, summary_text, ttl_seconds=3600)

    return {
        "summary": summary_text,
        "cached": False,
        "execution_time_ms": duration_ms
    }

# Endpoint: Retrieve Query Logs
@app.get(
    f"{settings.API_V1_STR}/logs",
    response_model=list[RequestLogSchema],
    dependencies=[Depends(verify_api_key)]
)
def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve audit logs of prompt requests."""
    logs = db.query(RequestLog).order_by(RequestLog.timestamp.desc()).limit(limit).all()
    return logs