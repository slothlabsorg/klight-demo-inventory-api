import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import engine, get_db, ensure_db_exists
from app.models import Base, Stock
from app.consumer import start_consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_db_exists()
    Base.metadata.create_all(bind=engine)
    start_consumer()
    yield


app = FastAPI(title="inventory-api", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "inventory-api"}


@app.get("/stock")
def list_stock(db: Session = Depends(get_db)):
    return [
        {"product_id": s.product_id, "name": s.name, "quantity": s.quantity}
        for s in db.query(Stock).order_by(Stock.product_id).all()
    ]


@app.get("/stock/{product_id}")
def get_stock(product_id: int, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.product_id == product_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Product not found in inventory")
    return {"product_id": stock.product_id, "name": stock.name, "quantity": stock.quantity}
