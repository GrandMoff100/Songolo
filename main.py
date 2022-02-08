from songolo.songs import Library, MetaData, Song

lib = Library()



songs = [
    Song(
        meta=MetaData(
            artist="One Republic",
            title="Secrets",
            link="https://www.youtube.com/watch?v=7U-9NlSmNKc"
        )
    ),
    Song(
        meta=MetaData(
            artist="The Weeknd",
            title="Blinding Lights",
            link="https://www.youtube.com/watch?v=fHI8X4OXluQ",
        )
    )
]

for song in songs:
    song.download()

for song in lib.songs():
    print(song)
