import asyncio
import os
from functools import wraps

from flask import Flask
from flask_cors import CORS
from flask_httpauth import HTTPTokenAuth

import models
from lib_common.db import db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://{}:{}@{}/{}".format(
    os.getenv("DB_USERNAME"),
    os.getenv("DB_PASS"),
    os.getenv("DB_HOST"),
    os.getenv("DB_NAME"),
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

CORS(app)
auth = HTTPTokenAuth(scheme="Bearer")


def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapped


@auth.verify_token
def verify_token(token):
    return True
