import pytz
import logging
import asyncio
from datetime import datetime

import utils
from config import config

__author__ = 'Kostel Serhii'


_MAX_UPDATE_ATTEMPTS = 5

_log = logging.getLogger('xop.mq.handler')


async def _report_error(pay_id, error):
    text = 'Failed to update payment [{pay_id}] status!\n\n'\
           'Problem description:\n{error}\n\nCommit time (UTC): {timestamp}'
    text = text.format(pay_id=pay_id, error=error, timestamp=datetime.now(tz=pytz.utc))
    await utils.report_to_admin(subject="XOPAY: Transaction update error.", text=text)


async def _update_transaction_retry(pay_id, url, method, body):
    """ Retry transaction update """
    errors = []

    for attempt in range(_MAX_UPDATE_ATTEMPTS):

        await asyncio.sleep(2 ** attempt)

        attempt_msg = '(attempt: %d/%d)' % (attempt + 1, _MAX_UPDATE_ATTEMPTS)
        _log.info('Update payment %s with: [%r] %s', pay_id, body, attempt_msg)

        result, error = await utils.http_request(url=url, method=method, body=body)
        if result:
            _log.info('Payment %s updated successfully with: [%r]', pay_id, body)
            return

        errors.append(error)
        _log.error('Error update payment %s status! %s Retry after timeout...', pay_id, attempt_msg)

    _log.critical('ERROR! Payment %s NOT UPDATED!!!', pay_id)
    err_msg = 'Payment NOT UPDATED after %d attempts. \n\nAll errors: \n%s\n'
    asyncio.ensure_future(_report_error(pay_id, err_msg % (_MAX_UPDATE_ATTEMPTS, '\n'.join(errors))))


async def transaction_queue_handler(message):
    """
    Transaction status queue handler.
    Retry update on error.
    :param message: json dict with information from queue
    """
    pay_id, pay_status, redirect_url = message.get('id'), message.get('status'), message.get('redirect_url')
    if not pay_id or not pay_status:
        _log.error('Missing required fields in transaction queue message [%r]. Skip notify!', message)
        return

    url = config.get('CLIENT_BASE_URL') + '/payment/%s' % pay_id
    request_kwargs = dict(url=url, method='PUT', body={'status': pay_status, 'redirect_url': redirect_url})

    result, error = await utils.http_request(**request_kwargs)

    if error:
        _log.error('Error update payment %s status! Try again later in the background...', pay_id)
        asyncio.ensure_future(_report_error(pay_id, error))
        asyncio.ensure_future(_update_transaction_retry(pay_id, **request_kwargs))
        return

    _log.info('Payment %s updated successfully with status: %s', pay_id, pay_status)


async def email_queue_handler(message):
    """
    Send email queue handler.
    :param message: json dict with information from queue
    """
    if set(message.keys()) != {'email_to', 'subject', 'text'}:
        _log.error('Wrong fields in email queue request: [%r]. Skip notify!', message)
        return

    await utils.send_email(**message)


async def sms_queue_handler(message):
    """
    Send sms queue handler.
    :param message: json dict with information from queue
    """
    if set(message.keys()) != {'phone', 'text'}:
        _log.error('Wrong fields in sms queue request: [%r]. Skip notify!', message)
        return

    await utils.send_sms(**message)
