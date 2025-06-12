import jwt
import datetime
from django.conf import settings


def create_token(payload):
    salt = settings.SECRET_KEY
    timeout = settings.MY_JWT_TOKEN_LIFETIME_MINUTES
    headers = {
        'typ': 'jwt',
        'alg': 'HS256'
    }
    payload['exp'] = datetime.datetime.utcnow() + datetime.timedelta(minutes=timeout)
    token = jwt.encode(payload=payload, key=salt, algorithm='HS256', headers=headers)
    return token
