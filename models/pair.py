from lib_common.db import db


class Pair(db.Model):
    __tablename__ = "pairs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.TIMESTAMP, nullable=False)
