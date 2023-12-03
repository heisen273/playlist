import spotipy
from more_itertools import chunked
from spotipy.oauth2 import SpotifyClientCredentials
from ytmusicapi import YTMusic
from ytmusicapi.model.Track import Track
import logging

DEFAULT_PATH = "/Users/anton/projects/playlist"
MAX_SPOTIFY_CHUNK_SIZE: int = 5

logger = logging.getLogger()


class PlaylistGenerator:
    """
    Generates playlist based on your last X tracks.
    Also adds suggestions.
    """

    def __init__(self) -> None:
        self.youtube: YTMusic = YTMusic(f"{DEFAULT_PATH}/.oauth.json")

        # TODO: Store spotify secrets in file.
        self.spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id="",
                                                                                           client_secret=""))

    def getLastYoutubeTracks(self, lastN: int = 10) -> list[Track]:
        """
        <useful doc-string>
        """
        if not self.youtube.config.mainYoutubePlaylist:
            allPlaylists: list[dict] = self.youtube.get_library_playlists()

            # Assume that biggest playlist is the main one
            self.youtube.config.mainYoutubePlaylist = allPlaylists[0]["playlistId"]
            self.youtube.config._store()

        mainPlaylist: dict = self.youtube.get_playlist(playlistId=self.youtube.config.mainYoutubePlaylist)

        # Override spotifyArtistId, since it's youtube-only tracks.
        tracks: list[Track] = [Track(**rawTrack, spotifyArtistId=None) for rawTrack in mainPlaylist.get("tracks", [])[:lastN]]

        return tracks

    def fillSpotifyId(self, tracks: list[Track]):
        """Fills `.spotifyId` property on each track"""

        for track in tracks:

            if not (spotifyMatch := self.searchTrackOnSpotify(track)):
                logger.warning(f"{track.title} / {track.artist} were not found on Spotify")
                continue

            track.spotifyId = spotifyMatch["id"]
            track.spotifyArtistId = [x.get("id") for x in spotifyMatch["artists"]]

    def fillYoutubeId(self, tracks: list[Track]):
        """Fills `.youtubeId` property on each track"""

        for track in tracks:

            if not (youtubeMatch := self.searchTrackOnYoutube(track)):
                logger.warning(f"{track.title} / {track.artist} were not found on Youtube")
                continue

            track.youtubeId = youtubeMatch.youtubeId
            track.youtubeArtistId = youtubeMatch.youtubeArtistId

    def searchTrackOnSpotify(self, track: Track) -> dict | None:
        """
        Searches for a track on Spotify based on the provided Track object.
        """
        # if/else to handle the case when artist name is already in track name.
        searchQuery = f"{track.title}" if track.artist in track.title else f"{track.artist} {track.title}"

        # Fetch results from spotify.
        searchResults = self.spotify.search(q=searchQuery, limit=5).get("tracks", {"item": []}).get("items", [])

        nonExplicitMatch: dict | None = None
        for searchResult in searchResults:

            searchResultDuration: int = round(searchResult.get("duration_ms", 1) / 1000)
            isExplicit: bool = searchResult.get('explicit', False) is True

            # If its duration is in range ±5sec - should be the same track.
            if searchResultDuration in range(track.duration - 5, track.duration + 5):

                # Return right away if it's explicit match.
                if isExplicit:
                    return searchResult
                # Otherwise search a bit more and fallback to non-explicit match.
                else:
                    nonExplicitMatch = searchResult

        return nonExplicitMatch

    def searchTrackOnYoutube(self, track: Track) -> Track | None:
        """
        Searches for a track on YouTube based on the provided Track object.
        """
        # if/else to handle the case when artist name is already in track name.
        searchQuery = f"{track.title}" if track.artist in track.title else f"{track.artist} {track.title}"

        # Fetch results from spotify.
        searchResults: list[Track] = [Track(**searchResult, spotifyArtistId=None) for searchResult in self.youtube.search(query=searchQuery, filter="songs", limit=5)[:5]]

        for searchResult in searchResults:

            searchResultDuration: int = searchResult.duration

            # If its duration is in range ±5sec - should be the same track.
            if searchResultDuration in range(track.duration - 5, track.duration + 5):
                return searchResult

    def getSpotifyRecommendations(self, tracks: list[Track]) -> list[Track]:
        """
        Retrieves Spotify recommendations based on a list of input tracks.
        """

        spotifyTracksIds: list[str] = [track.spotifyId for track in tracks if track.spotifyId]
        recommendedTracks: list[Track] = []

        # Default max chunk-size is 5 tracks(i.e. you can't ask for recommendation based on more than 5tracks).
        for tracksChunk in chunked(spotifyTracksIds, MAX_SPOTIFY_CHUNK_SIZE):

            # Limit result of recommendations also to 5. It helps to reduce junk recommendations from spotify.
            result = self.spotify.recommendations(seed_tracks=tracksChunk, limit=MAX_SPOTIFY_CHUNK_SIZE)

            for rawTrack in result.get("tracks", []):

                # Override youtubeArtistId, since it's spotify-only recommendations.
                recommendedTrack = Track(**rawTrack, youtubeArtistId=None)

                recommendedTracks.append(recommendedTrack)

        return recommendedTracks

    def createYoutubePlaylist(self) -> None:
        """
        <useful doc-string>
        """
        # Get last tracks from YouTube & fulfill them with `.spotifyId`
        lastYoutubeTracks: list[Track] = self.getLastYoutubeTracks()
        self.fillSpotifyId(tracks=lastYoutubeTracks)

        # Get spotify recommendations based on `lastYoutubeTracks` & fulfill them with `.youtubeId`.
        recommendedTracks: list[Track] = self.getSpotifyRecommendations(tracks=lastYoutubeTracks)
        self.fillYoutubeId(tracks=recommendedTracks)

        # Create playlist with last tracks + recommendations on YouTube.
        self.youtube.create_playlist(title="3rd December test",
                                     description="my test",
                                     video_ids=[x.youtubeId for x in recommendedTracks if x.youtubeId])


if __name__ == "__main__":
    generator = PlaylistGenerator()
    generator.createYoutubePlaylist()
