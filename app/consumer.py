"""Background Kafka consumer thread. Consumes sale.created and decrements stock."""
import json
import logging
import os
import threading
from confluent_kafka import Consumer, KafkaError

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC_SALE_CREATED", "sale.created")
GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP", "inventory-api-group")


def _consume_loop():
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })
    consumer.subscribe([TOPIC])
    logger.info("Kafka consumer started. Topic: %s", TOPIC)

    from app.database import SessionLocal
    from app.models import Stock

    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            logger.error("Kafka error: %s", msg.error())
            continue

        try:
            data = json.loads(msg.value().decode("utf-8"))
            product_id = data.get("product_id")
            quantity = data.get("quantity", 1)

            db = SessionLocal()
            try:
                stock = db.query(Stock).filter(Stock.product_id == product_id).first()
                if stock:
                    stock.quantity = max(0, stock.quantity - quantity)
                    db.commit()
                    logger.info(
                        "sale.created consumed: product_id=%s qty=%s → new_stock=%s",
                        product_id, quantity, stock.quantity,
                    )
                else:
                    logger.warning("No stock record for product_id=%s", product_id)
            finally:
                db.close()
        except Exception as e:
            logger.error("Error processing sale.created: %s", e)


def start_consumer():
    thread = threading.Thread(target=_consume_loop, daemon=True, name="kafka-consumer")
    thread.start()
    return thread
