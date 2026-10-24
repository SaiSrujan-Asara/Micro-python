
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os

app = FastAPI(
    title="Order Service",
    version="1.0.0"
)

PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL",
    "http://localhost:8000"
)

orders = {}
next_order_id = 1


class OrderCreate(BaseModel):
    product_id: int
    quantity: int


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/orders", status_code=201)
async def create_order(order: OrderCreate):
    global next_order_id

    # Call Product Service to validate the product
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            response = await client.get(
                f"{PRODUCT_SERVICE_URL}/products/{order.product_id}"
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="Product Service unavailable"
            )

    if response.status_code == 404:
        raise HTTPException(
            status_code=400,
            detail="Invalid product_id"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Unexpected response from Product Service"
        )

    product = response.json()

    new_order = {
        "id": next_order_id,
        "product_id": product["id"],
        "product_name": product["name"],
        "quantity": order.quantity,
        "total_price": product["price"] * order.quantity
    }

    orders[next_order_id] = new_order
    next_order_id += 1

    return new_order


@app.get("/orders")
def get_orders():
    return list(orders.values())


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    order = orders.get(order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return order
