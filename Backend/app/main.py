from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app import models
from app.migrations import migrate
from app.api.ai import router as ai_router
from app.api.payments import router as payments_router
from app.api.razorpay import router as razorpay_router
from app.api.recovery import router as recovery_router
from app.api.webhooks import router as webhooks_router
from app.api.simulator import router as simulator_router
from app.services.websocket_manager import manager, broadcast_payment_update
from app.database import SessionLocal
import json


app = FastAPI(
    title="RecoverAI API",
    description="Autonomous Payment Recovery Engine",
    version="1.0.0",
)


# Create database tables
Base.metadata.create_all(bind=engine)

# Apply non-destructive column migrations (existing data preserved)
migrate()


# Allow requests from Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers
app.include_router(ai_router)
app.include_router(payments_router)
app.include_router(razorpay_router)
app.include_router(recovery_router)
app.include_router(webhooks_router)
app.include_router(simulator_router)


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates.
    
    Clients connect to this endpoint to receive real-time updates
    when payment/recovery data changes.
    """
    await manager.connect(websocket)
    try:
        # Send initial data
        await broadcast_payment_update(SessionLocal)
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong or other client messages if needed
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        import logging
        logging.getLogger(__name__).error(f"WebSocket error: {e}")


@app.get("/")
async def root():
    return {
        "name": "RecoverAI",
        "status": "online",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "recoverai-backend",
    }