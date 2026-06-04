from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config import settings
from app.learning.scheduler import start_scheduler
from app.library.routes import router as library_router
from app.pipeline.routes import router as generate_router
from app.profile.routes import router as profile_router
from app.workspace.routes import router as workspace_router

_scheduler = None


@asynccontextmanager
async def lifespan(app):
    global _scheduler
    _scheduler = start_scheduler()
    yield
    if _scheduler:
        _scheduler.shutdown()


app = FastAPI(title="PromptForge API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(generate_router)
app.include_router(profile_router)
app.include_router(library_router)
app.include_router(workspace_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
