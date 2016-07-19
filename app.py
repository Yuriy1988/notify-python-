#!venv/bin/python
import logging
import asyncio
import motor.motor_asyncio
from aiohttp import web

from config import config
import message_queue.delivery_handlers
from message_queue.connect import QueueListener
from notification import handlers as nh, processing as np
from currency.daemon import CurrencyUpdateDaemon

__author__ = 'Kostel Serhii'


_log = logging.getLogger('xop.main')


async def shutdown(app):
    """
    Close connections, stop daemons and all process.
    :param app: web server app
    """
    _log.info('Stopping XOPay Notify Service...')

    queue_connect = app.get('queue_connect')
    if queue_connect:
        await queue_connect.close()

    currency_daemon = app.get('currency_daemon')
    if currency_daemon:
        currency_daemon.stop()

    _log.info('Shutdown tasks')
    tasks = asyncio.Task.all_tasks()
    if tasks:
        for task in tasks:
            task.cancel()
        try:
            await asyncio.wait(tasks)
        except Exception:
            pass

    _log.info('XOPay Notify Service Stopped!')


def register_handlers(app):
    """
    Register server handlers with urls.
    :param app: web server app
    """
    url_prefix = '/api/notify/{API_VERSION}'.format(**config)

    app.router.add_route('GET', url_prefix + '/notifications', nh.notifications_list)
    app.router.add_route('POST', url_prefix + '/notifications', nh.notification_create)
    app.router.add_route('GET', url_prefix + '/notifications/{notify_id}', nh.notification_detail)
    app.router.add_route('PUT', url_prefix + '/notifications/{notify_id}', nh.notification_update)
    app.router.add_route('DELETE', url_prefix + '/notifications/{notify_id}', nh.notification_delete)


def create_app():
    """Create server application and all necessary services."""
    app = web.Application()
    app['config'] = config

    register_handlers(app)

    motor_client = motor.motor_asyncio.AsyncIOMotorClient()
    db = motor_client[config['DB_NAME']]
    app['db'] = db

    notify_processor = np.NotifyProcessing(
        db=db,
        admin_base_url=config['ADMIN_BASE_URL']
    )
    notify_processor.start()
    app['notify_processor'] = notify_processor

    queue_connect = QueueListener(
        queue_handlers=[
            (config['QUEUE_TRANS_STATUS'], message_queue.delivery_handlers.transaction_queue_handler),
            (config['QUEUE_EMAIL'], message_queue.delivery_handlers.email_queue_handler),
            (config['QUEUE_SMS'], message_queue.delivery_handlers.sms_queue_handler),
            (config['QUEUE_REQUEST'], notify_processor.request_queue_handler),
        ],
        connect_parameters=config
    )
    queue_connect.start()
    app['queue_connect'] = queue_connect

    currency_daemon = CurrencyUpdateDaemon(
        admin_base_url=config['ADMIN_BASE_URL'],
        update_hours=config['CURRENCY_UPDATE_HOURS'],
        timezone=config['CURRENCY_TIMEZONE']
    )
    currency_daemon.start()
    app['currency_daemon'] = currency_daemon

    return app


if __name__ == "__main__":

    web_app = create_app()
    web_app.on_shutdown.append(shutdown)

    _log.info('Starting XOPay Notify Service...')
    if config['DEBUG']:
        _log.warning('Debug mode is active!')

    web.run_app(web_app, host='127.0.0.1', port=config['PORT'])
