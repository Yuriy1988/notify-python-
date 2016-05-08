from datetime import datetime

from currency import update
from utils import send_email

# TODO: add request to the admin service to get admin user email
ADMIN_EMAIL = "dpixelstudio@gmail.com"



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


def currency_update_report(message):
    send_email(
        email_to=ADMIN_EMAIL,
        subject="XOPAY. Exchange rates update.",
        text=message
    )


def send_mail(recipient, subject, message):
    send_email(
        email_to=recipient,
        subject=subject,
        text=message
    )
