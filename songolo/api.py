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


class Source(str, Enum):
    youtube = "youtube"
    spotify = "spotify"
    upload = "upload"


@router.post("/songs/import/{source}", response_model=SongOut)
async def import_song(
    song: Song,
    source: Source,
):
    song.download(source)
    return song
