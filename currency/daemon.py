import logging
import asyncio
import pytz
from datetime import datetime, timedelta

import utils
from config import config
from currency.parser import parse_currency, CurrencyError

__author__ = 'Kostel Serhii'


_log = logging.getLogger('cur.daemon')


class CurrencyUpdateDaemon:
    """
    Schedule currency update.
    Default update at 00:00, 06:00, 12:00, 18:00 every day.
    Default Timezone: Europe/Riga (GMT+3)
    """

    def __init__(self, update_hours=(0,), timezone='UTC'):
        self._closing = False
        self._update_hours = update_hours
        self._timezone = timezone

    def start(self):
        _log.info('Start currency update daemon')
        asyncio.ensure_future(self._daemon_loop())

    def stop(self):
        _log.info('Start currency update daemon')
        self._closing = True

    async def _update_currency(self):
        """
        Update currency data from specified sources and
        send notification to the xopay admin email.
        """
        _log.debug('Update currency exchange information')

        try:
            currency = await parse_currency()
        except CurrencyError as err:
            _log.error('Error load currency')
            asyncio.ensure_future(self._report_error('Error load currency:\n%r' % err))
            return

        url = config.get_admin_base_url() + '/currency/update'
        result, error = await utils.http_request(url, method='POST', body={'update': currency})

        if error:
            _log.error('Error update currency')
            err_msg = 'Error update currency.\nWrong response from Admin Service.\n%s' % error
            asyncio.ensure_future(self._report_error(err_msg))
            return

        _log.info('Currency exchange information updated successfully')
        asyncio.ensure_future(self._report_success(currency))

    @staticmethod
    async def _report(text):
        await utils.send_email(email_to=config['ADMIN_EMAIL'], subject="XOPAY: Exchange rates update.", text=text)

    async def _report_success(self, currency):
        formatted = '{from_currency}/{to_currency}:\t {rate}'.format
        text = 'Exchange rates was successfully updated.\n\n{rates}\n\nCommit time (UTC): {timestamp}'
        timestamp = datetime.now(tz=pytz.timezone(self._timezone))
        await self._report(text.format(rates="\n".join(map(formatted, currency)), timestamp=timestamp))

    async def _report_error(self, error):
        text = 'Failed to upgrade the exchange rate!\n\nProblem description:\n{error}\n\nCommit time (UTC): {timestamp}'
        timestamp = datetime.now(tz=pytz.timezone(self._timezone))
        await self._report(text.format(error=error, timestamp=timestamp))

    def _get_next_update_timeout_sec(self):
        """ Return the number of seconds till next update time """
        now = datetime.now(tz=pytz.timezone(self._timezone))
        day_offset = now.replace(hour=0, minute=0, second=0, microsecond=0) - now

        update_time = (day_offset + timedelta(days=d, hours=h) for d in (0, 1) for h in self._update_hours)
        nearest = min((ut for ut in update_time if ut > timedelta(minutes=30)))

        return round(nearest.total_seconds())

    async def _daemon_loop(self):
        """ Infinite update currency loop """
        while not self._closing:
            try:
                await asyncio.sleep(self._get_next_update_timeout_sec())
                await self._update_currency()
            except Exception as err:
                _log.exception('Unexpected error while currency updating: %r', err)
