"""Assembles all the routers into a central app."""
from fastapi import FastAPI

from songolo.api import router as api_router

app = FastAPI()
app.include_router(api_router, prefix="/api")
