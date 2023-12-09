from pydantic import BaseModel, Field, ConfigDict, AliasChoices

from pydantic.functional_validators import BeforeValidator, AfterValidator
from typing_extensions import Annotated


def artistNameValidator(value) -> list:
    # Handle case for
    # - Spotify & YouTube(when `x` is list).
    if isinstance(value, list):
        return [x.get("name") if isinstance(x, dict) else x for x in value]
    # Handle case for LastFM.
    elif isinstance(value, dict):
        return [value.get("name")]


ArtistName = Annotated[list, BeforeValidator(artistNameValidator)]

ArtistId = Annotated[
    list,
    AfterValidator(
        lambda artistList: [x.get("id") if type(x) is dict else x for x in artistList]
    ),
]
Duration = Annotated[
    int,
    AfterValidator(
        lambda duration: round(duration / 1000) if duration > 1000 else duration
    ),
]


class Track(BaseModel):

    model_config = ConfigDict(populate_by_name=True)

    # TODO:
    #  - needs a __hash__ method, so you could quickly check `if track is in list of tracks`.
    #  - think whether it make sense splitting youtube & spotify Tracks in separate classes and introducing
    #  new unitied one.

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Special handling for ArtistId, so you could set it as `None` in method related to specific platform.
        if kwargs.get("spotifyArtistId", 0) is None:
            self.spotifyArtistId = None
        if kwargs.get("youtubeArtistId", 0) is None:
            self.youtubeArtistId = None
        if kwargs.get("zeroDuration") is True:
            self.duration = 0

    # Choice alias to match title from raw youtube & spotify jsons.
    # Note: `first_choice` is always youtube, second is always spotify.
    title: str | None = Field(validation_alias=AliasChoices("title", "name"))
    artists: ArtistName | None = Field(
        validation_alias=AliasChoices("artists", "artist")
    )

    duration: Duration | None = Field(
        validation_alias=AliasChoices("duration_seconds", "duration_ms"), default=None
    )

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
