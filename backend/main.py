from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os

# Импорт роутеров
from bank import router as bank_router
from database import init_db as bank_init_db
from router import route_request
from vault_api import router as vault_router

app = FastAPI(title="ANANISIM OS API")

# CORS: локальная разработка + продакшен домен
cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://dronxgenie.com",
    "https://www.dronxgenie.com",
]
prod_origin = os.getenv("VITE_API_BASE_URL", "")
if prod_origin and prod_origin not in cors_origins:
    cors_origins.append(prod_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# PIN-защита API (переменная окружения API_PIN)
API_PIN = os.getenv("API_PIN", "")

@app.middleware("http")
async def pin_middleware(request: Request, call_next):
    if API_PIN and request.url.path.startswith("/api/"):
        provided = request.headers.get("X-PIN") or request.headers.get("Authorization", "").replace("Bearer ", "")
        if provided != API_PIN:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN")
    return await call_next(request)

app.include_router(bank_router, prefix="/api/bank", tags=["Bank"])
app.include_router(vault_router, prefix="/api/vault", tags=["Vault"])

class ChatRequest(BaseModel):
    query: str
    agent: str = None

@app.on_event("startup")
async def startup_event():
    bank_init_db()
    print("=== ANANISIM OS ЗАПУЩЕН ===")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "ANANISIM OS is alive and kicking!"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    return await route_request(request.query, request.agent)

if __name__ == "__main__":
    is_dev = os.getenv("ZHORIK_DEV", "0") == "1"
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=is_dev)

