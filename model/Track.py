import json
from pydantic import BaseModel, Field, ConfigDict, AliasChoices, ValidationInfo

from pydantic.functional_validators import BeforeValidator, AfterValidator
from typing_extensions import Annotated


DEFAULT_PATH = "/Users/anton/projects/playlist"
DEFAULT_CONFIG_FILE = ".config.json"


def artistNameValidator(value) -> list:
    # Handle case for
    # - Spotify & YouTube(when `x` is list).
    # - case for previously exported obj via self.__dict__(when `x` isn't a dict str)
    if type(value) is list:
        return [x.get('name') if type(x) is dict else x for x in value]
    # Handle case for LastFM.
    elif type(value) is dict:
        return [value.get("name")]
    # Handle case for previously exported obj via self.__dict__



ArtistName = Annotated[list, BeforeValidator(artistNameValidator)]

ArtistId = Annotated[list, AfterValidator(lambda artistList:
                                                  [x.get('id') if type(x) is dict else x for x in artistList])]
Duration = Annotated[int, AfterValidator(lambda duration: round(duration / 1000) if duration > 1000 else duration)]


class Track(BaseModel):
    # TODO: needs a __hash__ method, so you could quickly check if track is in list of tracks.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Special handling for ArtistId, so you could set it as `None` in method related to specific platform.
        if kwargs.get('spotifyArtistId', 0) is None:
            self.spotifyArtistId = None
        if kwargs.get('youtubeArtistId', 0) is None:
            self.youtubeArtistId = None
        if kwargs.get('zeroDuration') is True:
            self.duration = 0


    model_config = ConfigDict(populate_by_name=True)

    # Choice alias to match title from raw youtube & spotify jsons.
    title: str | None = Field(validation_alias=AliasChoices("title", "name"))
    artists: ArtistName | None = Field(validation_alias=AliasChoices("artists", "artist"))

    duration: Duration | None = Field(validation_alias=AliasChoices("duration_seconds", "duration_ms"), default=None)

    youtubeArtistId: ArtistId | None = Field(alias="artists", default=None)
    youtubeId: str | None = Field(alias="videoId", default=None)

    # Spotify is matched manually, so defaults to `None`.
    spotifyId: str | None = Field(alias="id", default=None)
    spotifyArtistId: ArtistId | None = Field(alias="artists", default=None)

    @classmethod
    def from_dict(cls, rawObject: dict) -> "Track":
        return cls(**rawObject)

    @property
    def artistName(self) -> str:
        """Docstring for artistName"""
        return " ".join(self.artists)

    @property
    def firstArtistName(self) -> str:
        """Docstring for artistName"""
        return self.artists[0]



if __name__ == "__main__":
    track = {'videoId': 'TNPmfBrmlxc', 'title': 'Big Big Sesh - Seshlehem', 'artists': [{'name': 'Seshlehem', 'id': 'UCGE1DCR_xJO5y72HWakqnbA'}], 'album': None, 'likeStatus': 'INDIFFERENT', 'inLibrary': None, 'thumbnails': [{'url': 'https://i.ytimg.com/vi/TNPmfBrmlxc/sddefault.jpg?sqp=-oaymwEWCJADEOEBIAQqCghqEJQEGHgg6AJIWg&rs=AMzJL3kwV8omBUowoxPCapdQgV5NaXUg7w', 'width': 400, 'height': 225}], 'isAvailable': True, 'isExplicit': False, 'videoType': 'MUSIC_VIDEO_TYPE_UGC', 'duration': '3:02', 'duration_seconds': 182, 'setVideoId': '74CEF74FBE23B0C5'}

    a = Track(**track, youtubeArtistId=None)
    print(Track(**a.__dict__))


