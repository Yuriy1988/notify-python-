import logging
from tornado.gen import maybe_future

from config import config

__author__ = 'Kostel Serhii'

log = logging.getLogger(__name__)


async def email_handler(message):
    pass


async def sms_handler(message):
    pass


async def transaction_handler(message):
    pass


async def _listener_daemon(queue_connector, queue_name, handler_callback):
    log.info('Declare and bind to the [%s] queue' % queue_name)
    await queue_connector.declare_and_bind(queue_name)

    while not queue_connector.closing:
        log.info('Waiting for [%s] queue message' % queue_name)
        message = await queue_connector.get_message(queue_name)

        log.info('Get message from the [%s] queue: %s' % (queue_name, message))
        await maybe_future(handler_callback(message))


async def start_consumer(queue_connector, io_loop):
    log.info('Connecting to RabbitMQ...')
    await queue_connector.connect()
    log.info('Connected to the RabbitMQ. Starting listeners...')

    io_loop.spawn_callback(_listener_daemon, queue_connector, config['QUEUE_EMAIL'], email_handler)
    io_loop.spawn_callback(_listener_daemon, queue_connector, config['QUEUE_SMS'], sms_handler)
    io_loop.spawn_callback(_listener_daemon, queue_connector, config['QUEUE_TRANSACTION'], transaction_handler)
