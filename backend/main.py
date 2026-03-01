from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.errors import register_exception_handlers
from app.routes.auth import router as auth_router
from app.routes.logs import router as logs_router

app = FastAPI(title="DroneAnalytics API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(logs_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}