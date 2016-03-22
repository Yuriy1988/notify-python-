import smtplib

# mail settings TODO: unhardcode SMTP settings
MAIL_SERVER = "smtp.gmail.com"
MAIL_USERNAME = "daniel.omelchenko@digitaloutlooks.com"
MAIL_PASSWORD = "Po03yeFGd54c9jHq"
DEFAULT_MAIL_SENDER = "daniel.omelchenko@digitaloutlooks.com"

ADMIN_EMAIL = "dpixelstudio@gmail.com"


def send_email(email_from, email_to, subject, text):
    """
    Send an email from "email_from" to "email_to" address with subject and content text.
    :param email_from: senders email address.
    :param email_to: recipients email address.
    :param subject: mail subject.
    :param text: mail content.
    :return:
    """
    with smtplib.SMTP(MAIL_SERVER) as server:
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        header = "From:{}\nSubject:{}\n\n".format(email_from, subject)
        server.sendmail(email_from, email_to, header + text)
