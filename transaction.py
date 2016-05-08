import logging
import asyncio
import json
from json.decoder import JSONDecodeError

from config import config
from utils import http_request

__author__ = 'Kostel Serhii'

_MAX_UPDATE_ATTEMPTS = 5

_log = logging.getLogger(__name__)


async def transaction_queue_handler(message):
    """
    Transaction status queue handler.
    :param message: bytes with information from queue
    """
    try:
        payment = json.loads(message.decode())
        pay_id, pay_status = payment['id'], payment['status']
    except (JSONDecodeError, TypeError, KeyError) as err:
        _log.error('Wrong transaction message [%r]: %r', message, err)
        return

    host, version = config['CLIENT_HOST'], config['CLIENT_API_VERSION']
    request_kwargs = dict(
        method='PUT',
        url='{host}/api/client/{version}/payment/{pay_id}'.format(host=host, version=version, pay_id=pay_id),
        body={'status': pay_status}
    )

    for attempt in range(1, _MAX_UPDATE_ATTEMPTS+1):

        _log.info('Update payment %s status: [%s] (attempt: %d/%d)', pay_id, pay_status, attempt, _MAX_UPDATE_ATTEMPTS)

        result = await http_request(**request_kwargs)
        if result is not None:
            _log.info('Payment %s status updated successfully', pay_id)
            return

        _log.error('Error update payment %s status! (attempt: %d/%d)! Retry after timeout...',
                   pay_id, attempt, _MAX_UPDATE_ATTEMPTS)

        await asyncio.sleep(2 ** attempt)

    else:
        _log.critical('ERROR! Payment %s NOT UPDATED: %r', pay_id, request_kwargs['body'])
