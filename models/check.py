from lib_common.db import db


class Check(db.Model):
    __tablename__ = "checks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exchange_id = db.Column(db.Integer, db.ForeignKey("exchanges.id"))
    active_orders = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.TIMESTAMP, nullable=False)
