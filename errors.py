import json
import logging
from aiohttp import web

__author__ = 'Kostel Serhii'

_log = logging.getLogger('xop.error')


# API Errors

class BaseApiError(web.HTTPClientError):

    status_code = 400
    default_message = 'Bad Request'

    def __init__(self, message=None, status_code=None, errors=None):
        """
        :param message: error message
        :param status_code: error http code
        :param errors: dict with additional information about errors
        """
        self.message = message or self.default_message
        self.status_code = status_code or self.status_code
        self.errors = errors
        super(BaseApiError, self).__init__(text=self._error_serializer(), content_type='application/json')

    def _error_serializer(self):
        """
        Error serializer in format:
        {
            error: {
                status_code: status_code,
                message: message,
                errors: {               // optional
                    ...
                },
                traceback: traceback    // optional
        }
        :return: json error
        """
        error_dict = {'message': self.message, 'status_code': self.status_code}
        if self.errors:
            error_dict['errors'] = self.errors

        return json.dumps({'error': error_dict})


class ValidationError(BaseApiError):

    status_code = 400
    default_message = 'Request with invalid arguments'


class UnauthorizedError(BaseApiError):

    status_code = 401
    default_message = 'Unauthorized'


class ForbiddenError(BaseApiError):

    status_code = 403
    default_message = 'Forbidden'


class NotFoundError(BaseApiError):

    status_code = 404
    default_message = 'Not Found'
