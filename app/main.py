from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.main import api_router
from app.core.config import settings
from app.core.rlimiter import limiter

app = FastAPI(title=settings.PROJECT_NAME)
app.state.limiter = limiter
app.add_middleware(
  CORSMiddleware,
  allow_origins=[settings.FRONTEND_HOST],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(api_router, prefix=settings.API_V1_STR)