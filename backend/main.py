import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.account_store import AccountStoreError, ensure_accounts_seeded
from app.config import CORS_ORIGINS
from app.errors import register_exception_handlers
from app.routes.accounts import router as accounts_router
from app.routes.auth import router as auth_router
from app.routes.logs import router as logs_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

app = FastAPI(title="DroneAnalytics API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.on_event("startup")
def bootstrap_account_state() -> None:
    try:
        ensure_accounts_seeded()
    except AccountStoreError:
        logging.getLogger(__name__).warning("Account state bootstrap skipped: Redis is unavailable")


register_exception_handlers(app)
app.include_router(accounts_router)
app.include_router(auth_router)
app.include_router(logs_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}
