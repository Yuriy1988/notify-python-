import logging
import asyncio
import pytz
from datetime import datetime, timedelta

import utils
from config import config
from currency.parser import parse_currency, CurrencyError

__author__ = 'Kostel Serhii'


_log = logging.getLogger(__name__)


async def _report(text):
    await utils.send_email(email_to=config['ADMIN_EMAIL'], subject="XOPAY: Exchange rates update.", text=text)


async def _report_success(currency):
    formatted = '{from_currency}/{to_currency}:\t {rate}'.format
    text = 'Exchange rates was successfully updated.\n\n{rates}\n\nCommit time (UTC): {date_time}'
    await _report(text.format(rates="\n".join(map(formatted, currency)), date_time=datetime.utcnow()))


async def _report_error(error):
    text = 'Failed to upgrade the exchange rate!\n\nProblem description: {error}\n\nCommit time (UTC): {date_time}'
    await _report(text.format(error=error, date_time=datetime.utcnow()))


async def _update_currency():
    """
    Update currency data from specified sources and
    send notification to the xopay admin email.
    """
    _log.debug('Update currency exchange information')

    try:
        currency = await parse_currency()
    except CurrencyError as err:
        _log.error('Error load currency: %r', err)
        asyncio.ensure_future(_report_error(err))
        return

    url = utils.get_client_base_url() + '/currency/update'
    result = await utils.http_request(url, method='POST', body={'update': currency})

    if result is None:
        err = 'Wrong response from Admin Service.'
        _log.error('Error update currency: %r', err)
        asyncio.ensure_future(_report_error(err))
        return

    _log.info('Currency exchange information updated successfully')
    asyncio.ensure_future(_report_success(currency))


class CurrencyUpdateDaemon:
    """
    Schedule currency update.
    Default update at 00:00, 06:00, 12:00, 18:00 every day.
    Default Timezone: Europe/Riga (GMT+3)
    """

    def __init__(self, update_hours=(0, 6, 12, 18), timezone='Europe/Riga'):
        self._closing = False
        self._update_hours = update_hours
        self._timezone = timezone

    def start(self):
        asyncio.ensure_future(self._daemon_loop)

    def stop(self):
        self._closing = True

    def _get_next_update_timeout_sec(self):
        """ Return the number of seconds till next update time """
        now = datetime.now(tz=pytz.timezone(self._timezone))
        day_offset = now.replace(hour=0, minute=0, second=0, microsecond=0) - now

        update_time = (day_offset + timedelta(days=d, hours=h) for d in (0, 1) for h in self._update_hours)
        nearest = min((ut for ut in update_time if ut > 0))

        return nearest.total_seconds()

    async def _daemon_loop(self):
        """ Infinite update currency loop """
        while not self._closing:
            await asyncio.sleep(self._get_next_update_timeout_sec)
            try:
                await _update_currency()
            except Exception as err:
                _log.exception('Unexpected error while currency updating: %r', err)