from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from app.models import OrderDetailTable, InspectionCuttingDetailRecord
from app.models import OrderTable
from loguru import logger
from django.db.models import Q, Sum
import sys
from app.views.user_table_view import UserTableView

class OrderDetailTableView(object):
    def query(self, request):
        sys.stdout.flush()
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        role = UserTableView().getRole(search_form.get('username'))
        delivery_date__range = search_form.get('delivery_date__range')
        if delivery_date__range is None and delivery_date__range:
            del search_form['delivery_date__range']
        if role == 1:
            del search_form['username']
        query_set = OrderDetailTable.objects.filter(Q(**search_form)) \
            .annotate(total_shipping_quantity=Sum('shippingdetailtable__shipping_quantity')) \
            .order_by('detailid') \
            .values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)
        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)


    def addRecord(self, request):
        foreign_key_fields = {}
        for field in OrderDetailTable._meta.get_fields():
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
            OrderDetailTable.objects.create(**addForm)
            order_number = (
                modalForm.get('order_number_id')
                .strip()  # 去首尾空白
                .replace('\u200b', '')  # 去零宽空格（可选）
            )
            order_status = OrderTable.objects.filter(order_number=order_number).first().order_status
            if order_status == 2:
                OrderTable.objects.filter(order_number=order_number).update(order_status=1)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            OrderDetailTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in OrderDetailTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        editForm = {}
        modalEditForm = request.data.get('modalEditForm')
        del modalEditForm['total_shipping_quantity']
        for key, value in modalEditForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                editForm[key[:-3]] = obj
            else:
                editForm[key] = value
        idmap = request.data.get('idmap')
        try:
            OrderDetailTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def getOptions(self, request):
        data = {}
        options = []
        for item in OrderTable.objects.all().values('order_number'):
            options.append({'label': item['order_number'], 'value': item['order_number']})
        data['order_number_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)    
