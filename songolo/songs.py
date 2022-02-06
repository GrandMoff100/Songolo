import hashlib
import json
import os
from typing import Dict, Optional

import eyed3  # type: ignore[import]
import youtube_dl  # type: ignore[import]
from pydantic import BaseModel
from pygit2 import Repository  # type: ignore[import]


class Library(BaseModel):
    path: str = None
    prefix = "[Songolo] "

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.path is None:
            self.path = ".songolo"
            os.mkdir(self.path)
        if not os.path.exists(self.path):
            raise OSError(f"Directory {self.path!r} does not exist.")
        self.repo = Repository(self.path)

    def cleanse_working_tree(self):
        pass

    def songs(self):
        pass


class Song(BaseModel):
    author: str
    title: str
    link: str
    prefix: str = "mp3"
    extras: Dict[str, str] = {}
    content: Optional[bytes] = None
    library: Library = Library()

    def digest(self) -> str:
        text = f"{self.author} {self.title} {self.link}"
        return hashlib.sha256(text.encode()).hexdigest()

    def save(self):
        if self.content:
            path = os.path.join(self.library.path, f"{self.digest()}.{self.prefix}")
            with open(path, "wb") as f:
                f.write(self.content)
            meta = eyed3.load(path)
            meta.tag.artist = self.author
            meta.tag.title = self.title
            meta.tag.link = self.link
            meta.tag.extras = json.dumps(self.extras)
            meta.tag.save()

    def download(self):
        with youtube_dl.YoutubeDL(self.options) as ydl:
            ydl.download([self.link])

    def _options(self):
        return {
            "extractaudio": True,
            "audioformat": "mp3",
            "ratelimit": "2M",
            "audioquality": "0",
            "noplaylist": True,
            "call_home": False,
            "prefer_ffmpeg": True,
            "ignoreerrors": True
        }
