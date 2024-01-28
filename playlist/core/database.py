import os
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import db, credentials
from telegram import Chat

from constants import DB_NAME, DB_URL, DEFAULT_PATH

try:
    from playlist.model.User import User
except ModuleNotFoundError:
    from model import User


cred = credentials.Certificate(f"{DEFAULT_PATH}/_firebase.json")
firebase_admin.initialize_app(cred, {"databaseURL": os.environ.get("DB", DB_URL)})
database = db.reference(DB_NAME)


def getUser(chat: Chat) -> User:
    """Docstring for get User"""

    userId = str(chat.id)
    data: object | dict | None = database.child(userId).get()

    # Create user if it does not exist.
    if not data:
        user = User(userId=userId, userName=chat.username)
        database.child(userId).set(user.model_dump(mode="json"))

        return user

    # Otherwise load it from db.
    user = User(**data)

    # Unset `inProgress` field if it wasn't updated for longer than 10min
    if user.inProgress and (datetime.now() - user.updated) > timedelta(seconds=600):
        user.inProgress = False

    return user


def storeUserInProgress(user: User) -> None:
    """Docstring for"""

    user.inProgress = True
    user.messages += 1
    user.updated = datetime.now()

    database.child(user.userId).update(
        {
            "inProgress": user.inProgress,
            "messages": user.messages,
            "_updated": str(user.updated),
        }
    )


def finishUserInProgress(user: User) -> None:
    """Docstring for"""
    usersReference = db.reference(DB_NAME)

    user.inProgress = False
    user.updated = datetime.now()

    database.child(user.userId).update(
        {"inProgress": user.inProgress, "_updated": str(user.updated)}
    )
