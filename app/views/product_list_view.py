from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from app.models import OrderDetailTable, UserTable, ProjectTable, DriverTable, CustomerTable
from app.models import OrderTable
from loguru import logger
from app.views.user_table_view import UserTableView
from django.db.models import Q, F, Sum


class ProductListView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        search_data = search_form.get('search_data')
        username = search_form.get('username')
        role = UserTableView().getRole(username)
        print(search_form)
        if role == 1:
            del search_form['username']
        query_set = OrderDetailTable.objects.filter(Q(customer_name_id__customer_name__icontains=search_data)
                                                    | Q(order_number_id__order_number__icontains=search_data)
                                                    | Q(commodity_details__icontains=search_data)
                                                    | Q(commodity_size__icontains=search_data)
                                                    | Q(control_no__icontains=search_data)
                                                    )

        if role == 1:
            query_set = query_set.order_by('detailid') \
            .values() \
            .annotate(project_name=F('order_number__project_name'), customer_name=F('order_number__customer_name'),total_shipping_quantity=Sum('shippingdetailtable__shipping_quantity'))
        else:
            query_set = query_set.filter(username=username).order_by('detailid') \
            .values() \
            .annotate(project_name=F('order_number__project_name'), customer_name=F('order_number__customer_name'),total_shipping_quantity=Sum('shippingdetailtable__shipping_quantity'))

        print(query_set)
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
        for item in ProjectTable.objects.all().values('project_name'):
            options.append({'label': item['project_name'], 'value': item['project_name']})
        data['project_name_options'] = options
        options = []
        for item in CustomerTable.objects.all().values('customer_name'):
            options.append({'label': item['customer_name'], 'value': item['customer_name']})
        data['customer_name_options'] = options
        options = []
        for item in OrderTable.objects.all().values('order_number'):
            options.append({'label': item['order_number'], 'value': item['order_number']})
        data['order_number_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)
    