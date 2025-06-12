from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from app.models import PurchaseDetailTable
from app.models import PurchaseTable
from loguru import logger

import datetime
import json

from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import Cast
from django.db.models import CharField
from django.http import JsonResponse

from app.models import PurchaseDetailTable, PurchaseTable, SupplierTable, UserTable

class PurchaseDetailTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        query_set = PurchaseDetailTable.objects.filter(**search_form).all().order_by('purchasedetailid').values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)

        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)


    def query_for_purchase_detail_table_view(self, request):
        """
        实现模糊查询 + 带上父表 PurchaseTable 的关联合并数据

        支持的精确/范围过滤字段（searchForm 中传入）：
          - purchase_date__range      (采购日期范围过滤)
          - currency                  (币种精确过滤或 icontains)
          - AOG_status                (到货状态精确过滤)

        支持的模糊查询关键字（searchForm 中传入 search_data）：
          对以下字段做 AND 级联的多关键字模糊匹配：
            • PurchaseDetailTable.product_name          (品名)
            • PurchaseDetailTable.product_size          (规格)
            • PurchaseDetailTable.material              (材质)
            • PurchaseDetailTable.unit                  (单位)
            • PurchaseDetailTable.remark                (明细备注)
            • PurchaseTable.purchase_number             (采购单号)
            • SupplierTable.supplier_name               (供应商名)
            • UserTable.username                        (采购员用户名)
            • PurchaseTable.purchase_date (格式化为字符串) (发货/采购日期)
        """
        # 1. 解析分页和搜索表单
        page_num = int(request.data.get("pageNum", 1))
        page_size = int(request.data.get("pageSize", 10))
        sf = request.data.get("searchForm", {}) or {}

        # 2. 先做精确或范围过滤的 dict
        filters = {}
        # 2.1 采购日期范围，如 ["2025-05-01", "2025-05-31"]
        if dr := sf.get("purchase_date__range"):
            try:
                start_date = datetime.datetime.strptime(dr[0], "%Y-%m-%d").date()
                end_date = datetime.datetime.strptime(dr[1], "%Y-%m-%d").date()
                filters["purchase_number__purchase_date__range"] = (start_date, end_date)
            except Exception:
                # 日期解析失败则忽略该条件
                pass

        # 2.2 币种过滤，可改为 icontains
        if curr := sf.get("currency"):
            filters["purchase_number__currency__icontains"] = curr.strip()
        # 2.3 到货状态 AOG_status 精确过滤
        if aog := sf.get("AOG_status"):
            try:
                filters["purchase_number__AOG_status"] = int(aog)
            except (ValueError, TypeError):
                pass

        # 3. 构造 Q 对象，用于多字段模糊 AND 且可支持多关键字
        kw_raw = (sf.get("search_data") or "").strip().replace("\u200b", "")
        q_obj = Q()
        if kw_raw:
            # 支持空格分割多个关键字，逐个关键字做 AND 关联
            for kw in kw_raw.split():
                sub_q = (
                        Q(product_name__icontains=kw) |
                        Q(product_size__icontains=kw) |
                        Q(material__icontains=kw) |
                        Q(unit__icontains=kw) |
                        Q(remark__icontains=kw) |
                        Q(purchase_number__purchase_number__icontains=kw) |
                        Q(purchase_number__supplier_name__supplier_name__icontains=kw) |
                        Q(purchase_number__username__username__icontains=kw) |
                        Q(purchase_date_str__icontains=kw)
                )
                q_obj &= sub_q

        # 4. 关联查询并分页
        qs = (
            PurchaseDetailTable.objects
            # 先按 filters 精确/范围过滤
            .filter(**filters)
            # 再把关联字段转换为字符串，便于日期等字段模糊匹配
            .annotate(
                purchase_date_str=Cast("purchase_number__purchase_date", CharField())
            )
            # 再做模糊过滤
            .filter(q_obj)
            # 预取关联父表及其外键，以防 N+1 查询
            .select_related(
                "purchase_number",  # PurchaseDetailTable → PurchaseTable
                "purchase_number__supplier_name",  # PurchaseTable → SupplierTable
                "purchase_number__username"  # PurchaseTable → UserTable
            )
            .order_by("-purchasedetailid")
        )

        total = qs.count()
        paginator = Paginator(qs, page_size)
        try:
            page = paginator.page(page_num)
        except:
            page = paginator.page(paginator.num_pages)

        # 5. 序列化输出，每条带上父表字段
        data = []
        for det in page:
            parent = det.purchase_number  # PurchaseTable 实例
            data.append({
                # —— PurchaseDetailTable 自身字段 ——
                "purchasedetailid": det.purchasedetailid,
                "requestid_id": det.requestid_id,
                "product_name": det.product_name,
                "product_size": det.product_size,
                "material": det.material,
                "quantity": float(det.quantity) if det.quantity is not None else 0,
                "unit": det.unit,
                "unit_price": float(det.unit_price) if det.unit_price is not None else 0,
                "total_price": float(det.total_price) if det.total_price is not None else 0,
                "detail_remark": det.remark or "",

                # —— 父表 PurchaseTable 合并字段 ——
                "purchase_number": parent.purchase_number,
                "purchase_date": parent.purchase_date.strftime("%Y-%m-%d") if parent.purchase_date else "",
                "currency": parent.currency or "",
                "parent_remark": parent.remark or "",
                "supplier_name": (parent.supplier_name.supplier_name
                                  if parent.supplier_name else ""),
                "purchaser": (parent.username.username
                              if parent.username else ""),
                "contact_person": parent.contact_person or "",
                "contact_number": parent.contact_number or "",
                "AOG_status": parent.AOG_status,
            })

        return JsonResponse({
            "code": 0,
            "msg": "success",
            "data": data,
            "total": total
        })
    def addRecord(self, request):
        foreign_key_fields = {}
        for field in PurchaseDetailTable._meta.get_fields():
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
            PurchaseDetailTable.objects.create(**addForm)
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
        try:
            PurchaseDetailTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))

    def addRecordList(self, modalFormList):
        foreign_key_fields = {}
        for field in PurchaseDetailTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        for modalForm in modalFormList:
            self.__addOneRecord(modalForm, foreign_key_fields)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteByPurchaseNumber(self, purchase_number):
        try:
            PurchaseDetailTable.objects.filter(purchase_number=purchase_number).delete()
        except Exception as e:
            logger.error(str(e))
            return -1
        return 0

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            PurchaseDetailTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in PurchaseDetailTable._meta.get_fields():
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
            PurchaseDetailTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def getOptions(self, request):
        data = {}
        options = []
        for item in PurchaseTable.objects.all().values('purchase_number'):
            options.append({'label': item['purchase_number'], 'value': item['purchase_number']})
        data['purchase_number_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)    
    