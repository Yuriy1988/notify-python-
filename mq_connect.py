import logging
import aioamqp
import asyncio

from config import config

__author__ = 'Kostel Serhii'


class _QueueConnect(object):
    """
    Async connector to RabbitMQ.
    * For Python 3.5 or higher.
    """

    MIN_RECONNECT_TIMEOUT_SEC = 1
    MAX_RECONNECT_TIMEOUT_SEC = 300

    _default_connect_params = dict(
        host=config['QUEUE_HOST'],
        port=config['QUEUE_PORT'],
        login=config['QUEUE_USERNAME'],
        password=config['QUEUE_PASSWORD'],
        virtualhost=config['QUEUE_VIRTUAL_HOST']
    )
    _default_declare_params= dict(
        passive=False,
        durable=True,
        exclusive=False,
        auto_delete=False,
        nowait=False
    )

    _log = logging.getLogger(__name__)

    def __init__(self, connect_parameters=None):
        """
        Create RabbitMQ Async Queue Connection
        :param dict connect_parameters: dict with keys: host, port, login, password, virtualhost
        """
        self._connect_params = connect_parameters or self._default_connect_params

        self._waiter = asyncio.Event()
        self._transport = None
        self._protocol = None

        self._closing = False

        self._reconnect_timeout_sec = self.MIN_RECONNECT_TIMEOUT_SEC

    async def connect(self):
        """
        Create async connection to the RabbitMQ, chanel and queue.
        Start unfinished loop.
        Try to reconnect after connection error.
        """

        while not self._closing:

            await asyncio.sleep(self._get_reconnect_timeout())

            try:
                self._transport, self._protocol = await aioamqp.connect(**self._connect_params)
            except aioamqp.AioamqpException as err:
                self._log.error("Queue connection error: %r \nReconnecting...", err)
                continue

            self._log.info('Connected to the RabbitMQ')

            try:
                await self._chanel_connection()
            except aioamqp.AioamqpException as err:
                self._log.error("Chanel connection error: %r \nReconnecting...", err)
                continue

            self._reset_reconnect_timeout()

            self._log.info('Start queue connection loop')
            await self._waiter.wait()

        logging.info('Queue connection loop has been finished!')

    async def close(self):
        """ Close connection to the RabbitMQ """
        self._log.info('Close queue connection')
        self._closing = True
        self._waiter.set()

        if self._protocol:
            await self._protocol.close()

        if self._transport:
            self._transport.close()

    async def _chanel_connection(self):
        """
        Async chanel connection method.
        Add here connection to the chanel (or many channels),
        declare and bind to the queue and/or exchange,
        start basic operations.
        """
        raise NotImplementedError('Queue chanel not created')

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


class QueueListener(_QueueConnect):
    """
    Async RabbitMQ listener (consumer)
    """
    def __init__(self, queue_handlers, connect_parameters=None):
        """
        Create RabbitMQ Async Queue Listener
        :param list queue_handlers: list with tuples (queue_name, async on_msg_callback)
        :param dict connect_parameters: dict with keys: host, port, login, password, virtualhost
        """
        self._queue_handlers = queue_handlers
        super().__init__(connect_parameters)

    async def _chanel_connection(self):
        """ Declare queues and register on message callback handlers """

        if not self._transport or not self._protocol:
            raise Exception('Queue connection missing')

        for queue_name, on_msg_callback in self._queue_handlers:
            callback = self._wrap_on_msg_callback_with_ack(on_msg_callback)

            channel = await self._protocol.channel()
            await channel.queue_declare(queue_name=queue_name, durable=True)
            await channel.basic_consume(callback, queue_name=queue_name)

    @classmethod
    def _wrap_on_msg_callback_with_ack(cls, callback):
        """
        Get on message callback function, make it async and
        wrap with basic queue ack after function end.
        :param callback: on message handler
        :return: async callback with ack
        """
        if not asyncio.iscoroutinefunction(callback):
            callback = asyncio.coroutine(callback)

        async def _on_message(channel, body, envelope, properties):
            cls._log.info('Received message #%s: %r', envelope.delivery_tag, body)

            await callback(body)

            cls._log.debug('Send message #%s ack', envelope.delivery_tag)
            await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)

        return _on_message


if __name__ == '__main__':

    async def on_message(body):
        logging.info('Get message: %r', body)

    loop = asyncio.get_event_loop()

    queue_daemon = QueueListener(queue_handlers=[
        (config['QUEUE_TRANSACTION'], on_message)])

    asyncio.ensure_future(queue_daemon.connect())

    try:
        logging.info(' [*] Start')
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    logging.info(' [*] Stop queue daemon')
    loop.run_until_complete(queue_daemon.close())

    logging.info(' [*] Shutdown tasks')
    for task in asyncio.Task.all_tasks():
        task.cancel()

    logging.info(' [*] Stopped')
    loop.close()
