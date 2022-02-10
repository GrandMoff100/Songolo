from enum import Enum
from pathlib import Path

from fastapi import APIRouter, File
from pydantic import BaseModel

from songolo.songs import MetaData, Song
from songolo.utils import sha256_snowflake


class LibraryOut(BaseModel):
    path: Path


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


router = APIRouter()


@router.get("/songs")
async def get_songs():
    pass


@router.post("/songs/new/upload")
async def upload_song(
    song: NewSong,
    override_meta: bool = True,
    file: bytes = File(...),
):
    song.content = file
    song.download("upload", override_meta=override_meta)
    return song


@router.post("/songs/new/import/{source}", response_model=SongOut)
async def import_song(song: Song, source: Source):
    song.download(source)
    return song


@router.get("/songs/{snowflake}/log")
async def get_song_log():
    pass


@router.get("/songs/{snowflake}/content")
async def get_song_content():
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
