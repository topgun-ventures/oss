from lib_common.db import db


class CancelledOrder(db.Model):
    __tablename__ = "cancelled_orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exchange_id = db.Column(db.Integer, db.ForeignKey("exchanges.id"))
    order_exchange_id = db.Column(db.BigInteger, nullable=False)
    amount_filled = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.TIMESTAMP, nullable=False)
