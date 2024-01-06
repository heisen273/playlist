from __future__ import annotations

import os
import json
import logging
import random


import requests
from datetime import datetime
from more_itertools import chunked
from dotenv import load_dotenv

# Integrations
import spotipy
from spotipy import CacheFileHandler, MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic

# Models
try:
    from model.Track import Track
    from model.User import User
    from model.Platform import Platform
except ModuleNotFoundError:
    from model import Track, User, Platform

# Constants
from constants import (
    SPOTIFY_SCOPES,
    MAX_SPOTIFY_PLAYLIST_CHUNK_SIZE,
    MAX_SPOTIFY_RECOMMENDATION_CHUNK_SIZE,
    lastFMUrl,
    DEFAULT_TIMEOUT,
)


load_dotenv()
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s"
)
logger: logging.Logger = logging.getLogger()


class PlaylistGenerator:
    # TODO:
    #  - has to be splitted in different chunks. Maybe per platform ? Really not sure.
    #  Yet, for sure i need to split this class in smaller chunks, it's too big.
    #  - Currently there's 3 files generated: .oauth.json, .config.json, .spotify_cache – it's too many, i'm sure it's
    #  possible to narrow it down to a single file(.config.json). Need to figure this one out.
    """
    Generates playlist based on your last X tracks.
    Also adds suggestions.
    """

    def __init__(self, user: User | None = None) -> None:
        self.user = user or User()
        # Init youtube.
        if self.user.youtubeAuth:
            self.youtube: YTMusic = YTMusic(
                auth=json.dumps(user.youtubeAuth), useCustomOauth=True
            )
        else:
            self.youtube: YTMusic = YTMusic(
                auth=Platform.YOUTUBE.defaultConfigPath, useCustomOauth=False
            )

        # Init spotify.
        cache = CacheFileHandler(cache_path=Platform.SPOTIFY.defaultConfigPath)
        if self.user.spotifyAuth:
            cache = MemoryCacheHandler(
                token_info={**user.spotifyAuth, "scope": " ".join(SPOTIFY_SCOPES)}
            )

        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                open_browser=False,
                scope=SPOTIFY_SCOPES,
                cache_handler=cache,
            )
        )

    def getYoutubePlaylists(self) -> list[dict]:
        """Docstring for getYoutubePlaylists"""
        return sorted(
            self.youtube.get_library_playlists(),
            key=lambda x: int(x.get("count", "0").replace(",", "")),
            reverse=True,
        )

    def getLastYoutubeTracks(self, lastN: int = 10) -> list[Track]:
        """
        Retrieves the last N tracks from the main YouTube playlist.
        """
        logger.info(f"Executing `getLastYoutubeTracks()`, fetching last {lastN} tracks")

        # To find out main youtube playlist, get all playlists & sort playlists by tracks count.
        allPlaylists: list[dict] = self.getYoutubePlaylists()
        # Assume that biggest playlist is the main one.
        playlistId = allPlaylists[0]["playlistId"]
        mainPlaylist: dict = self.youtube.get_playlist(playlistId=playlistId)

        # Get `lastN` tracks from this playlist & override spotifyArtistId, since it's youtube-only tracks.
        tracks: list[Track] = [
            Track(**rawTrack, spotifyArtistId=None)
            for rawTrack in mainPlaylist.get("tracks", [])[:lastN]
        ]

        return tracks

    def getLastSpotifyTracks(self, lastN: int = 10) -> list[Track]:
        """
        Retrieves the last N tracks from the main Spotify playlist.
        """
        logger.info(f"Executing `getLastSpotifyTracks()`, fetching last {lastN} tracks")

        rawTracks = self.spotify.current_user_saved_tracks(limit=lastN)

        # Override youtubeArtistId, since it's spotify-only tracks.
        tracks: list[Track] = [
            Track(**rawTrack["track"], youtubeArtistId=None)
            for rawTrack in rawTracks.get("items", [])[:lastN]
        ]

        return tracks

    def fillSpotifyId(self, tracks: list[Track]):
        """Fills `.spotifyId` property on each track"""
        logger.info(f"Executing `fillSpotifyId()` for {len(tracks)} tracks")
        for track in tracks:
            if not (spotifyMatch := self.searchTrackOnSpotify(track)):
                logger.warning(
                    f"{track.title} / {track.artistName} were not found on Spotify"
                )
                continue

            track.spotifyId = spotifyMatch["id"]
            track.spotifyArtistId = [x.get("id") for x in spotifyMatch["artists"]]

    def fillYoutubeId(self, tracks: list[Track]):
        """Fills `.youtubeId` property on each track"""
        logger.info(f"Executing `fillYoutubeId()` for {len(tracks)} tracks")
        for track in tracks:
            if not (youtubeMatch := self.searchTrackOnYoutube(track)):
                logger.warning(
                    f"{track.title} / {track.artistName} were not found on Youtube"
                )
                continue

            track.youtubeId = youtubeMatch.youtubeId
            track.youtubeArtistId = youtubeMatch.youtubeArtistId

    def searchTrackOnSpotify(self, track: Track) -> dict | None:
        """
        Searches for a track on Spotify based on the provided Track object.
        """
        # if/else to handle the case when artist name is already in track name.
        searchQuery = (
            f"{track.title}"
            if track.artistName in track.title
            else f"{track.artistName} {track.title}"
        )

        # Fetch results from spotify.
        searchResults = (
            self.spotify.search(q=searchQuery, limit=5)
            .get("tracks", {"item": []})
            .get("items", [])
        )

        nonExplicitMatch: dict | None = None
        for searchResult in searchResults:
            searchResultDuration: int = round(searchResult.get("duration_ms", 1) / 1000)
            isExplicit: bool = searchResult.get("explicit", False) is True

            # LastFM is so bad it won't even return durations._.
            if not track.duration:
                return searchResult

            # If its duration is in range ±5sec - should be the same track.
            if searchResultDuration in range(track.duration - 5, track.duration + 5):
                # Return right away if it's explicit match.
                if isExplicit:
                    return searchResult

                # Otherwise search a bit more and fallback to non-explicit match.
                nonExplicitMatch = searchResult

        return nonExplicitMatch

    def searchTrackOnYoutube(self, track: Track) -> Track | None:
        """
        Searches for a track on YouTube based on the provided Track object.
        """
        # TODO: add validator into the model to handle this case there upon init of `Track()`.
        # if/else to handle the case when artist name is already in track name.
        searchQuery = (
            f"{track.title}"
            if track.artistName in track.title
            else f"{track.artistName} {track.title}"
        )

        # Fetch results from spotify.
        searchResults: list[Track] = [
            Track(**searchResult, spotifyArtistId=None)
            for searchResult in self.youtube.search(
                query=searchQuery, filter="songs", limit=5
            )[:5]
        ]

        for searchResult in searchResults:
            # LastFM is so bad it won't even return durations._.
            if not track.duration:
                return searchResult

            searchResultDuration: int = searchResult.duration
            # If its duration is in range ±5sec - should be the same track.
            if searchResultDuration in range(track.duration - 5, track.duration + 5):
                return searchResult

    def getYoutubeRecommendations(
        self, tracks: list[Track], limit: int = 5
    ) -> list[Track]:
        """
        Retrieves Youtube recommendations based on a list of input tracks.

        In result, you'll get this many tracks:
        <...>
        """
        logger.info(
            f"Executing `getYoutubeRecommendations()` with {len(tracks)} tracks"
        )
        youtubeTracksIds: list[str] = [
            track.youtubeId for track in tracks if track.youtubeId
        ]
        recommendedTracks: list[Track] = []

        # need to do stuff with this method. pass there `videoId` of each track.
        for trackId in youtubeTracksIds:
            result: dict = self.youtube.get_watch_playlist(videoId=trackId)

            recommendationsPerTrack: int = 0
            for rawTrack in result.get("tracks", [])[1 : limit + 1]:
                if recommendationsPerTrack >= limit:
                    break

                # Override spotifyArtistId, since it's youtube-only recommendations.
                recommendedTrack = Track(**rawTrack, spotifyArtistId=None)

                if recommendedTrack.youtubeId not in [
                    x.youtubeId for x in recommendedTracks
                ]:
                    recommendedTracks.append(recommendedTrack)
                    recommendationsPerTrack += 1

        return recommendedTracks

    def getSpotifyRecommendations(
        self,
        tracks: list[Track],
        recommendationChunkSize: int = MAX_SPOTIFY_RECOMMENDATION_CHUNK_SIZE,
        limit: int = 5,
    ) -> list[Track]:
        """
        Retrieves Spotify recommendations based on a list of input tracks.

        In result, you'll get this many tracks:
        ( len(tracks) / recommendationChunkSize ) * 5
        """
        logger.info(
            f"Executing `getSpotifyRecommendations()` with {len(tracks)} tracks"
        )
        spotifyTracksIds: list[str] = [
            track.spotifyId for track in tracks if track.spotifyId
        ]
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

    def getLastFMRecommendations(
        self, tracks: list[Track], sameArtistMargin: int = 1, sameTrackMargin: int = 2
    ) -> list[Track]:
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
            url: str = lastFMUrl.format(
                artist=track.firstArtistName,
                title=track.title,
                apiKey=os.environ.get("LASTFM_CLIENT_ID"),
            )
            try:
                result: dict = requests.get(url, timeout=DEFAULT_TIMEOUT).json()
                if "error" in result:
                    logger.error(
                        f"{track.title} / {track.firstArtistName} was failed to find on LastFM: {result}"
                    )
                    continue
            except requests.exceptions.JSONDecodeError as err:
                logger.error(
                    f"{track.title} / {track.firstArtistName} was failed to find on LastFM: {err}"
                )
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
                recommendedTrack = Track(
                    **rawTrack,
                    youtubeArtistId=None,
                    spotifyArtistId=None,
                    zeroDuration=True,
                )

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

    def createSpotifyPlaylist(
        self,
        lastN: int = 10,
        shuffle: bool = True,
        includeOriginals: bool = True,
    ) -> str:
        """
        <useful doc-string>
        """

        # Get last tracks from YouTube & fulfill them with `.spotifyId`
        lastSpotifyTracks: list[Track] = self.getLastSpotifyTracks(lastN=lastN)
        self.fillYoutubeId(tracks=lastSpotifyTracks)

        lastYoutubeTracks: list[Track] = []
        if self.user.youtubeAuth:
            lastYoutubeTracks = self.getLastYoutubeTracks(lastN=lastN)
            self.fillSpotifyId(tracks=lastYoutubeTracks)

        # Get youtube recommendations based on `lastYoutubeTracks`.
        recommendedTracks: list[Track] = self.getYoutubeRecommendations(
            lastSpotifyTracks + lastYoutubeTracks
        )

        # Get lastFM recommendations based on Spotify tracks.
        recommendedTracks += self.getLastFMRecommendations(
            tracks=recommendedTracks or lastSpotifyTracks + lastYoutubeTracks
        )

        # Fulfill all recommendations with `.youtubeId`.
        self.fillSpotifyId(tracks=recommendedTracks)

        # Prepare a list of spotify tracks. Include original tracks if needed.
        if includeOriginals:
            recommendedTracks += lastSpotifyTracks + lastYoutubeTracks

        spotifyTracks: list[str] = [
            f"https://open.spotify.com/track/{x.spotifyId}"
            for x in recommendedTracks
            if x.spotifyId
        ]
        # Remove duplicates.
        spotifyTracks = list(set(spotifyTracks))

        # Shuffle tracks if needed.
        if shuffle:
            random.shuffle(spotifyTracks)

        # Create playlist with last tracks + recommendations on YouTube.
        logger.info(f"Creating playlist with {len(spotifyTracks)} tracks")

        # First create a playlist
        playlistName: str = datetime.now().strftime("%d %b %H:%M")
        playlist: dict = self.spotify.user_playlist_create(
            user=self.spotify.current_user()["id"],
            name=playlistName,
            description="Created by Playlist Generator Bot, @spotify_youtube_playlist_bot",
        )
        # Then fill it with tracks, 100tracks at a time.
        for tracksChunk in chunked(spotifyTracks, MAX_SPOTIFY_PLAYLIST_CHUNK_SIZE):
            self.spotify.playlist_add_items(
                playlist_id=playlist["id"], items=tracksChunk
            )

        return f"https://open.spotify.com/playlist/{playlist['id']}"

    def createYoutubePlaylist(
        self,
        lastN: int = 10,
        shuffle: bool = True,
        includeOriginals: bool = True,
        standaloneRecommendations: bool = True,
    ) -> str:
        """
        <useful doc-string>
        """
        # Get last tracks from YouTube & fulfill them with `.spotifyId`
        lastYoutubeTracks: list[Track] = self.getLastYoutubeTracks(lastN=lastN)
        self.fillSpotifyId(tracks=lastYoutubeTracks)

        lastSpotifyTracks: list[Track] = []
        if self.user.spotifyAuth:
            lastSpotifyTracks = self.getLastSpotifyTracks(lastN=lastN)
            self.fillYoutubeId(tracks=lastSpotifyTracks)

        # Get spotify recommendations based on `lastYoutubeTracks`.
        recommendedTracks = []
        # if self.user.spotifyAuth:
        getSpotifyRecommendationsParams: dict = {
            "tracks": lastYoutubeTracks + lastSpotifyTracks
        }
        if standaloneRecommendations:
            getSpotifyRecommendationsParams["recommendationChunkSize"] = 1
        recommendedTracks: list[Track] = self.getSpotifyRecommendations(
            **getSpotifyRecommendationsParams
        )

        # Get lastFM recommendations based on Spotify tracks.
        recommendedTracks += self.getLastFMRecommendations(
            tracks=recommendedTracks or lastYoutubeTracks + lastSpotifyTracks
        )
        # Fulfill all recommendations with `.youtubeId`.
        self.fillYoutubeId(tracks=recommendedTracks)
        # Include original tracks if needed.
        if includeOriginals:
            recommendedTracks += lastSpotifyTracks + lastYoutubeTracks

        # Prepare a list of youtube track ids.
        youtubeTracks: list[str] = [
            x.youtubeId for x in recommendedTracks if x.youtubeId
        ]

        # Remove duplicates.
        youtubeTracks = list(set(youtubeTracks))

        # Shuffle tracks if needed.
        if shuffle:
            random.shuffle(youtubeTracks)

        # Create playlist with last tracks + recommendations on YouTube.
        logger.info(f"Creating playlist with {len(youtubeTracks)} tracks")
        playlistName: str = datetime.now().strftime("%d %b %H:%M")
        playlistId: str = self.youtube.create_playlist(
            video_ids=youtubeTracks,
            title=playlistName,
            description="Created by Playlist Generator Bot, @spotify_youtube_playlist_bot",
        )

        return f"https://music.youtube.com/playlist?list={playlistId}"


if __name__ == "__main__":
    generator = PlaylistGenerator()
    # generator.createYoutubePlaylist()
    playlistUrl = generator.createYoutubePlaylist(
        lastN=1,
        shuffle=True,
        includeOriginals=True,
        standaloneRecommendations=True,
    )
    print(playlistUrl)
    # generator.createSpotifyPlaylist(lastN=10, shuffle=True, includeOriginals=True)
