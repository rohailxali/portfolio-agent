import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.memory.short_term import init_redis

from app.auth.router import router as auth_router
from app.agent.router import router as agent_router
from app.routers.health import router as health_router
from app.routers.deploy import router as deploy_router
from app.routers.content import router as content_router
from app.routers.leads import router as leads_router
from app.routers.logs import router as logs_router
from app.routers.admin import router as admin_router
from app.routers.memory import router as memory_router
from app.scheduler.tasks import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Portfolio Agent backend")
    await init_redis()
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(agent_router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(deploy_router, prefix="/api/v1/deploy", tags=["deploy"])
app.include_router(content_router, prefix="/api/v1/content", tags=["content"])
app.include_router(leads_router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(logs_router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(memory_router, prefix="/api/v1/memory", tags=["memory"])