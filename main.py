import logging
import random
import pylast
import requests
from more_itertools import chunked

# Integrations
import spotipy
from spotipy import CacheFileHandler
from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

# Models
from model.Config import Config
from model.Track import Track

# Constants
from constants import SPOTIFY_SCOPES, MAX_SPOTIFY_PLAYLIST_CHUNK_SIZE, MAX_SPOTIFY_RECOMMENDATION_CHUNK_SIZE, lastFMUrl

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger: logging.Logger = logging.getLogger()


class PlaylistGenerator:
    """
    Generates playlist based on your last X tracks.
    Also adds suggestions.
    """

    def __init__(self) -> None:
        # Init config.
        self.config: Config = Config(loadFromDisk=True)

        # Init youtube.
        self.youtube: YTMusic = YTMusic(self.config.youtubeAuthJson)

        # Init spotify.
        spotifyCredentials = SpotifyClientCredentials(client_id=self.config.spotifyClientId,
                                                      client_secret=self.config.spotifyClientSecret)

        self.spotify = spotipy.Spotify(client_credentials_manager=spotifyCredentials,
                                       auth_manager=SpotifyOAuth(
                                           open_browser=False,
                                           client_id=self.config.spotifyClientId,
                                           client_secret=self.config.spotifyClientSecret,
                                           redirect_uri=self.config.redirectUrl,
                                           scope=SPOTIFY_SCOPES,
                                           cache_handler=CacheFileHandler(cache_path=".spotify_cache"))
                                       )

        # Init lastFM
        self.lastfm = pylast.LastFMNetwork(api_key=self.config.lastFMClientId, api_secret=self.config.lastFMClientSecret)

    def getLastYoutubeTracks(self, lastN: int = 10) -> list[Track]:
        """
        Retrieves the last N tracks from the main YouTube playlist.
        """
        logger.info(f"Executing `getLastYoutubeTracks()`, fetching last {lastN} tracks")

        # If the main YouTube playlist is not set in the configuration fetch it directly from YouTube.
        if not self.config.mainYoutubePlaylist:
            # Get all playlists & sort playlists by tracks count.
            allPlaylists: list[dict] = sorted(self.youtube.get_library_playlists(),
                                              key=lambda x: x.get("count", 0), reverse=True)

            # Assume that biggest playlist is the main one.
            self.config.mainYoutubePlaylist = allPlaylists[0]["playlistId"]
            self.config.store()

        mainPlaylist: dict = self.youtube.get_playlist(playlistId=self.config.mainYoutubePlaylist)

        # Override spotifyArtistId, since it's youtube-only tracks.
        tracks: list[Track] = [Track(**rawTrack, spotifyArtistId=None) for rawTrack in mainPlaylist.get("tracks", [])[:lastN]]

        return tracks

    def getLastSpotifyTracks(self, lastN: int = 10) -> list[Track]:
        """
        Retrieves the last N tracks from the main Spotify playlist.
        """
        logger.info(f"Executing `getLastSpotifyTracks()`, fetching last {lastN} tracks")

        rawTracks = self.spotify.current_user_saved_tracks(limit=lastN)

        # Override youtubeArtistId, since it's spotify-only tracks.
        tracks: list[Track] = [Track(**rawTrack["track"], youtubeArtistId=None) for rawTrack in rawTracks.get("items", [])[:lastN]]

        return tracks

    def fillSpotifyId(self, tracks: list[Track]):
        """Fills `.spotifyId` property on each track"""
        logger.info(f"Executing `fillSpotifyId()` for {len(tracks)} tracks")
        for track in tracks:

            if not (spotifyMatch := self.searchTrackOnSpotify(track)):
                logger.warning(f"{track.title} / {track.artistName} were not found on Spotify")
                continue

            track.spotifyId = spotifyMatch["id"]
            track.spotifyArtistId = [x.get("id") for x in spotifyMatch["artists"]]

    def fillYoutubeId(self, tracks: list[Track]):
        """Fills `.youtubeId` property on each track"""
        logger.info(f"Executing `fillYoutubeId()` for {len(tracks)} tracks")
        for track in tracks:

            if not (youtubeMatch := self.searchTrackOnYoutube(track)):
                logger.warning(f"{track.title} / {track.artistName} were not found on Youtube")
                continue

            track.youtubeId = youtubeMatch.youtubeId
            track.youtubeArtistId = youtubeMatch.youtubeArtistId

    def searchTrackOnSpotify(self, track: Track) -> dict | None:
        """
        Searches for a track on Spotify based on the provided Track object.
        """
        # if/else to handle the case when artist name is already in track name.
        searchQuery = f"{track.title}" if track.artistName in track.title else f"{track.artistName} {track.title}"

        # Fetch results from spotify.
        searchResults = self.spotify.search(q=searchQuery, limit=5).get("tracks", {"item": []}).get("items", [])

        nonExplicitMatch: dict | None = None
        for searchResult in searchResults:

            searchResultDuration: int = round(searchResult.get("duration_ms", 1) / 1000)
            isExplicit: bool = searchResult.get('explicit', False) is True

            # LastFM is so bad it won't even return durations._.
            if not track.duration:
                return searchResult

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
        # TODO: add validator into the model to handle this case there upon init of `Track()`.
        # if/else to handle the case when artist name is already in track name.
        searchQuery = f"{track.title}" if track.artistName in track.title else f"{track.artistName} {track.title}"

        # Fetch results from spotify.
        searchResults: list[Track] = [Track(**searchResult, spotifyArtistId=None) for searchResult in
                                      self.youtube.search(query=searchQuery, filter="songs", limit=5)[:5]]

        for searchResult in searchResults:

            # LastFM is so bad it won't even return durations._.
            if not track.duration:
                return searchResult

            searchResultDuration: int = searchResult.duration
            # If its duration is in range ±5sec - should be the same track.
            if searchResultDuration in range(track.duration - 5, track.duration + 5):
                return searchResult

    def getYoutubeRecommendations(self, tracks: list[Track], limit: int = 5) -> list[Track]:
        """
        Retrieves Youtube recommendations based on a list of input tracks.

        In result, you'll get this many tracks:
        <...>
        """
        logger.info(f"Executing `getYoutubeRecommendations()` with {len(tracks)} tracks")
        youtubeTracksIds: list[str] = [track.youtubeId for track in tracks if track.youtubeId]
        recommendedTracks: list[Track] = []

        # need to do stuff with this method. pass there `videoId` of each track.
        for trackId in youtubeTracksIds:
            result: dict = self.youtube.get_watch_playlist(videoId=trackId)

            recommendationsPerTrack: int = 0
            for rawTrack in result.get("tracks", [])[1: limit + 1]:

                if recommendationsPerTrack >= limit:
                    break

                # Override spotifyArtistId, since it's youtube-only recommendations.
                recommendedTrack = Track(**rawTrack, spotifyArtistId=None)

                if recommendedTrack.youtubeId not in [x.youtubeId for x in recommendedTracks]:
                    recommendedTracks.append(recommendedTrack)
                    recommendationsPerTrack += 1

        return recommendedTracks

    def getSpotifyRecommendations(self,
                                  tracks: list[Track],
                                  recommendationChunkSize: int = MAX_SPOTIFY_RECOMMENDATION_CHUNK_SIZE,
                                  limit: int = 5) -> list[Track]:
        """
        Retrieves Spotify recommendations based on a list of input tracks.

        In result, you'll get this many tracks:
        ( len(tracks) / recommendationChunkSize ) * 5
        """
        logger.info(f"Executing `getSpotifyRecommendations()` with {len(tracks)} tracks")
        spotifyTracksIds: list[str] = [track.spotifyId for track in tracks if track.spotifyId]
        recommendedTracks: list[Track] = []

        # Default max chunk-size is 5 tracks(i.e. you can't ask for recommendation based on more than 5tracks).
        for tracksChunk in chunked(spotifyTracksIds, recommendationChunkSize):

            # Limit result of recommendations also to 5. It helps to reduce junk recommendations from spotify.
            result = self.spotify.recommendations(seed_tracks=tracksChunk, limit=limit)

            for rawTrack in result.get("tracks", []):

                # Override youtubeArtistId, since it's spotify-only recommendations.
                recommendedTrack = Track(**rawTrack, youtubeArtistId=None)

                recommendedTracks.append(recommendedTrack)

        return recommendedTracks

    def getLastFMRecommendationsV2(self, tracks: list[Track]) -> list[Track]:
        """
        Retrieves LastFM recommendations based on a list of input tracks.
        There's up to two recommendations per 1 input track.

        TODO: evaluate whether using `pylast` is any better - `duration` cannot be fetched either, so doing raw request
        might be a dirty overkill.
        """
        # somehow i think it won't work out well.
        pass

    def getLastFMRecommendations(self,
                                 tracks: list[Track],
                                 sameArtistMargin: int = 1,
                                 sameTrackMargin: int = 2) -> list[Track]:
        """
        Retrieves LastFM recommendations based on a list of input tracks.
        There's up to two recommendations per 1 input track.

        In result you'll get ±this many tracks:
        ± len(tracks) * 2

        TODO:  make sure no duplicates are returned.
        """
        logger.info(f"Executing `getLastFMRecommendations()` with {len(tracks)} tracks")
        recommendedTracks: list[Track] = []

        for track in tracks:

            url: str = lastFMUrl.format(artist=track.firstArtistName,
                                        title=track.title,
                                        apiKey=self.config.lastFMClientId)
            try:
                result: dict = requests.get(url).json()
                if "error" in result:
                    logger.error(f"{track.title} / {track.firstArtistName} was failed to find on LastFM: {result}")
                    continue
            except requests.exceptions.JSONDecodeError as err:
                logger.error(f"{track.title} / {track.firstArtistName} was failed to find on LastFM: {err}")
                continue

            sameArtistCounter: int = 0
            sameTrackCounter: int = 0
            for rawTrack in result.get("similartracks", {}).get("track", []):

                # Break the loop if already got enough of same track.
                if sameTrackCounter > sameTrackMargin:
                    break

                sameTrackCounter += 1
                # Override youtube & spotify artistIds, since it's lastfm-only recommendations.
                # Also override duration, since lastFM duration is unreliable.
                recommendedTrack = Track(**rawTrack, youtubeArtistId=None, spotifyArtistId=None, zeroDuration=True)

                # LastFM recommendations suck, thus we allow:
                # - Same artist only once.
                if recommendedTrack.firstArtistName == track.firstArtistName:

                    sameArtistCounter += 1
                    if sameArtistCounter > sameArtistMargin:
                        continue

                recommendedTracks.append(recommendedTrack)

        return recommendedTracks

    def geSoundCloudRecommendations(self, tracks: list[Track]) -> list[Track]:
        """
        TODO: evaluate whether it's even possible.
        """
        pass

    def createSpotifyPlaylist(self,
                              lastN: int = 10,
                              shuffle: bool = False,
                              includeOriginals: bool = False) -> None:
        """
        <useful doc-string>
        """

        # Get last tracks from YouTube & fulfill them with `.spotifyId`
        lasSpotifyTracks: list[Track] = self.getLastSpotifyTracks(lastN=lastN)
        self.fillYoutubeId(tracks=lasSpotifyTracks)

        # Get youtube recommendations based on `lastYoutubeTracks`.
        recommendedTracks: list[Track] = self.getYoutubeRecommendations(lasSpotifyTracks)

        # Get lastFM recommendations based on Spotify tracks.
        recommendedTracks += self.getLastFMRecommendations(tracks=recommendedTracks)
        #
        # Fulfill all recommendations with `.youtubeId`.
        self.fillSpotifyId(tracks=recommendedTracks)

        # Prepare a list of spotify tracks. Include original tracks if needed.
        if includeOriginals:
            recommendedTracks += lasSpotifyTracks

        spotifyTracks: list[str] = [f"https://open.spotify.com/track/{x.spotifyId}" for x in recommendedTracks]

        # Shuffle tracks if needed.
        if shuffle:
            random.shuffle(spotifyTracks)

        # Create playlist with last tracks + recommendations on YouTube.
        logger.info(f"Creating playlist with {len(spotifyTracks)} tracks")

        # First create a playlist
        if not self.config.spotifyUserId:
            self.config.spotifyUserId = self.spotify.current_user()["id"]
        playlist: dict = self.spotify.user_playlist_create(user=self.config.spotifyUserId,
                                                           name="6th December testV2",
                                                           description="my test")
        # Then fill it with tracks, 100tracks at a time.
        for tracksChunk in chunked(spotifyTracks, MAX_SPOTIFY_PLAYLIST_CHUNK_SIZE):
            self.spotify.playlist_add_items(playlist_id=playlist["id"], items=tracksChunk)

    def createYoutubePlaylist(self,
                              lastN: int = 10,
                              shuffle: bool = False,
                              includeOriginals: bool = False,
                              standaloneRecommendations: bool = False) -> None:
        """
        <useful doc-string>
        """
        # Get last tracks from YouTube & fulfill them with `.spotifyId`
        lastYoutubeTracks: list[Track] = self.getLastYoutubeTracks(lastN=lastN)
        self.fillSpotifyId(tracks=lastYoutubeTracks)

        # Get spotify recommendations based on `lastYoutubeTracks`.
        getSpotifyRecommendationsParams: dict = {"tracks": lastYoutubeTracks}
        if standaloneRecommendations:
            getSpotifyRecommendationsParams["recommendationChunkSize"] = 1
        recommendedTracks: list[Track] = self.getSpotifyRecommendations(**getSpotifyRecommendationsParams)

        # Get lastFM recommendations based on Spotify tracks.
        recommendedTracks += self.getLastFMRecommendations(tracks=recommendedTracks)

        # Fulfill all recommendations with `.youtubeId`.
        self.fillYoutubeId(tracks=recommendedTracks)
        # Prepare a list of youtube track ids.
        youtubeTracks: list[str] = [x.youtubeId for x in recommendedTracks if x.youtubeId]

        # Include original tracks if needed.
        if includeOriginals:
            youtubeTracks += [x.youtubeId for x in lastYoutubeTracks if x.youtubeId]
        # Shuffle tracks if needed.
        if shuffle:
            random.shuffle(youtubeTracks)

        # Create playlist with last tracks + recommendations on YouTube.
        logger.info(f"Creating playlist with {len(youtubeTracks)} tracks")
        self.youtube.create_playlist(title="6th December testV2",
                                     description="my test",
                                     video_ids=youtubeTracks)

    def testingCoverageReport(self):
        """Docstring for testingCoverageReport"""
        # For the sake of testing
        pass


if __name__ == "__main__":
    generator = PlaylistGenerator()
    # generator.createYoutubePlaylist()
    # generator.createYoutubePlaylist(lastN=10,
    #                                 shuffle=True,
    #                                 includeOriginals=True,
    #                                 standaloneRecommendations=True)
    generator.createSpotifyPlaylist(lastN=10,
                                    shuffle=True,
                                    includeOriginals=True)
