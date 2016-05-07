import smtplib

from config import config

__author__ = 'Kostel Serhii'


def send_email(email_from, email_to, subject, text):
    """
    Send an email from "email_from" to "email_to" address with subject and content text.
    :param email_from: senders email address.
    :param email_to: recipients email address.
    :param subject: mail subject.
    :param text: mail content.
    :return:
    """
    with smtplib.SMTP(config['MAIL_SERVER']) as server:
        server.starttls()
        server.login(config['MAIL_USERNAME'], config['MAIL_PASSWORD'])
        header = "From:{}\nSubject:{}\n\n".format(email_from, subject)
        server.sendmail(email_from, email_to, header + text)
