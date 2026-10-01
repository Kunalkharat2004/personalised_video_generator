"""FastAPI application entrypoint. Run with: uvicorn app.main:app --reload"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routes import health, image, video

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Townhall Video Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=not config.CORS_ALLOW_ALL,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(image.router)
app.include_router(video.router)


@app.get("/")
async def root():
    return {"message": "Townhall Video Generator API is running"}
