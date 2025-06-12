import json
from decimal import Decimal

from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from app.api_code import *
from app.models import WarehousEntryTable, IncomingWarehouseTable, InventoryTable, AttachmentFileTable
from app.models import SupplierTable
from app.models import UserTable
from loguru import logger
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

class WarehousEntryTableView(object):
    def query(self, request):
        # 1. 基本参数
        page_num   = int(request.data.get('pageNum', 1))
        page_size  = int(request.data.get('pageSize', 20))
        searchform = request.data.get('searchForm', {}) or {}

        # 2. 关键字 + 精确字段拆分
        keyword     = (searchform.pop('search_data', '') or '').strip()
        date_range  = searchform.pop('entry_date', None)     # 支持日期区间

        # 3. 组装 Q 条件
        q = Q()
        if keyword:
            q &= (
                Q(entry_number__icontains          = keyword) |
                Q(supplier_name__supplier_name__icontains = keyword) |
                Q(username__username__icontains    = keyword) |
                Q(entry_date__icontains    = keyword)
            )

        # 精确字段过滤
        for field, value in list(searchform.items()):
            if value in [None, '']:
                continue
            q &= Q(**{field: value})

        # 日期区间
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            q &= Q(entry_date__range = date_range)

        # 4. 查询
        queryset = (
            WarehousEntryTable.objects
            .select_related('supplier_name', 'username')
            .filter(q)
            .order_by('-entry_date')
            .values(
                'entryid', 'entry_number',
                'supplier_name_id', 'supplier_name__supplier_name',
                'username_id', 'username__username',
                'filename', 'entry_date'
            )
        )

        # 5. 分页
        paginator  = Paginator(queryset, page_size)
        page_data  = paginator.page(page_num)

        # 6. 整理结果
        data = []
        for item in page_data:
            item['supplier_label'] = item.pop('supplier_name__supplier_name')
            item['username_label'] = item.pop('username__username')
            data.append(item)

        # 7. 返回
        return JsonResponse({
            'code' : 0,
            'msg'  : 'success',
            'data' : data,
            'total': paginator.count
        })
    @transaction.atomic
    def addRecord(self, request):
        """
        新单据一次性写入：
          1) 创建 WarehousEntryTable（表头）
          2) 批量创建 IncomingWarehouseTable（明细）
        request.data:
          - modalForm   : 表头字段
          - inTableData : [{inventoryid_id, quantity, unit_price, ...}, ...]
        """
        # 因为前端是用 FormData 且把 modalForm/inTableData 当字符串发送，需要先 JSON 解析：
        try:
            modal = json.loads(request.data.get('modalForm', '{}'))
        except Exception as e:
            return JsonResponse({'code': 1, 'msg': '表头 JSON 解析失败: ' + str(e), 'data': ''})
        try:
            rows = json.loads(request.data.get('inTableData', '[]'))
        except Exception as e:
            return JsonResponse({'code': 1, 'msg': '明细 JSON 解析失败: ' + str(e), 'data': ''})

            # ── 0 校验 ────────────────────────────
        if not rows:
            return JsonResponse({'code': 1, 'msg': '明细不能为空', 'data': ''})

        # ── 1 解析外键字段（表头）──────────────
        fk_models = {
            f.name + '_id': f.related_model
            for f in WarehousEntryTable._meta.get_fields() if f.many_to_one
        }
        add_form = {}
        for k, v in modal.items():
            if k in fk_models:
                obj = fk_models[k].objects.get(**{k[:-3]: v})
                add_form[k[:-3]] = obj            # id → 对象
            else:
                add_form[k] = v

        # ── 2 创建表头 ────────────────────────
        try:
            entry = WarehousEntryTable.objects.create(**add_form)
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': 1, 'msg': str(e), 'data': ''})

        # ── 3 生成明细对象列表 ────────────────
        new_objs = []
        for idx, r in enumerate(rows, 1):
            try:
                inv = InventoryTable.objects.get(pk=r['inventoryid_id'])
            except InventoryTable.DoesNotExist:
                return JsonResponse({
                    'code': 1,
                    'msg' : f'第{idx}行 inventoryid {r["inventoryid_id"]} 不存在',
                    'data': ''
                })

            new_objs.append(
                IncomingWarehouseTable(
                    entry_number = entry,                  # 外键对象
                    inventoryid  = inv,
                    quantity     = Decimal(str(r['quantity'])),
                    remark       = r.get('remark', '')
                )
            )

        # ── 4 批量写入明细 ───────────────────
        IncomingWarehouseTable.objects.bulk_create(new_objs)
        # ── 5 保存附件 ───────────────────────────
        # 前端用 FormData 并多次 append('attachments', file)，Django 用 getlist 拿到所有文件
        files = request.FILES.getlist('attachments')
        for f in files:
            AttachmentFileTable.objects.create(
                parent=entry,  # GenericForeignKey 指向 WarehousEntryTable 实例
                file=f,
                filename=f.name,  # 原始文件名
                file_size=f.size
            )
        # ── 5 返回成功 ───────────────────────
        return JsonResponse({'code': 0, 'msg': 'succ', 'data': ''})

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            WarehousEntryTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    @transaction.atomic
    def editRecord(self, request):
        """
        整单编辑（表头 + 明细）+ 附件同步：
        1) 更新 WarehousEntryTable 表头
        2) 删除旧明细并批量写入新明细
        3) 处理附件：
           - keep_attachment_ids: 保留哪些旧附件
           - edited_attachments: [{ id, filename }, …]  对应旧附件重命名
           - request.FILES.getlist('attachments') 中的才是“新上传”文件 → 创建新的 AttachmentFileTable
        """

        # ── 0. 拆字段 ──────────────────────────
        raw_modal = request.data.get('modalForm', '{}')
        raw_rows  = request.data.get('inTableData', '[]')

        # 0.1 JSON 解析
        try:
            modalForm   = json.loads(raw_modal)
        except json.JSONDecodeError as e:
            return JsonResponse({'code': 1, 'msg': f'表头 JSON 解析失败: {e}', 'data': ''})
        try:
            detail_rows = json.loads(raw_rows)
        except json.JSONDecodeError as e:
            return JsonResponse({'code': 1, 'msg': f'明细 JSON 解析失败: {e}', 'data': ''})

        entry_number = modalForm.get('entry_number')
        if not entry_number:
            return JsonResponse({'code': 1, 'msg': '缺少 entry_number', 'data': ''})

        # 0.2 提取附件相关参数（前端用 FormData 发送）：
        #     keep_attachment_ids = 列表 或 空
        #     edited_attachments = 列表 of { "id": X, "filename": "newname.ext" }
        #     新文件列表从 request.FILES.getlist('attachments') 拿
        keep_ids_raw = modalForm.get('keep_attachment_ids', [])
        edited_raw   = modalForm.get('edited_attachments', [])

        # 可能前端直接传 list，也可能是字符串形式的 JSON，需要确保它们是 Python list
        try:
            keep_ids = json.loads(keep_ids_raw) if isinstance(keep_ids_raw, str) else keep_ids_raw
        except:
            keep_ids = []
        try:
            edited = json.loads(edited_raw) if isinstance(edited_raw, str) else edited_raw
        except:
            edited = []

        # ── 1. 更新表头 ─────────────────────────────
        # 构造要更新的字段，走外键映射逻辑
        foreign_key_fields = {}
        for f in WarehousEntryTable._meta.get_fields():
            if f.many_to_one:
                foreign_key_fields[f.name + '_id'] = f.related_model

        update_fields = {}
        for k, v in modalForm.items():
            if k in foreign_key_fields:
                try:
                    obj = foreign_key_fields[k].objects.get(**{k[:-3]: v})
                except foreign_key_fields[k].DoesNotExist:
                    return JsonResponse({'code': 1, 'msg': f'外键 {k} 对应对象不存在', 'data': ''})
                update_fields[k[:-3]] = obj
            else:
                update_fields[k] = v

        try:
            entry = (
                WarehousEntryTable.objects
                .select_for_update()
                .get(entry_number=entry_number)
            )
        except WarehousEntryTable.DoesNotExist:
            return JsonResponse({'code': 1, 'msg': '入库单不存在', 'data': ''})

        for attr, value in update_fields.items():
            setattr(entry, attr, value)
        entry.save()

        # ── 2. 删除旧明细 & 批量写入新明细 ─────────────────────────────
        IncomingWarehouseTable.objects.filter(entry_number=entry).delete()

        new_objs = []
        for idx, row in enumerate(detail_rows, 1):
            try:
                inv = InventoryTable.objects.get(pk=row['inventoryid_id'])
            except InventoryTable.DoesNotExist:
                return JsonResponse({
                    'code': 1,
                    'msg': f'第 {idx} 行 inventoryid {row["inventoryid_id"]} 不存在',
                    'data': ''
                })

            new_objs.append(
                IncomingWarehouseTable(
                    entry_number = entry,
                    inventoryid  = inv,
                    quantity     = row['quantity'],
                    remark       = row.get('remark', '')
                )
            )
        IncomingWarehouseTable.objects.bulk_create(new_objs)

        # ── 3. 处理附件 ────────────────────────────────────────

        # 3.1 先找到该入库单下所有“现存”附件 qs_all
        qs_all = AttachmentFileTable.objects.filter(
            content_type=ContentType.objects.get_for_model(WarehousEntryTable),
            object_id=entry.pk
        )

        # 3.2 如果前端给了 keep_ids，就删除那些不在 keep_ids 里的旧附件
        if keep_ids:
            qs_all.exclude(pk__in=keep_ids).delete()
        else:
            # 如果前端不想保留任何旧附件，一口气删光
            qs_all.delete()

        # 3.3 对于留存的旧附件，如果前端改了文件名，就更新它们的 filename 字段
        for item in edited:
            aid = item.get('id')
            new_name = item.get('filename', '').strip()
            if aid and new_name:
                AttachmentFileTable.objects.filter(pk=aid).update(filename=new_name)

        # 3.4 把前端新上传的文件存入 AttachmentFileTable
        for f in request.FILES.getlist('attachments'):
            AttachmentFileTable.objects.create(
                parent     = entry,       # GenericForeignKey 指向 WarehousEntryTable
                file       = f,
                filename   = f.name,
                file_size  = f.size
            )

        # ── 4. 返回成功 ─────────────────────────────────────
        return JsonResponse({'code': 0, 'msg': 'editRecord ok', 'data': ''})

    def getOptions(self, request):
        data = {}
        options = []
        for item in SupplierTable.objects.all().values('supplier_name'):
            options.append({'label': item['supplier_name'], 'value': item['supplier_name']})
        data['supplier_name_options'] = options
        options = []
        for item in UserTable.objects.all().values('username'):
            options.append({'label': item['username'], 'value': item['username']})
        data['username_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)    
    