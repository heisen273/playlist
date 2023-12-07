import json
import logging
from pathlib import Path
from pydantic import BaseModel, ConfigDict

# TODO: Add these globals into file with constants.
DEFAULT_PATH = "/Users/anton/projects/playlist"
DEFAULT_CONFIG_FILE = ".config.json"


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger: logging.Logger = logging.getLogger()


class Config(BaseModel):

    model_config = ConfigDict(populate_by_name=True)

    def __init__(self, filePath: str = "", fileName: str = "", loadFromDisk: bool = False, **kwargs):
        """
        <useful doc-string>
        """

        formattedPath: Path = Path(f"{filePath or DEFAULT_PATH}/{fileName or DEFAULT_CONFIG_FILE}")

        # Early exit in case if:
        # - not loading from disk.
        if not loadFromDisk:
            super().__init__(**kwargs)
            return
        # -it's not possible to load requested config.
        elif not Path.exists(formattedPath):
            logging.error(f"Requested config filepath does not exist: {formattedPath}")
            super().__init__(**kwargs)
            return

        with open(formattedPath) as f:
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

    def store(self, filePath: str = DEFAULT_PATH, fileName: str = DEFAULT_CONFIG_FILE):
        """(Over)writes config into default path"""
        with open(f"{filePath}/{fileName}", "w") as f:
            json.dump(self.__dict__, f)


if __name__ == "__main__":
    print(Config())

