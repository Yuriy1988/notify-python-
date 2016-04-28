import logging
from json.decoder import JSONDecodeError
from tornado.escape import json_decode, json_encode
from tornado.httpclient import AsyncHTTPClient, HTTPError

from config import config

__author__ = 'Kostel Serhii'

log = logging.getLogger(__name__)

_http_client = AsyncHTTPClient()


async def email_handler(message):
    pass


async def sms_handler(message):
    pass


async def transaction_handler(message):
    try:
        payment = json_decode(message)
        pay_id, pay_status = payment['id'], payment['status']
    except (JSONDecodeError, TypeError, KeyError) as err:
        log.warning('Wrong transaction message [{}]: {}'.format(message, err))
        return

    payment_update_url = '{host}/api/client/{version}/payment/{pay_id}'.format(
        host=config['CLIENT_HOST'], version=config['CLIENT_API_VERSION'], pay_id=pay_id)

    body = json_encode({'status': pay_status})
    headers = {"Content-Type": "application/json"}

    # TODO: if server not found - try later
    try:
        log.info('Update payment {} status: [{}]'.format(pay_id, pay_status))
        res = await _http_client.fetch(payment_update_url, method='PUT', body=body, headers=headers)
    except HTTPError as err:
        log.warning('HTTP Error on payment {} status update: {}'.format(pay_id, err))
    except Exception as err:
        log.warning('Unexpected exception on payment {} update: {}'.format(pay_id, err))


async def _listener_daemon(queue_connector, queue_name, handler_callback):
    log.info('Declare and bind to the [%s] queue' % queue_name)
    await queue_connector.declare_and_bind(queue_name)

    while not queue_connector.closing:
        log.info('Waiting for [%s] queue message' % queue_name)
        message = await queue_connector.get_message(queue_name)

        log.info('Get message from the [%s] queue: %s' % (queue_name, message))
        await handler_callback(message)


async def start_consumer(queue_connector, io_loop):
    log.info('Connecting to RabbitMQ...')
    await queue_connector.connect()
    log.info('Connected to the RabbitMQ. Starting listeners...')

    # io_loop.spawn_callback(_listener_daemon, queue_connector, config['QUEUE_EMAIL'], email_handler)
    # io_loop.spawn_callback(_listener_daemon, queue_connector, config['QUEUE_SMS'], sms_handler)
    io_loop.spawn_callback(_listener_daemon, queue_connector, config['QUEUE_TRANSACTION'], transaction_handler)
