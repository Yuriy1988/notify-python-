import logging
import signal
import time
import tornado.web
from tornado.ioloop import IOLoop
from tornado.options import options, define
from tornado.httpserver import HTTPServer

__author__ = 'Kostel Serhii'

logging.basicConfig(format='[NOTIFY][%(levelname)s]|%(asctime)s| %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3

define("debug", default=True, help="run in debug mode", type=bool)
define("log_level", default='DEBUG', help="log level", type=str)
define("port", default=7461, help="run on the given port", type=int)


class Application(tornado.web.Application):
    """ Tornado server application. """

    def __init__(self):
        """ Configure handlers and settings. """

        handlers = [
           # (r"/api/notify/dev/payment/(?P<payment_id>[\w]+)'/?$", PaymentHandler),
        ]

        settings = dict(
            debug=True,
        )

        super(Application, self).__init__(handlers, **settings)


def shutdown(server):
    """ Stop server, wait for connection closed and stop IOLoop. """

    io_loop = IOLoop.current()
    logging.info('Stopping XOPay Notify Service...')
    server.stop()

    def finalize():
        io_loop.stop()
        logging.info('Service stopped!')

    if options.debug:
        finalize()
    else:
        io_loop.add_timeout(time.time() + MAX_WAIT_SECONDS_BEFORE_SHUTDOWN, finalize)


def main():
    """ Parse arguments, update settings, start server and start IOLoop. """
    options.parse_command_line()

    # configure logger level
    logging.getLogger().setLevel('DEBUG')

    app = Application()

    logging.info('Starting XOPay Notify Service on http://127.0.0.1:{port}/'.format(port=options.port))

    server = HTTPServer(app)
    server.listen(options.port)

    signal.signal(signal.SIGINT, lambda sig, frame: shutdown(server))
    signal.signal(signal.SIGTERM, lambda sig, frame: shutdown(server))

    IOLoop.current().start()


if __name__ == "__main__":
    main()
