
from contextlib import asynccontextmanager
from decimal import Decimal
import os

import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine,
    Integer,
    String,
    Numeric,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)


PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL",
    "http://localhost:8000",
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://commercehub:change-me@localhost:5432/commercehub",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )


class OrderCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


def get_db():
    with SessionLocal() as db:
        yield db


def serialize_order(order: Order):
    return {
        "id": order.id,
        "product_id": order.product_id,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "total_price": float(order.total_price),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenient for this learning project.
    # Use database migrations for production deployments.
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(
    title="Order Service",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/orders", status_code=201)
async def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
):
    # Validate the product through Product Service.
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            response = await client.get(
                f"{PRODUCT_SERVICE_URL}/products/{order.product_id}"
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="Product Service unavailable",
            )

    if response.status_code == 404:
        raise HTTPException(
            status_code=400,
            detail="Invalid product_id",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Unexpected response from Product Service",
        )

    product = response.json()

    new_order = Order(
        product_id=product["id"],
        product_name=product["name"],
        quantity=order.quantity,
        total_price=Decimal(str(product["price"])) * order.quantity,
    )

    try:
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to save order",
        )

    return serialize_order(new_order)


@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    orders = db.scalars(
        select(Order).order_by(Order.id)
    ).all()

    return [serialize_order(order) for order in orders]


@app.get("/orders/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return serialize_order(order)
