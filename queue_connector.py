import logging
import pika
import pika.adapters
from datetime import timedelta

from tornado import gen
from tornado.concurrent import Future
from tornado.queues import Queue

__author__ = 'Kostel Serhii'


class QueueConsumer(object):
    """
    Async connector of RabbitMQ to Tornado.
    * For Python 3.5 or higher.

    Example to use:

        from tornado.ioloop import IOLoop

        async def test(consumer):
            await consumer.connect()
            await consumer.declare_and_bind('queue_name')

            while True:
                msg = await consumer.get_message('queue_name')
                print('Test msg: %s' % msg)

        io_loop = IOLoop.current()
        consumer = QueueConsumer('amqp://guest:guest@localhost:5672/%2F', io_loop)

        try:
            io_loop.add_callback(test, consumer)
            io_loop.start()
        except KeyboardInterrupt:
            consumer.close()
            io_loop.add_timeout(timedelta(seconds=3), io_loop.stop)

    """

    MIN_RECONNECT_TIMEOUT_SEC = 1
    MAX_RECONNECT_TIMEOUT_SEC = 300

    FIFO_BUFFER_LIMIT = 1000

    _default_declare_kwargs = dict(passive=False, durable=True, exclusive=False, auto_delete=False, nowait=False)

    _log = logging.getLogger('queue_consumer')

    def __init__(self, parameters, io_loop=None):
        self._parameters = self._parse_parameters(parameters)
        self._io_loop = io_loop or IOLoop.current()

        self._reconnect_timeout_sec = self.MIN_RECONNECT_TIMEOUT_SEC

        self._closing = False
        self._connecting = False
        self._connected = False

        self._connection = None
        self._channel = None

        self._consumer_tags = dict()
        self._fifo_query_buffer = dict()

    @staticmethod
    def _parse_parameters(parameters):
        """
        Parse parameters for pika connection adapter.
        :param parameters: values for rabbitmq connection.
         Can be one of:
          - pika.ConnectionParameters object;
          - pika.URLParameters object;
          - dict with keys: host, port, virtual_host, username, password
          - url string: amqp://<username>:<password>@<host>:<port><virtual_host>
        :return: pika.ConnectionParameters or pika.URLParameters
        """
        if isinstance(parameters, (pika.ConnectionParameters, pika.URLParameters)):
            return parameters

        if isinstance(parameters, dict):
            return pika.ConnectionParameters(
                host=parameters['host'],
                port=parameters['port'],
                virtual_host=parameters['virtual_host'],
                credentials=pika.credentials.PlainCredentials(
                    username=parameters['username'],
                    password=parameters['password'],
                )
            )

        if isinstance(parameters, str):
            return pika.URLParameters(parameters)

    # Reconnection

    def _get_reconnect_timeout(self):
        """
        This function double reconnection timeout on every request
        to protect from frequent attempts to connect."""
        timeout_sec = self._reconnect_timeout_sec
        self._reconnect_timeout_sec = min(self._reconnect_timeout_sec * 2, self.MAX_RECONNECT_TIMEOUT_SEC)
        return timeout_sec

    def _reset_reconnect_timeout(self):
        """ Set reconnection timeout to start value. """
        self._reconnect_timeout_sec = self.MIN_RECONNECT_TIMEOUT_SEC

    def _reconnect_on_connection_closed(self, *args):
        """
        This function is called when an error or the connection is closed.
        If connection closed by itself - try to reconnect after timeout.
        When this method called by on_close_callback, args will be:
        - connection (pika.connection.Connection): the closed connection obj
        - reply_code (int): the server provided reply_code if given
        - reply_text (str): the server provided reply_text if given
        """
        if not self._closing:
            timeout_sec = self._get_reconnect_timeout()

            msg = 'Connection closed, reopening in %d seconds' % timeout_sec
            msg = msg + ' (code: %s,  reply: %s)' % tuple(args[1:3]) if len(args) >= 3 else msg
            self._log.warning(msg)

            self._connecting = False
            self._connected = False

            self._consumer_tags = dict()
            self._fifo_query_buffer = dict()

            self._io_loop.add_timeout(timedelta(seconds=timeout_sec), self.connect)

    # Connection

    def _open_connection(self):
        """ Create Tornado Connection and return on open future. """
        future = Future()

        pika.adapters.TornadoConnection(
            parameters=self._parameters,
            on_open_callback=future.set_result,
            on_open_error_callback=self._reconnect_on_connection_closed,
            on_close_callback=self._reconnect_on_connection_closed,
            stop_ioloop_on_close=False,
            custom_ioloop=self._io_loop)

        return future

    async def _close_connection(self):
        """ Wait for closing all consumers and then close the chanel """
        self._log.info('Closing connection')
        self._closing = True

        if self._channel:
            await gen.multi([self._cancel_consumer(tag) for tag in self._consumer_tags.values()])

            self._log.info('Closing the channel')
            self._channel.close()

    def close(self):
        """ Close connection to the RabbitMQ in a sync way. """
        self._io_loop.add_callback(self._close_connection)

    async def connect(self):
        """ Open connection with the RabbitMQ and then open chanel """
        if self._connecting or self._connected:
            self._log.info('Connection already created. Skip current attempt')
            return

        self._log.info('Open connection')
        self._connecting = True
        self._connection = await self._open_connection()

        self._connecting = False
        self._connected = True
        self._reset_reconnect_timeout()

        self._log.info('Open channel')
        self._channel = await self._open_channel()

    # Channel

    def _on_channel_closed(self, channel, reply_code, reply_text):
        """ On chanel close callback
        :param channel: the closed chanel obj
        :param int reply_code: the server provided reply_code if given
        :param str reply_text: the server provided reply_text if given
        """
        self._log.info('Channel closed')
        self._connection.close()

    def _open_channel(self):
        """ Open chanel and return on open future """
        future = Future()

        def on_channel_open(channel):
            channel.add_on_close_callback(self._on_channel_closed)
            future.set_result(channel)

        self._connection.channel(on_open_callback=on_channel_open)
        return future

    # Declare queue

    def _on_consumer_cancelled(self, method_frame):
        """
        Close chanel when consumer cancelled
        :param method_frame: method frame
        """
        self._log.info('Consumer was cancelled remotely, shutting down: %r', method_frame)
        if self._channel:
            self._channel.close()

    def _declare_queue(self, queue_name, **kwargs):
        """
        Declare queue and return on declared future
        :param queue_name: name of the queue to declare
        :param kwargs: pika chanel queue_declare additional parameters
        """
        future = Future()

        def on_channel_declared(method_frame):
            self._channel.add_on_cancel_callback(self._on_consumer_cancelled)
            future.set_result(method_frame)

        self._channel.queue_declare(on_channel_declared, **kwargs)

        return future

    # Consumer

    def _cancel_consumer(self, consumer_tag):
        """
        Cancel consumer and return on cancelled future
        :param consumer_tag: consumer tag
        """
        future = Future()

        if self._channel:
            self._log.info('Cancel consumer %s', consumer_tag)
            self._channel.basic_cancel(future.set_result, consumer_tag)
        else:
            future.set_result(None)

        return future

    async def unbind(self, queue_name):
        """
        Unbind from the queue
        :param queue_name: name of the queue to unbind
        """
        self._log.info('Unbind from the queue [%s] and remove messages from FIFO Buffer', queue_name)
        self._fifo_query_buffer.pop(queue_name, None)
        consumer_tag = self._consumer_tags.pop(queue_name, None)
        if consumer_tag:
            await self._cancel_consumer(consumer_tag)
        else:
            self._log.info('Not found the queue [%s] to unbind', queue_name)

    def _on_message_fabric(self, queue_name):
        """
        Create on message callback handler for specified queue
        :param queue_name: name of the queue to handle the message
        :return: on_message callback function
        """
        def _on_message(*args):
            """
            Queue messages handler.

            * WARNING: If FIFI BUFFER is full - current bind will be cancelled.

            :param args: channel, basic_deliver, properties, body
            """
            buffer = self._fifo_query_buffer.get(queue_name)
            if not buffer:
                self._log.warning('FIFO Buffer for [%s] queue is not created. Skip on message handler.', queue_name)
                return

            if buffer.qsize() > self.FIFO_BUFFER_LIMIT:
                self._log.warning('FIFO Buffer is full. Unbind from [%s] queue.', queue_name)
                self._io_loop.add_callback(self.unbind, queue_name)
            else:
                buffer.put_nowait(args)

        return _on_message

    def _bind_consumer(self, queue_name):
        """
        Start consuming queue and bind callback to the on message handler.
        Use FIFI QUEUE BUFFER to handle messages from RabbitMQ.
        If buffer not created yet - create it.
        Every queue has its own buffer.

        :param queue_name: name of the queue to bind
        """
        self._log.info('Bind to the queue [%s]', queue_name)

        if queue_name not in self._fifo_query_buffer:
            self._fifo_query_buffer[queue_name] = Queue(maxsize=self.FIFO_BUFFER_LIMIT)

        _on_message = self._on_message_fabric(queue_name)

        consumer_tag = self._channel.basic_consume(_on_message, queue_name)
        self._consumer_tags[queue_name] = consumer_tag

        return consumer_tag

    async def declare_and_bind(self, queue_name, **kwargs):
        """
        Declare and bind to the queue.
        Default declare arguments specified in _default_declare_kwargs dict.

        :param queue_name: name of the queue to declare and  bind
        :param kwargs: additional arguments to declare
        """
        declare_kwargs = self._default_declare_kwargs.copy()
        declare_kwargs.update(kwargs)
        await self._declare_queue(queue_name, **declare_kwargs)

        self._bind_consumer(queue_name)

    async def get_message(self, queue_name):
        """
        Get message from queue.
        All messages are buffered into FIFO message buffer.

        * WARNING: do not bind to queue without this function call.
        Internal FIFO Buffer may overflow and unbind from queue

        :param queue_name: name of the queue from witch reade the message
        :return: message body string
        """
        if queue_name not in self._fifo_query_buffer:
            raise ValueError('Declare and bind queue first.')

        buffer = self._fifo_query_buffer[queue_name]

        self._log.info('Waiting for message from [%s] queue.', queue_name)

        channel, basic_deliver, properties, body = await buffer.get()

        self._log.info('Received message # %s: %s', basic_deliver.delivery_tag, body)

        self._channel.basic_ack(basic_deliver.delivery_tag)
        buffer.task_done()

        return body


if __name__ == '__main__':

    from tornado.ioloop import IOLoop

    LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s')
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    params = dict(
        host='localhost',
        port=5672,
        virtual_host='/xopay',
        username='xopay_rabbit',
        password='5lf01xiOFwyMLvQrkzz7'
    )

    QUEUE_NAME = 'transactions_for_processing'

    async def test(consumer):
        print('Connect')
        await consumer.connect()
        print('Declare')
        await consumer.declare_and_bind(QUEUE_NAME)

        while True:
            print('Wait for message...')
            msg = await consumer.get_message(QUEUE_NAME)
            print('Test msg: %s' % msg)


    loop = IOLoop.current()
    consumer = QueueConsumer(params, loop)

    try:
        loop.add_callback(test, consumer)
        loop.start()
    except KeyboardInterrupt:
        consumer.close()
        loop.add_timeout(timedelta(seconds=3), loop.stop)
        print(' [*] Stopped')
