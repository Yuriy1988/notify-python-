__author__ = 'Kostel Serhii'


_default = dict(
    PORT=7461,

    QUEUE_HOST='127.0.01',
    QUEUE_PORT=5672,
    QUEUE_USERNAME='xopay_rabbit',
    QUEUE_PASSWORD='5lf01xiOFwyMLvQrkzz7',
    QUEUE_VIRTUAL_HOST='/xopay',

    QUEUE_EMAIL='notify_email',
    QUEUE_SMS='notify_sms',
    QUEUE_TRANSACTION='transactions_status',

    CLIENT_HOST='http://127.0.0.1:7254',
    CLIENT_API_VERSION='dev',
)

_debug = dict(
    DEBUG=True,
    LOG_LEVEL='DEBUG',

    WAIT_BEFORE_SHUTDOWN_SEC=1,
)

_production = dict(
    DEBUG=False,
    LOG_LEVEL='INFO',

    WAIT_BEFORE_SHUTDOWN_SEC=3,
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
