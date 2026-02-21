import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.services.vector_store import vector_store
from app.services.embeddings import embedding_service
from app.scheduler import scheduler_loop, register_ws, unregister_ws

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🌍 OSIRIS starting up...")
    embedding_service.load()
    await vector_store.connect()

    # Start background scheduler
    task = asyncio.create_task(scheduler_loop())
    logger.info("✅ OSIRIS ready")
    yield
    # Shutdown
    task.cancel()
    logger.info("OSIRIS shutting down")


app = FastAPI(
    title="OSIRIS",
    description="Open Source Intelligence Reconnaissance & Insight System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "osiris"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    register_ws(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        unregister_ws(websocket)
