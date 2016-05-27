#!venv/bin/python
import logging
import logging.handlers
import argparse
import asyncio

from config import config
import message_queue.handlers
from message_queue.connect import QueueListener
from currency.daemon import CurrencyUpdateDaemon

__author__ = 'Kostel Serhii'


def logger_configure(log_config):

    if 'LOG_FILENAME' in log_config:
        log_handler = logging.handlers.RotatingFileHandler(
            filename=log_config['LOG_FILENAME'],
            maxBytes=log_config['LOG_MAX_BYTES'],
            backupCount=log_config['LOG_BACKUP_COUNT'],
            encoding='utf8',
        )
    else:
        log_handler = logging.StreamHandler()

    log_formatter = logging.Formatter(fmt=log_config['LOG_FORMAT'], datefmt=log_config['LOG_DATE_FORMAT'])
    log_handler.setFormatter(log_formatter)

    # root logger
    logging.getLogger('').addHandler(log_handler)
    logging.getLogger('').setLevel(log_config['LOG_ROOT_LEVEL'])

    # local logger
    logging.getLogger(log_config.get('LOG_BASE_NAME', '')).setLevel(log_config['LOG_LEVEL'])


def shutdown(loop, queue_connect, currency_daemon):
    """
    Stop daemons and all process.
    Wait for connection closed and stop IOLoop.

    :param loop: current loop
    :param queue_connect: connection to the RabbitMQ
    :param currency_daemon: currency update scheduler
    """
    log = logging.getLogger('xop.shutdown')

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

    logger_configure(config)

    log = logging.getLogger('xop.main')
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
