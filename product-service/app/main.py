
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Product Service",
    version="1.0.0"
)

# Temporary in-memory data
products = {
    1: {"id": 1, "name": "Laptop", "price": 65000},
    2: {"id": 2, "name": "Keyboard", "price": 2500},
    3: {"id": 3, "name": "Mouse", "price": 800},
}


class ProductCreate(BaseModel):
    name: str
    price: float


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/products")
def get_products():
    return list(products.values())


@app.get("/products/{product_id}")
def get_product(product_id: int):
    product = products.get(product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


@app.post("/products", status_code=201)
def create_product(product: ProductCreate):
    new_id = max(products.keys(), default=0) + 1

    new_product = {
        "id": new_id,
        "name": product.name,
        "price": product.price,
    }

    products[new_id] = new_product

    return new_product
