import os
import argparse
import logging
import logging.handlers
from datetime import timedelta


_default = dict(
    PORT=7461,

    QUEUE_HOST='127.0.0.1',
    QUEUE_PORT=5672,
    QUEUE_USERNAME='xopay_rabbit',
    QUEUE_PASSWORD='5lf01xiOFwyMLvQrkzz7',
    QUEUE_VIRTUAL_HOST='/xopay',

    QUEUE_TRANS_STATUS='transactions_status',
    QUEUE_EMAIL='notify_email',
    QUEUE_SMS='notify_sms',

    CURRENCY_UPDATE_HOURS=(0, 6, 12, 18),
    CURRENCY_TIMEZONE='Europe/Riga',

    AUTH_ALGORITHM='HS512',
    AUTH_KEY='PzYs2qLh}2$8uUJbBnWB800iYKe5xdYqItRNo7@38yW@tPDVAX}EV5V31*ZK78QS',
    AUTH_TOKEN_LIFE_TIME=timedelta(minutes=30),
    AUTH_SYSTEM_USER_ID='xopay.notify',

    LOG_BASE_NAME='xop',
    LOG_FORMAT=' %(levelname)-6.6s | NOTIFY | %(name)-15.15s | %(asctime)s | %(message)s',
    LOG_DATE_FORMAT='%d.%m %H:%M:%S'
)

_debug = dict(
    DEBUG=True,

    LOG_ROOT_LEVEL='DEBUG',
    LOG_LEVEL='DEBUG',

    CLIENT_BASE_URL='http://127.0.0.1:7254/api/client/dev',
    ADMIN_BASE_URL='http://127.0.0.1:7254/api/admin/dev',

    MAIL_SERVER="smtp.gmail.com",
    MAIL_USERNAME="daniel.omelchenko@digitaloutlooks.com",
    MAIL_PASSWORD="Po03yeFGd54c9jHq",
    MAIL_DEFAULT_SENDER="daniel.omelchenko@digitaloutlooks.com",

)

_production = dict(
    DEBUG=False,

    LOG_ROOT_LEVEL='INFO',
    LOG_LEVEL='INFO',

    LOG_FILE='/var/log/xopay/xopay.log',
    LOG_MAX_BYTES=10*1024*1024,
    LOG_BACKUP_COUNT=10,

    CLIENT_BASE_URL='https://xopay.digitaloutlooks.com/api/client/dev',
    ADMIN_BASE_URL='https://xopay.digitaloutlooks.com/api/admin/dev',

    # TODO: change production settings
    MAIL_SERVER="smtp.gmail.com",
    MAIL_USERNAME="daniel.omelchenko@digitaloutlooks.com",
    MAIL_PASSWORD="Po03yeFGd54c9jHq",
    MAIL_DEFAULT_SENDER="daniel.omelchenko@digitaloutlooks.com",

)


def logger_configure(log_config):

    if 'LOG_FILE' in log_config and os.access(os.path.dirname(log_config['LOG_FILE']), os.W_OK):
        log_handler = logging.handlers.RotatingFileHandler(
            filename=log_config['LOG_FILE'],
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


class _Config(dict):
    """
    Load settings lazily.
    """
    def __init__(self, *args, **kwargs):
        super(_Config, self).__init__(*args, **kwargs)
        self._load_config_from_args()

    def _load_config_from_args(self):
        parser = argparse.ArgumentParser(description='XOPay Notify Service.', allow_abbrev=False)
        parser.add_argument('--debug', action='store_true', default=False, help='run in debug mode')

        args = parser.parse_args()
        if args.debug:
            self.load_debug_config()
        else:
            self.load_production_config()

    def _load(self, loaded_config):
        self.update(loaded_config)
        logger_configure(self)

    def load_debug_config(self):
        self._load(_debug)

    def load_production_config(self):
        self._load(_production)

config = _Config(_default)
