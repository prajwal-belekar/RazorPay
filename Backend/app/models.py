from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    amount = Column(Float, nullable=False)

    failure_reason = Column(String, nullable=False)

    customer_type = Column(String, nullable=False)

    recommended_action = Column(String, nullable=True)

    reason = Column(String, nullable=True)

    confidence = Column(Float, nullable=True)

    decision_source = Column(String, nullable=True)

    recovery_status = Column(String, nullable=True)

    retry_count = Column(Integer, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )