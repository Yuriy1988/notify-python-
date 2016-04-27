import logging
import signal
from datetime import timedelta

import tornado.web
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.options import options, define

from config import config

__author__ = 'Kostel Serhii'


LOG_FORMAT = '[NOTIFY][%(levelname)s]|%(asctime)s| %(message)s'
logging.basicConfig(format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S', level='DEBUG')

log = logging.getLogger(__name__)

define("debug", default=False, help="run in debug mode", type=bool)


class Application(tornado.web.Application):
    """ Tornado server application. """

    def __init__(self):
        """ Configure handlers and settings. """

        handlers = [
           # (r"/api/notify/dev/payment/(?P<payment_id>[\w]+)'/?$", PaymentHandler),
        ]

        settings = dict(
            debug=config['DEBUG'],
        )

        super(Application, self).__init__(handlers, **settings)


def shutdown(http_server):
    """
    Stop server and all process.
    Wait for connection closed and stop IOLoop.

    :param http_server: server instance to stop
    """
    io_loop = IOLoop.current()

    log.info('Stopping XOPay Notify Service...')
    http_server.stop()

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

    # configure logger level
    log.setLevel(config['LOG_LEVEL'])

    log.info('Starting XOPay Notify Service')
    if config['DEBUG']:
        log.info('Debug mode is active!!')

    app = Application()

    log.info('Run HTTP Notify Server on http://127.0.0.1:{port}/'.format(port=config['PORT']))

    server = HTTPServer(app)
    server.listen(config['PORT'])

    signal.signal(signal.SIGINT, lambda sig, frame: shutdown(server))
    signal.signal(signal.SIGTERM, lambda sig, frame: shutdown(server))

    IOLoop.current().start()


if __name__ == "__main__":
    main()
