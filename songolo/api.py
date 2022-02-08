from typing import List

from fastapi import APIRouter, Query

from .songs import Library, Song

router = APIRouter()


@router.get("/songs")
async def get_songs(library: Library = Library(), max_count: int = Query(9999)):
    return list(library.songs(max_count))
