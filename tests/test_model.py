import json
from datetime import datetime

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from playlist import constants
from playlist.model.Track import Track
from playlist.model.Config import Config
from playlist.model.Platform import Platform, getSpotifyAuthUrl, getYoutubeAuthUrl
from playlist.model.User import User


# TODO:
#  - add 'unhappy path' coverage
#  - move below dicts to fixtures.
# Mock data for testing
rawSpotifyTrack = {
    "id": "spotify_track_id",
    "name": "Spotify Track",
    "artists": [{"id": "spotify_artist_id", "name": "Spotify Artist"}],
    "album": {"images": [{"height": 100, "width": 100, "url": "image.url"}]},
    "duration_ms": 300000,  # 5 minutes
}

rawYoutubeTrack = {
    "videoId": "TNPmfBrmlxc",
    "title": "Big Big Sesh - Seshlehem",
    "artists": [{"name": "Seshlehem", "id": "UCGE1DCR_xJO5y72HWakqnbA"}],
    "album": None,
    "likeStatus": "INDIFFERENT",
    "inLibrary": None,
    "thumbnails": [
        {
            "url": "https://i.ytimg.com/vi/TNPmfBrmlxc/sddefault.jpg?sqp=-oaymwEWCJADEOEBIAQqCghqEJQEGHgg6AJIWg&rs=AMzJL3kwV8omBUowoxPCapdQgV5NaXUg7w",
            "width": 400,
            "height": 225,
        }
    ],
    "isAvailable": True,
    "isExplicit": False,
    "videoType": "MUSIC_VIDEO_TYPE_UGC",
    "duration": "3:02",
    "duration_seconds": 182,
    "setVideoId": "74CEF74FBE23B0C5",
}

rawConfig = {
    "mainYoutubePlaylist": "main_youtube_playlist_id",
    "tmpYoutubePlaylist": "tmp_youtube_playlist_id",
    "tmpSpotifyPlaylist": "tmp_spotify_playlist_id",
    "spotifyUserId": "spotify_user_id",
    "youtubeUserId": "youtube_user_id",
    "spotifyClientId": "spotify_client_id",
    "spotifyClientSecret": "spotify_client_secret",
    "lastFMClientId": "lastfm_client_id",
    "lastFMClientSecret": "lastfm_client_secret",
    "youtubeAuthJson": "path/to/youtube_auth.json",
    "redirectUrl": "my.redirect",
}


def test_spotifyTrackParsing() -> None:
    """Test for parsing raw Spotify track"""
    spotifyTrack = Track(
        **rawSpotifyTrack,
        image=rawSpotifyTrack["album"].get("images", []),
        youtubeArtistId=None,
    )

    assert spotifyTrack.spotifyId == "spotify_track_id"
    assert spotifyTrack.title == "Spotify Track"
    assert spotifyTrack.artists == ["Spotify Artist"]
    assert spotifyTrack.artistName == "Spotify Artist"
    assert spotifyTrack.firstArtistName == "Spotify Artist"
    assert spotifyTrack.duration == 300  # seconds
    assert spotifyTrack.image == "image.url"

    assert not spotifyTrack.youtubeId
    assert not spotifyTrack.youtubeArtistId


def test_youtubeTrackParsing() -> None:
    """Test for parsing raw YouTube track"""
    youtubeTrack = Track(
        **rawYoutubeTrack,
        image=rawYoutubeTrack.get("thumbnails", [])
        or rawYoutubeTrack.get("thumbnail", []),
        spotifyArtistId=None,
    )

    assert youtubeTrack.youtubeId == "TNPmfBrmlxc"
    assert youtubeTrack.title == "Big Big Sesh - Seshlehem"
    assert youtubeTrack.artists == ["Seshlehem"]
    assert youtubeTrack.artistName == "Seshlehem"
    assert youtubeTrack.firstArtistName == "Seshlehem"
    assert youtubeTrack.youtubeArtistId == ["UCGE1DCR_xJO5y72HWakqnbA"]
    assert youtubeTrack.duration == 182  # seconds
    assert (
        youtubeTrack.image
        == "https://i.ytimg.com/vi/TNPmfBrmlxc/sddefault.jpg?sqp=-oaymwEWCJADEOEBIAQqCghqEJQEGHgg6AJIWg&rs=AMzJL3kwV8omBUowoxPCapdQgV5NaXUg7w"
    )

    assert not youtubeTrack.spotifyId
    assert not youtubeTrack.spotifyArtistId


