from __future__ import annotations

# Stdlib
import os
import time
import traceback

# External
import requests
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import CallbackContext

# In-house
try:
    from playlist.model.Track import Track
    from playlist.model.User import User
    from playlist.model.Platform import Platform
    from playlist.constants import (
        GENERATE_PLAYLIST,
        LAST_N_ROW,
        LAST_N_PREFIX,
        SELECTOR,
        SEPARATOR,
        EXTRA_SETTINGS,
        AUTH,
    )
except ModuleNotFoundError:
    from model import User, Platform, Track
    from constants import (
        GENERATE_PLAYLIST,
        LAST_N_ROW,
        LAST_N_PREFIX,
        SELECTOR,
        SEPARATOR,
        EXTRA_SETTINGS,
        AUTH,
    )

import database
from generator import PlaylistGenerator


bot = telegram.Bot(token=os.environ["BOT_TOKEN"])


async def startCommand(update: Update, _: CallbackContext) -> None:
    startMessage = (
        "To start, you need to authorize Spotify and/or Youtube. \n"
        "Please note: generation works MUCH better if you authorize both.\n"
    )
    await update.effective_message.reply_text(startMessage)
    user: User = database.getUser(update.effective_chat)

    spotifyButton = InlineKeyboardButton(
        **Platform.SPOTIFY.getAuthButtonParams(user, update)
    )
    youtubeButton = InlineKeyboardButton(
        **Platform.YOUTUBE.getAuthButtonParams(user, update)
    )
    generatePlaylistButton = InlineKeyboardButton(
        "💽 Generate Playlist", callback_data=GENERATE_PLAYLIST
    )

    buttons = [[spotifyButton], [youtubeButton], [generatePlaylistButton]]
    replyMarkup = InlineKeyboardMarkup(buttons)

    await update.effective_message.reply_text(
        "Once you're done, use /generate_playlist to create a new playlist.",
        reply_markup=replyMarkup,
    )


