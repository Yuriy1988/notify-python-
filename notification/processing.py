import re
import asyncio
import logging
import jinja2
from itertools import chain
from collections import namedtuple

import utils

__author__ = 'Kostel Serhii'

_log = logging.getLogger('xop.notify')


BaseNotifyNode = namedtuple(
    'BaseNotifyNode',
    'id, name, case_regex, case_template, header_template, body_template, subscribers_template'
)
NotifyNode = namedtuple(
    'NotifyNode',
    'id, name, case_regex, case, header, body, subscribers'
)

email_name2url = dict(
    group='/emails/groups/%s',
    user='/emails/users/%s',
    store_merchants='/emails/stores/%s/merchants',
    store_managers='/emails/stores/%s/managers',
)

recursive_urls_regex = re.compile(r'(?:%s)' % '|'.join((url % '[\w-]+' for url in email_name2url.values())))
email_regex = re.compile(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)')
email_pattern_regex = re.compile(r'^(?:%s):[\w-]+$' % '|'.join(email_name2url.keys()))


class NotifyProcessing:

    _base_node_storage = set()
    _compiled_regex = dict()

    def __init__(self, db, admin_base_url):
        self.db = db
        self.admin_base_url = admin_base_url

    async def _remove_bad_node(self, node):
        """Remove bad node from internal storage and database."""
        _log.warning('Remove bad notify node "%s" from storage', node.name)

        if node in self._base_node_storage:
            self._base_node_storage.remove(node)

        await self.db.notifications.remove(node.id)

    def start(self):
        _log.info('Start notify processing')
        asyncio.ensure_future(self.load_notify_nodes())

    async def load_notify_nodes(self):
        """
        Load base notify nodes from database
        and add to internal storage.
        """
        self._base_node_storage = set()
        notifications = await self.db.notifications.find().to_list(None)

        for notify in notifications:
            base_node = BaseNotifyNode(
                id=notify['_id'],
                name=notify['name'],
                case_regex=notify['case_regex'],
                case_template=notify['case_template'],
                header_template=notify['header_template'],
                body_template=notify['body_template'],
                subscribers_template=notify['subscribers_template']
            )
            self._base_node_storage.add(base_node)

    def rendered_notify_nodes(self, values):
        """
        Generator, that yield rendered base node templates
        with values from values dict.
        :param dict values: values to fill templates
        """
        def fill_template(template):
            return jinja2.Template(template).render(values)

        for base_node in self._base_node_storage.copy():
            try:

                notify_node = NotifyNode(
                    id=base_node._id,
                    name=base_node.name,
                    case_regex=base_node.case_regex,
                    case=fill_template(base_node.case_template),
                    header=fill_template(base_node.header_template),
                    body=fill_template(base_node.body_template),
                    subscribers=fill_template(base_node.subscribers_template)
                )
                yield notify_node

            except jinja2.TemplateError as err:
                _log.warning('Base node "%s" template render error: %s', base_node.name, err)
                asyncio.ensure_future(self._remove_bad_node(base_node))

    def matched_notify_nodes(self, nodes):
        """
        Generator, that yields matched notification nodes
        :param nodes: notify nodes to check matched cases
        """
        for node in nodes:
            try:

                case_regex = self._compiled_regex.get(node.case_regex)
                if case_regex is None:
                    case_regex = re.compile(node.case_regex)
                    self._compiled_regex[node.case_regex] = case_regex

                if recursive_urls_regex.search(node.case):
                    raise ValueError('Recursive url found in node "%s": [%s]', node.name, node.case)

                if case_regex.match(node.case):
                    yield node

            except re.error as err:
                _log.warning('Match node "%s" regex error: %s', node.name, err)
                asyncio.ensure_future(self._remove_bad_node(node))

            except ValueError as err:
                _log.warning('Match node "%s" value error: %s', node.name, err)

    async def extract_subscriber_emails(self, subscribers_str):
        """
        Parse subscribers string to get emails for notification.
        Subscribers must be separated by ",".
        Subscriber address can be:
            - email (e.g. test@mail.me)
            - request_pattern (e.g. group:admin, user:32, store_merchants:store33)
        Request pattern prefixes are listed in email_name2url dict keys.
        If subscriber is request pattern, than get its url and request emails from admin service.
        :param subscribers_str: string with subscribers info
        :return: emails set
        """
        # TODO: add caching
        subscribers = set(map(str.strip, subscribers_str.split(',')))

        emails = set(filter(email_regex.match, subscribers))

        request_emails = set()
        request_emails_raw_info = (addr.split(':') for addr in subscribers if email_pattern_regex.match(addr))
        request_email_urls = [self.admin_base_url + email_name2url[name] % data for name, data in request_emails_raw_info]

        if request_email_urls:
            request_email_futures, _ = await asyncio.wait(list(map(utils.http_request, request_email_urls)))
            request_email_json_iter = filter(None, (ref.result()[0] for ref in request_email_futures))
            request_emails = set(chain.from_iterable(resp.get('emails', []) for resp in request_email_json_iter))

            request_errors = list(filter(None, (ref.result()[1] for ref in request_email_futures)))
            if request_errors:
                _log.warning('Request email errors: %s',
                             ' '.join(map(str, ((url, err) for url, err in zip(request_email_urls, request_errors)))))

        emails = emails | request_emails

        return emails

    async def send_notification(self, node):
        """
        Extract emails from notification node and send emails.
        :param node: notification node
        """
        emails = await self.extract_subscriber_emails(node.subscribers)
        if emails:
            _log.info('Send notification "%s" to emails: %s' % (node.name, str(emails)))
            await asyncio.wait([utils.send_email(email, node.header, node.body) for email in emails])
        else:
            _log.warning('Emails for notification "%s" not found: [%s]' % (node.name, node.subscribers))

    async def request_queue_handler(self, message):
        """
        Requests queue handler.
        :param message: json dict with information from queue
        """
        try:
            rendered_nodes = self.rendered_notify_nodes(message)
            matched_nodes = list(self.matched_notify_nodes(rendered_nodes))
            if matched_nodes:
                await asyncio.wait(list(map(self.send_notification, matched_nodes)))
        except Exception as err:
            _log.exception('Error match notification nodes for message [%s]: %s', message, err)


if __name__ == '__main__':
    import motor.motor_asyncio

    logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S', level='DEBUG')
    motor_client = motor.motor_asyncio.AsyncIOMotorClient()
    db = motor_client['local']

    np = NotifyProcessing(db=db, admin_base_url='http://127.0.0.1:7128/api/admin/dev')
    np_values = ({'service_name': 'xopay-admin', 'query': {'path': '/api/admin/dev/test/42', 'status_code': 200}})
    loop = asyncio.get_event_loop()
    loop.run_until_complete(np.request_queue_handler(np_values))
    loop.close()
