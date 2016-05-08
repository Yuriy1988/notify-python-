import logging
import json
import smtplib
import asyncio
import aiohttp
import concurrent.futures

from asyncio import TimeoutError
from aiohttp.errors import ClientError
from json.decoder import JSONDecodeError

from config import config

__author__ = 'Kostel Serhii'

_log = logging.getLogger(__name__)
_email_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def send_email(email_to, subject, text, email_from=None):
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


async def send_email_async(email_to, subject, text, email_from=None):
    """
    Send email asyncronously with threade executor
    :param email_from: senders email address. If None - use default
    :param email_to: recipients email address
    :param subject: mail subject
    :param text: mail content
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_email_executor, send_email, email_to, subject, text, email_from)


async def http_request(url, method='GET', body=None, params=None):
    """
    Create async http request to the REST API.
    Work only with json objects.
    :param url: request url
    :param method: one of: GET, PUT, POST, DELETE
    :param body: dict with request body for PUT or POST
    :param params: dict with request url arguments
    :return: response body dict if status 200 OK or None on error
    """
    data = json.dumps(body)
    headers = {'Content-Type': 'application/json'}

    try:
        with aiohttp.ClientSession() as session:
            with aiohttp.Timeout(10):
                async with session.request(method, url, data=data, params=params, headers=headers) as response:
                    rest_status = response.status
                    resp_body = await response.json()

    except (JSONDecodeError, TypeError) as err:
        _log.error('HTTP bad response error: %r', err)
        return None
    except (TimeoutError, ClientError) as err:
        _log.critical('HTTP request error: %r', err)
        return None

    if rest_status != 200:
        _log.error('HTTP wrong status %d. Error detail: %r', rest_status, resp_body.get('error'))
        return None

    return resp_body
