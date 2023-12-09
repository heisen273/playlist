import json
from pathlib import Path
from model.Track import Track
from model.Config import Config


# TODO:
#  - add 'unhappy path' coverage
#  - move below dicts to fixtures.
# Mock data for testing
rawSpotifyTrack = {
    "id": "spotify_track_id",
    "name": "Spotify Track",
    "artists": [{"id": "spotify_artist_id", "name": "Spotify Artist"}],
    "duration_ms": 300000  # 5 minutes
}

rawYoutubeTrack = {
    "videoId": "youtube_video_id",
    "title": "YouTube Track",
    "artists": [{"name": "YouTube Artist"}],
    "duration_seconds": 300  # 5 minutes
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
    spotifyTrack = Track(**rawSpotifyTrack)

    assert spotifyTrack.spotifyId == "spotify_track_id"
    assert spotifyTrack.title == "Spotify Track"
    assert spotifyTrack.artists == ["Spotify Artist"]
    assert spotifyTrack.duration == 300  # seconds


def test_youtubeTrackParsing() -> None:
    """Test for parsing raw YouTube track"""
    youtubeTrack = Track(**rawYoutubeTrack)

    assert youtubeTrack.youtubeId == "youtube_video_id"
    assert youtubeTrack.title == "YouTube Track"
    assert youtubeTrack.artists == ["YouTube Artist"]
    assert youtubeTrack.duration == 300  # seconds


def test_trackTitleFormatting() -> None:
    """TODO: Test to make sure that if the artist name is in the title - it'll be excluded & nicely formatted."""
    rawTrackWithArtistInTitle = {
        "title": "Artist - Track",
        "artists": [{"name": "Artist"}]
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
