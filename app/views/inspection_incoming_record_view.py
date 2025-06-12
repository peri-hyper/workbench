# app/views/inspection_incoming_record_view.py
import json
import os
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from loguru import logger

from app.api_code import API_OK, API_SYS_ERR
from app.models import (IncomingInspectionRecord, OrderTable,
                        CustomerTable, IncomingInspectionDetail)
from django.contrib.auth import get_user_model


class InspectionIncomingRecordView(object):
    """
    IncomingInspectionRecord (表头) 增删改查
    ────────────────────────────────────────
    action = inspection_incoming_record_view
    """

    # ---------------- 查询 ----------------
    def query(self, request):
        page_num   = request.data.get('pageNum', 1)
        page_size  = request.data.get('pageSize', 10)
        search_key = request.data.get('search_data', '')

        try:
            qs = IncomingInspectionRecord.objects.filter(
                    Q(inspection_number__icontains=search_key) |
                    Q(order_number__order_number__icontains=search_key)
                 ).order_by('-created_date')

            paginator  = Paginator(qs, page_size)
            page_data  = paginator.page(page_num)

            data = []
            for rec in page_data:
                data.append({
                    'inspection_number'  : rec.inspection_number,
                    'inspection_location': rec.inspection_location,
                    'inspection_standard': rec.inspection_standard,
                    'order_number'       : rec.order_number.order_number if rec.order_number else None,
                    'customer_name'      : rec.customer_name.customer_name if rec.customer_name else None,
                    'inspector_name'     : rec.inspector_name,
                    'created_date'       : rec.created_date.strftime('%Y-%m-%d'),
                })

            return JsonResponse({'code': API_OK, 'msg': 'success',
                                 'data': data, 'total': paginator.count})
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

    # ---------------- 新增 ----------------
    def addRecord(self, request):
        modalForm = request.data.get('modalForm', '{}')


        try:
            rec = IncomingInspectionRecord.objects.create(
                inspection_number   = modalForm['inspection_number'],
                inspection_location = modalForm['inspection_location'],
                inspection_standard = modalForm['inspection_standard'],
                order_number        = OrderTable.objects.get(order_number=modalForm['order_number_id']),
                customer_name       = CustomerTable.objects.get(customer_name=modalForm['customer_name_id']),
                inspector_name           = modalForm['inspector_name'],
                created_date        = modalForm['created_date']
            )
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

        return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': {'id': rec.inspection_number}})

    # ---------------- 删除 ----------------
    def deleteRecord(self, request):
        idmap = request.data.get('inspection_number', {})
        try:
            IncomingInspectionRecord.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})
        return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': ''})

    # ---------------- 编辑 ----------------
    def editRecord(self, request):
        """
        先删旧，再建新（与 cutting 代码保持一致）
        """
        modal_form_str = request.data.get('modalForm', '{}')

        old_number = modal_form_str.get('inspection_number')
        print(old_number)
        if not old_number:
            return JsonResponse({'code': 400, 'msg': 'missing inspection_number', 'data': ''})

        try:
            IncomingInspectionRecord.objects.filter(inspection_number=old_number).delete()

            rec = IncomingInspectionRecord.objects.create(
                inspection_number   = modal_form_str['inspection_number'],
                inspection_location = modal_form_str['inspection_location'],
                inspection_standard = modal_form_str['inspection_standard'],
                order_number        = OrderTable.objects.get(order_number=modal_form_str['order_number_id']),
                customer_name       = CustomerTable.objects.get(customer_name=modal_form_str['customer_name_id']),
                inspector_name           = modal_form_str['inspector_name'],
                created_date        = modal_form_str['created_date']
            )
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

        return JsonResponse({'code': API_OK, 'msg': 'edit done', 'data': {'id': rec.inspection_number}})
