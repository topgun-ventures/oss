from lib_common.db import db


class Exchange(db.Model):
    __tablename__ = "exchanges"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(40), nullable=False)
    timestamp = db.Column(db.TIMESTAMP, nullable=False)
