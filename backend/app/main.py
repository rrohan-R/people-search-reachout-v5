import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app import models
from app.security import hash_password

from app.routers import auth, jobs, search, outreach, dashboard, agents, schedules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

SCHEDULE_DISPATCH_INTERVAL_SECONDS = 60
_schedule_dispatch_task: "asyncio.Task | None" = None

app = FastAPI(
    title="Outreach API",
    description="Search for candidates via people-search providers and run AI voice-agent outreach.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(search.router)
app.include_router(outreach.router)
app.include_router(dashboard.router)
app.include_router(agents.router)
app.include_router(schedules.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _ensure_default_admin()


@app.on_event("startup")
async def start_schedule_dispatcher():
    """
    Every tick, look for CallSchedule rows whose calling window is open right
    now and hand them to Hunar. This is what makes "schedule a call for
    Tue-Thu 9-1" actually fire on its own instead of requiring the user to
    come back and click a button -- and, just as importantly, it's what
    makes deleting/editing a still-PENDING schedule a *real* cancellation:
    nothing is sent to Hunar until this loop (or a manual "Call now") picks
    it up, so removing the row here guarantees the call never happens.
    """
    global _schedule_dispatch_task
    _schedule_dispatch_task = asyncio.create_task(_schedule_dispatch_loop())


@app.on_event("shutdown")
async def stop_schedule_dispatcher():
    if _schedule_dispatch_task:
        _schedule_dispatch_task.cancel()


async def _schedule_dispatch_loop():
    while True:
        try:
            db = SessionLocal()
            try:
                dispatched = schedules.dispatch_due_schedules(db)
                if dispatched:
                    logger.info("Schedule dispatcher: sent %s call(s) whose window just opened.", dispatched)
            finally:
                db.close()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Schedule dispatch loop failed on this tick; will retry next tick.")
        await asyncio.sleep(SCHEDULE_DISPATCH_INTERVAL_SECONDS)


def _ensure_default_admin():
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(
            models.User.username == settings.DEFAULT_ADMIN_USERNAME
        ).first()
        if not existing:
            admin = models.User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                full_name="Default Admin",
            )
            db.add(admin)
            db.commit()
            logger.info("Created default admin user '%s'", settings.DEFAULT_ADMIN_USERNAME)
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "name": "Outreach API",
        "status": "ok",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}