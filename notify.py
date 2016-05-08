import logging
from datetime import datetime

from currency import update
from utils import send_email

__author__ = 'Kostel Serhii'

_log = logging.getLogger(__name__)

# TODO: add request to the admin service to get admin user email
ADMIN_EMAIL = "dpixelstudio@gmail.com"


async def email_queue_handler(message):
    """
    Send email queue handler.
    :param message: json dict with information from queue
    """
    if set(message.keys()) != {'email_to', 'subject', 'text'}:
        _log.error('Wrong message fields in email queue [%r]', message)
        return

    await send_email(**message)


async def sms_queue_handler(message):
    """
    Send sms queue handler.
    :param message: json dict with information from queue
    """
    _log.warning('Send SMS function NOT IMPLEMENTED!')


def format_currency(currency_dict):
    """
    Returns formatted representation of currency rate.
    :param currency_dict: currency raw data.
    :return: formatted string.
    """
    return '{from_currency}/{to_currency}:\t {rate}'.format(**currency_dict)


def success_update_message(rates, update_errors):
    return "Exchange rates was successfully updated.\n\n{rates}\n\nCommit time (UTC): {date_time}\n\n{update_errors}"\
        .format(
            rates="\n".join(map(format_currency, rates)),
            update_errors="\n".join(update_errors),
            date_time=datetime.utcnow(),
        )


def currency_update():
    rates, errors = update()
    # send email notification to admin
    if rates:
        message = success_update_message(rates, errors)
    else:
        message = "Update totally failed."
    currency_update_report.delay(message)
    return bool(rates)


async def currency_update_report(message):
    await send_email(
        email_to=ADMIN_EMAIL,
        subject="XOPAY. Exchange rates update.",
        text=message
    )
