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
    spotifyTrack = Track(**rawSpotifyTrack, youtubeArtistId=None)

    assert spotifyTrack.spotifyId == "spotify_track_id"
    assert spotifyTrack.title == "Spotify Track"
    assert spotifyTrack.artists == ["Spotify Artist"]
    assert spotifyTrack.artistName == "Spotify Artist"
    assert spotifyTrack.firstArtistName == "Spotify Artist"
    assert spotifyTrack.duration == 300  # seconds

    assert not spotifyTrack.youtubeId
    assert not spotifyTrack.youtubeArtistId


def test_youtubeTrackParsing() -> None:
    """Test for parsing raw YouTube track"""
    youtubeTrack = Track(**rawYoutubeTrack, spotifyArtistId=None)

    assert youtubeTrack.youtubeId == "TNPmfBrmlxc"
    assert youtubeTrack.title == "Big Big Sesh - Seshlehem"
    assert youtubeTrack.artists == ["Seshlehem"]
    assert youtubeTrack.artistName == "Seshlehem"
    assert youtubeTrack.firstArtistName == "Seshlehem"
    assert youtubeTrack.youtubeArtistId == ["UCGE1DCR_xJO5y72HWakqnbA"]
    assert youtubeTrack.duration == 182  # seconds

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
