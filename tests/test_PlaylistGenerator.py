import pytest

from playlist.core.generator import PlaylistGenerator
from playlist.model.Track import Track
from playlist.model.User import User, Auth

rawTracks: list[dict] = [
    {
        "title": "Runaway",
        "artists": ["Kanye West"],
        "duration": 548,
        "youtubeArtistId": ["UCRY5dYsbIN5TylSbd7gVnZg"],
        "youtubeId": "VhEoCOWUtcU",
        "spotifyId": "3DK6m7It6Pw857FcQftMds",
        "spotifyArtistId": ["5K4W6rqBFWDnAN6FQUkS6x", "0ONHkAv9pCAFxb0zJwDNTy"],
    }
]
generator = PlaylistGenerator()


def test_getLastYoutubeTracks():
    """
    Test that validates `getLastYoutubeTracks()` functionality & makes sure that it returns `lastN` tracks.
    """
    tracks: list[Track] = generator.getLastYoutubeTracks(lastN=10)
    assert tracks
    assert len(tracks) == 10
    track: Track = tracks[0]
    assert track.artists
    assert track.title
    assert track.duration
    assert track.youtubeId
    assert track.youtubeArtistId
    assert track.image

    # Spotify values were not filled, because it's youtube-oriented method.
    assert not track.spotifyId
    assert not track.spotifyArtistId


def test_fillSpotifyId():
    """
    Docstring for test_fillSpotifyId
    """
    # Prepare data.
    tracks: list[Track] = [Track(**x) for x in rawTracks]
    tracks[0].youtubeId = None
    tracks[0].youtubeArtistId = None
    tracks[0].spotifyId = None
    tracks[0].spotifyArtistId = None

    # Fill spotify ids.
    generator.fillSpotifyId(tracks)
    # Assert that spotify IDs were filled, youtube IDs remained empty.
    assert tracks[0].spotifyId
    assert tracks[0].spotifyArtistId
    assert not tracks[0].youtubeId
    assert not tracks[0].youtubeArtistId


def test_fillYoutubeId():
    """
    Docstring for test_fillSpotifyId
    """
    # Prepare data.
    tracks: list[Track] = [Track(**x) for x in rawTracks]
    tracks[0].youtubeId = None
    tracks[0].youtubeArtistId = None
    tracks[0].spotifyId = None
    tracks[0].spotifyArtistId = None

    # Fill spotify ids.
    generator.fillYoutubeId(tracks)
    # Assert that youtube IDs were filled, spotify IDs remained empty.
    assert tracks[0].youtubeId
    assert tracks[0].youtubeArtistId
    assert not tracks[0].spotifyId
    assert not tracks[0].spotifyArtistId


def test_spotifyRecommendations():
    """
    Docstring for test_spotifyRecommendations
    """
    tracks: list[Track] = [Track(**x) for x in rawTracks]
    tracks[0].youtubeId = None
    tracks[0].youtubeArtistId = None

    recommendations: list[Track] = generator.getSpotifyRecommendations(tracks)
    assert recommendations
    # Default spotify recommendation size is `5`.
    assert len(recommendations) == 5

    recommendedTrack: Track = recommendations[0]
    assert recommendedTrack.artists
    assert recommendedTrack.title
    assert recommendedTrack.spotifyId
    assert recommendedTrack.spotifyArtistId
    assert recommendedTrack.image

    assert not recommendedTrack.youtubeId
    assert not recommendedTrack.youtubeArtistId


def test_youtubeRecommendations() -> None:
    """
    Docstring for test_youtubeRecommendations
    """
    tracks: list[Track] = [Track(**x) for x in rawTracks]
    tracks[0].spotifyId = None
    tracks[0].spotifyArtistId = None

    recommendations: list[Track] = generator.getYoutubeRecommendations(tracks)
    assert recommendations
    # Default youtube recommendation size is `5`.
    assert len(recommendations) == 5

    recommendedTrack: Track = recommendations[0]
    assert recommendedTrack.artists
    assert recommendedTrack.title
    assert recommendedTrack.youtubeId
    assert recommendedTrack.youtubeArtistId
    assert recommendedTrack.image

    assert not recommendedTrack.spotifyId
    assert not recommendedTrack.spotifyArtistId


def test_getLastSpotifyTracks():
    """
    Test that validates `getLastSpotifyTracks()` functionality & makes sure that it returns `lastN` tracks.
    """
    tracks: list[Track] = generator.getLastSpotifyTracks()
    assert len(tracks) == 10
    track: Track = tracks[0]
    assert track.artists
    assert track.title
    assert track.duration
    assert track.spotifyId
    assert track.spotifyArtistId
    assert track.image

    # Youtube values were not filled, because it's spotify-oriented method.
    assert not track.youtubeId
    assert not track.youtubeArtistId


def test_lastFMRecommendations() -> None:
    """
    Docstring for test_spotifyRecommendations
    """
    tracks: list[Track] = [Track(**x) for x in rawTracks]
    tracks[0].youtubeId = None
    tracks[0].youtubeArtistId = None

    recommendations: list[Track] = generator.getLastFMRecommendations(tracks)
    assert len(recommendations) == 2
    uniqueRecommendedArtists: set[str] = {x.firstArtistName for x in recommendations}
    assert len(uniqueRecommendedArtists) == 2
    assert tracks[0].firstArtistName in uniqueRecommendedArtists

    recommendedTrack: Track = recommendations[0]
    assert recommendedTrack.artists
    assert recommendedTrack.title
    assert recommendedTrack.image

    assert not recommendedTrack.spotifyId
    assert not recommendedTrack.spotifyArtistId
    assert not recommendedTrack.youtubeId
    assert not recommendedTrack.youtubeArtistId


@pytest.mark.parametrize(
    "isDummy, expectedResult", [[True, False], [False, True], [None, False]]
)
def test__notDummyAuth(isDummy: bool, expectedResult: bool) -> None:
    """Docstring for test_dummyAUth"""
    user = User(**{"spotify": {"cool": "data", "1": 2, "3": 4, "isDummy": isDummy}})

    if isDummy is None:
        user.spotifyAuth = None

    assert generator._isNotDummy(auth=user.spotifyAuth) == expectedResult


def test_createYoutubePlaylist():
    """Docstring for test_createYoutubePlaylist"""
    pass


def test_createSpotifyPlaylist():
    """Docstring for test_createSpotifyPlaylist"""
    pass
