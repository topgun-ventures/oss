from lib_common.db import db


class ReferencePrice(db.Model):
    __tablename__ = "reference_prices"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exchange_id = db.Column(db.Integer, db.ForeignKey("exchanges.id"))
    pair_id = db.Column(db.Integer, db.ForeignKey("pairs.id"))
    av_price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.TIMESTAMP, nullable=False)
