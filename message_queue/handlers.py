import logging
import asyncio

import utils

__author__ = 'Kostel Serhii'


_MAX_UPDATE_ATTEMPTS = 5

_log = logging.getLogger('mq.handler')


async def _update_transaction_retry(pay_id, url, method, body):
    """ Retry transaction update """

    for attempt in range(_MAX_UPDATE_ATTEMPTS):

        await asyncio.sleep(2 ** attempt)

        attempt_msg = '(attempt: %d/%d)' % (attempt + 1, _MAX_UPDATE_ATTEMPTS)
        _log.info('Update payment %s with: [%r] %s', pay_id, body, attempt_msg)

        result = await utils.http_request(url=url, method=method, body=body)
        if result is not None:
            _log.info('Payment %s updated successfully with: [%r]', pay_id, body)
            return

        _log.error('Error update payment %s status! %s Retry after timeout...', pay_id, attempt_msg)

    _log.critical('ERROR! Payment %s NOT UPDATED!!!', pay_id)


async def transaction_queue_handler(message):
    """
    Transaction status queue handler.
    Retry update on error.

    :param message: json dict with information from queue
    """
    pay_id, pay_status = message.get('id'), message.get('status')
    if not pay_id or not pay_status:
        _log.error('Missing required fields in transaction queue message [%r]. Skip notify!', message)
        return

    url = utils.get_client_base_url() + '/payment/%s' % pay_id
    request_kwargs = dict(url=url, method='PUT', body={'status': pay_status})

    result = await utils.http_request(**request_kwargs)

    if result is None:
        _log.error('Error update payment %s status! Try again later in the background...', pay_id)
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

