import json
import os
import hashlib
import youtube_dl
from pydantic import BaseModel
from typing import Optional, Dict
from pygit2 import Repository


class Library(BaseModel):
    prefix = "[Songolo] "

    def __init__(self, path: Optional[str] = None) -> None:
        if path is None:
            path = ".songolo"
            os.mkdir(path)
        if not os.path.exists(path):
            raise OSError(f"Directory {path!r} does not exist.")
        self.repo = Repository(path)

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

    def digest(self) -> str:
        text = f"{author} {title} {link}"
        return hashlib.sha256(text.encode()).hexdigest()

    def save(self, library: Library):
        if self.content:
            path = os.path.join(library.path, self.digest() + "." + self.prefix)
            with open(path, "w") as f:
                f.write(self.content)
            meta = eyed3.load(path)
            meta.tag.artist = self.author
            meta.tag.title = self.title
            meta.tag.link = self.link
            meta.tag.extras = json.dumps(self.extras)
            meta.tag.save()

    def download(self, library: Library):
        options = self._options(library)
        with youtube_dl.YoutubeDL() as ydl:
            ydl.download([self.link])

    def _options(self, library: Library):
        return {}




