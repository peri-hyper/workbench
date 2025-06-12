from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from app.models import OutgoingWarehouseTable
from app.models import InventoryTable
from loguru import logger
import datetime
from django.core.paginator import Paginator
from django.db.models import Q, CharField
from django.db.models.functions import Cast
from django.http import JsonResponse
from django.db import transaction
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

API_OK = 0
API_SYS_ERR = 500


class OutgoingWarehouseTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        query_set = OutgoingWarehouseTable.objects.filter(**search_form).all().order_by('outid').values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)

        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)
    def query_for_outgoing_warehouse_table_view(self, request):
        """
        分页查询 OutgoingWarehouseTable，并带出关联的 InventoryTable 数据，
        支持以下搜索条件（来自 searchForm）：
          1) search_data：全局关键词，对下列字段做模糊 AND：
             - OutgoingWarehouseTable.person_name
             - OutgoingWarehouseTable.outdate（字符串形式）
             - InventoryTable.product_name
             - InventoryTable.product_size
             - InventoryTable.brand
             - InventoryTable.material_certificate
             - InventoryTable.material_type
          2) outdate__range：["YYYY-MM-DD","YYYY-MM-DD"]，对出库日期范围过滤

        前端传参（JSON body）：
          pageNum       int, 默认为 1
          pageSize      int, 默认为 20
          searchForm: {
            search_data:       str,
            outdate__range:    [str, str], 如 ["2025-05-01","2025-05-31"]
          }

        返回 JSON:
        {
          "code": 0,
          "msg": "succ",
          "data": [
            {
              "outid":  12,
              "outdate": "2025-05-29",
              "out_quantity":  50.00,
              "person_name": "张三",

              // —— 库存表字段 ——
              "inventoryid":          34,
              "product_name":         "原材料A",
              "product_size":         "规格X",
              "unit":                 "千克",       // 对应 choices
              "stock_quantity":       100,
              "brand":                "品牌Y",
              "material_certificate": "材质Z",
              "material_type":        "原材料",
              "stock_remark":         "库存备注"
            },
            … 下一条记录 …
          ],
          "total": 57
        }
        """
        # 1. 解析分页参数
        try:
            page_num = int(request.data.get("pageNum", 1))
            page_size = int(request.data.get("pageSize", 20))
        except (ValueError, TypeError):
            return JsonResponse({"code": 1, "msg": "分页参数必须是数字"}, status=400)

        sf = request.data.get("searchForm", {}) or {}

        # 2. 构造精确/范围过滤
        filters = {}
        if dr := sf.get("outdate__range"):
            if isinstance(dr, (list, tuple)) and len(dr) == 2:
                try:
                    start_date = datetime.datetime.strptime(dr[0], "%Y-%m-%d").date()
                    end_date = datetime.datetime.strptime(dr[1], "%Y-%m-%d").date()
                    filters["outdate__range"] = (start_date, end_date)
                except Exception:
                    pass

        # 3. 构造 Q 对象，用于全局模糊 AND
        kw_raw = (sf.get("search_data") or "").strip().replace("\u200b", "")
        q_obj = Q()
        if kw_raw:
            for kw in kw_raw.split():
                sub_q = (
                    Q(person_name__icontains=kw) |
                    Q(outdate_str__icontains=kw) |
                    Q(inventoryid__product_name__icontains=kw) |
                    Q(inventoryid__product_size__icontains=kw) |
                    Q(inventoryid__brand__icontains=kw) |
                    Q(inventoryid__material_certificate__icontains=kw) |
                    Q(inventoryid__material_type__icontains=kw)
                )
                q_obj &= sub_q

        # 4. 查询并分页
        qs = (
            OutgoingWarehouseTable.objects
            # 4.1 范围过滤
            .filter(**filters)
            # 4.2 注入 outdate_str 便于模糊匹配
            .annotate(
                outdate_str=Cast("outdate", CharField())
            )
            # 4.3 全局模糊过滤
            .filter(q_obj)
            # 4.4 预取关联库存表，避免 N+1
            .select_related("inventoryid")
            .order_by("-outid")
        )

        total = qs.count()
        paginator = Paginator(qs, page_size)
        try:
            page = paginator.page(page_num)
        except:
            page = paginator.page(paginator.num_pages)

        # 5. 序列化输出，每条带上库存表字段
        data = []
        for rec in page:
            inv = rec.inventoryid  # InventoryTable 实例
            data.append({
                "outid":        rec.outid,
                "outdate":      rec.outdate.strftime("%Y-%m-%d") if rec.outdate else "",
                "quantity": float(rec.quantity),
                "person_name":  rec.person_name or "",

                # —— 库存表字段 ——
                "inventoryid":          inv.inventoryid,
                "product_name":         inv.product_name,
                "product_size":         inv.product_size,
                "unit_label":                 inv.get_unit_display(),
                "stock_quantity":       inv.quantity,
                "brand":                inv.brand or "",
                "material_certificate": inv.material_certificate or "",
                "material_type":        inv.material_type or "",
                "stock_remark":         inv.remark or ""
            })

        return JsonResponse({
            "code":  0,
            "msg":   "succ",
            "data":  data,
            "total": total
        })
    def __minus_quality(self, inventoryid, num):
        """ 减少库存数 """
        oldnum = InventoryTable.objects.filter(inventoryid=inventoryid).values('quantity')[0]['quantity']
        newnum = oldnum - int(num)
        InventoryTable.objects.filter(inventoryid=inventoryid).update(quantity=newnum)


    def addRecord(self, request):
        """
        支持：
        1) 单条插入： modalForm 是一个 dict
        2) 批量插入： modalForm 是一个 list，list 中每个元素都是 dict
        """
        modalForm = request.data.get('modalForm')

        # 先判断前端是否传了 modalForm
        if modalForm is None:
            return JsonResponse({
                'code': API_SYS_ERR,
                'msg': '请求参数缺失 modalForm',
                'data': ''
            })

        # 准备外键字段映射：形如 { 'inventoryid_id': ModelClass, ... }
        foreign_key_fields = {}
        for field in OutgoingWarehouseTable._meta.get_fields():
            if field.many_to_one:
                # field.name 是 'inventoryid'，Django 会自动生成 column 'inventoryid_id'
                # 这里我们把 key 设为 'inventoryid_id'
                foreign_key_fields[field.name + '_id'] = field.related_model

        # 定义一个内部函数：把一个单独的 record_dict 转成 ORM 创建所需的 kwargs
        def build_kwargs(record_dict):
            """
            record_dict 示例：
              {
                'outdate': '2025-06-01',
                'inventoryid_id': 123,
                'quantity': 10,
                'person_name': '张三'
              }
            返回一个字典，可以直接传给 .objects.create(**kwargs)
            """
            addForm = {}
            for key, value in record_dict.items():
                if key in foreign_key_fields:
                    # 如果字段名在外键映射里，比如 key == 'inventoryid_id'
                    # 那么我们要把它转换成 ORM 需要的外键对象
                    model_cls = foreign_key_fields[key]
                    # 传给 get 的参数形如 {'id': value}，只要主键名称和字段保持一致即可
                    # 例如 field.name == 'inventoryid'，那么 field.column == 'inventoryid_id'
                    # mmap = { 'inventoryid' : <int ID> }
                    mmap = { key[:-3]: value }
                    try:
                        obj = model_cls.objects.get(**mmap)
                    except model_cls.DoesNotExist:
                        raise ValueError(f"外键 {key[:-3]}={value} 不存在")
                    addForm[key[:-3]] = obj
                else:
                    # 普通字段直接赋值
                    addForm[key] = value
            return addForm

        # 如果前端传来了一个列表，我们就当“批量插入”处理
        if isinstance(modalForm, list):
            records = modalForm
        else:
            # 否则当成单个 dict
            records = [modalForm]

        # 把事务包裹一下：要么全部成功，要么全部回滚
        try:
            with transaction.atomic():
                for idx, record_dict in enumerate(records):
                    # 1. 简单校验：inventoryid_id、quantity、person_name 这些必须在 record_dict 中
                    #    注意：如果某一项校验不通过，可以抛异常让事务回滚
                    if 'inventoryid_id' not in record_dict:
                        raise ValueError(f"第 {idx + 1} 条缺少字段 inventoryid_id")
                    if 'quantity' not in record_dict:
                        raise ValueError(f"第 {idx + 1} 条缺少字段 quantity")
                    if 'person_name' not in record_dict:
                        raise ValueError(f"第 {idx + 1} 条缺少字段 person_name")
                    # 你还可以在这里加更多后端校验，例如：
                    # if record_dict['quantity'] <= 0: ...

                    # 2. 调用 __minus_quality 逻辑（假设它会根据 inventoryid_id 扣库存）
                    inventoryid = record_dict.get('inventoryid_id')
                    add_num = record_dict.get('quantity')
                    try:
                        # 如果 __minus_quality 也有异常，就会触发事务回滚
                        self.__minus_quality(inventoryid, add_num)
                    except Exception as e:
                        raise ValueError(f"第 {idx + 1} 条执行减库存失败：{str(e)}")

                    # 3. 转成 ORM 可用的 kwargs，然后插入数据库
                    addForm = build_kwargs(record_dict)
                    OutgoingWarehouseTable.objects.create(**addForm)

        except Exception as e:
            # 只要捕获到任何异常，整个事务会回滚
            logger.error(f"addRecord 出错: {str(e)}")
            return JsonResponse({
                'code': API_SYS_ERR,
                'msg': str(e),
                'data': ''
            })

        # 如果走到这里说明所有记录都已插入
        return JsonResponse({
            'code': API_OK,
            'msg': 'succ',
            'data': ''
        })
    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            OutgoingWarehouseTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        """
        只允许更新以下三个字段：
          - quantity
          - outdate
          - person_name

        前端需传：
          modalEditForm: {
            quantity: <新数量>,
            outdate: "<YYYY-MM-DD>",
            person_name: "<领料人>"
          }
          idmap: { "outid": <要修改的记录ID> }
        """
        modal_form = request.data.get("modalEditForm", {}) or {}
        idmap = request.data.get("idmap", {}) or {}

        # 只取这三个字段
        edit_kwargs = {}
        if "quantity" in modal_form:
            edit_kwargs["quantity"] = modal_form["quantity"]
        if "outdate" in modal_form:
            edit_kwargs["outdate"] = modal_form["outdate"]
        if "person_name" in modal_form:
            edit_kwargs["person_name"] = modal_form["person_name"]

        if not idmap:
            return JsonResponse({"code": 1, "msg": "缺少 idmap", "data": ""}, status=400)

        try:
            # 根据 idmap 定位记录并更新
            OutgoingWarehouseTable.objects.filter(**idmap).update(**edit_kwargs)
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({"code": 1, "msg": str(e), "data": ""})

        return JsonResponse({"code": 0, "msg": "succ", "data": ""})

    def getOptions(self, request):
        data = {}
        options = []
        for item in InventoryTable.objects.all().values('inventoryid'):
            options.append({'label': item['inventoryid'], 'value': item['inventoryid']})
        data['inventoryid_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)    
    