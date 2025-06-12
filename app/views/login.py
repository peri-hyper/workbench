# -*- coding: utf-8 -*-
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import action
from rest_framework import viewsets
from loguru import logger
from app.auth.my_auth import MyAuth
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import serializers
from app.api_code import *
from app.auth.create_token import create_token
from rest_framework import serializers

from app.views.user_table_view import UserTableView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class Login(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = []

    # http://127.0.0.1:8000/vue-element-admin/user/login
    @action(methods=['post'], detail=False)
    def login(self, request):
        print(request.data)
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        print(username)
        print(password)
        if not username or not password:
            resp = {'code': API_PARAM_ERR, 'msg': '请输入用户名和密码', 'data': None}
            return JsonResponse(resp)
        obj = UserTableView()

        exists = obj.verfiyUser(username, password)
        if not exists:
            resp = {'code': API_PARAM_ERR, 'msg': '用户名或密码错误', 'data': None}
            return JsonResponse(resp)
        payload = {
            'userid': username,
        }
        token = create_token(payload)
        resp = {'code': 20000, 'msg': 'success', 'data': {'token': token}}
        return JsonResponse(resp)

    @action(methods=['get'], detail=False, authentication_classes=[MyAuth])
    def info(self, request):
        logger.debug(f'{request.traceid} token payload user:{request.user}')
        userid = request.user['userid']
        print(userid)
        users = {
            'admin-token': {
                'roles': ['admin'],
                'introduction': 'I am a super administrator',
                'avatar': 'https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif',
                'name': userid
            },
            'editor-token': {
                'roles': ['editor'],
                'introduction': 'I am an editor',
                'avatar': 'https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif',
                'name': userid
            }
        }
        obj = UserTableView()
        role = obj.getRole(userid)
        print(f'role:{role}')
        if role == 1:
            data = users['admin-token']
        else:
            data = users['editor-token']
        resp = {'code': 20000, 'msg': 'success', 'data': data}
        return JsonResponse(resp)

    @action(methods=['options', 'post'], detail=False, authentication_classes=[MyAuth])
    def logout(self, request):
        resp = {'code': 20000, 'msg': 'success', 'data': 'success'}
        return JsonResponse(resp)

