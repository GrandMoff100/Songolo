from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import List

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from songolo.songs import Library, MetaData, Song


class LibraryOut(BaseModel):
    path: Path


class SongOut(BaseModel):
    library: LibraryOut
    meta: MetaData
    sha: str


router = APIRouter()


@router.get("/songs/{sha}", response_model=SongOut)
async def get_song(
    sha: str,
    library: Library = Library(),
):
    return library.get_song(sha)


@router.put("/songs/{sha}", response_model=SongOut)
async def update_song(
    sha: str,
    updated_song: Song,
    library: Library = Library(),
):
    song = library.get_song(sha)
    return song


@router.get("/songs/{sha}/content", response_class=StreamingResponse)
async def get_song_content(
    sha: str,
    library: Library = Library(),
):
    return StreamingResponse(
        BytesIO(library.get_song(sha).content),
        media_type="audio/mp3",
    )


@router.get("/songs", response_model=List[SongOut])
async def get_songs(
    library: Library = Library(),
    max_count: int = Query(9999),
):
    return list(library.songs(max_count))


class Source(str, Enum):
    youtube = "youtube"
    spotify = "spotify"
    upload = "upload"


@router.post("/songs/import/{source}", response_model=SongOut)
async def import_song(
    song: Song,
    source: Source,
    library: Library = Library(),
):
    song.download(source)
    return song
