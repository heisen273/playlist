import os

DEFAULT_PATH: str = os.path.dirname(os.path.realpath(__file__))
DEFAULT_CONFIG_FILE = ".config.json"

# Spotify
SPOTIFY_SCOPES: list[str] = ["user-library-read", "playlist-modify-public", "playlist-modify-private"]
MAX_SPOTIFY_RECOMMENDATION_CHUNK_SIZE: int = 5
MAX_SPOTIFY_PLAYLIST_CHUNK_SIZE: int = 100

# TODO: implement 'what I don't want to hear' functionality.
blackList: list[str] = ["travis scott"]