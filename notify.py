from celery import Celery

from currency import update
from currency.utils.general import success_update_message
from message_delivery.email import send_email, ADMIN_EMAIL, DEFAULT_MAIL_SENDER


app = Celery(__file__)
app.config_from_object("celeryconfig")


@app.task
def currency_update():
    rates, errors = update()
    # send email notification to admin
    if rates:
        message = success_update_message(rates, errors)
    else:
        message = "Update totally failed."
    currency_update_report.delay(message)
    return bool(rates)


@app.task
def currency_update_report(message):
    send_email(
        email_from=DEFAULT_MAIL_SENDER,
        email_to=ADMIN_EMAIL,
        subject="XOPAY. Exchange rates update.",
        text=message
    )


@app.task
def send_mail(recipient, subject, message):
    send_email(
        email_from=DEFAULT_MAIL_SENDER,
        email_to=recipient,
        subject=subject,
        text=message
    )