def test_youtubeTrackDumping() -> None:
    """Test for parsing raw YouTube track, then dumping it and validating that fields are still there."""
    youtubeTrack = Track(**rawYoutubeTrack)

    dumpedTrack: dict = youtubeTrack.model_dump()

    assert dumpedTrack["artistName"] == "Seshlehem"
    assert dumpedTrack["firstArtistName"] == "Seshlehem"


def test_trackTitleFormatting() -> None:
    """TODO: Test to make sure that if the artist name is in the title - it'll be excluded & nicely formatted."""
    rawTrackWithArtistInTitle = {
        "title": "Artist - Track",
        "artists": [{"name": "Artist"}],
    }

    track = Track(**rawTrackWithArtistInTitle)

    # FIXME:
    # assert track.formatted_title == "Track"
    assert track.artists == ["Artist"]


def test_configParsing() -> None:
    """Test for parsing config JSON"""
    config = Config(**rawConfig, loadFromDisk=False)

    assert config.mainYoutubePlaylist == "main_youtube_playlist_id"
    assert config.tmpYoutubePlaylist == "tmp_youtube_playlist_id"
    assert config.tmpSpotifyPlaylist == "tmp_spotify_playlist_id"
    assert config.spotifyUserId == "spotify_user_id"
    assert config.youtubeUserId == "youtube_user_id"
    assert config.spotifyClientId == "spotify_client_id"
    assert config.spotifyClientSecret == "spotify_client_secret"
    assert config.lastFMClientId == "lastfm_client_id"
    assert config.lastFMClientSecret == "lastfm_client_secret"
    assert config.youtubeAuthJson == "path/to/youtube_auth.json"
    assert config.redirectUrl == "my.redirect"


def test_configStoring(tmp_path: Path) -> None:
    """Test for storing config JSON"""
    configData = {"mainYoutubePlaylist": "main_youtube_playlist_id"}
    config = Config(**configData, loadFromDisk=False)

    # Use a temporary file for testing
    configFileName = "test_config.json"
    config.store(filePath=str(tmp_path), fileName=configFileName)

    # Read the stored config file
    with open(f"{tmp_path}/{configFileName}", "r") as f:
        storedConfigData = json.load(f)

    assert storedConfigData["mainYoutubePlaylist"] == configData["mainYoutubePlaylist"]
    del storedConfigData["mainYoutubePlaylist"]

    # All other 9 keys are `None`
    assert not any(storedConfigData.values())
    assert len(storedConfigData.values()) == 10


def test_authKey():
    """Test for authKey property"""
    assert Platform.SPOTIFY.authKey == "spotifyAuth"
    assert Platform.YOUTUBE.authKey == "youtubeAuth"


def test_defaultConfigPath():
    """Test for defaultConfigPath property"""
    with patch.object(constants, "DEFAULT_PATH", "path/to/config"):
        assert Platform.SPOTIFY.defaultConfigPath == "path/to/config/_spotify.json"
        assert Platform.YOUTUBE.defaultConfigPath == "path/to/config/_youtube.json"


def test_successfulAuthText():
    """Test for successfulAuthText property"""
    assert Platform.SPOTIFY.successfulAuthText == "Successfully authorized Spotify!"
    assert Platform.YOUTUBE.successfulAuthText == "Successfully authorized Youtube!"


def test_isAuthorized():
    """Test for isAuthorized method"""
    userMock = Mock()
    userMock.spotifyAuth = True
    assert Platform.SPOTIFY.isAuthorized(userMock)

    userMock.spotifyAuth = False
    assert not Platform.SPOTIFY.isAuthorized(userMock)


def test_authButtonText():
    """Test for authButtonText method"""
    userMock = Mock()
    userMock.spotifyAuth = True
    assert Platform.SPOTIFY.authButtonText(userMock) == "✅ Authorized Spotify"

    userMock.spotifyAuth = False
    assert Platform.SPOTIFY.authButtonText(userMock) == "Authorize Spotify"


