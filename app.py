#!venv/bin/python
import logging
import argparse
import asyncio

from config import config
import message_queue.handlers
from message_queue.connect import QueueListener
from currency.daemon import CurrencyUpdateDaemon

__author__ = 'Kostel Serhii'


def shutdown(loop, queue_connect, currency_daemon):
    """
    Stop daemons and all process.
    Wait for connection closed and stop IOLoop.

    :param loop: current loop
    :param queue_connect: connection to the RabbitMQ
    """
    log = logging.getLogger('shutdown')

    log.info('Stopping XOPay Notify Service...')

    loop.run_until_complete(queue_connect.close())

    currency_daemon.stop()

    log.info('Shutdown tasks')
    for task in asyncio.Task.all_tasks():
        task.cancel()

    loop.close()
    log.info('XOPay Notify Service Stopped!')


def main():
    """ Parse arguments, update settings and start main loop. """
    parser = argparse.ArgumentParser(description='XOPay Notify Service.', allow_abbrev=False)
    parser.add_argument('--debug', action='store_true', default=False, help='run in debug mode')

    args = parser.parse_args()
    if args.debug:
        config.load_debug_config()
    else:
        config.load_production_config()

    log = logging.getLogger('main')
    log.info('Starting XOPay Notify Service...')
    if config['DEBUG']:
        log.info('Debug mode is active!')

    loop = asyncio.get_event_loop()

    queue_connect = QueueListener(queue_handlers=[
        (config['QUEUE_TRANS_STATUS'], message_queue.handlers.transaction_queue_handler),
        (config['QUEUE_EMAIL'], message_queue.handlers.email_queue_handler),
        (config['QUEUE_SMS'], message_queue.handlers.sms_queue_handler),
    ])
    asyncio.ensure_future(queue_connect.connect())

    currency_daemon = CurrencyUpdateDaemon(config['CURRENCY_UPDATE_HOURS'], config['CURRENCY_TIMEZONE'])
    currency_daemon.start()

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        shutdown(loop, queue_connect, currency_daemon)


if __name__ == "__main__":
    main()
