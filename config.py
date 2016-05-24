import logging
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

    # TODO: add request to the admin service to get admin user email
    ADMIN_EMAIL="serhii.kostel@digitaloutlooks.com",

    LOG_FORMAT='NOTIFY | %(levelname)-6.6s | %(name)-10.10s | %(asctime)s | %(message)s',
)

_debug = dict(
    DEBUG=True,

    LOG_LEVEL='DEBUG',

    CLIENT_HOST='http://127.0.0.1:7254',
    CLIENT_API_VERSION='dev',

    ADMIN_HOST='http://127.0.0.1:7128',
    ADMIN_API_VERSION='dev',

    MAIL_SERVER="smtp.gmail.com",
    MAIL_USERNAME="daniel.omelchenko@digitaloutlooks.com",
    MAIL_PASSWORD="Po03yeFGd54c9jHq",
    MAIL_DEFAULT_SENDER="daniel.omelchenko@digitaloutlooks.com",

)

_production = dict(
    DEBUG=False,

    LOG_LEVEL='INFO',

    CLIENT_HOST='https://xopay.digitaloutlooks.com',
    CLIENT_API_VERSION='dev',

    ADMIN_HOST='https://xopay.digitaloutlooks.com',
    ADMIN_API_VERSION='dev',

    # TODO: change production settings
    MAIL_SERVER="smtp.gmail.com",
    MAIL_USERNAME="daniel.omelchenko@digitaloutlooks.com",
    MAIL_PASSWORD="Po03yeFGd54c9jHq",
    MAIL_DEFAULT_SENDER="daniel.omelchenko@digitaloutlooks.com",

)


class _Config(dict):
    """
    Load settings lazily.
    """
    def _update_log_config(self):
        logging.basicConfig(format=config['LOG_FORMAT'], datefmt='%d.%m %H:%M:%S', level=config['LOG_LEVEL'])

    def _load(self, loaded_config):
        for key, val in loaded_config.items():
            self[key] = val
        self._update_log_config()

    def load_debug_config(self):
        self._load(_debug)

    def load_production_config(self):
        self._load(_production)

    def get_client_base_url(self):
        return '{CLIENT_HOST}/api/client/{CLIENT_API_VERSION}'.format(**self)

    def get_admin_base_url(self):
        return '{ADMIN_HOST}/api/admin/{ADMIN_API_VERSION}'.format(**self)

config = _Config(_default)
