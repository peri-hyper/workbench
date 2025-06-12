from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from app.models import CustomerTable
from loguru import logger
from django.db.models import Q, F
class CustomerTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        query_set = CustomerTable.objects.filter(Q(**search_form)).all().order_by('customerid').values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)
        print(query_set)
        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)

    def addRecord(self, request):
        foreign_key_fields = {}
        for field in CustomerTable._meta.get_fields():
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
                addForm[key] = value
        try:
            CustomerTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            CustomerTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in CustomerTable._meta.get_fields():
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
                editForm[key] = value
        idmap = request.data.get('idmap')
        try:
            CustomerTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)
    def getOptions(self, request):
        print(111)
        data = {}
        options = []
        for item in CustomerTable.objects.all().values('customer_name'):
            options.append({'label': item['customer_name'], 'value': item['customer_name']})
        data['customer_name_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        print(resp)
        return JsonResponse(resp)