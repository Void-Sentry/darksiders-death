from .connection import RabbitMQManager, logger
import os

bus_client = RabbitMQManager()

def start_consuming():
    global bus_client

    try:
        bus_client.start_consuming(os.getenv('BUS_QUEUE'))
    except Exception as e:
        logger.error(f"Failed to start consuming messages: {str(e)}")
        raise
