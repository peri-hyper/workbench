import json

from django.core.paginator import Paginator
from django.db.models import Q
from app.api_code import *
from app.models import OrderTable, UserTable, CustomerTable, ProjectTable, OrderDetailTable, InvoicesTable, FileTable, \
    CheckContentsTable, DriverTable
from app.views.user_table_view import UserTableView 
from django.db import transaction
from pypinyin import lazy_pinyin, Style

from loguru import logger
import pandas as pd
import openpyxl
import os, uuid, datetime
from django.conf import settings
from django.http import JsonResponse

class OrderTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        username = search_form.get('username')
        role = UserTableView().getRole(username)
        delivery_date__range = search_form.get('delivery_date__range')
        search_data = search_form.get('search_data')
        if delivery_date__range is None and delivery_date__range:
            del search_form['delivery_date__range']
        order_status = search_form.get('order_status')
        del search_form['order_status']
        today_date = datetime.date.today()  # 当日时间
        if order_status != 1:
            query_set = OrderTable.objects.filter(shpping_date__lt=today_date).exclude(shpping_date='1900-01-01').all().filter(Q(order_number__icontains=search_data)
                                                                                                                                                           | Q(customer_name_id__customer_name__icontains=search_data)
                                                                                                                                                           | Q(project_name__icontains=search_data)
                                                                                                                                                           | Q(order_date__icontains=search_data)
                                                                                                                                                           | Q(manufacture_date__icontains=search_data)
                                                                                                                                                           | Q(delivery_date__icontains=search_data)
                                                                                                                                                           | Q(order_details__icontains=search_data)
                                                                                                                                                           | Q(remarks__icontains=search_data))
        else:
            query_set = OrderTable.objects.filter(
                Q(shpping_date__gt=today_date) | Q(shpping_date='1900-01-01') | Q(shpping_date=today_date)).all().filter(
                Q(order_number__icontains=search_data)
                | Q(customer_name_id__customer_name__icontains=search_data)
                | Q(project_name__icontains=search_data)
                | Q(order_date__icontains=search_data)
                | Q(manufacture_date__icontains=search_data)
                | Q(delivery_date__icontains=search_data)
                | Q(order_details__icontains=search_data)
                | Q(remarks__icontains=search_data)
                )
        if role == 1:
            query_set = query_set.order_by('order_status','customer_name').values()
        else:
            query_set = query_set.filter(username=username).order_by('order_status', 'customer_name').values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)
        order_status_choices_map = {'1': '生产中', '2': '已完成', '0': '已暂停'}
        for item in page_data:
            item['order_status_label'] = order_status_choices_map.get(str(item['order_status']), '')
        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)

    def queryProducing(self, request):
        """ 最近20天排产甘特图 """
        today_date = datetime.date.today()  # 当日时间
        query_set = OrderTable.objects.filter(Q(shpping_date__gt=today_date) | Q(shpping_date='1900-01-01')).all().order_by('-order_status','delivery_date').values()
        if len(query_set) == 0:
            resp = {'code': 0, 'msg': 'success', 'data': []}
            return JsonResponse(resp)
        columns = [{
            'field': 'customer_name_id',
            'title': '<span style="color:#909399;font-size:12px;">客户代码</span>',
            'type': 'html'
        },
        {
            'field': 'order_number',
            'title': '<span style="color:#909399;font-size:12px">订单号码</span>',
            'type': 'html'
        },
        {
            'field': 'project_name',
            'title': '<span style="color:#909399;font-size:12px">项目名称</span>',
            'type': 'html'
        }]
        data = []
        is_first = True
        for item in query_set:
            item['customer_name_id'] = lazy_pinyin(item['customer_name_id'], style=Style.FIRST_LETTER)
            item['customer_name_id'] = ''.join([letter.upper() if letter.isalpha() else letter for letter in item['customer_name_id']])
            order_status = item['order_status']
            item_order_date = item['manufacture_date']
            item_delivery_date = item['delivery_date']  #出货时间
            retrow = item.copy()
            schedule_start_date = datetime.date.today()
            # 最近days天的排产甘特图
            days = 30
            if item_delivery_date < schedule_start_date and order_status !=2 and order_status !=0:
                order_status = 4
            schedule_end_date = schedule_start_date + datetime.timedelta(days=days)
            while schedule_start_date < schedule_end_date:
                fielddate = schedule_start_date.strftime('%m/%d')
                if is_first:
                    title = f'<span style="color:#909399;font-size:12px">{fielddate}</span>'
                    columns.append({'field': fielddate, 'title': title, 'type': 'html'})
                if order_status == 0:
                    retrow[fielddate] = 3
                elif (schedule_start_date >= item_order_date) and (item_delivery_date - today_date).days > 3 and (order_status == 1)  and item_delivery_date >= schedule_start_date:
                    retrow[fielddate] = 1
                elif (schedule_start_date >= item_order_date) and 0 <= (item_delivery_date - today_date).days <= 3 and (order_status == 1) and item_delivery_date >= schedule_start_date:
                    retrow[fielddate] = 2
                elif order_status == 4:
                    retrow[fielddate] = 4
                elif order_status == 2:
                    retrow[fielddate] = 0
                else:
                    retrow[fielddate] = ''
                schedule_start_date += datetime.timedelta(days=1)
            is_first = False
            data.append(retrow)
        resp = {'code': 0, 'msg': 'success', 'data': data, 'columns': columns}
        return JsonResponse(resp)

    def addRecord(self, request):
        foreign_key_fields = {}
        for field in OrderTable._meta.get_fields():
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
            OrderTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            OrderTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        print(request.data)
        foreign_key_fields = {}
        for field in OrderTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model

        editForm = {}
        modalEditForm = request.data.get('modalEditForm', {})
        old_order_number = modalEditForm.pop('old_order_number', None)
        new_order_number = modalEditForm.get('order_number', None)

        # 构建更新的字段
        if 'order_number' in modalEditForm:
            del modalEditForm['order_number']
        if 'orderid' in modalEditForm:
            del modalEditForm['orderid']
        for key, value in modalEditForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                editForm[key[:-3]] = obj
            else:
                editForm[key] = value
        # try:

        with transaction.atomic():
                # 1. 插入新的 `order_number` 记录
                if old_order_number and new_order_number and old_order_number != new_order_number:
                    old_order = OrderTable.objects.get(order_number=old_order_number)

                    # 使用 `values()` 获取旧记录的字段值，并排除 `order_number` 和 `orderid`
                    old_order_values = {field.name: getattr(old_order, field.name) for field in OrderTable._meta.fields}
                    old_order_values['order_number'] = new_order_number
                    old_order_values.pop('orderid')  # 去掉主键字段以便生成新记录

                    # 创建新记录
                    OrderTable.objects.create(**old_order_values)

                # 2. 更新子表中的外键引用
                if old_order_number and new_order_number:
                    OrderDetailTable.objects.filter(order_number_id=old_order_number).update(
                        order_number_id=new_order_number)
                InvoicesTable.objects.filter(order_number_id=old_order_number).update(order_number_id=new_order_number)
                FileTable.objects.filter(order_number_id=old_order_number).update(order_number_id=new_order_number)
                CheckContentsTable.objects.filter(order_number_id=old_order_number).update(
                    order_number_id=new_order_number)

                # 3. 更新新的 `order_number` 记录中的其他字段
                OrderTable.objects.filter(order_number=new_order_number).update(**editForm)

                # 4. 删除旧的 `order_number` 记录（如果需要）
                if old_order_number and old_order_number != new_order_number:
                    OrderTable.objects.filter(order_number=old_order_number).delete()

        # except Exception as e:
        #     logger.error(str(e))
        #     resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
        #     return JsonResponse(resp)

        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def getOptions(self, request):
        """ 获取外键下拉框选项 """
        data = {}
        options = []
        for item in UserTable.objects.all().values('username'):
            options.append({'label': item['username'], 'value': item['username']})
        data['username_options'] = options
        options = []
        for item in CustomerTable.objects.all().values('customer_name'):
            options.append({'label': item['customer_name'], 'value': item['customer_name']})
        data['customer_name_options'] = options
        options = []
        for item in ProjectTable.objects.all().values('project_name'):
            options.append({'label': item['project_name'], 'value': item['project_name']})
        data['project_name_options'] = options
        options = []
        for item in OrderTable.objects.all().filter(order_status__in=[1, 2]).values('order_number'):
            options.append({'label': item['order_number'], 'value': item['order_number']})
        data['order_number_options'] = options
        options = []
        for item in DriverTable.objects.all().values('driver_name','licence_plate','driver_phone'):
            options.append({'label': 'driver_name', 'value': item['driver_name']})
            options.append({'label': 'licence_plate', 'value': item['licence_plate']})
            options.append({'label': 'driver_phone', 'value': item['driver_phone']})
        data['driver_name_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)
    def getOptions_for_Android(self, request):
        """ 获取外键下拉框选项 """
        data = {}
        options = []
        for item in UserTable.objects.all().values('username'):
            options.append({'label': item['username'], 'value': item['username']})
        data['username_options'] = options
        options = []
        for item in CustomerTable.objects.all().values('customer_name'):
            options.append({'label': 'customer_name', 'value': item['customer_name']})
        data['customer_name_options'] = options
        options = []
        for item in ProjectTable.objects.all().values('project_name','project_contact_name','project_contact_phone'):
            options.append({'label': 'project_name', 'value': item['project_name']})
            options.append({'label': 'project_contact_name', 'value': item['project_contact_name']})
            options.append({'label': 'project_contact_phone', 'value': item['project_contact_phone']})
        data['project_name_options'] = options
        options = []
        for item in OrderTable.objects.all().filter(order_status__in=[1, 2]).values('order_number'):
            options.append({'label': 'order_number', 'value': item['order_number']})
        data['order_number_options'] = options
        options = []
        for item in DriverTable.objects.all().values('driver_name','licence_plate','driver_phone'):
            options.append({'label': 'driver_name', 'value': item['driver_name']})
            options.append({'label': 'licence_plate', 'value': item['licence_plate']})
            options.append({'label': 'driver_phone', 'value': item['driver_phone']})
        data['driver_name_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)
    def export_excel(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return JsonResponse({'code': 400, 'msg': 'ids is empty', 'data': ''})

        # ① 取数据
        qs = OrderTable.objects.filter(orderid__in=ids).values()
        if not qs:
            return JsonResponse({'code': 404, 'msg': 'no data', 'data': ''})
        df = pd.DataFrame(list(qs))
        df.insert(0, '序号', range(1, len(df) + 1))
        # ② 删掉不需要的列
        drop_cols = ['orderid','invoice_date', 'order_status', 'shpping_date', 'quote_date']
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])

        # ③ 改中文列头
        header_map = {
            'orderid'        : '序号',
            'customer_name_id': '客户名称',
            'order_number'   : '订单号',
            'project_name'   : '项目名称',
            'order_date'     : '下单日期',
            'manufacture_date': '开始生产',
            'delivery_date'  : '预出货',
            'order_details'  : '订单内容',
            'remarks'        : '备注',
            'username_id'    : '跟单员',
            # ……如需再映射就补充……
        }
        df = df.rename(columns=header_map)

        # ④ 保存到临时文件
        fname_no_suffix = f"order_{uuid.uuid4().hex}"
        fname           = f"{fname_no_suffix}.xlsx"
        file_path       = os.path.join(settings.PDF_DIR, fname)

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='订单')
            ws = writer.sheets['订单']

            # —— ⑤ 自动列宽（按内容最大字符宽度） ——
            for col_idx, col in enumerate(df.columns, 1):           # 1‑based
                max_len = max(
                    df[col].astype(str).map(len).max(),             # 数据
                    len(str(col))                                   # 列头
                )
                # 粗略 *1.2 得到像素宽（中文算 2 个字符效果不错）
                ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max_len * 1.6

        # ⑥ 返回文件名
        return JsonResponse({'code': 0, 'msg': 'success', 'order_excel': fname_no_suffix})
if __name__ == '__main__':
    obj = OrderTableView()
    request = {}
    obj.queryProducing(request)