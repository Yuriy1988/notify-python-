import logging
import json
import smtplib
import asyncio
import aiohttp
import concurrent.futures

from asyncio import TimeoutError
from aiohttp.errors import ClientError
from json.decoder import JSONDecodeError

import auth
from config import config

__author__ = 'Kostel Serhii'


_log = logging.getLogger('xop.utils')
_email_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
_sms_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _send_email_sync(email_to, subject, text, email_from=None):
    """
    Send an email from "email_from" to "email_to" address with subject and content text
    :param email_from: senders email address. If None - use default
    :param email_to: recipients email address
    :param subject: mail subject
    :param text: mail content
    """
    email_from = email_from or config['MAIL_DEFAULT_SENDER']

    try:
        with smtplib.SMTP(config['MAIL_SERVER']) as server:
            server.starttls()
            server.login(config['MAIL_USERNAME'], config['MAIL_PASSWORD'])

            content = "From:{}\nSubject:{}\n\n{}".format(email_from, subject, text)
            server.sendmail(email_from, email_to, content)

    except smtplib.SMTPException as err:
        _log.critical('Send Email Error: %r', err)


async def send_email(email_to, subject, text, email_from=None):
    """
    Send email asyncronously with thread executor
    :param str email_to: recipients email address
    :param str subject: mail subject
    :param str text: mail content
    :param str email_from: senders email address. If None - use default
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_email_executor, _send_email_sync, email_to, subject, text, email_from)


def _send_sms_sync(phone, text):
    """
    Send sms to the phone number.
    :param str phone: recipients phone number
    :param str text: sms content
    """
    _log.warning('Send SMS function NOT IMPLEMENTED!')


async def send_sms(phone, text):
    """
    Send sms asyncronously with thread executor.
    If + in phone is missing - it will be added.
    :param str phone: recipients phone number in the international format
    :param str text: sms content
    """
    if len(text) >= 127:
        _log.error('Sms message too long: [%r]. SMS NOT SEND!', text)
        return

    if not phone.startswith('+'):
        phone = '+' + phone

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_sms_executor, _send_sms_sync, phone, text)


async def http_request(url, method='GET', body=None, params=None):
    """
    Create async http request to the REST API.
    Work only with json objects.
    :param url: request url
    :param method: one of: GET, PUT, POST, DELETE
    :param body: dict with request body for PUT or POST
    :param params: dict with request url arguments
    :return: tuple (response body dict, error message)
    """
    data = json.dumps(body)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer %s' % auth.get_system_token()
    }

    try:
        with aiohttp.ClientSession() as session:
            with aiohttp.Timeout(10):
                async with session.request(method, url, data=data, params=params, headers=headers) as response:
                    rest_status = response.status
                    resp_body = await response.json()

    except (JSONDecodeError, TypeError) as err:
        err_msg = 'HTTP bad response error: %r' % err
        _log.error(err_msg)
        return None, err_msg
    except (TimeoutError, ClientError) as err:
        err_msg = 'HTTP request error: %r' % err
        _log.critical(err_msg)
        return None, err_msg

    if rest_status != 200:
        err_msg = 'HTTP wrong status %d. Error detail: %r' % (rest_status, resp_body)
        _log.error(err_msg)
        return None, err_msg

    return resp_body, None


async def get_admins_emails():
    result, error = await http_request(config.get('ADMIN_BASE_URL') + '/admins_emails')
    if error:
        _log.critical('Error get admins emails.\nWrong response from Admin Service.\n%s' % error)
        return

    return result.get('emails')


async def report_to_admin(subject, text):
        admin_email_list = await get_admins_emails()
        if not admin_email_list:
            _log.warning('Report not send. Admin email address is missing!')
            return

        await asyncio.gather(*[send_email(email, subject=subject, text=text) for email in admin_email_list])
