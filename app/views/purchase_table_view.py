import os

from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from app.models import PurchaseTable, RequestBuyTable, PurchaseDetailTable
from app.models import UserTable
from app.models import SupplierTable
from loguru import logger
from django.db.models import Q
import io
import os
import zipfile

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, Http404
from rest_framework.response import Response

from app.models import PurchaseTable, PurchaseDetailTable
from app.util.purchase_excel_utils import genereate_excel
from django_websvr import settings


class PurchaseTableView(object):
    def query(self, request):
        # ---------- 1. 基本参数 ----------
        page_num   = int(request.data.get('pageNum', 1))
        page_size  = int(request.data.get('pageSize', 20))
        searchform = request.data.get('searchForm', {}) or {}

        # ---------- 2. 取出关键字，剩余的都是精确条件 ----------
        keyword = (searchform.pop('search_data', '') or '').strip()

        # 如果有日期区间前端可传 {"purchase_date": ["2024-01-01","2024-01-31"]}
        date_range = searchform.pop('purchase_date', None)

        # ---------- 3. 组装 Q 条件 ----------
        q = Q()

        # 3-1 关键字模糊
        if keyword:
            q &= (
                Q(purchase_number__icontains = keyword) |
                Q(username__username__icontains = keyword) |
                Q(supplier_name__supplier_name__icontains = keyword) |
                Q(contact_person__icontains = keyword) |
                Q(contact_number__icontains = keyword) |
                Q(remark__icontains = keyword) |
                Q(purchase_date__icontains=keyword)
            )

        # 3-2 其它精确字段（AOG_status、currency …）
        for field, value in list(searchform.items()):
            if value in [None, '']:
                continue
            q &= Q(**{field : value})

        # 3-3 采购日期范围
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start, end = date_range
            q &= Q(purchase_date__range = (start, end))

        # ---------- 4. 查询 ----------
        queryset = (
            PurchaseTable.objects
            .select_related('username', 'supplier_name')
            .filter(q)
            .order_by('-purchase_date')
            .values(
                'purchaseid', 'purchase_number', 'username__username',
                'supplier_name__supplier_name', 'contact_person',
                'contact_number', 'purchase_date', 'currency',
                'AOG_status', 'remark'
            )
        )

        # ---------- 5. 分页 ----------
        paginator = Paginator(queryset, page_size)
        page_data = paginator.page(page_num)

        # ---------- 6. 补中文标签 ----------
        status_map = {1: '未到货', 2: '已到货'}
        result = []
        for item in page_data:
            item['username_id']      = item.pop('username__username')
            item['supplier_name_id'] = item.pop('supplier_name__supplier_name')
            item['AOG_status_label'] = status_map.get(item['AOG_status'], '')
            result.append(item)

        # ---------- 7. 返回 ----------
        resp = {
            'code' : 0,
            'msg'  : 'success',
            'data' : result,
            'total': paginator.count
        }
        return JsonResponse(resp)
    def realAddRecord(self, modalForm):
        foreign_key_fields = {}
        for field in PurchaseTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        addForm = {}
        for key, value in modalForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                addForm[key[:-3]] = obj
            else:

                addForm[key] = value
        try:
            PurchaseTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            return -1
        return 0

    def addRecord(self, request):
        modalForm = request.data.get('modalForm')
        ret = self.realAddRecord(modalForm)
        if ret == -1:
            resp = {'code': API_SYS_ERR, 'msg': 'add fail', 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        if idmap == '':
            return
        # try:
        purchase_number = PurchaseTable.objects.filter(purchaseid=idmap.get('purchaseid')).first().purchase_number
        data = PurchaseDetailTable.objects.filter(purchase_number=purchase_number).all()
        for requestid in data:
            requestid=requestid.requestid.requestid
            RequestBuyTable.objects.filter(requestid=requestid).update(whether_buy=2)
        PurchaseTable.objects.filter(**idmap).delete()
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in PurchaseTable._meta.get_fields():
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
            PurchaseTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editStatus(self, request):
        purchaseid = request.data.get('purchaseid')
        AOG_status = request.data.get('AOG_status')
        print(purchaseid)
        print(AOG_status)
        PurchaseTable.objects.filter(purchaseid=purchaseid).update(AOG_status=AOG_status)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)
    def modifyRecord(self, modalEditForm, idmap):
        foreign_key_fields = {}
        for field in PurchaseTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        editForm = {}
        for key, value in modalEditForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                editForm[key[:-3]] = obj
            else:
                editForm[key] = value
        try:
            ret = PurchaseTable.objects.filter(**idmap).update(**editForm)
            print(ret)
        except Exception as e:
            logger.error(str(e))
            return -1
        return 0

    def getOptions(self, request):
        data = {}
        options = []
        for item in UserTable.objects.all().values('username'):
            options.append({'label': item['username'], 'value': item['username']})
        data['username_options'] = options
        options = []
        for item in SupplierTable.objects.all().values('supplier_name'):
            options.append({'label': item['supplier_name'], 'value': item['supplier_name']})
        data['supplier_name_options'] = options
        options = []
        for item in PurchaseTable.objects.all().values('purchase_number'):
            options.append({'label': item['purchase_number'], 'value': item['purchase_number']})
        data['purchase_number_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)
    @transaction.atomic
    def batch_download_pdf(self, request):
        """
        把本地已存在的 PDF 文件打包成 ZIP 返回。
        前端传：purchaseids = [1,2,3,...]
        """
        # 1. 获取前端传来的 ID 列表
        purchaseids = request.data.get('purchaseids')
        if not isinstance(purchaseids, list) or not purchaseids:
            return Response({'code': 1, 'msg': '请传 purchaseids 列表'}, status=400)

        # 2. 取出对应 PurchaseTable 对象
        purchases = PurchaseTable.objects.filter(purchase_number__in=purchaseids)
        if not purchases.exists():
            return Response({'code': 1, 'msg': '未找到对应采购单'}, status=404)

        # 3. 确保 PDF_DIR 正确
        pdf_dir = getattr(settings, 'PDF_DIR', None)
        if not pdf_dir:
            # 如果 settings 中没定义 PDF_DIR，就立刻报错
            return Response({'code': 1, 'msg': '后台未配置 PDF_DIR'}, status=500)

        # 4. 创建一个内存缓冲区，用于写入 ZIP
        zip_buffer = io.BytesIO()
        any_file_added = False  # 标记至少有一个文件成功加入 ZIP

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for purchase in purchases:
                purchase_number = purchase.purchase_number
                # 约定文件名：purchase_<purchase_number>.pdf
                file_name = f'purchase_{purchase_number}.pdf'
                file_path = os.path.join(pdf_dir, file_name)



                if not os.path.isfile(file_path):
                    # 找不到就跳过，继续打包下一个；也可以改为抛错
                    continue

                try:
                    with open(file_path, 'rb') as f:
                        pdf_bytes = f.read()
                except Exception as e:
                    continue

                # 若读到文件，就写入 ZIP，ZIP 内文件名去掉前缀，直接用 “<采购单号>.pdf”
                zf.writestr(f"采购单 {purchase_number}.pdf", pdf_bytes)
                any_file_added = True

        # 5. 如果一个文件都没加进 ZIP，可以返回错误给前端
        if not any_file_added:
            return Response({'code': 1, 'msg': '没有任何 PDF 文件可打包'}, status=404)

        # 6. 如果至少有一个文件，重置缓冲区指针，并返回 ZIP
        zip_buffer.seek(0)
        response = FileResponse(zip_buffer, as_attachment=True, filename='采购单批量PDF.zip')
        response['Content-Type'] = 'application/zip'
        return response

    @transaction.atomic
    def batch_download_excel(self, request):
        """
        针对前端传的 purchaseids 列表，对每个采购单：
        1）获取该采购单的明细数据列表 data
        2）调用 _genereate_excel(data, purchase_number)，在磁盘生成 purchase_<purchase_number>.xlsx
        3）读取生成的 .xlsx 文件，写入内存 ZIP
        4）删除磁盘上的临时 .xlsx
        最后，返回 ZIP（二进制流）给前端。
        """
        purchaseids = request.data.get('purchaseids', [])
        if not isinstance(purchaseids, list) or not purchaseids:
            return Response({'code': 1, 'msg': '请传 purchaseids 列表'}, status=400)

        # 取出所有对应的采购单
        purchases = PurchaseTable.objects.filter(purchase_number__in=purchaseids)
        if not purchases.exists():
            return Response({'code': 1, 'msg': '未找到对应采购单'}, status=404)

        # 确保有一个目录用来存放临时的 Excel 文件（可以和 PDF_DIR 共用目录）
        excel_dir = getattr(settings, 'PDF_DIR', None)
        if not excel_dir:
            return Response({'code': 1, 'msg': '后台未配置 PDF_DIR (用于存放临时 Excel)'}, status=500)

        # 准备一个 BytesIO 缓冲，用于 ZIP 写入
        zip_buffer = io.BytesIO()
        any_file_added = False

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for purchase in purchases:
                purchase_number = purchase.purchase_number

                # —— 1. 获取该采购单对应的“明细数据列表” ——
                # 假设 ComplexView 里按下面方式组织 data：
                details_qs = PurchaseDetailTable.objects.filter(purchase_number=purchase)
                # 把明细对象转换成字典列表，key 要与 _genereate_excel 里预期字段一致
                data = []
                for det in details_qs:
                    data.append({
                        'purchase_number': purchase.purchase_number,
                        'supplier_name':   purchase.supplier_name.supplier_name,
                        'supplier_contact_name': purchase.contact_person or '',
                        'supplier_contact_phone': purchase.contact_number or '',
                        'username':        purchase.username.username,
                        'purchase_date':   purchase.purchase_date.strftime('%Y-%m-%d'),
                        'currency':        purchase.currency,
                        # 以下字段是该明细行需要的：
                        'product_name':    det.product_name,
                        'product_size':    det.product_size,
                        'unit':            det.unit,
                        'quantity':        det.quantity,
                        'unit_price':      det.unit_price,
                        'total_price':     det.total_price,
                        'remark':          det.remark or ''
                    })

                # —— 2. 调用 _genereate_excel 生成单个 .xlsx ——
                #    返回值是文件名，比如："purchase_2025052901.xlsx"
                try:
                    excel_file_name = genereate_excel(data, purchase_number)
                except Exception as e:
                    # 遇到生成错误时，跳过此采购单，继续处理下一个
                    print(f"[batch_download_excel] 生成 Excel 失败: {purchase_number}, 错误: {e}")
                    continue

                # 完整的磁盘路径：
                excel_path = os.path.join(excel_dir, excel_file_name)

                # 先确认文件存在
                if not os.path.isfile(excel_path):
                    print(f"[batch_download_excel] 期望路径不存在: {excel_path}")
                    continue

                # —— 3. 读取该临时文件并写入 ZIP ——
                try:
                    with open(excel_path, 'rb') as f:
                        excel_bytes = f.read()
                except Exception as e:
                    print(f"[batch_download_excel] 读取文件失败: {excel_path}, 错误: {e}")
                    # 尝试删除这个文件以免残留
                    try:
                        os.remove(excel_path)
                    except:
                        pass
                    continue

                # ZIP 内文件名使用 "<采购单号>.xlsx"
                zf.writestr(f"采购单 {purchase_number}.xlsx", excel_bytes)
                any_file_added = True
                print(f"[batch_download_excel] Added to ZIP: {purchase_number}.xlsx")

                # —— 4. 删除临时的磁盘文件 ——
                try:
                    os.remove(excel_path)
                    print(f"[batch_download_excel] Deleted temp file: {excel_path}")
                except Exception as e:
                    print(f"[batch_download_excel] 删除临时文件失败: {excel_path}, 错误: {e}")

        # 如果一个文件都没加进 ZIP，返回错误
        if not any_file_added:
            return Response({'code': 1, 'msg': '没有任何 Excel 文件可打包'}, status=404)

        # —— 5. 返回 ZIP 二进制流 ——
        zip_buffer.seek(0)
        response = FileResponse(zip_buffer, as_attachment=True, filename='采购单批量Excel.zip')
        response['Content-Type'] = 'application/zip'
        return response
