import json
import logging
import os
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from app.api_code import *
from app.models import InventoryTable, RequestBuyTable, PurchaseDetailTable,PurchaseTable,AttachmentFileTable
from loguru import logger
from app.util.db_util import DBUtil
import pdfkit
from jinja2 import Template
from app.util.db_util import DBUtil
from app.util.purchase_excel_utils import genereate_excel
from app.views.purchase_table_view import PurchaseTableView
from openpyxl import Workbook
from openpyxl.styles import Border,Side,Alignment



logger = logging.getLogger(__name__)


def _to_decimal(num):
    """把前端可能传来的 '', None, float 统统转成 Decimal(2 位)"""
    return Decimal(str(num or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)
class ComplexView(object):
    def get_processname_info(self, request):
        """ 获取工艺总数和完成数 """
        sql = """
            SELECT 
                p.process_name AS process_name,
                SUM(d.commodity_quantity + COALESCE(s.shipping_quantity, 0)) AS total_count,
                SUM(p.process_quantity) AS finished_count
            FROM 
                production_process_tb p
            JOIN 
                order_detail_tb d ON p.detailid_id = d.detailid
            LEFT JOIN 
                shipping_detail_tb s ON d.detailid = s.detailid_id
            LEFT JOIN 
                order_tb ob ON d.order_number_id = ob.order_number
            WHERE
                ob.order_status = 1    
            GROUP BY 
                p.process_name;
    """
        db_util = DBUtil()
        code, msg, data = db_util.query(sql)
        print(data)
        return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': data})

    def get_inwarehouse_info(self, request):
        """ 获取入库详情 """
        entry_number = request.data.get('entry_number')
        sql = f"""select a.incomeid as incomeid,
    b.inventoryid as inventoryid,
       b.product_name as product_name,
       b.product_size as product_size,
       b.unit as unit,
       a.quantity as quantity
       from incoming_warehouse_tb a, inventory_tb b
       where a.inventoryid_id = b.inventoryid and a.entry_number_id = '{entry_number}'"""
        db_util = DBUtil()
        code, msg, data = db_util.query(sql)
        unit_choices_map = {'1': '件', '2': '套', '3': '批', '4': '千克', '5': '吨', '6': '包', '7': '盒', '8': '其他'}
        for item in data:
            item['unit_label'] = unit_choices_map.get(str(item['unit']), '')
        return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': data})

    def get_out_info(self, request):
        """ 获取出库详情 """
        sql = """select a.outdate as outdate,
       a.outid as outid,
       a.quantity as quantity,
       a.person_name as person_name,
       b.product_name as product_name,
       b.product_size as product_size,
       b.unit as unit
        from outgoing_warehouse_tb a, inventory_tb b
        where a.inventoryid_id = b.inventoryid"""
        db_util = DBUtil()
        code, msg, data = db_util.query(sql)
        unit_choices_map = {'1': '件', '2': '套', '3': '批', '4': '千克', '5': '吨', '6': '包', '7': '盒', '8': '其他'}
        for item in data:
            item['unit_label'] = unit_choices_map.get(str(item['unit']), '')
        return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': data})

    def __genereate_pdf(self, tabledata, formdata):
        pdf_template_path = os.path.join(settings.BASE_DIR, 'templates', 'purchase_template.html')
        header_template_path = os.path.join(settings.BASE_DIR, 'templates', 'header_for_purchase.html')
        with open(pdf_template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()
        template = Template(template_content)
        rendered_html_content = template.render(info=formdata, rows=tabledata)
        purchase_number = formdata.get('purchase_number')
        rendered_html_filename = os.path.join(settings.PDF_DIR, f'purchase_{purchase_number}.html')
        with open(rendered_html_filename, 'w', encoding='utf-8') as file:
            file.write(rendered_html_content)
        with open(header_template_path, 'r', encoding='utf-8') as file:
            template_content2 = file.read()
        template2 = Template(template_content2)
        header_html_path = template2.render(info=formdata)
        header_html_path_filename = os.path.join(settings.PDF_DIR, f'shipping_{purchase_number}2.html')
        with open(header_html_path_filename, 'w', encoding='utf-8') as file:
            file.write(header_html_path)
        options = {
            'page-size': 'A4',
            'margin-top': '60mm',
            'margin-right': '10mm',
            'margin-bottom': '40mm',
            'margin-left': '10mm',
            'encoding': 'UTF-8',
            'no-outline': None,
            "enable-local-file-access": True,
            'header-html': header_html_path_filename,
            'header-right': '第' + '[page]' + '页 ''共' + '[topage]' + '页 ',
            'header-font-name': '宋体',
            'header-font-size': '8'
        }
        config = pdfkit.configuration(wkhtmltopdf='.\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
        pdf_filename = f'purchase_{purchase_number}.pdf'
        pdf_file_path = os.path.join(settings.PDF_DIR, pdf_filename)
        ret = pdfkit.from_file(rendered_html_filename, pdf_file_path, configuration=config, options=options)
        if ret:
            logger.info(f'Generate pdf file {pdf_filename} success')
        else:
            logger.error(f'Generate pdf file {pdf_filename} failed, msg: {ret}')
        return pdf_filename



    @transaction.atomic
    def generate_purchase_order(self,request):
        """一次提交：新建采购单（表头 + 明细）"""
        form = request.data.get('formdata', {})
        rows = request.data.get('tabledata', [])
        files = request.FILES.getlist('attachments')
        print(form)
        print(rows)
        print(files)
        if not rows:
            return JsonResponse({'code': 1, 'msg': '明细不能为空', 'data': ''})

        # ── 1. 创建表头 ─────────────────────────────────────────────
        try:
            form = json.loads(form or '{}')
            rows = json.loads(rows or '[]')
        except json.JSONDecodeError as e:
            return JsonResponse({'code': 1, 'msg': f'JSON 解析失败: {e}', 'data': ''})

        if not rows:
            return JsonResponse({'code': 1, 'msg': '明细不能为空', 'data': ''})

        # ----- 2. 创建采购单表头 ---------------------------------------
        try:
            purchase = PurchaseTable.objects.create(
                purchase_number=form['purchase_number'],
                username_id=form['username_id'],
                supplier_name_id=form['supplier_name_id'],
                contact_person=form.get('contact_person'),
                contact_number=form.get('contact_number'),
                purchase_date=form.get('purchase_date'),
                currency=form.get('currency'),
                remark=form.get('remark'),
            )
        except Exception as e:
            logger.error('创建采购单失败: %s', e)
            return JsonResponse({'code': 1, 'msg': str(e), 'data': ''})

        # ── 2. 处理 RequestBuy 状态 & 取对象字典 ───────────────────
        req_ids = [r.get('requestid_id') or r.get('requestid') for r in rows]
        RequestBuyTable.objects.filter(requestid__in=req_ids).update(whether_buy=1)

        req_objs = RequestBuyTable.objects.in_bulk(req_ids)  # {id: obj}

        # ── 3. 组装明细 & 批量插入 ─────────────────────────────────
        details = [
            PurchaseDetailTable(
                purchase_number=purchase,
                requestid=req_objs[req_id],
                product_name=r.get('product_name'),
                product_size=r.get('product_size'),
                unit=r.get('unit_label'),
                quantity=r.get('quantity'),
                unit_price=_to_decimal(r.get('unit_price')),
                total_price=_to_decimal(r.get('total_prices')),
                remark=r.get('remark')
            )
            for req_id, r in zip(req_ids, rows)
        ]
        PurchaseDetailTable.objects.bulk_create(details)
        for f in files:
            AttachmentFileTable.objects.create(
                parent=purchase,  # 直接传对象即可
                file=f,
                filename=f.name,
                file_size=f.size,
            )

        # ── 4. 生成 PDF（如失败自动回滚） ──────────────────────────
        try:
            self.__genereate_pdf(rows, form)  # 改成你的实际函数名
        except Exception as e:
            logger.error('生成 PDF 失败: %s', e)
            raise  # 抛出让事务回滚；前端会收到 code 1

        return JsonResponse({'code': 0, 'msg': 'succ', 'data': ''})
    def downloadExcel(purchase_number):
        sql = f"""
            SELECT 
                pd.requestid_id,
                st.purchase_number,
                GROUP_CONCAT(DISTINCT p.supplier_name) AS supplier_name,
                GROUP_CONCAT(DISTINCT p.supplier_contact_name) AS supplier_contact_name,
                GROUP_CONCAT(DISTINCT p.supplier_contact_phone) AS supplier_contact_phone,
                MAX(pd.product_name) AS product_name,
                MAX(pd.product_size) AS product_size,
                MAX(pd.material) AS material,
                MAX(pd.quantity) AS quantity,
                MAX(pd.unit) AS unit,
                MAX(pd.unit_price) AS unit_price,
                MAX(pd.total_price) AS total_price,
                MAX(pd.remark) AS remark,
                MAX(st.username_id) AS username,
                MAX(st.purchase_date) AS purchase_date,
                MAX(st.currency) AS currency,
                MAX(d.requestdate) AS requestdate
            FROM 
                purchase_detail_tb pd
            INNER JOIN 
                purchase_tb st ON pd.purchase_number_id = st.purchase_number
            LEFT JOIN 
                supplier_tb p ON st.supplier_name_id = p.supplier_name
            INNER JOIN 
                request_buy_tb d ON pd.requestid_id = d.requestid
            WHERE 
                st.purchase_number = {purchase_number}
            GROUP BY 
                pd.requestid_id, st.purchase_number;
        """
        code, msg, data = DBUtil.query(sql, {})
        genereate_excel(data,purchase_number)
        return JsonResponse({'code': code, 'msg': msg, 'data':[]})

    @transaction.atomic
    def generate_purchase_order_modify(self, request):
        import json
        from decimal import Decimal, ROUND_HALF_UP
        from django.http import JsonResponse, Http404

        # 0. 解析 JSON
        form_raw = request.data.get('formdata', '{}')
        print(form_raw)
        rows_raw = request.data.get('tabledata', '[]')
        print(rows_raw)
        try:
            form = json.loads(form_raw)
            rows = json.loads(rows_raw)
        except json.JSONDecodeError as e:
            return JsonResponse({'code': 1, 'msg': f'JSON 解析失败: {e}', 'data': ''})

        pn = form.get('purchase_number')
        print(pn)
        if not pn or not isinstance(rows, list) or not rows:
            return JsonResponse({'code': 1, 'msg': '参数缺失或明细不能为空', 'data': ''})

        # 1. 取出 purchase 对象
        try:
            purchase = PurchaseTable.objects.get(purchase_number=pn)
        except PurchaseTable.DoesNotExist:
            raise Http404('采购单不存在')

        # 2. 更新表头
        head_fields = {
            'username_id': form.get('username_id'),
            'supplier_name_id': form.get('supplier_name_id'),
            'contact_person': form.get('contact_person'),
            'contact_number': form.get('contact_number'),
            'purchase_date': form.get('purchase_date'),
            'currency': form.get('currency'),
            'remark': form.get('remark'),
        }
        for k, v in head_fields.items():
            setattr(purchase, k, v)
        purchase.save()

        # 3. 回退旧 RequestBuy
        old_ids = list(PurchaseDetailTable.objects
                       .filter(purchase_number=purchase)
                       .values_list('requestid_id', flat=True))
        if old_ids:
            RequestBuyTable.objects.filter(requestid__in=old_ids).update(whether_buy=2)

        # 4. 重建明细
        PurchaseDetailTable.objects.filter(purchase_number=purchase).delete()
        new_req_ids = []
        details = []
        for r in rows:
            req_id = r.get('requestid_id') or r.get('requestid')
            new_req_ids.append(req_id)
            details.append(PurchaseDetailTable(
                purchase_number=purchase,
                requestid_id=req_id,
                product_name=r.get('product_name'),
                product_size=r.get('product_size'),
                unit=r.get('unit_label'),
                quantity=r.get('quantity'),
                unit_price=Decimal(r.get('unit_price', 0))
                .quantize(Decimal('0.01'), ROUND_HALF_UP),
                total_price=Decimal(r.get('total_prices', 0))
                .quantize(Decimal('0.01'), ROUND_HALF_UP),
                remark=r.get('remark', '')
            ))
        PurchaseDetailTable.objects.bulk_create(details)
        RequestBuyTable.objects.filter(requestid__in=new_req_ids).update(whether_buy=1)

        # 5. 处理附件保留 & 新增
        keep_ids_raw = form.get('keep_attachment_ids', '[]')
        edited_raw = form.get('edited_attachments', '[]')
        edited = json.loads(edited_raw) if isinstance(edited_raw, str) else edited_raw
        for item in edited:
            aid = item.get('id')
            new_name = item.get('filename')
            if aid and new_name:
                AttachmentFileTable.objects.filter(pk=aid).update(filename=new_name)
        try:
            keep_ids = json.loads(keep_ids_raw) if isinstance(keep_ids_raw, str) else keep_ids_raw
        except:
            keep_ids = []

        qs = purchase.attachments.all()
        if keep_ids:
            qs.exclude(pk__in=keep_ids).delete()

        for f in request.FILES.getlist('attachments'):
            AttachmentFileTable.objects.create(
                parent=purchase,
                file=f,
                filename=f.name,
                file_size=f.size
            )

        # 6. 生成 PDF
        try:
            self.__genereate_pdf(rows, form)
        except Exception:
            raise

        return JsonResponse({'code': 0, 'msg': 'succ', 'data': ''})

