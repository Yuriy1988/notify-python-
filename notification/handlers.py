import json
from uuid import uuid4
from aiohttp import web
from marshmallow import Schema, fields, validates_schema
from marshmallow.validate import Length

import auth
from errors import ValidationError, NotFoundError

__author__ = 'Kostel Serhii'


class NotificationSchema(Schema):

    _id = fields.Str(dump_to='id', dump_only=True)
    name = fields.Str(required=True, validate=Length(min=4, max=50))
    case_regex = fields.Str(required=True, validate=Length(min=2, max=255))
    case_template = fields.Str(required=True, validate=Length(min=2, max=255))
    header_template = fields.Str(required=True, validate=Length(min=2, max=255))
    body_template = fields.Str(required=True, validate=Length(min=2, max=255))
    subscribers_template = fields.Str(required=True, validate=Length(min=2, max=255))

    @validates_schema
    def validate_not_blank(self, data):
        if data is None or not str(data):
            raise ValidationError('Wrong request body or Content-Type header missing')


def jsonify(*args, **kwargs):
    return web.Response(text=json.dumps(dict(*args, **kwargs)), content_type='application/json')


# Handlers

@auth.auth('admin')
async def notifications_list(request):
    notifications = await request.app['db'].notifications.find().to_list(None)

    schema = NotificationSchema(many=True)
    result = schema.dump(notifications)
    return jsonify(notifications=result.data)


@auth.auth('admin')
async def notification_create(request):
    schema = NotificationSchema()
    body_json = await request.json()
    data, errors = schema.load(body_json)
    if errors:
        raise ValidationError(errors=errors)

    data['_id'] = str(uuid4())
    await request.app['db'].notifications.insert(data)
    await request.app['notify_processor'].load_notify_nodes()

    result = schema.dump(data)
    return jsonify(result.data)


@auth.auth('admin')
async def notification_detail(request):
    notify_id = request.match_info.get('notify_id', '')
    notification = await request.app['db'].notifications.find_one({'_id': notify_id})
    if not notification:
        raise NotFoundError()

    schema = NotificationSchema()
    result = schema.dump(notification)

    return jsonify(result.data)


@auth.auth('admin')
async def notification_update(request):
    notify_id = request.match_info.get('notify_id', '')
    notification = await request.app['db'].notifications.find_one({'_id': notify_id})
    if not notification:
        raise NotFoundError()

    body_json = await request.json()
    changed_fields = dict(set(body_json.items()) - set(notification.items()))

    schema = NotificationSchema(partial=True)
    data, errors = schema.load(changed_fields)
    if errors:
        raise ValidationError(errors=errors)

    if data:
        await request.app['db'].notifications.update({'_id': notify_id}, {'$set': data})
        await request.app['notify_processor'].load_notify_nodes()

    notification = await request.app['db'].notifications.find_one({'_id': notify_id})
    result = schema.dump(notification)
    return jsonify(result.data)


@auth.auth('admin')
async def notification_delete(request):
    notify_id = request.match_info.get('notify_id', '')
    result = await request.app['db'].notifications.remove(notify_id)
    if result['n'] == 0:
        raise NotFoundError()

    await request.app['notify_processor'].load_notify_nodes()
    return web.Response(status=200, content_type='application/json')
