from app.api_code import *
from loguru import logger
import datetime
from django.core.paginator import Paginator
from django.db.models import Q, CharField
from django.db.models.functions import Cast
from django.http import JsonResponse

from app.models import (
    IncomingWarehouseTable,
    WarehousEntryTable,
    SupplierTable,
    UserTable,
    InventoryTable
)


class IncomingWarehouseTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        query_set = IncomingWarehouseTable.objects.filter(Q(**search_form)).all().order_by('incomeid').values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)

        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)
    def query_for_incoming_warehouse_detail_table_view(self, request):
        """
        模糊查询 + 带上父表 WarehousEntryTable 和库存明细 InventoryTable 的关联合并数据。

        支持过滤：
          - entry_date__range   (入库日期范围)

        支持全局关键词 search_data，对以下字段做 AND 级联模糊：
          • IncomingWarehouseTable.remark
          • WarehousEntryTable.entry_number
          • SupplierTable.supplier_name
          • UserTable.username
          • 格式化后的 WarehousEntryTable.entry_date
          • InventoryTable.product_name
          • InventoryTable.product_size
        """
        # 1. 解析分页和搜索表单
        try:
            page_num = int(request.data.get("pageNum", 1))
            page_size = int(request.data.get("pageSize", 10))
        except (ValueError, TypeError):
            return JsonResponse({"code": 1, "msg": "分页参数必须是数字"}, status=400)

        sf = request.data.get("searchForm", {}) or {}

        # 2. 构造精确/范围过滤 dict
        filters = {}
        # 2.1 入库日期范围过滤（entry_date__range）
        if dr := sf.get("entry_date__range"):
            try:
                start_date = datetime.datetime.strptime(dr[0], "%Y-%m-%d").date()
                end_date = datetime.datetime.strptime(dr[1], "%Y-%m-%d").date()
                filters["entry_number__entry_date__range"] = (start_date, end_date)
            except Exception:
                pass

        # 3. 构造 Q 对象，用于全局模糊 AND
        kw_raw = (sf.get("search_data") or "").strip().replace("\u200b", "")
        q_obj = Q()
        if kw_raw:
            for kw in kw_raw.split():
                sub_q = (
                    Q(remark__icontains=kw) |
                    Q(entry_number__entry_number__icontains=kw) |
                    Q(entry_number__supplier_name__supplier_name__icontains=kw) |
                    Q(entry_number__username__username__icontains=kw) |
                    Q(entry_date_str__icontains=kw) |
                    Q(inventoryid__product_name__icontains=kw) |
                    Q(inventoryid__product_size__icontains=kw)
                )
                q_obj &= sub_q

        # 4. 关联查询并分页
        qs = (
            IncomingWarehouseTable.objects
            # 先按 filters 精确/范围过滤
            .filter(**filters)
            # 再把父表的 entry_date 转为字符串，以便模糊匹配
            .annotate(
                entry_date_str=Cast("entry_number__entry_date", CharField())
            )
            # 再做模糊过滤
            .filter(q_obj)
            # 预取关联父表、库存表、及其外键，避免 N+1
            .select_related(
                "entry_number",                    # → WarehousEntryTable
                "entry_number__supplier_name",     # → SupplierTable
                "entry_number__username",          # → UserTable
                "inventoryid"                      # → InventoryTable
            )
            .order_by("-incomeid")
        )

        total = qs.count()
        paginator = Paginator(qs, page_size)
        try:
            page = paginator.page(page_num)
        except:
            page = paginator.page(paginator.num_pages)

        # 5. 序列化输出，每条带上父表 and 库存表字段
        data = []
        for det in page:
            parent = det.entry_number       # WarehousEntryTable
            inv    = det.inventoryid        # InventoryTable
            data.append({
                # —— 入库记录字段 ——
                "incomeid":      det.incomeid,
                "quantity":      float(det.quantity),
                "detail_remark": det.remark or "",

                # —— 父表 WarehousEntryTable 字段 ——
                "entry_number":    parent.entry_number,
                "supplier_name":   parent.supplier_name.supplier_name if parent.supplier_name else "",
                "username":        parent.username.username if parent.username else "",
                "filename":        parent.filename or "",
                "entry_date":      parent.entry_date.strftime("%Y-%m-%d") if parent.entry_date else "",

                # —— 库存明细 InventoryTable 字段 ——
                "inventoryid":          inv.inventoryid,
                "product_name":         inv.product_name,
                "product_size":         inv.product_size,
                "unit":                 inv.get_unit_display(),
                "stock_quantity":       inv.quantity,
                "brand":                inv.brand or "",
                "material_certificate": inv.material_certificate or "",
                "material_type":        inv.material_type or "",
                "stock_remark":         inv.remark or ""
            })

        return JsonResponse({
            "code":  0,
            "msg":   "success",
            "data":  data,
            "total": total
        })
    def addRecord(self, request):
        foreign_key_fields = {}
        for field in IncomingWarehouseTable._meta.get_fields():
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
            IncomingWarehouseTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def __add_quality(self, inventoryid, add_num):
        """ 增加库存数 """
        oldnum = InventoryTable.objects.filter(inventoryid=inventoryid).values('quantity')[0]['quantity']
        newnum = oldnum + int(add_num)
        print(oldnum, newnum)
        InventoryTable.objects.filter(inventoryid=inventoryid).update(quantity=newnum)

    def addRecordList(self, request):
        foreign_key_fields = {}
        for field in IncomingWarehouseTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        for modalForm in request.data.get('inTableData'):
            try:
                inventoryid = modalForm['inventoryid_id']
                add_num = modalForm['quantity']
                self.__add_quality(inventoryid, add_num)
            except Exception as e:
                logger.error(str(e))
                resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
                return JsonResponse(resp)
            addForm = {}
            for key, value in modalForm.items():
                if key in foreign_key_fields:
                    mmap = {key[:-3]: value}
                    obj = foreign_key_fields[key].objects.get(**mmap)
                    addForm[key[:-3]] = obj
                else:
                    addForm[key] = value
            try:
                IncomingWarehouseTable.objects.create(**addForm)
            except Exception as e:
                logger.error(str(e))
                resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
                return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            IncomingWarehouseTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in IncomingWarehouseTable._meta.get_fields():
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
            IncomingWarehouseTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def getOptions(self, request):
        data = {}
        options = []
        for item in WarehousEntryTable.objects.all().values('entry_number'):
            options.append({'label': item['entry_number'], 'value': item['entry_number']})
        data['entry_number_options'] = options
        options = []
        for item in InventoryTable.objects.all().values('inventoryid'):
            options.append({'label': item['inventoryid'], 'value': item['inventoryid']})
        data['inventoryid_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)    
    