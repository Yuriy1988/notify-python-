import logging
import signal
from datetime import timedelta

from tornado.ioloop import IOLoop
from tornado.options import options, define
from tornado.httpserver import HTTPServer
from tornado.web import Application

import daemons
from config import config
from queue_connector import QueueConsumer

__author__ = 'Kostel Serhii'

define("debug", default=False, help="run in debug mode", type=bool)

LOG_FORMAT = '[NOTIFY][%(levelname)s]|%(asctime)s| %(message)s'
logging.basicConfig(format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S', level='DEBUG')

log = logging.getLogger(__name__)


class App(Application):
    """ Tornado server application. """

    def __init__(self):
        """ Configure handlers and settings. """
        handlers = [
            # (r'/api/notify/dev/payment/(?P<payment_id>[\w]+)/?$', TransactionHandler),
        ]
        settings = dict(debug=config['DEBUG'])
        super(App, self).__init__(handlers, **settings)


def shutdown(http_server, queue_connect):
    """
    Stop server and all process.
    Wait for connection closed and stop IOLoop.

    :param http_server: server instance to stop
    :param queue_connect: connection to the RabbitMQ
    """
    io_loop = IOLoop.current()

    log.info('Stopping XOPay Notify Service...')

    http_server.stop()
    queue_connect.close()

    def finalize():
        io_loop.stop()
        log.info('Service stopped!')

    wait_sec = config['WAIT_BEFORE_SHUTDOWN_SEC']
    if wait_sec:
        io_loop.add_timeout(timedelta(seconds=wait_sec), finalize)
    else:
        finalize()


def main():
    """ Parse arguments, update settings, start server and start IOLoop. """

    options.parse_command_line()

    if options.debug:
        config.load_debug_config()
    else:
        config.load_production_config()

    log.setLevel(config['LOG_LEVEL'])

    log.info('Starting XOPay Notify Service')
    if config['DEBUG']:
        log.info('Debug mode is active!!')

    app = App()
    io_loop = IOLoop.current()

    log.info('Run HTTP Notify Server on http://127.0.0.1:{port}/'.format(port=config['PORT']))

    server = HTTPServer(app)
    server.listen(config['PORT'])

    queue_connection_params = dict(
        host=config['QUEUE_HOST'],
        port=config['QUEUE_PORT'],
        virtual_host=config['QUEUE_VIRTUAL_HOST'],
        username=config['QUEUE_USERNAME'],
        password=config['QUEUE_PASSWORD']
    )

    queue_connect = QueueConsumer(queue_connection_params, io_loop)
    io_loop.spawn_callback(daemons.start_consumer, queue_connect, io_loop)

    signal.signal(signal.SIGINT, lambda sig, frame: shutdown(server, queue_connect))
    signal.signal(signal.SIGTERM, lambda sig, frame: shutdown(server, queue_connect))

    io_loop.start()


if __name__ == "__main__":
    main()
