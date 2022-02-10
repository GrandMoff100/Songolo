from songolo.songs import Library, MetaData, Song
from songolo.utils import sha256_snowflake

lib = Library(path="dist")


songs = [
    Song(
        library=lib,
        snowflake=sha256_snowflake(),
        meta=MetaData(
            artist="One Republic",
            title="Secrets",
            extras=dict(
                link="https://www.youtube.com/watch?v=7U-9NlSmNKc",
                snowflake=sha256_snowflake(),
            ),
        ),
    ),
    Song(
        library=lib,
        snowflake=sha256_snowflake(),
        meta=MetaData(
            extras=dict(
                snowflake=sha256_snowflake(),
                link="https://www.youtube.com/watch?v=fHI8X4OXluQ",
            ),
            artist="The Weeknd",
            title="Blinding Lights",
        ),
    ),
    Song(
        library=lib,
        meta=MetaData(
            extras=dict(
                snowflake=sha256_snowflake(),
                link="https://open.spotify.com/track/6kcHg7XL6SKyPNd78daRBL",
            ),
            artist="Saint Motel",
            title="My Type",
        ),
    ),
]


def main():
    for song in songs:
        if song.meta.link is not None:
            if "youtube" in song.meta.link:
                song.download("youtube")
            elif "spotify" in song.meta.link:
                song.download("spotify")


main()
