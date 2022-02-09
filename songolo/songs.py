import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple

import eyed3  # type: ignore[import]
import gitdb  # type: ignore[import]
import youtube_dl  # type: ignore[import]
from git import Actor, Repo
from git.objects.commit import Commit
from pydantic import BaseModel, HttpUrl

from songolo.utils import Base64


class Library(BaseModel):
    path: Path = Path(".songolo")
    remote: Optional[HttpUrl] = None
    prefix: str = "[Songolo] "
    initial_branch: str = "master"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.path = self.path.absolute()
        Repo.init(
            self.path,
            mkdir=True,
            initial_branch=self.initial_branch,
        )
        try:
            self.repo.commit("master")
        except gitdb.exc.BadName:
            self.first_commit()

    @property
    def actor(self) -> Actor:
        return Actor(
            "Songolo Storage", "songolo-storage@users.noreply.github.com"
        )

    def first_commit(self) -> None:
        with open(self.path.joinpath("README.md").absolute(), "w") as f:
            f.write(
                "# Songolo Storage\n\n"
                "This is the storage directory for your Songolo instance.\n"
                f"Created `{datetime.now()}`"
            )
        self.repo.index.add(["README.md"])
        self.repo.index.commit(
            self.prefix + json.dumps({"job": "init", "details": {}}),
            author=self.actor,
        )

    @property
    def repo(self) -> Repo:
        return Repo(self.path)

    def cleanse_master(self) -> None:
        self.repo.git.checkout(self.initial_branch)
        for file in self.path.glob("*.mp3"):
            self.repo.git.rm(str(file.absolute()))
        self.repo.index.commit(
            self.prefix + json.dumps({"entry": "cleanse", "details": {}}),
            author=self.actor,
            skip_hooks=True,
        )

    def songs(self, max_count=9999) -> Generator["Song", None, None]:
        for commit, data in self.library.commit_data_history:
            if data.get("entry") == "import":
                yield Song(
                    library=self,
                    meta=MetaData(**data.get("details", {})),
                )

    def get_song(self, snowflake: str) -> Optional["Song"]:
        for commit, data in self.commit_data_history:
            if data.get("entry") == "import":
                return Song(
                    library=self,
                    meta=MetaData(**data.get("details", {})),
                )

    def load_song_content(self, song: "Song") -> Optional[bytes]:
        exists, commit = song.exists_in_history
        if exists:
            self.repo.git.checkout(commit)
            self.repo.git.reset(hard=True)
            with open(song.filepath, "rb") as f:
                content = f.read()
            self.repo.git.checkout(self.initial_branch)
            return content

    @property
    def commit_data_history(self):
        for commit in self.repo.iter_commits(
            self.initial_branch,
            max_count=9999,
            reverse=True
        ):
            message = commit.message
            if isinstance(message, bytes):
                message = message.decode()
            if message.startswith(self.prefix):
                json_data = message.replace(self.prefix, "", 1)
                data = json.loads(json_data)
                yield commit, data


class MetaData(BaseModel):
    artist: str
    title: str
    album: Optional[str] = None
    album_artist: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[str] = None
    composer: Optional[str] = None
    link: Optional[str] = None

    def dict(self, *args, **kwargs):
        return dict(
            [
                *filter(
                    lambda item: bool(item[1]),
                    super().dict(*args, **kwargs).items(),
                )
            ]
        )


class Song(BaseModel):
    meta: MetaData
    content: Optional[bytes] = None
    snowflake: str = None
    library: Library = Library()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.content is None:
            self.content = self.library.load_song_content(self)
        if self.snowflake is None:
            self.snowflake = "abc"  # TODO: Implement song snowflakes
            

    @property
    def digest(self) -> Optional[str]:
        if self.content is not None:
            return hashlib.sha256(self.content).hexdigest()
        raise ValueError("Cannot hash a song with no content.")

    @property
    def branch(self) -> str:
        return f"song/{self.snowflake}"

    @property
    def exists_in_history(self) -> Tuple[bool, Optional[Commit]]:
        for commit, data in self.library.commit_data_history:
            if data.get("entry") == "song":
                if details := data.get("details"):
                    constant_data = super().dict()
                    testing_data = constant_data.copy()
                    testing_data.update(meta=details)
                    if constant_data == testing_data:
                        return True, commit
        return False, None

    @property
    def commit(self) -> Optional[Commit]:
        _, commit = self.exists_in_history
        return commit

    @property
    def filename(self) -> str:
        return f"{self.snowflake}.mp3"

    @property
    def filepath(self) -> Path:
        return self.library.path.joinpath(self.filename)

    def save_metadata(self) -> None:
        path = self.library.path.joinpath(self.filename)
        meta = eyed3.load(path)
        for attr, value in self.meta.dict().items():
            if self.meta.link:
                meta.tag.comment = self.meta.link
                continue
            setattr(meta.tag, attr, value)
        
        meta.tag.save()

    def commit_file(self) -> None:
        self.library.repo.index.add([self.filename])
        self.library.repo.index.commit(
            self.library.prefix
            + json.dumps(
                {
                    "entry": "song",
                    "details": self.meta.dict(),
                }
            ),
            author=self.library.actor,
        )
        self.library.repo.git.checkout(self.library.initial_branch)
        self.library.repo.git.merge(self.branch, no_commit=True)
        self.library.cleanse_master()

    def scrape_from_youtube(self) -> None:
        with youtube_dl.YoutubeDL(self._options) as ydl:
            ydl.download([self.meta.link])
        with open(self.library.path.joinpath(self.filename), "rb") as f:
            self.content = f.read()

    def download(self, source: str, override_meta=True):
        if self.branch not in map(
            str,
            self.library.repo.branches,
        ):  # type: ignore[call-overload]
            commit = self.library.repo.commit(self.library.initial_branch)
            self.library.repo.git.checkout(commit, b=self.branch)
        else:
            self.library.repo.git.checkout(self.branch)
        
        if source == "youtube":
            self.scrape_from_youtube()
        elif source == "spotify":
            raise NotImplementedError("Sorry :( Spotify not implementated yet")
        elif source == "upload":
            with open(self.filepath, "wb") as f:
                f.write(self.content)

        if override_meta:
            self.save_metadata()
        self.commit_file()

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
                self.library.path.absolute().joinpath(f"{self.snowflake}.%(ext)s")
            ),
        }

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        result = super().dict(*args, **kwargs)
        result.update(meta=self.meta.dict())
        result.update(content=Base64.encode(self.content))
        result.update(sha=self.commit.hexsha)
        return result
