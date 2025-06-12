import jwt
from rest_framework.authentication import BaseAuthentication
from django.conf import settings
from jwt import exceptions
from rest_framework.exceptions import AuthenticationFailed
from loguru import logger
from app.api_code import *


class MyAuth(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logger.error('missing auth header')
            raise AuthenticationFailed({'code': API_MISSING_AUTH_HEADER, 'error': 'missing auth header'})
        auth_list = auth_header.split(' ')
        if len(auth_list) < 2:
            logger.error('auth header format error')
            raise AuthenticationFailed({'code': API_AUTH_HEADER_FORMAT_ERR, 'error': 'auth header format error'})
        token = auth_list[1]
        salt = settings.SECRET_KEY
        try:
            payload = jwt.decode(token, salt, algorithms=["HS256"])
        except exceptions.ExpiredSignatureError:
            logger.error('token is expired')
            raise AuthenticationFailed({'code': API_TOKEN_EXPIRED, 'error': 'token is expired'})
        except jwt.DecodeError:
            logger.error('token auth fail:', token)
            raise AuthenticationFailed({'code': API_TOKEN_AUTH_FAIL, 'error': 'token auth fail'})
        except jwt.InvalidTokenError:
            logger.error('illegal token:', token)
            raise AuthenticationFailed({'code': API_ILLEGAL_TOKEN, 'error': 'illegal token'})
        request.traceid = payload['userid']
        return (payload, token)

