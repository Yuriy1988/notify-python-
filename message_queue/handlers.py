import logging
import asyncio

import utils

__author__ = 'Kostel Serhii'


_MAX_UPDATE_ATTEMPTS = 5

_log = logging.getLogger(__name__)


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

    request_kwargs = dict(
        method='PUT',
        url=utils.get_client_base_url() + '/payment/' + str(pay_id),
        body={'status': pay_status}
    )

    for attempt in range(1, _MAX_UPDATE_ATTEMPTS+1):
        _log.info('Update payment %s status: [%s] (attempt: %d/%d)', pay_id, pay_status, attempt, _MAX_UPDATE_ATTEMPTS)

        result = await utils.http_request(**request_kwargs)
        if result is not None:
            _log.info('Payment %s status updated successfully', pay_id)
            return

        _log.error('Error update payment %s status! (attempt: %d/%d)! Retry after timeout...',
                   pay_id, attempt, _MAX_UPDATE_ATTEMPTS)

        await asyncio.sleep(2 ** attempt)
    else:
        _log.critical('ERROR! Payment %s NOT UPDATED: %r', pay_id, request_kwargs['body'])


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

