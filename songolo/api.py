from fastapi import APIRouter
from .songs import Library, Song


router = APIRouter()


@router.get("/songs")
async def get_songs(library: Library):
    pass
