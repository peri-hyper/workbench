# app/views/attachment.py
import io, zipfile, mimetypes
import json
from datetime import datetime
from pathlib import Path
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from app.models import AttachmentFileTable, PurchaseTable, WarehousEntryTable, ShippingTable
from app.models import ShippingTable, AttachmentFileTable
import io, zipfile, mimetypes
from pathlib import Path
from django.http import FileResponse, Http404, JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework import status

SHIPPING_CT = ContentType.objects.get_for_model(ShippingTable)


# ---------------- 辅助函数 ----------------
def _parse_int_list(raw, field_name):
    """
    把 [1, '2', 3] 或 '1,2,3' 统一转成去重整数列表
    """
    if isinstance(raw, str):
        raw = raw.split(',')
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f'{field_name} 必须是列表')

    try:
        return list({int(x) for x in raw if str(x).strip()})
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} 内必须都是整数')


def _unique_name(zip_file, filename):
    """
    若 zip 内已有同名文件，自动加 (1)、(2)…，避免覆盖
    """
    base, ext = Path(filename).stem, Path(filename).suffix
    n = 0
    new_name = filename
    while new_name in zip_file.namelist():
        n += 1
        new_name = f'{base}({n}){ext}'
    return new_name
class AttachmentFileView(APIView):
    """
    action = 'attachment_file_view'
    """

    def post(self, request, *args, **kwargs):
        subaction = request.data.get('subaction')
        if subaction == 'query':
            return self.query(request)
        if subaction == 'download':
            return self.download(request)
        if subaction == 'delete':
            return self.delete(request)

        return Response(
            {'code': 1, 'msg': f'Unsupported subaction: {subaction}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ────────────────────────────────────────────────────────────
    def _get_parent_ct_and_oid(self, search: dict):
        """
        把 searchForm 解析成 (ContentType, object_id)
        允许两种写法：
          A) {'model': 'app.PurchaseTable', 'pk': 23}
          B) {'model': 'app.PurchaseTable', 'purchase_number': 'xxx'}
        """
        model_path = search.get('model')
        if not model_path:
            raise ValueError('缺少 model')

        try:
            app_label, model_name = model_path.split('.')
            model_cls = apps.get_model(app_label, model_name)
        except (ValueError, LookupError):
            raise ValueError('model 不存在')

        ct = ContentType.objects.get_for_model(model_cls)

        # ① 主键
        if 'pk' in search:
            return ct, search['pk']

        # ② 业务字段（以 purchase_number 为例）
        if 'purchase_number' in search:
            parent = model_cls.objects.filter(
                purchase_number=search['purchase_number']
            ).only('pk').first()
            if not parent:
                raise Http404('父记录不存在')
            return ct, parent.pk

        if 'entry_number' in search:
            parent = model_cls.objects.filter(
                entry_number=search['entry_number']
            ).only('pk').first()
            if not parent:
                raise Http404('父记录不存在')
            return ct, parent.pk

        if 'shippingid' in search:
            parent = model_cls.objects.filter(
                shippingid=search['shippingid']
            ).only('pk').first()
            if not parent:
                raise Http404('父记录不存在')
            return ct, parent.pk

        if 'orderid' in search:
            parent = model_cls.objects.filter(
                orderid=search['orderid']
            ).only('pk').first()
            if not parent:
                raise Http404('父记录不存在')
            return ct, parent.pk

        raise ValueError('缺少 pk 或业务字段')

    # ───────────────── 查询 ─────────────────
    def query(self, request):
        try:
            page_num  = int(request.data.get('pageNum', 1))
            page_size = int(request.data.get('pageSize', 20))
        except ValueError:
            return Response({'code': 1, 'msg': '分页参数必须是数字'}, 400)

        try:
            ct, oid = self._get_parent_ct_and_oid(request.data.get('searchForm', {}))
        except (ValueError, Http404) as e:
            return Response({'code': 1, 'msg': str(e)}, 400)

        qs = AttachmentFileTable.objects.filter(
            content_type=ct, object_id=oid
        ).order_by('-upload_time')

        total  = qs.count()
        offset = (page_num - 1) * page_size
        page   = qs[offset: offset + page_size]

        data = [
            {
                'attachmentid': a.attachmentid,
                'filename':     a.filename,
                'file_size':    a.file_size,
                'object_id':    a.object_id,
                'stored_name': Path(a.file.name).name,  # 磁盘名（包括随机前缀）
                'upload_time':  datetime.strftime(a.upload_time, '%Y-%m-%d %H:%M:%S'),
            } for a in page
        ]
        return Response({'code': 0, 'msg': 'succ', 'data': data, 'total': total})

    # ───────────────── 下载 ─────────────────
    def download(self, request):
        att_id = request.data.get('id')
        if not att_id:
            return Response({'code': 1, 'msg': '缺少 id'}, 400)

        try:
            att = AttachmentFileTable.objects.get(pk=att_id)
        except AttachmentFileTable.DoesNotExist:
            raise Http404

        # FileResponse 会在 chunk 方式回传，不占内存
        file_handle = att.file.open('rb')
        content_type, _ = mimetypes.guess_type(att.filename)
        response = FileResponse(file_handle, as_attachment=True, filename=Path(att.filename).name)
        if content_type:
            response['Content-Type'] = content_type
        return response

    # ───────────────── 删除 ─────────────────
    @transaction.atomic
    def delete(self, request):
        att_id = request.data.get('id')
        if not att_id:
            return Response({'code': 1, 'msg': '缺少 id'}, 400)

        try:
            att = AttachmentFileTable.objects.select_for_update().get(pk=att_id)
        except AttachmentFileTable.DoesNotExist:
            raise Http404

        # 1) 物理文件删掉 (Storage API)
        att.file.delete(save=False)
        # 2) 数据库记录删掉
        att.delete()
        # 删除完以后
        if not AttachmentFileTable.objects.filter(
                content_type_id=SHIPPING_CT.id,
                object_id=att_id).exists():
            ShippingTable.objects.filter(shippingid=att_id).update(sign_back=1)
        return Response({'code': 0, 'msg': 'deleted'})

    @transaction.atomic
    def bulk_delete(self, request):
        ids = request.data.get('ids')
        if not isinstance(ids, (list, tuple)) or not ids:
            return Response({'code': 1, 'msg': 'ids 必须是非空列表'}, 400)

        try:
            ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            return Response({'code': 1, 'msg': 'ids 必须都是整数'}, 400)

        # ------- ① 先拿到准备删除的附件 queryset -------
        qs = AttachmentFileTable.objects.filter(pk__in=ids)

        # 只关心属于 ShippingTable 的附件（别的模型可忽略）
        shipping_ids = list(
            qs.filter(content_type_id=SHIPPING_CT.id).values_list('object_id', flat=True)
        )

        if not qs.exists():
            return Response({'code': 1, 'msg': '附件不存在'}, 404)

        # ------- ② 删除物理文件（可选） -------
        for att in qs:
            if att.file:
                att.file.delete(save=False)

        # ------- ③ 删除数据库记录 -------
        deleted_cnt, _ = qs.delete()

        # ------- ④ 对每个 shippingid 检查剩余附件数 -------
        for sid in set(shipping_ids):
            has_left = AttachmentFileTable.objects.filter(
                content_type_id=SHIPPING_CT.id,
                object_id=sid
            ).exists()

            if not has_left:
                ShippingTable.objects.filter(shippingid=sid).update(sign_back=1)

        return Response({'code': 0, 'msg': 'succ', 'deleted': deleted_cnt})

    @transaction.atomic
    def edit(self, request):
        """
        POST 例子
        {
          "action": "attachment_file_view",
          "subaction": "edit",
          "files": [
            {"attachmentid": 17, "filename": "合同.pdf",  "remark": "客户 A"},
            {"attachmentid": 22, "filename": "装箱单.xlsx", "remark": "客户 B"},
            ...
          ]
        }
        """
        files = request.data.get('files')
        if not isinstance(files, list) or not files:
            return Response({'code': 1, 'msg': 'files 必须是非空列表'}, 400)

        # 1) 解析 ID 列表，构成 {id: payload}
        try:
            update_map = {
                int(item['attachmentid']): item  # item = {"attachmentid":17, ...}
                for item in files
                if 'attachmentid' in item
            }
        except (TypeError, ValueError):
            return Response({'code': 1, 'msg': 'attachmentid 必须是整数'}, 400)

        ids = list(update_map.keys())
        if not ids:
            return Response({'code': 1, 'msg': '没有合法 attachmentid'}, 400)

        # 2) 一次性取出所有实例
        atts = list(AttachmentFileTable.objects.filter(pk__in=ids))
        if len(atts) != len(ids):
            return Response({'code': 1, 'msg': '存在非法 attachmentid'}, 400)

        # 3) 修改内存对象
        editable_fields = {'filename', 'remark'}  # 允许被改的字段
        touched_fields = set()  # 统计到底改了哪些字段

        for att in atts:
            payload = update_map[att.pk]
            for field in editable_fields:
                if field in payload:
                    old_val = getattr(att, field)
                    new_val = payload[field].strip()
                    if new_val != old_val:
                        setattr(att, field, new_val)
                        touched_fields.add(field)

        if not touched_fields:
            return Response({'code': 0, 'msg': '无字段改动', 'updated': 0})

        # 4) bulk_update —— 一条 SQL
        AttachmentFileTable.objects.bulk_update(atts, list(touched_fields))

        return Response({'code': 0, 'msg': 'succ', 'updated': len(atts)})
    # ───────────────── 批量下载 ─────────────────

    def batch_download(self, request):
        """
        支持两种入参（二选一，优先 ids）：
          ① ids          = [17, 18, 22]                # 直接附件主键
          ② shippingids  = [42, 43]                    # 送货单 pk，自动取其附件

        返回：
          application/zip   attachments.zip
        """
        ids_param = request.data.get('ids')
        shippingids_param = request.data.get('shippingids')

        # -------- 1. 收集需要下载的附件 queryset --------
        if ids_param:
            ids = _parse_int_list(ids_param, 'ids')  # helper 在下方
            qs = AttachmentFileTable.objects.filter(pk__in=ids)

        elif shippingids_param:
            sids = _parse_int_list(shippingids_param, 'shippingids')
            qs = AttachmentFileTable.objects.filter(
                content_type_id=SHIPPING_CT.id,
                object_id__in=sids
            )
        else:
            return JsonResponse({'code': 1, 'msg': 'ids 或 shippingids 至少传一个'}, status=400)

        if not qs.exists():
            return JsonResponse({'code': 1, 'msg': '附件不存在'}, status=404)

        # -------- 2. 打 ZIP （全内存，附件通常体量较小；若超大改用临时文件流） --------
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for att in qs:
                # 去掉同名冲突：若重名自动加 (1)
                arc_name = _unique_name(zf, att.filename)
                zf.writestr(arc_name, att.file.read())

        buf.seek(0)

        # -------- 3. 流式返回 --------
        resp = FileResponse(buf, as_attachment=True, filename='attachments.zip')
        resp['Content-Type'] = 'application/zip'
        return resp



    def purchasetable_query(self, request):
        """
        针对 model='app.PurchaseTable' 的附件表 AttachmentFileTable 分页查询，
        并附带父表 PurchaseTable 的信息，同时支持前端 vxe-form 中的两个搜索条件：
          1) search_data: 全局关键词，对下列字段做模糊 AND：
               - PurchaseTable.supplier_name__supplier_name
               - PurchaseTable.purchase_number
               - PurchaseTable.username__username
               - PurchaseTable.purchase_date（字符串 icontains）
               - AttachmentFileTable.filename
               - AttachmentFileTable.file（存储全名，含随机前缀）
          2) purchase_date__range: ["YYYY-MM-DD","YYYY-MM-DD"]，对父表 PurchaseTable.purchase_date 范围过滤

        前端传参（JSON body）：
          pageNum              int, 默认为 1
          pageSize             int, 默认为 20
          searchForm: {
            search_data:       str, 全局搜索关键词
            purchase_date__range: [str, str], 如 ["2025-05-01","2025-05-31"]
          }

        返回 JSON:
          {
            "code":  0,
            "msg":   "succ",
            "data": [
              {
                "attachmentid": 1,
                "filename": "报价单.pdf",
                "file_size": 102400,
                "object_id": 123,
                "stored_name": "a1b2c3d4ef_报价单.pdf",
                "upload_time": "2025-05-30 14:22:10",
                "purchaseid": 123,
                "purchase_number": "PO2025052901",
                "username": "zhangsan",
                "supplier_name": "供应商A",
                "contact_person": "李四",
                "contact_number": "13800138000",
                "purchase_date": "2025-05-29",
                "currency": "CNY",
                "AOG_status": 1,
                "parent_remark": "父表备注"
              },
              … 下一条记录 …
            ],
            "total": 42
          }
        """
        # 1. 解析分页参数
        try:
            page_num = int(request.data.get("pageNum", 1))
            page_size = int(request.data.get("pageSize", 20))
        except (ValueError, TypeError):
            return Response({"code": 1, "msg": "分页参数必须是数字"}, status=400)

        # 2. 解析 searchForm
        sf = request.data.get("searchForm", {}) or {}
        kw_raw = (sf.get("search_data") or "").strip().replace("\u200b", "")
        date_range = sf.get("purchase_date__range")  # 例如 ["2025-05-01","2025-05-31"]

        # 3. 确定 ContentType，锁定只查 PurchaseTable 关联的附件
        try:
            ct = ContentType.objects.get(app_label="app", model="purchasetable")
        except ContentType.DoesNotExist:
            return Response({"code": 1, "msg": "未找到 PurchaseTable 对应的 ContentType"}, status=500)

        # 4. 初始 QuerySet 仅筛选 content_type=PurchaseTable
        qs = AttachmentFileTable.objects.filter(content_type=ct)

        # 5. 如果传了采购日期范围，先过滤父表 PurchaseTable，得到符合范围的父表 ID 列表
        if date_range and isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            try:
                start_dt = datetime.strptime(date_range[0], "%Y-%m-%d").date()
                end_dt = datetime.strptime(date_range[1], "%Y-%m-%d").date()
                parent_ids = PurchaseTable.objects.filter(
                    purchase_date__gte=start_dt,
                    purchase_date__lte=end_dt
                ).values_list("purchaseid", flat=True)
                qs = qs.filter(object_id__in=list(parent_ids))
            except ValueError:
                pass

        # 6. 如果存在全局关键词，构造 Q 对象，但需要分开“AttachmentFileTable 字段”和“父表 PurchaseTable 字段”两种情况：
        if kw_raw:
            # 每个关键字对应一个子 Q，再把它们 AND 级联
            combined_q = Q()
            for kw in kw_raw.split():
                # 6.1 在附件表本身做模糊
                sub_q = Q(filename__icontains=kw) | Q(file__icontains=kw)

                # 6.2 在父表 PurchaseTable 做模糊，需要先查询父表符合条件的 purchaseid 列表
                parent_match_ids = PurchaseTable.objects.filter(
                    Q(supplier_name__supplier_name__icontains=kw) |
                    Q(purchase_number__icontains=kw) |
                    Q(username__username__icontains=kw) |
                    Q(purchase_date__icontains=kw)
                ).values_list("purchaseid", flat=True)
                if parent_match_ids:
                    sub_q |= Q(object_id__in=list(parent_match_ids))

                # 6.3 把该关键字的 sub_q 加入 combined_q（AND 逻辑）
                combined_q &= sub_q

            qs = qs.filter(combined_q)

        # 7. 排序
        qs = qs.order_by("-upload_time")

        # 8. 分页
        total = qs.count()
        paginator = Paginator(qs, page_size)
        try:
            page = paginator.page(page_num)
        except:
            page = paginator.page(paginator.num_pages)

        # 9. 批量获取父表 PurchaseTable，避免 N+1 查询
        object_ids = [a.object_id for a in page]
        parent_map = {}
        if object_ids:
            parents = PurchaseTable.objects.filter(purchaseid__in=object_ids) \
                .select_related("supplier_name", "username")
            parent_map = {p.purchaseid: p for p in parents}

        # 10. 构造返回数据
        data = []
        for a in page:
            parent = parent_map.get(a.object_id)
            item = {
                "attachmentid": a.attachmentid,
                "filename": a.filename,
                "file_size": a.file_size,
                "object_id": a.object_id,
                "stored_name": Path(a.file.name).name,
                "upload_time": a.upload_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            if parent:
                item.update({
                    "purchaseid": parent.purchaseid,
                    "purchase_number": parent.purchase_number,
                    "purchaser": parent.username.username if parent.username else "",
                    "supplier_name": parent.supplier_name.supplier_name if parent.supplier_name else "",
                    "contact_person": parent.contact_person or "",
                    "contact_number": parent.contact_number or "",
                    "purchase_date": parent.purchase_date.strftime("%Y-%m-%d") if parent.purchase_date else "",
                    "currency": parent.currency or "",
                    "AOG_status": parent.AOG_status,
                    "parent_remark": parent.remark or "",
                })
            data.append(item)

        # 11. 返回 JSON
        return Response({
            "code": 0,
            "msg": "succ",
            "data": data,
            "total": total
        })

    def entry_warehouse_query(self, request):
        """
        针对 model='app.WarehousEntryTable' 的附件表 AttachmentFileTable 分页查询，
        并附带父表 WarehousEntryTable 的信息，同时支持前端 vxe-form 中的两个搜索条件：
          1) search_data: 全局关键词，对下列字段做模糊 AND：
               - WarehousEntryTable.supplier_name__supplier_name
               - WarehousEntryTable.entry_number
               - WarehousEntryTable.username__username
               - WarehousEntryTable.entry_date（字符串 icontains）
               - AttachmentFileTable.filename
               - AttachmentFileTable.file（存储全名，含随机前缀）
          2) entry_date__range: ["YYYY-MM-DD","YYYY-MM-DD"]，对父表 WarehousEntryTable.entry_date 范围过滤

        前端传参（JSON body）：
          pageNum            int, 默认为 1
          pageSize           int, 默认为 20
          searchForm: {
            search_data:       str, 全局搜索关键词
            entry_date__range: [str, str], 如 ["2025-05-01","2025-05-31"]
          }

        返回 JSON:
          {
            "code": 0,
            "msg": "succ",
            "data": [
              {
                "attachmentid": 1,
                "filename": "示例.pdf",
                "file_size": 102400,
                "object_id": 5,
                "stored_name": "abc123_示例.pdf",
                "upload_time": "2025-05-30 14:22:10",
                "entryid": 5,
                "entry_number": "E2025053001",
                "username": "zhangsan",
                "supplier_name": "供应商A",
                "parent_filename": "入库单_E2025053001.pdf",
                "entry_date": "2025-05-29"
              },
              … 下一条记录 …
            ],
            "total": 42
          }
        """
        # 1. 解析分页参数
        try:
            page_num = int(request.data.get("pageNum", 1))
            page_size = int(request.data.get("pageSize", 20))
        except (ValueError, TypeError):
            return Response({"code": 1, "msg": "分页参数必须是数字"}, status=400)

        # 2. 解析 searchForm
        sf = request.data.get("searchForm", {}) or {}
        kw_raw = (sf.get("search_data") or "").strip().replace("\u200b", "")
        date_range = sf.get("entry_date__range")  # 例如 ["2025-05-01","2025-05-31"]

        # 3. 确定 ContentType，锁定只查 WarehousEntryTable 关联的附件
        try:
            ct = ContentType.objects.get(app_label="app", model="warehousentrytable")
        except ContentType.DoesNotExist:
            return Response({"code": 1, "msg": "未找到 WarehousEntryTable 对应的 ContentType"}, status=500)

        # 4. 初始 QuerySet 仅筛选 content_type=WarehousEntryTable
        qs = AttachmentFileTable.objects.filter(content_type=ct)

        # 5. 如果传了入库日期范围，先过滤父表 WarehousEntryTable，得到符合范围的父表 ID 列表
        if date_range and isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            try:
                start_dt = datetime.datetime.strptime(date_range[0], "%Y-%m-%d").date()
                end_dt = datetime.datetime.strptime(date_range[1], "%Y-%m-%d").date()
                parent_ids = WarehousEntryTable.objects.filter(
                    entry_date__gte=start_dt,
                    entry_date__lte=end_dt
                ).values_list("entryid", flat=True)
                qs = qs.filter(object_id__in=list(parent_ids))
            except ValueError:
                pass

        # 6. 如果存在全局关键词，构造 Q 对象，分开附件表字段和父表字段两类情况
        if kw_raw:
            combined_q = Q()
            for kw in kw_raw.split():
                # 6.1 在附件表本身做模糊
                sub_q = Q(filename__icontains=kw) | Q(file__icontains=kw)

                # 6.2 在父表 WarehousEntryTable 做模糊，需要先查询父表符合条件的 entryid 列表
                parent_match_ids = WarehousEntryTable.objects.filter(
                    Q(supplier_name__supplier_name__icontains=kw) |
                    Q(entry_number__icontains=kw) |
                    Q(username__username__icontains=kw) |
                    Q(entry_date__icontains=kw)
                ).values_list("entryid", flat=True)
                if parent_match_ids:
                    sub_q |= Q(object_id__in=list(parent_match_ids))

                # 6.3 把该关键字的 sub_q 加入 combined_q（AND 逻辑）
                combined_q &= sub_q

            qs = qs.filter(combined_q)

        # 7. 排序
        qs = qs.order_by("-upload_time")

        # 8. 分页
        total = qs.count()
        paginator = Paginator(qs, page_size)
        try:
            page = paginator.page(page_num)
        except:
            page = paginator.page(paginator.num_pages)

        # 9. 批量获取父表 WarehousEntryTable，避免 N+1 查询
        object_ids = [a.object_id for a in page]
        parent_map = {}
        if object_ids:
            parents = WarehousEntryTable.objects.filter(entryid__in=object_ids) \
                .select_related("supplier_name", "username")
            parent_map = {p.entryid: p for p in parents}

        # 10. 构造返回数据
        data = []
        for a in page:
            parent = parent_map.get(a.object_id)
            item = {
                "attachmentid": a.attachmentid,
                "filename":     a.filename,
                "file_size":    a.file_size,
                "object_id":    a.object_id,
                "stored_name":  Path(a.file.name).name,
                "upload_time":  a.upload_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            if parent:
                item.update({
                    "entryid":        parent.entryid,
                    "entry_number":   parent.entry_number,
                    "username":       parent.username.username if parent.username else "",
                    "supplier_name":  parent.supplier_name.supplier_name if parent.supplier_name else "",
                    "parent_filename": parent.filename or "",
                    "entry_date":     parent.entry_date.strftime("%Y-%m-%d") if parent.entry_date else ""
                })
            data.append(item)

        # 11. 返回 JSON
        return Response({
            "code":  0,
            "msg":   "succ",
            "data":  data,
            "total": total
        })
    @transaction.atomic
    def add(self, request):
        """
        前端请求示例（multipart/form-data）：
          subaction     = add
          searchForm    = {"model":"app.PurchaseTable","pk":23}       # 字符串 JSON
          maxCount      = 3        # 可选，不传表示不限
          files         = <FileList>  # 可多选

        成功返回：
          {"code":0,"msg":"succ","data":[
              {"attachmentid":1,"filename":"报价单.pdf","file_size":102400,
               "upload_time":"2025-06-04 15:20:11"}
          ]}
        """
        # 1. 解析 searchForm，找到父记录
        try:
            sf_json = json.loads(request.data.get('searchForm', '{}'))
            ct, oid_raw = self._get_parent_ct_and_oid(sf_json)
            print(ct)
            print(oid_raw)
            try:
                oid = int(oid_raw)  # '23' / 23 都 OK；[] / ['23'] 会抛异常
            except (TypeError, ValueError):
                return Response({'code': 1, 'msg': '非法 pk'}, 400)
        except (ValueError, Http404) as e:
            return Response({'code' : 1, 'msg': str(e)}, 400)

        # 2. 拿到上传文件列表
        files = request.FILES.getlist('files')
        if not files:
            return Response({'code': 1, 'msg': '缺少文件'}, 400)

        # 3. 判断附件数量上限（可选）
        max_cnt = request.data.get('maxCount')
        if max_cnt and max_cnt != 'Infinity':
            try:
                max_cnt = int(max_cnt)
            except ValueError:
                return Response({'code': 1, 'msg': 'maxCount 必须是整数'}, 400)

            exist_cnt = AttachmentFileTable.objects.filter(
                content_type=ct, object_id=oid
            ).count()
            if exist_cnt + len(files) > max_cnt:
                return Response({'code': 1, 'msg': '超出允许上传的数量'}, 400)
        # attachment_file_view.add 或 bulk_sync 成功保存附件后
        if sf_json.get('model') == 'app.ShippingTable':
            print(oid)
            ShippingTable.objects.filter(shippingid=oid).update(sign_back=2)

        # 4. 保存文件
        created = []
        for f in files:
            att = AttachmentFileTable.objects.create(
                content_type=ct,
                object_id=oid,
                filename=f.name,
                file_size=f.size,
                file=f,                 # Django Storage 会自动保存
            )
            created.append({
                'attachmentid': att.attachmentid,
                'filename':     att.filename,
                'file_size':    att.file_size,
                'upload_time':  att.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
            })

        return Response({'code': 0, 'msg': 'succ', 'data': created})