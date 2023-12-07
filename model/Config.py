import json
from pydantic import BaseModel

# TODO: Add these globals into file with constants.
DEFAULT_PATH = "/Users/anton/projects/playlist"
DEFAULT_CONFIG_FILE = ".config.json"


class Config(BaseModel):
    """
    useful doc-string
    """
    def __init__(self, fileName: str = ""):
        """
        <useful doc-string>
        """
        # TODO: Add check `if file exists`.
        with open(f"{DEFAULT_PATH}/{fileName or DEFAULT_CONFIG_FILE}") as f:
            super().__init__(**json.load(f))

    # Playlists.
    # `main` playlist where all liked songs are.
    mainYoutubePlaylist: str | None = None
    # `tmp` playlist – not sure what for, but might be useful in the future.
    tmpYoutubePlaylist: str | None = None

    # Same idea here, but for spotify no need to have `main` playlist as it's available in API.
    tmpSpotifyPlaylist: str | None = None

    # User ID.
    spotifyUserId: str | None = None
    youtubeUserId: str | None = None

    # Credentials.
    # Spotify credentials.
    spotifyClientId: str | None = None
    spotifyClientSecret: str | None = None

    # LastFM Credentials
    lastFMClientId: str | None = None
    lastFMClientSecret: str | None = None

    # Youtube credentials are loaded from .oauth.json file, so it's required to just store the filePath.
    youtubeAuthJson: str | None = None

    def store(self, fileName: str = DEFAULT_CONFIG_FILE):
        """(Over)writes config into default path"""
        with open(f"{DEFAULT_PATH}/{fileName}", "w") as f:
            json.dump(self.__dict__, f)


if __name__ == "__main__":
    print(Config())
