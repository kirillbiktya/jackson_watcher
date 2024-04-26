from sqlalchemy import Column, BIGINT, Integer, Identity, Float, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship

from . import Base


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BIGINT, primary_key=True, index=True, unique=True)

    tickers = relationship("Ticker", back_populates="owner")


class Ticker(Base):
    __tablename__ = "tickers"

    id = Column(Integer, Identity(start=1, cycle=False), primary_key=True, index=True, unique=True)
    cmc_coin_id = Column(Integer)
    name = Column(String)
    floor_value = Column(Float)
    ceil_value = Column(Float)
    owner_id = Column(BIGINT, ForeignKey("users.telegram_id"))
    latest_notify = Column(DateTime, nullable=True)  # TODO

    owner = relationship("User", back_populates="tickers")