@patch("playlist.model.Platform.getSpotifyAuthUrl")
def test_getAuthButtonParams(mock_get_spotify_auth_url):
    """Test for getAuthButtonParams method"""
    userMock = Mock()
    update_mock = Mock()
    userMock.spotifyAuth = True
    expected_params = {"text": "✅ Authorized Spotify", "callback_data": "auth_spotify"}
    assert (
        Platform.SPOTIFY.getAuthButtonParams(userMock, update_mock) == expected_params
    )

    userMock.spotifyAuth = False
    mock_get_spotify_auth_url.return_value = "auth_url"
    expected_params = {"text": "Authorize Spotify", "url": "auth_url"}
    assert (
        Platform.SPOTIFY.getAuthButtonParams(userMock, update_mock) == expected_params
    )


def test_getGeneratePlaylistButton():
    """Test for getGeneratePlaylistButton method"""
    userMock = Mock()
    userMock.spotifyAuth = True
    button = Platform.SPOTIFY.getGeneratePlaylistButton(userMock)
    assert button.text == "✅ Publish on Spotify"
    assert button.callback_data == "generate_playlist_spotify"

    userMock.spotifyAuth = False
    button = Platform.SPOTIFY.getGeneratePlaylistButton(userMock)
    assert button.text == "Publish on Spotify"
    assert button.callback_data == "generate_playlist_spotify"


# Test for authCommandMessageText method
def test_authCommandMessageText():
    userMock = Mock()
    userMock.spotifyAuth = True
    assert (
        Platform.SPOTIFY.authCommandMessageText(userMock)
        == "You've already authorized Spotify! If you want to re-auth, click the button below: "
    )

    userMock.spotifyAuth = False
    assert (
        Platform.SPOTIFY.authCommandMessageText(userMock)
        == "Click the button below to authorize Spotify:"
    )


def test_getAuthUrlMethod():
    """Test for getAuthUrlMethod method"""
    assert Platform.SPOTIFY.getAuthUrlMethod() == getSpotifyAuthUrl
    assert Platform.YOUTUBE.getAuthUrlMethod() == getYoutubeAuthUrl


@pytest.mark.asyncio
async def test_createPlaylist():
    """Test for createPlaylist method"""
    playlistGenerator = Mock()
    playlistGenerator.createSpotifyPlaylist.return_value = "spotify_playlist_url"
    playlistGenerator.createYoutubePlaylist.return_value = "youtube_playlist_url"

    result = await Platform.SPOTIFY.createPlaylist(playlistGenerator, 10)
    assert result == "spotify_playlist_url"
    playlistGenerator.createSpotifyPlaylist.assert_called_once_with(lastN=10)


def test_UserDefaultFieldValues():
    """
    Test that default values for User fields are correctly set.
    """
    user = User()
    assert user.userId is None
    assert user.userName is None
    assert user.messages == 0
    assert not user.inProgress
    assert user.spotifyAuth is None
    assert user.youtubeAuth is None
    assert isinstance(user.created, datetime)
    assert isinstance(user.updated, datetime)


def test_UserFieldAliases():
    """
    Test that field aliases are correctly mapped in the User model.
    """
    userData = {
        "userId": "test_id",
        "username": "test_name",
        "messages": 5,
        "inProgress": True,
        "_created": datetime(2020, 1, 1),
        "_updated": datetime(2020, 1, 2),
    }
    user = User(**userData)
    assert user.userId == "test_id"
    assert user.userName == "test_name"
    assert user.messages == 5
    assert user.inProgress
    assert user.created == datetime(2020, 1, 1)
    assert user.updated == datetime(2020, 1, 2)


def test_UserFromDict():
    """
    Test that the from_dict class method correctly creates a User instance from a dictionary.
    """
    userData = {
        "userId": "user123",
        "username": "user_name",
        "messages": 10,
        "inProgress": False,
    }
    user = User.from_dict(userData)
    assert user.userId == "user123"
    assert user.userName == "user_name"
    assert user.messages == 10
    assert not user.inProgress
