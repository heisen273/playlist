import os

try:
    from playlist.model.Platform import Platform
except:
    from model import Platform

# File-paths
DEFAULT_PATH: str = os.path.dirname(os.path.realpath(__file__)).split("venv/")[0]
DEFAULT_CONFIG_FILE = ".config.json"

# Spotify
SPOTIFY_SCOPES: list[str] = [
    "user-library-read",
    "playlist-modify-public",
    "playlist-modify-private",
]
MAX_SPOTIFY_RECOMMENDATION_CHUNK_SIZE: int = 5
MAX_SPOTIFY_PLAYLIST_CHUNK_SIZE: int = 100

# LastFM
lastFMUrl: str = "https://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist={artist}&track={title}&api_key={apiKey}&format=json&limit=5"


# Timeouts
DEFAULT_TIMEOUT = 5

DB_NAME = "playlist"
DB_URL = "https://datastorage-140b8-default-rtdb.europe-west1.firebasedatabase.app/"
LOG_CHAT_ID = 2014609673

# Bot constants
EXTRA_SETTINGS = "extra_settings"
GENERATE_PLAYLIST = "generate_playlist"
GENERATE_PLAYLIST_SPOTIFY = f"{GENERATE_PLAYLIST}_{Platform.SPOTIFY}"
GENERATE_PLAYLIST_YOUTUBE = f"{GENERATE_PLAYLIST}_{Platform.YOUTUBE}"


AUTH = "auth_"
AUTH_SPOTIFY = f"auth_{Platform.SPOTIFY}"
AUTH_YOUTUBE = f"auth_{Platform.YOUTUBE}"

SEPARATOR = "separator"
LAST_N_PREFIX = "last_"
LAST_N_ROW = 4
SELECTOR = "🔷"


# TODO: implement 'what I don't want to hear' functionality.
blackList: list[str] = ["travis scott"]
