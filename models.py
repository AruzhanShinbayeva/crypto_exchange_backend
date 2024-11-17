from sqlalchemy import Column, Integer, String, ForeignKey, Float, BigInteger
from sqlalchemy.orm import relationship

from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    user_address = Column(String, index=True)
    password_hash = Column(String)
    encrypted_mnemonic = Column(String)

    wallets = relationship("Wallet", back_populates="user")

    orders = relationship("Order", back_populates="user", foreign_keys="[Order.user_id]")


class Wallet(Base):
    __tablename__ = 'wallets'

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    currency = Column(String, nullable=False)
    value = Column(Float, nullable=False, default=0)

    user = relationship("User", back_populates="wallets")


class Order(Base):
    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    from_currency = Column(String, nullable=False)
    to_currency = Column(String, nullable=False)
    amount_sold = Column(Float, nullable=False)
    exchange_rate = Column(Float, nullable=False)
    amount_received = Column(Float, nullable=False)
    status = Column(String, default="pending")

    user = relationship("User", back_populates="orders", foreign_keys=[user_id])