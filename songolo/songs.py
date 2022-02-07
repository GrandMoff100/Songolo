import hashlib
from pathlib import Path
import json
import os
from dataclasses import field
from typing import Dict, Optional, Any

import eyed3  # type: ignore[import]
import youtube_dl  # type: ignore[import]
from pydantic import BaseModel, HttpUrl
from pydantic.dataclasses import dataclass
from git import Repo, Actor  # type: ignore[import]


class Library(BaseModel):
    path: Optional[Path] = None
    remote: Optional[HttpUrl] = None
    prefix: str = "[Songolo] "

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.path is None:
            self.path = Path(".songolo")
        Repo.init(self.path, mkdir=True, initial_branch="master")        

    @property
    def actor(self) -> Actor:
        return Actor("Songolo Storage <songolo-storage@users.noreply.github.com>")

    @property
    def repo(self):
        return Repo(self.path)

    def cleanse_master(self):
        if not self.repo.active_branch.name == "master":
            self.repo.heads.master.checkout()
        for file in self.path.glob("*.mp3"):
            self.repo.add([file])
            os.remove(file)
        self.repo.index.commit(
            self.prefix + json.dumps(
                {
                    "job": "cleanse",
                    "details": {}
                }
            ),
            author=self.actor,
            skip_hooks=True
        )

    def songs(self):
        pass


class Song(BaseModel):
    author: str
    title: str
    link: str
    extras: Dict[str, str] = {}
    content: Optional[bytes] = None
    library: Optional[Library] = Library()

    @property
    def digest(self) -> str:
        text = f"{self.author} {self.title} {self.link}"
        return hashlib.sha256(text.encode()).hexdigest()

    @property
    def filename(self) -> str:
        return f"{self.digest()}.mp3"

    def save(self):
        if self.content:
            path = os.path.join(self.library.path,)
            with open(path, "wb") as f:
                f.write(self.content)
            meta = eyed3.load(path)
            meta.tag.artist = self.author
            meta.tag.title = self.title
            meta.tag.link = self.link
            meta.tag.extras = json.dumps(self.extras)
            meta.tag.save()
            self.commit()
    
    def commit(self):
        new_head = self.library.repo.create_head(f"song/{self.digest}", commit=self.repo.commit("master"))
        new_head.checkout()
        self.library.repo.index.add([self.filename])
        self.library.repo.index.commit(
            self.library.prefix + json.dumps(
                {
                    "job": "import",
                    "details": {}
                }
            ),
            author=self.library.actor
        )
        self.repo.heads.master.checkout()
        self.repo.git.merge(f"song/{self.digest}", no_commit=True)
        self.library.cleanse_master()

    def download(self):
        with youtube_dl.YoutubeDL(self._options) as ydl:
            ydl.download([self.link])
        self.save()

    @property
    def _options(self) -> Dict[str, Any]:
        """Returns our download options for YoutubeDL."""
        return {
            "config_location": "download.conf",
            "outtmpl": f"{self.library.path.absolute()}/{self.digest}.%(ext)s"
        }
