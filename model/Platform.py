from __future__ import annotations

import os
from enum import StrEnum

from spotipy import CacheFileHandler, MemoryCacheHandler, SpotifyOAuth
from telegram import Update, InlineKeyboardButton
from typing import Callable, TYPE_CHECKING


if TYPE_CHECKING:
    try:
        from core.generator import PlaylistGenerator
        from model.User import User
    except ModuleNotFoundError:
        from generator import PlaylistGenerator
        from model import User


class Platform(StrEnum):
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"

    @property
    def name(self) -> str:
        return self.value.capitalize()

    @property
    def authKey(self) -> str:
        """
        <useful doc-string>
        """
        return f"{self.value}Auth"

    @property
    def defaultConfigPath(self) -> str:
        from constants import DEFAULT_PATH

        return f"{DEFAULT_PATH}/_{self}.json"

    @property
    def successfulAuthText(self) -> str:
        return f"Successfully authorized {self.name}!"

    def isAuthorized(self, user: User) -> bool:
        """Boolean that determines whether user authorized the platform"""
        if getattr(user, self.authKey):
            return True
        return False

    def authButtonText(self, user: User) -> str:
        """
        <useful doc-string>
        """
        # User already authorized this platform.
        if self.isAuthorized(user):
            return f"✅ Authorized {self.name}"

        return f"Authorize {self.name}"

    def getAuthButtonParams(self, user: User, update: Update) -> dict:
        if self.isAuthorized(user):
            return {
                "text": f"✅ Authorized {self.name}",
                "callback_data": f"auth_{self}",
            }

        authUrl = self.getAuthUrlMethod()
        return {
            "text": f"Authorize {self.name}",
            "url": authUrl(user=user, update=update),
        }

    def getGeneratePlaylistButton(self, user: User) -> InlineKeyboardButton:
        """
        <useful doc-string>
        """
        buttonPrefix = "✅ " if self.isAuthorized(user) else ""
        buttonText = f"{buttonPrefix}Publish on {self.name}"

        callbackData = f"generate_playlist_{self.value}"
        return InlineKeyboardButton(text=buttonText, callback_data=callbackData)

    def authCommandMessageText(self, user: User) -> str:
        """
        <useful doc-string>
        """
        # User already authorized this platform.
        if self.isAuthorized(user):
            return f"You've already authorized {self.name}! If you want to re-auth, click the button below: "

        return f"Click the button below to authorize {self.name}:"

    def getAuthUrlMethod(self) -> Callable:
        # <useful doc-string>
        match self:
            case Platform.SPOTIFY:
                return getSpotifyAuthUrl
            case Platform.YOUTUBE:
                return getYoutubeAuthUrl

    # I think it's a bit too much to have an extra method for params. not 100% sure though.
    # def getCreatePlaylistParams(self) -> dict:
    #     """Docstring for getCreatePlaylistParams"""
    #     match self:
    #         case Platform.SPOTIFY:
    #             return {"shuffle": True, "includeOriginals": True}
    #         case Platform.YOUTUBE:
    #             return {"shuffle": True, "includeOriginals": True, "standaloneRecommendations": True}

    async def createPlaylist(
        self, playlistGenerator: PlaylistGenerator, lastN: int
    ) -> str:
        """
        <useful doc-string>
        """
        match self:
            case Platform.SPOTIFY:
                return playlistGenerator.createSpotifyPlaylist(lastN=lastN)
            case Platform.YOUTUBE:
                return playlistGenerator.createYoutubePlaylist(lastN=lastN)


def getSpotifyAuthUrl(update: Update, user: User) -> str:
    """Docstring for getSpotifyAuthUrl"""
    from constants import SPOTIFY_SCOPES

    cache = CacheFileHandler(cache_path=Platform.SPOTIFY.defaultConfigPath)
    if user.spotifyAuth:
        cache = MemoryCacheHandler(
            token_info={**user.spotifyAuth, "scope": " ".join(SPOTIFY_SCOPES)}
        )

    spotifyAuth = SpotifyOAuth(
        open_browser=False,
        scope=SPOTIFY_SCOPES,
        cache_handler=cache,
    )
    spotifyUrl = spotifyAuth.get_authorize_url()
    return f"{spotifyUrl}&state={update.effective_chat.id}"


def getYoutubeAuthUrl(update: Update, *args, **kwargs) -> str:
    """Docstring for getSpotifyAuthUrl"""
    client_id = os.environ["YOUTUBE_CLIENT_ID"]
    redirect_uri = os.environ["YOUTUBE_REDIRECT_URI"]
    authUrl = f"https://accounts.google.com/o/oauth2/auth?prompt=consent&access_type=offline&response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope=https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.readonly"

    return f"{authUrl}&state={update.effective_chat.id}_youtube"
