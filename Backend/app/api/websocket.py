"""WebSocket endpoint for real-time dashboard updates."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import manager

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"],
)


@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates.
    
    Clients connect to this endpoint to receive real-time updates
    when payment/recovery data changes.
    """
    await manager.connect(websocket)
    try:
        # Send initial data
        from app.services.websocket_manager import broadcast_payment_update
        from app.database import SessionLocal
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