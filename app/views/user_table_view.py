from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from app.models import UserTable
from loguru import logger
from app.util.commutil import CommUtil

class UserTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        query_set = UserTable.objects.filter(**search_form).all().order_by('userid').values('userid', 'username', 'role')
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)
        role_choices_map = {'1': '管理员', '2': '跟单员', '3': '质检员', '4': '仓管员'}
        for item in page_data:
            item['role_label'] = role_choices_map.get(str(item['role']), '')
        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)

    def verfiyUser(self, username, password):
        print(password)
        passwordmd5 = CommUtil.get_md5(password)
        print(passwordmd5)
        return UserTable.objects.filter(username=username, password=passwordmd5).exists()

    def getRole(self, username):
        return UserTable.objects.filter(username=username).values('role')[0]['role']

    def addRecord(self, request):
        foreign_key_fields = {}
        for field in UserTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        addForm = {}
        modalForm = request.data.get('modalForm')
        for key, value in modalForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                addForm[key] = obj
            else:
                if key == 'password':
                    addForm[key] = CommUtil.get_md5(value)
                else:
                    addForm[key] = value
        try:
            UserTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            UserTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in UserTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        editForm = {}
        modalEditForm = request.data.get('modalEditForm')
        for key, value in modalEditForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                editForm[key] = obj
            else:
                if key == 'password':
                    if value.strip() == '':
                        continue
                    editForm[key] = CommUtil.get_md5(value)
                else:
                    editForm[key] = value
        idmap = request.data.get('idmap')
        try:
            UserTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)
