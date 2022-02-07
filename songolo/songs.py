import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import eyed3  # type: ignore[import]
import gitdb  # type: ignore[import]
import youtube_dl  # type: ignore[import]
from git import Actor, Repo  # type: ignore[import]
from pydantic import BaseModel, HttpUrl


class Library(BaseModel):
    path: Path = Path(".songolo")
    remote: Optional[HttpUrl] = None
    prefix: str = "[Songolo] "

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        Repo.init(self.path, mkdir=True, initial_branch="master")
        try:
            self.repo.commit("master")
        except gitdb.exc.BadName:
            self.first_commit()

    @property
    def actor(self) -> Actor:
        return Actor(
            "Songolo Storage", "songolo-storage@users.noreply.github.com"
        )

    def first_commit(self):
        with open(self.path.joinpath("README.md"), "w") as f:
            f.write(
                "# Songolo Storage\n\n"
                "This is the storage directory for your Songolo instance.\n"
            )
        self.repo.index.add(["README.md"])
        self.repo.index.commit(
            self.prefix + "Initial Commit", author=self.actor
        )

    @property
    def repo(self):
        return Repo(self.path)

    def cleanse_master(self):
        if not self.repo.active_branch.name == "master":
            self.repo.git.checkout("master", no_commit=True)
        for file in self.path.glob("*.mp3"):
            os.remove(str(file))
        self.repo.index.commit(
            self.prefix + json.dumps({"entry": "cleanse", "details": {}}),
            author=self.actor,
            skip_hooks=True,
        )

    def songs(self, max_count=9999) -> Generator["Song", None, None]:
        for commit in self.repo.iter_commits("master", max_count=max_count):
            data = json.loads(commit.message.replace(self.prefix, "", 1))
            if data.get("job") == "import":
                yield Song(library=self, **data.get("details", {}))


class Song(BaseModel):
    author: str
    title: str
    link: Optional[str] = None
    extras: Dict[str, str] = {}
    content: Optional[bytes] = None
    library: Library = Library()

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
            self.library.prefix
            + json.dumps(
                {
                    "entry": "import",
                    "details": dict(
                        author=self.author, title=self.title, link=self.link
                    ),
                }
            ),
            author=self.library.actor,
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
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "noplaylist": True,
            "call_home": False,
            "prefer_ffmpeg": True,
            "outtmpl": str(
                self.library.path.absolute().joinpath(f"{self.digest}.%(ext)s")
            ),
        }
