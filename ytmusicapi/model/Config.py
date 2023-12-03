import json
from dataclasses import dataclass
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from pydantic.tools import parse_obj_as

DEFAULT_PATH = "/Users/anton/projects/playlist"
DEFAULT_CONFIG_FILE = ".config.json"

# @dataclass
class Config(BaseModel):

    def __init__(self, fileName: str = ""):
        """
        <useful doc-string>
        """
        with open(f"{DEFAULT_PATH}/{fileName or DEFAULT_CONFIG_FILE}") as f:
            super().__init__(**json.load(f))

    # `main` playlist where all liked songs are.
    mainYoutubePlaylist: str | None = None
    # `tmp` playlist – not sure what for, but might be useful in the future.
    tmpYoutubePlaylist: str | None = None

    # Same idea here
    mainSpotifyPlaylist: str | None = None
    tmpSpotifyPlaylist: str | None = None

    def _store(self, fileName: str = DEFAULT_CONFIG_FILE):
        """Writes config into default path"""
        with open(f"{DEFAULT_PATH}/{fileName}", "w") as f:
            json.dump(self.__dict__, f)


if __name__ == "__main__":
    print(Config())
    # print(a)
