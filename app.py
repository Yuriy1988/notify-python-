#!venv/bin/python
import logging
import argparse
import asyncio

from config import config
from mq_connect import QueueListener
from transaction import transaction_queue_handler
from notify import email_queue_handler, sms_queue_handler

__author__ = 'Kostel Serhii'


def shutdown(loop, queue_connect):
    """
    Stop daemons and all process.
    Wait for connection closed and stop IOLoop.

    :param loop: current loop
    :param queue_connect: connection to the RabbitMQ
    """
    log = logging.getLogger('shutdown')

    log.info('Stopping XOPay Notify Service...')

    loop.run_until_complete(queue_connect.close())

    log.info('Shutdown tasks')
    for task in asyncio.Task.all_tasks():
        task.cancel()

    loop.close()
    logging.info('XOPay Notify Service Stopped!')


def main():
    """ Parse arguments, update settings and start main loop. """
    parser = argparse.ArgumentParser(description='XOPay Notify Service.', allow_abbrev=False)
    parser.add_argument('--debug', action='store_true', default=False, help='run in debug mode')

    args = parser.parse_args()
    if args.debug:
        config.load_debug_config()
    else:
        config.load_production_config()

    logging.basicConfig(format=config['LOG_FORMAT'], datefmt='%Y-%m-%d %H:%M:%S', level=config['LOG_LEVEL'])

    log = logging.getLogger('main')
    log.info('Starting XOPay Notify Service...')
    if config['DEBUG']:
        log.info('Debug mode is active!')

    loop = asyncio.get_event_loop()

    queue_connect = QueueListener(queue_handlers=[
        (config['QUEUE_TRANSACTION'], transaction_queue_handler),
        (config['QUEUE_EMAIL'], email_queue_handler),
        (config['QUEUE_SMS'], sms_queue_handler),
    ])
    asyncio.ensure_future(queue_connect.connect())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        shutdown(loop, queue_connect)


if __name__ == "__main__":
    main()
