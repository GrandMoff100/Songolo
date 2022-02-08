import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import eyed3  # type: ignore[import]
import gitdb  # type: ignore[import]
import youtube_dl  # type: ignore[import]
from git import Actor, Repo
from pydantic import BaseModel, HttpUrl


class Library(BaseModel):
    path: Path = Path(".songolo")
    remote: Optional[HttpUrl] = None
    prefix: str = "[Songolo] "
    initial_branch: str = "master"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        Repo.init(self.path, mkdir=True, initial_branch=self.initial_branch)
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
            self.prefix + json.dumps({"job": "init", "details": {}}),
            author=self.actor,
        )

    @property
    def repo(self):
        return Repo(self.path)

    def cleanse_master(self):
        self.repo.git.checkout(self.initial_branch)
        for file in self.path.glob("*.mp3"):
            os.remove(str(file))
        self.repo.index.commit(
            self.prefix + json.dumps({"entry": "cleanse", "details": {}}),
            author=self.actor,
            skip_hooks=True,
        )

    def songs(self, max_count=9999) -> Generator["Song", None, None]:
        for commit in self.repo.iter_commits(self.initial_branch, max_count=max_count):
            if commit.message.startswith(self.prefix):
                json_data = commit.message.replace(self.prefix, "", 1)
                data = json.loads(json_data)
                if data.get("entry") == "import":
                    print(commit.diff())
                    yield Song(
                        library=self, meta=MetaData(**data.get("details", {}))
                    )

    def load_song(self, song: "Song") -> Optional[bytes]:
        exists, commit = self.exists_in_history
        if exists:
            self.repo.git.checkout(commit)
            with open(song.filepath, "rb") as f:
                content = f.read()
            self.repo.git.checkout(self.initial_branch)
            return content


class MetaData(BaseModel):
    artist: str
    title: str
    album: Optional[str] = None
    album_artist: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[str] = None
    composer: Optional[str] = None
    link: Optional[str] = None

    def effective_dict(self):
        return dict([*filter(lambda item: bool(item[1]), self.dict().items())])


class Song(BaseModel):
    meta: MetaData
    content: Optional[bytes] = None
    library: Library = Library()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = self.library.load_song(self)

    @property
    def digest(self) -> str:
        text = f"{self.meta.artist} - {self.meta.title}"
        return hashlib.sha256(text.encode()).hexdigest()

    @property
    def branch(self) -> str:
        return f"song/{self.digest}"

    @property
    def exists_in_history(self) -> bool:
        for commit in self.library.repo.iter_commits(self.library.initial_branch, max_count=9999):
            if commit.message.startswith(self.library.prefix):
                json_data = commit.message.replace(self.library.prefix, "", 1)
                data = json.loads(json_data)
                if data.get("entry") == "import":
                    if details := data.get("details"):
                        constant_data = self.dict()
                        testing_data = constant_data.copy()
                        testing_data.update(details)
                        if constant_data == testing_data:
                            return True, commit
        return False, None

    @property
    def filename(self) -> str:
        return f"{self.digest}.mp3"

    @property
    def filepath(self) -> Path:
        return self.library.path.joinpath(self.filename)

    def save_metadata(self) -> None:
        path = self.library.path.joinpath(self.filename)
        meta = eyed3.load(path)
        for attr, value in self.meta.effective_dict().items():
            setattr(meta.tag, attr, value)
        if self.meta.link:
            meta.tag.comment = self.meta.link
        meta.tag.save()

    def commit(self) -> None:
        self.library.repo.index.add([str(self.filename)])
        self.library.repo.index.commit(
            self.library.prefix
            + json.dumps(
                {
                    "entry": "import",
                    "details": self.meta.effective_dict(),
                }
            ),
            author=self.library.actor,
        )
        self.library.repo.git.checkout(self.library.initial_branch)
        self.library.repo.git.merge(f"song/{self.digest}", no_commit=True)
        self.library.cleanse_master()

    def download(self, override_meta=True) -> None:
        self.library.repo.git.checkout(self.library.initial_branch)
        if self.branch not in map(str, self.library.repo.branches):
            commit = self.library.repo.commit(self.library.initial_branch)
            self.library.repo.git.checkout(commit, b=self.branch)
        else:
            self.library.repo.git.checkout(self.branch)
        with youtube_dl.YoutubeDL(self._options) as ydl:
            ydl.download([self.meta.link])
        with open(self.library.path.joinpath(self.filename), "rb") as f:
            self.content = f.read()
        if override_meta:
            self.save_metadata()
        self.commit()

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
    
    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        result = super().dict(*args, **kwargs)
        result.update(meta=self.meta.effective_dict())
        return result
