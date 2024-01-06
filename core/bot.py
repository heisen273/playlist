from __future__ import annotations
import logging
import json
import asyncio
import os
import telegram
import traceback
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    ApplicationBuilder,
    CallbackQueryHandler,
)

try:
    from model.User import User
except ModuleNotFoundError:
    from model import User

from handlers import (
    startCommand,
    handleGETRequest,
    handleChoice,
    handleAuthCommand,
    handleGeneratePlaylistCommand,
)
from constants import GENERATE_PLAYLIST, AUTH_SPOTIFY, AUTH_YOUTUBE

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


async def wrapper(request) -> str:
    """Docstring for wrapper"""

    if request.method == "GET":
        return await handleGETRequest(request)
    if request.method != "POST":
        return "not post"

    try:
        rawRequest = json.loads(request.body.read().decode())
    except:
        if not (rawRequest := request.get_json(silent=True)):
            return "bad json"

    # Assume that update is always parsed correctly.
    update: Update = Update.de_json(rawRequest, bot)

    await application.initialize()
    await application.process_update(update)

    return "ok"


import cherrypy


@cherrypy.expose
@cherrypy.tools.allow(methods=["GET", "POST"])
def entryPoint(**kwargs) -> str:
    """Docstring for entryPoint"""
    try:
        eventLoop.run_until_complete(wrapper(cherrypy.request))
    except:
        print(traceback.format_exc())
        return "ok"


eventLoop = asyncio.new_event_loop()
asyncio.set_event_loop(eventLoop)
bot = telegram.Bot(token=os.environ["BOT_TOKEN"])
application = ApplicationBuilder().bot(bot).build()

conversation_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", startCommand),
        CommandHandler(AUTH_SPOTIFY, handleAuthCommand),
        CommandHandler(AUTH_YOUTUBE, handleAuthCommand),
        CommandHandler(GENERATE_PLAYLIST, handleGeneratePlaylistCommand),
    ],
    states={},
    fallbacks=[CommandHandler("start", startCommand)],
    allow_reentry=True,
)


application.add_handler(conversation_handler)
application.add_handler(CallbackQueryHandler(handleChoice))


if __name__ == "__main__":
    cherrypy.server.socket_port = 8081
    cherrypy.tree.mount(entryPoint)
    cherrypy.engine.start()
    cherrypy.engine.block()
