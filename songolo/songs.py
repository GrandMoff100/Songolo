import hashlib
from pathlib import Path
import json
import os
import gitdb
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
        try:
            self.repo.commit("master")
        except gitdb.exc.BadName:
            self.first_commit()

    @property
    def actor(self) -> Actor:
        return Actor("Songolo Storage", "songolo-storage@users.noreply.github.com")

    def first_commit(self):
        with open((file := self.path.joinpath("README.md")), "w") as f:
            f.write("# Songolo Storage\n\nThis is the storage directory for your Songolo instance.\n")
        self.repo.index.add(["README.md"])
        self.repo.index.commit(self.prefix + "Initial Commit", author=self.actor)

    @property
    def repo(self):
        return Repo(self.path)

    def cleanse_master(self):
        if not self.repo.active_branch.name == "master":
            self.repo.git.checkout("master", no_commit=True)
        for file in self.path.glob("*.mp3"):
            os.remove(str(file))
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

    def songs(self, max_count=9999):
        for commit in self.repo.iter_commits("master", max_count=max_count):
            yield commit



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
        return f"{self.digest}.mp3"

    def save(self):
        path = self.library.path.joinpath(self.filename)
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
        self.library.repo.index.add([str(self.filename)])
        self.library.repo.index.commit(
            self.library.prefix + json.dumps(
                {
                    "job": "import",
                    "details": dict(author=self.author, title=self.title, link=self.link)
                }
            ),
            author=self.library.actor
        )
        self.library.repo.git.checkout("master")
        self.library.repo.git.merge(f"song/{self.digest}", no_commit=True)
        self.library.cleanse_master()

    def download(self):
        branch = f"song/{self.digest}"
        if branch not in map(str, self.library.repo.branches):
            commit = self.library.repo.commit("master")
            self.library.repo.git.checkout(commit, b=branch)
        else:
            self.library.repo.git.checkout(branch)

        with youtube_dl.YoutubeDL(self._options) as ydl:
            ydl.download([self.link])
        with open(self.library.path.joinpath(self.filename), "rb") as f:
            self.content = f.read()
        self.save()

    @property
    def _options(self) -> Dict[str, Any]:
        """Returns our download options for YoutubeDL."""
        return {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "noplaylist": True,
            "call_home": False,
            "prefer_ffmpeg": True,
            "outtmpl": str(self.library.path.absolute().joinpath(f"{self.digest}.%(ext)s"))
        }
