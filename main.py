from typing import List

from bcrypt import checkpw
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from mnemonic import Mnemonic
from sqlalchemy.orm import selectinload

from dto.buy_order_request import OrderBuyRequest
from dto.create_order_request import CreateOrderRequest
from dto.order_info_response import OrderInfoResponse
from dto.password_recovery_request import PasswordRecoveryRequest
from dto.user_create_request import UserCreateRequest
from dto.user_info_response import UserInfoResponse, WalletInfo
from hashing import Hash
from models import User, Wallet, Order
from db import init_db, SessionLocal
import uuid

from util_cryptography import hash_mnemonic

app = FastAPI()

available_currencies = ["BTC", "ETH", "LTC"]

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.post("/user/createAccount/")
async def create_account(request: UserCreateRequest, db: AsyncSession = Depends(get_db)):
    user_id = request.user_id
    print(user_id)

    result = await db.execute(select(User).where(User.id == user_id))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this ID already exists")

    password = request.password
    password_hash = Hash.hash_password(password)

    mnemonic_generator = Mnemonic("english")
    mnemonic_phrase = mnemonic_generator.generate(strength=128)
    mnemonic_hash = hash_mnemonic(mnemonic_phrase)

    user_address = str(uuid.uuid4())

    new_user = User(id=user_id,
                    user_address=user_address,
                    password_hash=password_hash,
                    encrypted_mnemonic=mnemonic_hash)
    db.add(new_user)
    await db.flush()

    for currency in available_currencies:
        wallet = Wallet(user_id=new_user.id, currency=currency, value=50)
        db.add(wallet)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="User with this data already exists")

    return {
        "msg": "Account created successfully",
        "password": password,
        "user_address": user_address,
        "mnemonic_phrase": mnemonic_phrase.split()
    }



@app.post("/user/recoverPassword/")
async def recover_password(request: PasswordRecoveryRequest, db: AsyncSession = Depends(get_db)):
    user_id = request.user_id
    mnemonic_phrase = request.mnemonic_phrase
    new_password = request.new_password

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not checkpw(mnemonic_phrase.encode(), user.encrypted_mnemonic.encode()):
        raise HTTPException(status_code=400, detail="Invalid mnemonic phrase")

    new_password_hash = Hash.hash_password(new_password)
    user.password_hash = new_password_hash

    try:
        await db.commit()
        return {"msg": "Password updated successfully"}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update password")


@app.get("/user/info", response_model=UserInfoResponse)
async def get_user_info(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.wallets)))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_info = UserInfoResponse(
        user_address=user.user_address,
        wallets=[
            WalletInfo(currency=wallet.currency, value=wallet.value)
            for wallet in user.wallets
        ]
    )

    return user_info


@app.get("/user/exist")
async def check_user_exist(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if user:
        return {"exists": True}
    else:
        return {"exists": False}


@app.post("/order/create/")
async def create_order(request: CreateOrderRequest, db: AsyncSession = Depends(get_db)):
    user_id = request.user_id
    from_currency = request.from_currency
    to_currency = request.to_currency
    value = request.value
    exchange_rate = request.exchange_rate

    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.wallets)))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from_wallet = next((wallet for wallet in user.wallets if wallet.currency == from_currency), None)
    to_wallet = next((wallet for wallet in user.wallets if wallet.currency == to_currency), None)

    if not from_wallet:
        raise HTTPException(status_code=404, detail=f"{from_currency} wallet not found")
    if from_wallet.value < value:
        raise HTTPException(status_code=400, detail="Insufficient funds in the from_currency wallet")

    amount_to_receive = value * exchange_rate

    if not to_wallet:
        raise HTTPException(status_code=404, detail=f"{to_currency} wallet not found")

    new_order = Order(
        user_id=user_id,
        from_currency=from_currency,
        to_currency=to_currency,
        amount_sold=value,
        exchange_rate=exchange_rate,
        amount_received=amount_to_receive,
        status="pending"
    )
    db.add(new_order)

    try:
        await db.commit()
        return {"msg": f"Order created successfully. {value} {from_currency} exchanged to {amount_to_receive} {to_currency}"}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create order")


@app.get("/user/orders", response_model=List[OrderInfoResponse])
async def list_user_orders(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.orders)))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    orders = [
        OrderInfoResponse(
            order_id=order.id,
            from_currency=order.from_currency,
            to_currency=order.to_currency,
            amount_sold=order.amount_sold,
            exchange_rate=order.exchange_rate,
            amount_to_receive=order.amount_received,
            status=order.status
        )
        for order in user.orders
    ]

    return orders


@app.delete("/order/delete")
async def delete_order(order_id: int, user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != user_id:
        raise HTTPException(status_code=403, detail="You are not authorized to delete this order")

    await db.delete(order)
    try:
        await db.commit()
        return {"msg": "Order deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete the order")


@app.get("/orders/list")
async def list_orders(user_id: int, currency_to_sell: str, currency_to_buy: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order)
        .where(
            Order.user_id != user_id,
            Order.from_currency == currency_to_buy,
            Order.to_currency == currency_to_sell
        )
    )
    orders = result.scalars().all()

    if not orders:
        return []

    order_responses = [
        OrderInfoResponse(
            order_id=order.id,
            from_currency=order.from_currency,
            to_currency=order.to_currency,
            amount_sold=order.amount_sold,
            exchange_rate=order.exchange_rate,
            amount_to_receive=order.amount_received,
            status=order.status
        )
        for order in orders
    ]

    return order_responses


@app.post("/orders/buy")
async def buy_order(request: OrderBuyRequest, db: AsyncSession = Depends(get_db)):
    order_id = request.order_id
    user_id = request.user_id
    amount_to_buy = request.amount_to_buy

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id, Wallet.currency == order.to_currency))
    wallet_buyer_to_sell = result.scalars().first()

    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id, Wallet.currency == order.from_currency))
    wallet_buyer_to_buy = result.scalars().first()

    result = await db.execute(select(Wallet).where(Wallet.user_id == order.user_id, Wallet.currency == order.to_currency))
    wallet_seller_to_buy = result.scalars().first()

    result = await db.execute(select(Wallet).where(Wallet.user_id == order.user_id, Wallet.currency == order.from_currency))
    wallet_seller_to_sell = result.scalars().first()

    amount_to_pay = amount_to_buy * order.exchange_rate

    if order.amount_sold < amount_to_buy or wallet_seller_to_sell.value < amount_to_buy:
        raise HTTPException(status_code=400, detail="Not enough quantity available for purchase")

    if not wallet_buyer_to_sell or wallet_buyer_to_sell.value < amount_to_pay:
        raise HTTPException(status_code=400, detail="Insufficient funds in your wallet")

    wallet_buyer_to_sell.value -= amount_to_pay
    wallet_buyer_to_buy.value += amount_to_buy

    wallet_seller_to_buy.value += amount_to_pay
    wallet_seller_to_sell.value -= amount_to_buy

    order.amount_sold -= amount_to_buy
    order.amount_received -= amount_to_pay

    if order.amount_sold == 0:
        await delete_order(order_id=order_id, user_id=order.user_id, db=db)

    try:
        await db.commit()
        return {"msg": "Order successfully purchased", "amount_to_receive": amount_to_buy, "amount_paid": amount_to_pay}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to complete the transaction")