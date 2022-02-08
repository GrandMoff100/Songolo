from songolo.songs import Library, MetaData, Song

lib = Library()


songs = [
    Song(
        meta=MetaData(
            artist="One Republic",
            title="Secrets",
            link="https://www.youtube.com/watch?v=7U-9NlSmNKc",
        )
    ),
    Song(
        meta=MetaData(
            artist="The Weeknd",
            title="Blinding Lights",
            link="https://www.youtube.com/watch?v=fHI8X4OXluQ",
        )
    ),
    Song(
        meta=MetaData(
            artist="Saint Motel",
            title="My Type",
            link="https://open.spotify.com/track/6kcHg7XL6SKyPNd78daRBL?si=612bf861a2364a6b"
        )
    )
]


for song in songs:
    if "youtube" in song.meta.link:
        song.download("youtube")
    elif "spotify" in song.meta.link:
        song.download("spotify")


for song in lib.songs():
    print(song)
