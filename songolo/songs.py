"""Module for interacting with and storing songs/audios."""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
from unittest.mock import patch

import eyed3  # type: ignore[import]
import gitdb  # type: ignore[import]
import youtube_dl  # type: ignore[import]
from git import Actor, Repo
from git.objects.commit import Commit
from pydantic import BaseModel
from spotdl.download import DownloadManager
from spotdl.parsers import parse_arguments, parse_query
from spotdl.search import SpotifyClient

from songolo.utils import Base64


class Library(BaseModel):
    """Storage for MP3 Songs as an Object Model."""

    path: Path = Path(".songolo")
    prefix: str = "[Songolo] "
    initial_branch: str = "master"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.path = self.path.absolute()
        if not self.path.exists():
            self.path.mkdir()
        Repo.init(
            self.storagepath,
            mkdir=True,
            initial_branch=self.initial_branch,
        )
        try:
            self.repo.commit("master")
        except gitdb.exc.BadName:
            self.first_commit()

    @property
    def storagepath(self) -> Path:
        """The path to the storage repository."""
        return self.path.joinpath("songs")

    @property
    def actor(self) -> Actor:
        """Author of all Songolo Commits."""
        return Actor(
            "Songolo Storage",
            "songolo-storage@users.noreply.github.com",
        )

    def first_commit(self) -> None:
        """Intializes the storage path with a README Initial Commit."""
        with open(
            self.storagepath.joinpath("README.md").absolute(),
            mode="w",
            encoding=Base64.encoding,
        ) as file:
            file.write(
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
        """The git repository object for the library storage path."""
        return Repo(self.storagepath)

    def cleanse_master(self) -> None:
        """Deletes songs from the master branch to keep filesystem clean."""
        self.repo.git.checkout(self.initial_branch)
        for file in self.path.glob("*.mp3"):
            self.repo.git.rm(str(file.absolute()))
        self.repo.index.commit(
            self.prefix + json.dumps({"entry": "cleanse", "details": {}}),
            author=self.actor,
            skip_hooks=True,
        )

    def songs(self) -> Generator["Song", None, None]:
        """Yields up to as many songs as possible or specified from commit history."""
        for _, data in self.commit_data_history:
            if data.get("entry") == "import":
                yield Song(
                    library=self,
                    meta=MetaData(**data.get("details", {})),
                )

    def get_song(self, snowflake: str) -> Optional["Song"]:
        """Exchanges snowflake for Song object from commit history."""
        for _, data in self.commit_data_history:
            if data.get("entry") == "import":
                if data.get("details", {}).get("snowflake") == snowflake:
                    return Song(
                        library=self,
                        meta=MetaData(**data.get("details", {})),
                    )
        return None

    def load_song_content(self, song: "Song") -> Optional[bytes]:
        """Checks out the song commit and returns the file content."""
        exists, commit = song.exists_in_history
        if exists:
            self.repo.git.checkout(commit)
            self.repo.git.reset(hard=True)
            with open(song.filepath, "rb") as file:
                content = file.read()
            self.repo.git.checkout(self.initial_branch)
            return content
        return None

    @property
    def logpath(self) -> Path:
        """The path to the download logs folder."""
        path = self.path.joinpath("logs")
        if not path.exists():
            path.mkdir()
        return path

    @property
    def commit_data_history(
        self,
    ) -> Generator[Tuple[Commit, Dict[str, Any]], None, None]:
        """Iterates through storage commits to yield valid Songolo entries."""
        for commit in self.repo.iter_commits(
            self.initial_branch, max_count=9999, reverse=True
        ):
            message = commit.message
            if isinstance(message, bytes):
                message = message.decode()
            if message.startswith(self.prefix):
                json_data = message.replace(self.prefix, "", 1)
                data = json.loads(json_data)
                yield commit, data


class MetaData(BaseModel):
    """Sub-model for song meta-data."""

    artist: str
    title: str
    album: Optional[str] = None
    album_artist: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[str] = None
    composer: Optional[str] = None
    extras: Dict[str, str] = {}

    @property
    def link(self) -> Optional[str]:
        """Return the link from mp3 meta-data extras."""
        return self.extras.get("link")

    @property
    def snowflake(self) -> str:
        """Returns the snowflake string uniquely indentifying a song."""
        snowflake = self.extras.get("snowflake")
        if snowflake is None:
            raise ValueError("Invalid song! Song does not have a snowflake.")
        return snowflake

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Filters non-set attributes from the output mapping."""
        return dict(
            [
                *filter(
                    lambda item: bool(item[1]),
                    super().dict(*args, **kwargs).items(),
                )
            ]
        )


class Song(BaseModel):
    """MP3 Song Object Model for the API."""

    meta: MetaData
    library: Library
    content: Optional[bytes] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(
            logging.FileHandler(
                self.logpath,
            ),
        )
        self.logger.info("Log initialized at %s" % str(datetime.now()))
        if self.content is None:
            self.content = self.library.load_song_content(self)

    @property
    def logger(self) -> logging.Logger:
        """The logger used for download output."""
        return logging.getLogger(self.meta.snowflake)

    @property
    def branch(self) -> str:
        """The git branch that the song exists on."""
        return f"song/{self.meta.snowflake}"

    @property
    def logpath(self) -> Path:
        return self.library.logpath.joinpath(f"{self.meta.snowflake}.log")

    @property
    def exists_in_history(self) -> Tuple[bool, Optional[Commit]]:
        """Iterates through commit history to find where this song is stored."""
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
        """Returns the commit where this song is stored. Can return `None`"""
        _, commit = self.exists_in_history
        return commit

    @property
    def filename(self) -> str:
        """Name of the song file."""
        return f"{self.meta.snowflake}.mp3"

    @property
    def filepath(self) -> Path:
        """Returns the path to the mp3 file."""
        return self.library.storagepath.joinpath(self.filename)

    def save_metadata(self) -> None:
        """Saves the song meta-data to the mp3 file."""
        path = self.library.storagepath.joinpath(self.filename)
        meta = eyed3.load(path)
        for attr, value in self.meta.dict().items():
            if self.meta.link:
                meta.tag.comment = self.meta.link
                continue
            setattr(meta.tag, attr, value)
        meta.tag.save()

    def commit_file(self) -> None:
        """Stores the modified file on its own branch."""
        self.library.repo.index.add([self.filename])  # ``git add <song>``
        self.library.repo.index.commit(
            self.library.prefix
            + json.dumps(
                {
                    "entry": "song",
                    "details": self.meta.dict(),
                }
            ),
            author=self.library.actor,
        )  # ``git commit -m "<prefix><json>"``
        self.library.repo.git.checkout(
            self.library.initial_branch
        )  # ``git checkout <main>``
        self.library.repo.git.merge(
            self.branch, no_commit=True
        )  # ``git merge <song_branch>``
        self.library.cleanse_master()  # Keep the main branch clean.

    def scrape_from_youtube(self) -> None:
        """Uses `youtube_dl` to extract the audio from the youtube link."""
        with youtube_dl.YoutubeDL(self._youtubedl_options) as ydl:
            ydl.download([self.meta.link])
        with open(
            self.library.storagepath.joinpath(self.filename), "rb"
        ) as file:
            self.content = file.read()

    def scrape_from_spotify(self) -> None:
        """Uses `spotdl` to to extract audio from the spotify song link."""
        # TODO: Find spotify downloading module that has suitable logging support.
        
    def download(self, source: str, override_meta=True):
        """Downloads and commits itself, the song, to the storage from the given source."""
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
            self.scrape_from_spotify()
        elif source == "upload":
            with open(self.filepath, "wb") as file:
                if self.content is not None:
                    file.write(self.content)
                else:
                    raise ValueError(
                        "Expected song content, "
                        "but I cannot access it! "
                        "How did this happen?!"
                    )
        if override_meta:
            self.save_metadata()
        self.commit_file()

    @property
    def _youtubedl_options(self) -> Dict[str, Any]:
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
                self.library.storagepath.joinpath(
                    f"{self.meta.snowflake}.%(ext)s"
                )
            ),
            "logger": self.logger,
        }

    @property
    def _spotdl_options(self) -> List[str]:
        if self.meta.link is None:
            raise ValueError("Missing spotify link when downloading!!!")
        return [
            "spotdl",
            "--path-template",
            str(self.filepath.absolute()),
            self.meta.link,
        ]

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Custom method for converting Song objects into JSON dictionaries."""
        result = super().dict(*args, **kwargs)
        result.update(meta=self.meta.dict())
        if self.content is not None:
            result.update(content=Base64.encode(self.content))
        return result
