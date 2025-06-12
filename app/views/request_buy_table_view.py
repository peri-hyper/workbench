from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from app.models import RequestBuyTable
from app.models import UserTable
from loguru import logger


class RequestBuyTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        product_name = search_form.get('product_name')
        if product_name:
            query_set = RequestBuyTable.objects.filter(product_name__contains=product_name).all().order_by('requestid').values()
        else:
            query_set = RequestBuyTable.objects.filter(**search_form).all().order_by('requestid').values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)
        whether_buy_choices_map = {'1': '是', '2': '否'}
        for item in page_data:
            item['whether_buy_label'] = whether_buy_choices_map.get(str(item['whether_buy']), '')
        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)

    def addRecord(self, request):
        foreign_key_fields = {}
        for field in RequestBuyTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        addForm = {}
        modalForm = request.data.get('modalForm')
        for key, value in modalForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                addForm[key[:-3]] = obj
            else:
                addForm[key] = value
        try:
            RequestBuyTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def __addOneRecord(self, modalForm, foreign_key_fields):
        addForm = {}
        for key, value in modalForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                addForm[key[:-3]] = obj
            else:
                addForm[key] = value
        print(addForm)
        try:
            RequestBuyTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))

    def addRecordList(self, request):
        foreign_key_fields = {}
        for field in RequestBuyTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        modalFormList = request.data.get('modalFormList')
        for modalForm in modalFormList:
            self.__addOneRecord(modalForm, foreign_key_fields)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            RequestBuyTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in RequestBuyTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        editForm = {}
        print(foreign_key_fields)
        modalEditForm = request.data.get('modalEditForm')
        print(modalEditForm)
        for key, value in modalEditForm.items():
            if key != "isChecked":
                if key in foreign_key_fields:
                    mmap = {key[:-3]: value}
                    obj = foreign_key_fields[key].objects.get(**mmap)
                    editForm[key[:-3]] = obj
                else:
                    editForm[key] = value
        idmap = request.data.get('idmap')
        try:
            RequestBuyTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)
    def batchDelete(self, request):
        requestid_list = request.data.get('requestid_list')
        print(requestid_list)
        for requestid in requestid_list:
            RequestBuyTable.objects.filter(requestid=requestid).delete()
        resp = {'code': 0, 'msg': 'success', 'data': ''}
        return JsonResponse(resp)
    def getOptions(self, request):
        data = {}
        options = []
        for item in UserTable.objects.all().values('username'):
            options.append({'label': item['username'], 'value': item['username']})
        data['username_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)    
    