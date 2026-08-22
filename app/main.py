import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import api_router, router
from app.config.settings import get_settings
from app.database.db import init_db

logger = logging.getLogger("trading_bot")

settings = get_settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("database initialized")
    except Exception as exc:
        logger.warning("database initialization failed: %s", exc)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
app.include_router(api_router)
