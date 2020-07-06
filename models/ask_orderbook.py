from lib_common.db import db


class AskOrderbook(db.Model):
    __tablename__ = "ask_orderbooks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    exchange_id = db.Column(db.Integer, db.ForeignKey("exchanges.id"))
    pair_id = db.Column(db.Integer, db.ForeignKey("pairs.id"))
    timestamp = db.Column(db.TIMESTAMP, nullable=False)
