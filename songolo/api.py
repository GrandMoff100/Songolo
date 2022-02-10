from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import List

from fastapi import APIRouter, Query, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from songolo.songs import Library, MetaData, Song
from songolo.utils import sha256_snowflake


class LibraryOut(BaseModel):
    path: Path


router = APIRouter()


class NewSong(Song):
    def __init__(self, *args, **kwargs):
        kwargs.update(snowflake=sha256_snowflake())
        super().__init__(*args, **kwargs)


class SongOut(BaseModel):
    library: LibraryOut
    meta: MetaData
    snowflake: str


class Source(str, Enum):
    youtube = "youtube"
    spotify = "spotify"


@router.post("/songs/upload")
async def upload_song(
    song: NewSong,
    override_meta: bool = True,
    file: bytes = File(...),
):
    song.content = file
    song.download("upload", override_meta=override_meta)
    return song


@router.post("/songs/import/{source}", response_model=SongOut)
async def import_song(
    song: Song,
    source: Source,
):
    song.download(source)
    return song


@router.get("/songs/{snowflake}/log")
async def get_song_log(
    library: Library
):
    pass


@router.get("/songs/{snowflake}/content")
async def get_song_content(self):
    pass


@router.get("/songs/{snowflake}")
async def get_song_info():
    pass


@router.put("/songs/{snowflake}")
async def update_song_info():
    pass


@router.delete("/songs/{snowflake}")
async def delete_song():
    pass




