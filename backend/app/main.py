from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 

from app.api.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.auth.services import seed_admin_user
from app.modules.measurement_units.services import seed_default_units

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_admin_user()
    try:
        with SessionLocal() as db:
            seed_default_units(db)
    except Exception as exc:
        logger.warning("Default units seed skipped: %s", exc)
    yield

def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://129.148.49.83:5173",
            "http://129.148.49.83",
            "http://localhost:5173"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router)
    return application

app = create_application()

