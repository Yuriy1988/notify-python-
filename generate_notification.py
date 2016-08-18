#!venv/bin/python
import config
import uuid
from pymongo import MongoClient

motor_client = MongoClient()
db = motor_client[config.debug.DB_NAME]

db.notifications.remove()
for i in range(16):
    example = {
        "_id": str(uuid.uuid4()),
        "name": "Template " + str(i),
        "case_regex":  "status: 401",
        "case_template": "status: {{ query.status_code }}",
        "header_template": "Prevented attempt to access {{ query.path }}",
        "body_template": "Date {{ query.timestamp }}\nUser {{ user.name }} try to access {{ query.path }} from {{ query.remote_address}}",
        "subscribers_template": "test@mail.me, and@me.too, group:admin"
    }

    db.notifications.insert(example)

print("Generation OK. 16 records were added.")