async def handleAuthCommand(
    update: Update, _: CallbackContext, platform: Platform | None = None
) -> None:
    """Generic method to handle authentication for both Spotify and YouTube"""

    # If platform was not explicitly specified, then this method was triggered through the `/auth_<platform>` message.
    if not platform:
        platform = Platform(update.effective_message.text.split("_")[1])

    # Fetch the user from db.
    user: User = database.getUser(update.effective_chat)

    # Prepare button metadata.
    authUrl: str = platform.getAuthUrlMethod()(update, user)
    authButtonText: str = platform.authButtonText(user=User())
    authButtonMessageText = platform.authCommandMessageText(user)

    keyboard = [[InlineKeyboardButton(authButtonText, url=authUrl)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        authButtonMessageText, reply_markup=reply_markup
    )


async def handleGeneratePlaylistCommand(update: Update, _: CallbackContext) -> None:
    """Docstring for handleGeneratePlaylistCommand()"""
    user: User = database.getUser(update.effective_chat)

    buttons = [
        [Platform.SPOTIFY.getGeneratePlaylistButton(user)],
        [Platform.YOUTUBE.getGeneratePlaylistButton(user)],
        [InlineKeyboardButton(" ", callback_data=SEPARATOR)],
        [InlineKeyboardButton("Generate based on X songs:", callback_data=SEPARATOR)],
        [
            InlineKeyboardButton(f"{x}", callback_data=f"{LAST_N_PREFIX}_{x}")
            for x in range(4, 11)
        ],
        [InlineKeyboardButton("Extra settings ⚙️", callback_data=EXTRA_SETTINGS)],
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    replyMethodName = (
        "edit_text" if update.effective_message.from_user.is_bot else "reply_text"
    )
    replyMethod = getattr(update.effective_message, replyMethodName)

    await replyMethod(
        f"Choose where do you want to publish generated playlist:",
        reply_markup=reply_markup,
    )


async def handleChoice(update: Update, context: CallbackContext) -> None:
    choice: str = update.callback_query.data
    matchedPlatform: Platform | None = _getPlatform(choice)

    # Early exit in case if user taps separator.
    if choice == SEPARATOR:
        await update.callback_query.answer("It's a separator, dummy;)")

    elif choice == EXTRA_SETTINGS:
        await extraSettings(update, context)

    elif GENERATE_PLAYLIST in choice:
        await generatePlaylist(
            update, context, platform=matchedPlatform
        ) if matchedPlatform else handleGeneratePlaylistCommand(update, context)

    elif AUTH in choice:
        rawPlatform = choice.replace(AUTH, "")
        await handleAuthCommand(update, context, platform=Platform(rawPlatform))

    elif LAST_N_PREFIX in choice:
        await handleLastNChoice(update, context)


async def extraSettings(update: Update, _: CallbackContext) -> None:
    """
    Still WIP. . .
    """

    buttons = [
        [
            InlineKeyboardButton("Shuffle", callback_data=SEPARATOR),
            InlineKeyboardButton("Include originals", callback_data=SEPARATOR),
        ],
        [InlineKeyboardButton("Choose 'X songs' randomly", callback_data=SEPARATOR)],
        [
            InlineKeyboardButton("Change Spotify Playlist", callback_data=SEPARATOR),
            InlineKeyboardButton("Change YouTube Playlist", callback_data=SEPARATOR),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    replyMethodName = (
        "edit_text" if update.effective_message.from_user.is_bot else "reply_text"
    )
    replyMethod = getattr(update.effective_message, replyMethodName)

    await replyMethod(
        f"Choose where do you want to publish generated playlist:",
        reply_markup=reply_markup,
    )


async def generatePlaylist(
    update: Update, context: CallbackContext, platform: Platform | None = None
) -> str | None:
    """Handles playlist generation(and publishing) for both Spotify and YouTube"""
    user: User = database.getUser(update.effective_chat)

    # Early exit in case if:
    # 1. Generation is already in progress
    if user.inProgress:
        await update.effective_message.reply_text("Generating, please wait...")
        return "ok"

    # 2. User requested generate & publish to unauthorized platform
    elif not getattr(user, platform.authKey):
        errorMessage: str = f"You have to authorize {platform.name} to publish generated playlists there!"
        await update.effective_message.reply_text(errorMessage)
        return await handleAuthCommand(update, context, platform)

    playlistGenerator = PlaylistGenerator(user=user)
    lastN: int = _getLastN(update.effective_message.reply_markup.inline_keyboard)

    database.storeUserInProgress(user)
    await update.effective_message.reply_text("Generating, please wait...")
    await update.effective_message.reply_chat_action(action=ChatAction.TYPING)

    try:
        playlistUrl = await platform.createPlaylist(playlistGenerator, lastN)
        await update.effective_message.reply_text(
            f"Done! Link to playlist: {playlistUrl}"
        )
        database.finishUserInProgress(user)
    except Exception:
        traceback.print_exc()
        database.finishUserInProgress(user)


async def handleLastNChoice(update: Update, _: CallbackContext) -> None:
    """Docstring for"""
    query = update.callback_query
    existingKeyboard = query.message.reply_markup.inline_keyboard
    selectedNumber = query.data.split("_")[-1]

    # Get row with `Last N` buttons
    lastNRow: list[InlineKeyboardButton] = list(
        query.message.reply_markup.inline_keyboard[LAST_N_ROW]
    )

    alreadySelected = None
    # Iterate through the row.
    for indx, button in enumerate(lastNRow):
        # If we've matched the button that user tapped
        if button.callback_data == query.data:
            # Enable or disable selector on the button.
            alreadySelected = True if SELECTOR in button.text else False
            buttonText = (
                f"{selectedNumber}"
                if alreadySelected
                else f"{SELECTOR}{selectedNumber}"
            )

            # Store result in the lastN row at specific index.
            lastNRow[indx] = InlineKeyboardButton(
                buttonText, callback_data=button.callback_data
            )

        # If another button was previously selected - disable selector, so two buttons won't be selected at same time.
        elif SELECTOR in button.text:
            lastNRow[indx] = InlineKeyboardButton(
                button.text.replace(SELECTOR, ""), callback_data=button.callback_data
            )

    # Get track names & store them below `lastN` row.
    # user: User = database.getUser(update.effective_chat)
    # trackButtons: list = getTrackButtons(lastN=10, user=user)

    # if not alreadySelected:
    #     updatedMarkup = InlineKeyboardMarkup(existingKeyboard[:LAST_N_ROW] + tuple([lastNRow]) + tuple(trackButtons))
    # else:
    # Create a new InlineKeyboardMarkup
    updatedMarkup = InlineKeyboardMarkup(
        existingKeyboard[:LAST_N_ROW] + tuple([lastNRow])
    )

    # Edit the message with the updated text and keyboard
    # Add a space to the text to force an update
    await query.message.edit_reply_markup(reply_markup=updatedMarkup)
    await query.answer(f"Playlist will be generated using {selectedNumber} last songs")


def getTrackButtons(lastN: int, user: User) -> list:
    """Docstring for getNTracks"""
    if not any([user.spotifyAuth, user.youtubeAuth]):
        return []

    tracks: list[Track] = []
    playlistGenerator = PlaylistGenerator(user=user)
    if user.spotifyAuth:
        tracks += playlistGenerator.getLastSpotifyTracks(lastN=lastN)
    if user.youtubeAuth:
        tracks += playlistGenerator.getLastYoutubeTracks(lastN=lastN)

    import json

    rawTracks = json.dumps([x.model_dump_json() for x in tracks])[:64]

    return [
        (
            InlineKeyboardButton(f"🎙{track.firstArtistName}", callback_data=rawTracks),
            InlineKeyboardButton(f"❌", callback_data=rawTracks),
        )
        for track in tracks
    ]


def getCrossSign(track: Track) -> str:
    """Docstring for getCrossSign"""
    maxLineLength = 35
    trackNameLength: int = len(f"🎙{track.firstArtistName}: {track.title}")
    spaceLength = maxLineLength - trackNameLength

    # if spaceLength <= 0:
    #     spaceLength = 1

    return "\u2002" + " " * spaceLength + "\u2002"


async def handleGETRequest(request) -> str:
    """Docstring for"""

    allParams = (
        getattr(request, "args")
        if hasattr(request, "args")
        else getattr(request, "params")
    )

    # Serve HTML web-page, if it's not a redirect from Spotify / YouTube.
    if "state" not in allParams and "code" not in allParams:
        if "privacyPolicy" in allParams:
            return open("privacyPolicy.html").read()

        return open("index.html").read()

    # Handle redirect from Spotify / YouTube.
    if Platform.YOUTUBE in allParams["state"]:
        platform = Platform.YOUTUBE
    else:
        platform = Platform.SPOTIFY

    # Consider dropping junk keys from `creds` before storing them in firebase.
    if platform == Platform.SPOTIFY:
        from spotipy.oauth2 import SpotifyOAuth

        creds = SpotifyOAuth().get_access_token(code=allParams["code"])

        database.database.child(allParams["state"]).update({platform.value: creds})
        await bot.sendMessage(
            chat_id=allParams["state"], text=platform.successfulAuthText
        )
        return platform.successfulAuthText

    # Token endpoint URL
    token_url = "https://oauth2.googleapis.com/token"

    # Payload for the token request
    token_payload = {
        "code": allParams["code"],
        "client_id": os.environ["YOUTUBE_CLIENT_ID"],
        "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
        "redirect_uri": os.environ["YOUTUBE_REDIRECT_URI"],
        "grant_type": "authorization_code",
    }

    # Make the POST request to exchange the authorization code for tokens
    response: request.Response = requests.post(token_url, data=token_payload)
    creds: dict = response.json()

    userId: str = allParams["state"].split("_")[0]
    creds["expires_at"] = int(time.time()) + creds["expires_in"]
    database.database.child(userId).update({platform: creds})
    await bot.sendMessage(chat_id=userId, text=platform.successfulAuthText)
    return platform.successfulAuthText


def _getLastN(replyMarkup: tuple[tuple[InlineKeyboardButton], ...]) -> int:
    """Docstring for get User"""
    row: tuple[InlineKeyboardButton] = replyMarkup[LAST_N_ROW]

    if selectedOption := [
        int(x.text.replace(SELECTOR, "")) for x in row if f"{SELECTOR}" in x.text
    ]:
        return selectedOption[0]

    return 1


def _getPlatform(rawString: str) -> Platform | None:
    """Docstring for _getPlatform"""
    if match := [x.value for x in list(Platform) if x.value in rawString]:
        return Platform(match[0])
