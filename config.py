_default = dict(
    PORT=7461,

    QUEUE_HOST='127.0.0.1',
    QUEUE_PORT=5672,
    QUEUE_USERNAME='xopay_rabbit',
    QUEUE_PASSWORD='5lf01xiOFwyMLvQrkzz7',
    QUEUE_VIRTUAL_HOST='/xopay',

    QUEUE_TRANSACTION='transactions_status',
    QUEUE_EMAIL='notify_email',
    QUEUE_SMS='notify_sms',

    CURRENCY_UPDATE_HOURS=(0, 6, 12, 18),
    CURRENCY_TIMEZONE='Europe/Riga',

    # TODO: add request to the admin service to get admin user email
    ADMIN_EMAIL = "dpixelstudio@gmail.com",

    LOG_FORMAT='[NOTIFY][%(levelname)s][%(name)s]|%(asctime)s| %(message)s'
)

_debug = dict(
    DEBUG=True,

    LOG_LEVEL='DEBUG',

    CLIENT_HOST='http://127.0.0.1:7254',
    CLIENT_API_VERSION='dev',

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

    def _load(self, loaded_config):
        for key, val in loaded_config.items():
            self[key] = val

    def load_debug_config(self):
        self._load(_debug)

    def load_production_config(self):
        self._load(_production)

config = _Config(_default)
