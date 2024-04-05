from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

try:
    from playlist.model.Platform import Platform
except ModuleNotFoundError:
    from model import Platform


class Auth(dict):
    isDummy: bool = False

    def __init__(self, data):
        super().__init__(self, **data)
        self.isDummy = self.pop("isDummy", False)


class User(BaseModel):
    """
    Model for managing the Users.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")},
        arbitrary_types_allowed=True,
    )

    userId: str | None = Field(alias="userId", default=None)
    userName: str | None = Field(alias="username", default=None)
    messages: int | None = Field(alias="messages", default=0)
    inProgress: bool = Field(alias="inProgress", default=False)
    spotifyAuth: Auth | dict | None = Field(alias=Platform.SPOTIFY, default=None)
    youtubeAuth: Auth | dict | None = Field(alias=Platform.YOUTUBE, default=None)
    created: datetime | None = Field(alias="_created", default=datetime.now())
    updated: datetime | None = Field(alias="_updated", default=datetime.now())

    @field_validator("spotifyAuth", mode="before")
    @classmethod
    def preprocessSpotifyAuth(cls, v: dict | None) -> Auth | None:
        """
        Pre-process auth dict.
        """
        if v is None:
            return v
        return Auth(v)

    @field_validator("youtubeAuth", mode="before")
    @classmethod
    def preprocessYoutubeAuth(cls, v: dict | None) -> Auth | None:
        """
        Pre-process auth dict.
        """
        if v is None:
            return v
        return Auth(v)

    @classmethod
    def from_dict(cls, rawObject: dict) -> "User":
        """
        Loading User object from raw dictionary.
        """
        return cls(**rawObject)


if __name__ == "__main__":
    a = User(**{"spotify": Auth({"cool": "data", "1": 2, "3": 4, "isDummy": True})})
    print(a)
    print(a.model_dump(mode="json"))
