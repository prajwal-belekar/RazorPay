from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app import models
from app.api.ai import router as ai_router
from app.api.payments import router as payments_router


app = FastAPI(
    title="RecoverAI API",
    description="Autonomous Payment Recovery Engine",
    version="1.0.0",
)


# Create database tables
Base.metadata.create_all(bind=engine)


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