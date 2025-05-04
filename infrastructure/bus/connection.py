import threading
import logging
import json
import pika
import uuid
import os
import time
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RabbitMQManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self._connection_params = pika.ConnectionParameters(
            host=os.getenv('BUS_HOST'),
            port=int(os.getenv('BUS_PORT')),
            credentials=pika.PlainCredentials(
                username=os.getenv('BUS_USER'),
                password=os.getenv('BUS_PASS')),
            virtual_host=os.getenv('BUS_VHOST'),
            heartbeat=30,  # Heartbeat reduzido para 30 segundos
            blocked_connection_timeout=300,
            connection_attempts=5,
            retry_delay=5,
            socket_timeout=10
        )
        self._connect()
        self._event_handlers = {}
        self._consuming = False
        self._consumer_tags = {}

    def _connect(self):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.connection = pika.BlockingConnection(self._connection_params)
                self.channel = self.connection.channel()
                self.channel.queue_declare(
                    queue=os.getenv('BUS_QUEUE'),
                    durable=True
                )
                logger.info("RabbitMQ connection established successfully")
                return
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(5)

    def _reconnect(self):
        try:
            if hasattr(self, 'connection') and self.connection.is_open:
                self.connection.close()
            self._connect()
            # Re-register consumers after reconnection
            if self._consuming:
                for queue_name, callback in self._consumer_tags.items():
                    self._start_consumer(queue_name, callback)
        except Exception as e:
            logger.error(f"Reconnection failed: {str(e)}")
            raise

    def _ensure_connection(self):
        if not hasattr(self, 'connection') or not self.connection.is_open:
            self._reconnect()

    def publish_event(self, queue_name, event_name, payload, timeout=10):
        connection = pika.BlockingConnection(self._connection_params)
        channel = connection.channel()
        try:
            corr_id = str(uuid.uuid4())
            response = None
            response_lock = threading.Event()

            result = channel.queue_declare(queue='', exclusive=True, durable=False, auto_delete=True)
            callback_queue = result.method.queue

            def on_response(ch, method, properties, body):
                nonlocal response
                if properties.correlation_id == corr_id:
                    try:
                        response = json.loads(body)['data']
                    except Exception:
                        response = body.decode()
                    finally:
                        response_lock.set()

            channel.basic_consume(
                queue=callback_queue,
                on_message_callback=on_response,
                auto_ack=True
            )

            message = {'event': event_name, 'data': payload}

            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    reply_to=callback_queue,
                    correlation_id=corr_id,
                    delivery_mode=2,
                    content_type='application/json',
                    expiration=str(timeout * 1000)
                )
            )

            # Inicia a espera ativa pelo response
            start_time = time.time()
            while not response_lock.is_set():
                connection.process_data_events(time_limit=1)
                if time.time() - start_time > timeout:
                    raise TimeoutError("No response received in time")

            return response

        finally:
            try:
                channel.queue_delete(queue=callback_queue)
                channel.close()
            except Exception:
                pass
            try:
                connection.close()
            except Exception:
                pass

    def register_handler(self, event_name):
        def decorator(callback):
            if not callable(callback):
                raise ValueError("Callback must be callable")
            self._event_handlers[event_name] = callback
            logger.info(f"Handler registered for event: {event_name}")
            return callback
        return decorator

    def start_consuming(self, queue_name):
        if self._consuming:
            logger.warning("Already consuming messages")
            return
            
        def callback(ch, method, properties, body):
            try:
                message = json.loads(body)
                event_name = message.get('event')
                payload = message.get('data')
                
                logger.debug(f"Received event: {event_name}")
                
                if event_name in self._event_handlers:
                    try:
                        res = self._event_handlers[event_name](payload, ch)

                        if properties.reply_to:
                            ch.basic_publish(
                            exchange='',
                            routing_key=properties.reply_to,
                            body=json.dumps({ 'data': res }, default=str),
                            properties=pika.BasicProperties(
                                correlation_id=properties.correlation_id,
                                content_type='application/json',
                                delivery_mode=2,
                            )
                        )

                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.error(f"Handler failed for {event_name}: {str(e)}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                else:
                    logger.warning(f"No handler for event: {event_name}")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except json.JSONDecodeError:
                logger.error("Invalid message format")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        try:
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False
            )
            
            self._consuming = True

            thread = threading.Thread(
                target=self._start_consuming_loop,
                daemon=True,
                name=f"RabbitMQConsumer-{queue_name}"
            )
            thread.start()
            logger.info(f"Started consuming from queue: {queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to start consuming: {str(e)}")
            raise

    def _start_consuming_loop(self):
        while self._consuming:
            try:
                self.channel.start_consuming()
            except pika.exceptions.ConnectionClosedByBroker:
                logger.warning("Connection closed by broker, reconnecting...")
                self._reconnect()
                continue
            except pika.exceptions.AMQPChannelError as err:
                logger.error(f"Channel error: {str(err)}, recreating channel")
                self.channel = self.connection.channel()
                continue
            except pika.exceptions.AMQPConnectionError:
                logger.warning("Connection lost, reconnecting...")
                self._reconnect()
                continue
            except Exception as e:
                logger.error(f"Unexpected error in consuming loop: {str(e)}")
                break

    def close(self):
        try:
            self._consuming = False
            if hasattr(self, 'connection') and self.connection.is_open:
                self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")
