"""WebSocket connection manager for real-time dashboard updates."""

import json
import logging
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.add(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")
            self.disconnect(websocket)


manager = ConnectionManager()


async def broadcast_payment_update(db_session_factory):
    """Fetch latest dashboard data and broadcast to all connected clients."""
    from app.database import SessionLocal
    from app.models import Payment

    db = SessionLocal()
    try:
        payments = db.query(Payment).all()
        
        # Compute metrics
        total_at_risk = sum(p.amount for p in payments if p.recovery_status == "PENDING")
        total_recovered = sum(p.amount for p in payments if p.recovery_status == "SUCCESS")
        total_payments = len(payments)
        recovered_payments = len([p for p in payments if p.recovery_status == "SUCCESS"])
        recovery_rate = (recovered_payments / total_payments * 100) if total_payments > 0 else 0
        
        pending_count = len([p for p in payments if p.recovery_status == "PENDING"])
        ai_actions_count = len([p for p in payments if p.recommended_action is not None])
        
        message = {
            "type": "dashboard_update",
            "data": {
                "revenueAtRisk": total_at_risk,
                "revenueRecovered": total_recovered,
                "recoveryRate": round(recovery_rate, 1),
                "opportunitiesCount": pending_count,
                "aiActionsCount": ai_actions_count,
                "totalPayments": total_payments,
                "recoveredPayments": recovered_payments,
                "payments": [
                    {
                        "id": p.id,
                        "amount": p.amount,
                        "failure_reason": p.failure_reason,
                        "customer_type": p.customer_type,
                        "recommended_action": p.recommended_action,
                        "recovery_status": p.recovery_status,
                        "payment_status": p.payment_status,
                        "confidence": p.confidence,
                        "decision_source": p.decision_source,
                        "firewall_decision": p.firewall_decision,
                        "firewall_reason": p.firewall_reason,
                        "firewall_checks": p.firewall_checks,
                        "retry_count": p.retry_count,
                        "previous_recovery_attempts": p.previous_recovery_attempts,
                        "payment_method": p.payment_method,
                        "payment_timestamp": p.payment_timestamp.isoformat() if p.payment_timestamp else None,
                        "webhook_received_at": p.webhook_received_at.isoformat() if p.webhook_received_at else None,
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                    }
                    for p in payments
                ]
            }
        }
        
        await manager.broadcast(message)
    finally:
        db.close()