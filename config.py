__author__ = 'Kostel Serhii'


_default = dict(
    PORT=7461,
)

_debug = dict(
    DEBUG=True,
    LOG_LEVEL='DEBUG',

    WAIT_BEFORE_SHUTDOWN_SEC=0,
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
