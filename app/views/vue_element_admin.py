# -*- coding: utf-8 -*-
import json
import mimetypes
import os
import time
import uuid

from typing import Dict, Type, Callable

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils.encoding import smart_str
from rest_framework.decorators import action
from rest_framework import viewsets
from app.api_code import *
from app.models import ManagedTable, FileTable, OrderTable, OrderDetailTable, ProductionProcessTable, CustomerTable, \
    InspectionCuttingRecord,InspectionCuttingDetailRecord
from app.util.db_util import DBUtil
from loguru import logger
from app.views.complex_view import ComplexView
from app.views.customer_table_view import CustomerTableView
from app.views.driver_table_view import DriverTableView
from app.views.file_table_view import FileTableView
from app.views.incoming_warehouse_table_view import IncomingWarehouseTableView
from app.views.inventory_table_view import InventoryTableView
from app.views.order_detail_table_view import OrderDetailTableView
from app.views.order_table_view import OrderTableView
from app.views.outgoing_warehouse_table_view import OutgoingWarehouseTableView
from app.views.product_list_view import ProductListView
from app.views.production_process_table_view import ProductionProcessTableView
from app.views.project_table_view import ProjectTableView
from app.views.purchase_detail_table_view import PurchaseDetailTableView
from app.views.purchase_table_view import PurchaseTableView
from app.views.request_buy_table_view import RequestBuyTableView
from app.views.shipping_detail_table_view import ShippingDetailTableView
from app.views.shpping_plan_view import ShppingPlanView
from app.views.supplier_table_view import SupplierTableView
from app.views.user_table_view import UserTableView
from app.views.inspection_cutting_record_view import InspectionCuttingRecordView
from app.views.inspection_cutting_detail_view import InspectionCuttingDetailView
from app.views.inspection_assembly_record_view import InspectionAssemblyRecordView
from app.views.inspection_assembly_detail_view import InspectionAssemblyDetailView
from app.views.inspection_welding_record_view import InspectionWeldingRecordView
from app.views.inspection_welding_detail_view import InspectionWeldingDetailView
from app.views.inspection_finish_record_view import InspectionFinishRecordView
from app.views.inspection_finish_detail_view import InspectionFinishDetailView
from app.views.inspection_finish_surface_view import InspectionFinishSurfaceRecordView
from app.views.material_list_view import MaterialListView
from app.views.inspection_incoming_record_view import InspectionIncomingRecordView
from app.views.inspection_incoming_detail_view import InspectionIncomingDetailView
from app.views.attachment_file_view import AttachmentFileView
import pandas as pd
import os
import uuid
import PyPDF2
import pdf2image
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from rest_framework.decorators import action
from pyzbar.pyzbar import decode
from PIL import Image
from io import BytesIO
from app.views.warehous_entry_table_view import WarehousEntryTableView
from app.models import InspectionAssemblyRecord, InspectionAssemblyDetailRecord  # ★
from app.models import InspectionWeldingRecord, InspectionWeldingDetailRecord  # ★
from app.models import InspectionFinishRecord, InspectionFinishDetailRecord, InspectionFinishSurfaceRecord  # ★
from app.models import IncomingInspectionRecord, IncomingInspectionDetail  # ★
from django.http import FileResponse, JsonResponse
from app.views.shipping_table_view import ShippingTableView
from app.views.remarks_template_view import RemarksTemplateTableView
from io import BytesIO
from urllib.parse import quote
from django.http import StreamingHttpResponse, JsonResponse
import pdfkit, math, os
from jinja2 import Template
from django.conf import settings




ACTION_MAP: Dict[str, Type] = {
    "user_table_view": UserTableView,
    "customer_table_view": CustomerTableView,
    "project_table_view": ProjectTableView,
    "order_table_view": OrderTableView,
    "file_table_view": FileTableView,
    "order_detail_table_view": OrderDetailTableView,
    "production_process_table_view": ProductionProcessTableView,
    "shipping_table_view": ShippingTableView,
    "shipping_detail_table_view": ShippingDetailTableView,
    "driver_table_view": DriverTableView,
    "inventory_table_view": InventoryTableView,
    "complex_view": ComplexView,
    "outgoing_warehouse_table_view": OutgoingWarehouseTableView,
    "warehous_entry_table_view": WarehousEntryTableView,
    "supplier_table_view": SupplierTableView,
    "incoming_warehouse_table_view": IncomingWarehouseTableView,
    "product_list_view": ProductListView,
    "request_buy_table_view": RequestBuyTableView,
    "purchase_table_view": PurchaseTableView,
    "purchase_detail_table_view": PurchaseDetailTableView,
    "shpping_plan_view": ShppingPlanView,
    "inspection_cutting_record_view": InspectionCuttingRecordView,
    "inspection_cutting_detail_view": InspectionCuttingDetailView,
    "inspection_assembly_record_view": InspectionAssemblyRecordView,
    "inspection_assembly_detail_view": InspectionAssemblyDetailView,
    "inspection_welding_record_view": InspectionWeldingRecordView,
    "inspection_welding_detail_view": InspectionWeldingDetailView,
    "inspection_finish_record_view": InspectionFinishRecordView,
    "inspection_finish_detail_view": InspectionFinishDetailView,
    "inspection_finish_surface_view": InspectionFinishSurfaceRecordView,
    "material_list_view": MaterialListView,
    "inspection_incoming_record_view": InspectionIncomingRecordView,
    "inspection_incoming_detail_view": InspectionIncomingDetailView,
    "remarks_template_view": RemarksTemplateTableView,
    "attachment_file_view": AttachmentFileView,
}

authentication_classes = []
permission_classes = []
class ProcessFactory(object):
    @action(methods=['get'], detail=False)
    def get_file(self, request):
        filename = request.query_params.get('filename', '')
        if not filename:
            resp = {'code': API_PARAM_ERR, 'msg': 'missing filename'}
            return JsonResponse(resp)
        store_dir = os.path.join(settings.BASE_DIR, 'upload/')
        file_path = os.path.join(store_dir, filename)
        image_data = open(file_path, 'rb').read()
        response = HttpResponse(content_type='image/jpeg')
        response.content = image_data
        return response

class VueElementAdmin(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = []

    # http://127.0.0.1:8000/vue-element-admin/backend/get_image/
    @action(methods=['get'], detail=False)
    def get_file(self, request):
        filename = request.query_params.get('filename', '')
        print(111)
        print(filename)
        if not filename:
            resp = {'code': API_PARAM_ERR, 'msg': 'missing filename'}
            return JsonResponse(resp)
        store_dir = os.path.join(settings.BASE_DIR, 'upload/')
        file_path = os.path.join(store_dir, filename)
        image_data = open(file_path, 'rb').read()
        response = HttpResponse(content_type='image/jpeg')
        response.content = image_data
        return response

    def __upload_plan_file(self, request):
        file_obj = request.FILES['file']
        new_filename = 'plan.jpeg'
        file_path = os.path.join(settings.UPLOAD_DIR, new_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        fs = FileSystemStorage()
        fs.save(file_path, file_obj)
        resp = {'code': API_OK, 'msg': 'success', 'data': new_filename}
        return JsonResponse(resp)

    def __normal_upload_file(self, request):
        print(111)
        file_obj = request.FILES['file']
        filename = file_obj.name.split(".")[0]
        file_suffix = file_obj.name.split(".").pop()                         # 文件后缀
        new_filename = '%s.%s' % (filename + '_' + str(int(time.time())), file_suffix)                 # 重命名文件，这样可以上传同名文件
        file_path = os.path.join(settings.UPLOAD_DIR, new_filename)          # 文件保存路径（包含文件名）
        fs = FileSystemStorage()
        fs.save(file_path, file_obj)
        resp = {'code': API_OK, 'msg': 'success', 'data': new_filename}
        return JsonResponse(resp)

    def __upload_picture(self, request):
        file_obj = request.FILES['file']
        filename = file_obj.name.split(".")[0]
        file_suffix = file_obj.name.split(".").pop()                         # 文件后缀
        new_filename = '%s.%s' % (filename + '_' + str(int(time.time())), file_suffix)                 # 重命名文件，这样可以上传同名文件
        file_path = os.path.join(settings.PICTURE_DIR, new_filename)          # 文件保存路径（包含文件名）
        fs = FileSystemStorage()
        fs.save(file_path, file_obj)
        resp = {'code': API_OK, 'msg': 'success', 'data': new_filename}
        return JsonResponse(resp)

    def __batch_add_products(self, request):
        file_obj = request.FILES['file']
        username = request.data.get("username")
        customer_name_id = request.data.get("customer_name")
        order_number = (
            request.data.get('order_number')
            .strip()  # 去首尾空白
            .replace('\u200b', '')  # 去零宽空格（可选）
        )
        file_suffix = file_obj.name.split(".").pop()  # 文件后缀
        new_filename = '%s.%s' % (uuid.uuid4(), file_suffix)  # 重命名文件，这样可以上传同名文件
        file_path = os.path.join(settings.UPLOAD_DIR, new_filename)  # 文件保存路径（包含文件名）
        fs = FileSystemStorage()
        fs.save(file_path, file_obj)
        ## 解析文件内容，批量添加产品
        df = pd.read_excel(file_path, dtype=str)
        df.fillna('', inplace=True)
        msg = 'succ'
        for index, row in df.iterrows():
            try:
                # order_number = row['订单号']
                if order_number:
                    commodity_details = row['品名']
                    commodity_size = row['规格']
                    control_no = row['编号']
                    commodity_units = row['单位']
                    commodity_quantity = row['数量']
                    if row['单件重量(kg)'] != '':
                        print(row['单件重量(kg)'])
                        unit_weight = round(float(row['单件重量(kg)']), 2)
                        quantity = round(float(commodity_quantity), 2)
                        commodity_weight = unit_weight * quantity
                    else:
                        unit_weight = 0
                        commodity_weight = 0
                    remarks = row['备注']
                    username = username
                    customer_name_id = customer_name_id
                    customer_name_id_obj = CustomerTable.objects.get(customer_name=customer_name_id)
                    order_number_obj = OrderTable.objects.get(order_number=order_number)
                    OrderDetailTable.objects.create(order_number=order_number_obj, commodity_details=commodity_details,
                                                     commodity_size=commodity_size, control_no=control_no,
                                                     commodity_units=commodity_units, commodity_quantity=commodity_quantity,
                                                     commodity_weight=commodity_weight, unit_weight=unit_weight,
                                                     remarks=remarks,username=username,customer_name=customer_name_id_obj)
            except Exception as e:
                logger.error(f'batch_add_products error:{str(e)}')
                msg = str(e)
        os.remove(file_path)
        if 'succ' == msg:
            resp = {'code': API_OK, 'msg': 'success', 'data': ''}
        else:
            resp = {'code': API_SYS_ERR, 'msg': msg, 'data': ''}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/vue-element-admin/backend/upload_file/
    def __upload_pdf(self, request):
        if 'file' not in request.FILES:
            return JsonResponse({'code': API_PARAM_ERR, 'msg': 'no file in request'})

        file_obj = request.FILES['file']
        if file_obj.name == '':
            return JsonResponse({'code': API_PARAM_ERR, 'msg': 'No selected file'}, status=400)
        print(file_obj)
        file_suffix = file_obj.name.split(".").pop()
        new_filename = '%s.%s' % (uuid.uuid4(), file_suffix)
        file_path = os.path.join(settings.UPLOAD_DIR, new_filename)
        fs = FileSystemStorage()
        fs.save(file_path, file_obj)
        print(file_path)
        # 提取每页PDF的图像
        pages = pdf2image.convert_from_path(file_path)

        # 创建一个字典来存储条形码编号与其对应的页面
        barcode_pages = {}

        for i, page in enumerate(pages):
            # 将页面转换为图像
            image = page.convert('RGB')
            byte_io = BytesIO()
            image.save(byte_io, 'PNG')
            byte_io.seek(0)
            pil_image = Image.open(byte_io)

            # 识别图像中的条形码
            barcodes = decode(pil_image)
            print(barcodes)
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                if barcode_data not in barcode_pages:
                    barcode_pages[barcode_data] = []
                barcode_pages[barcode_data].append(i)

        # 合并相同条形码编号的页面并保存
        saved_files = []
        for barcode_data, page_indices in barcode_pages.items():
            pdf_writer = PyPDF2.PdfWriter()
            for index in page_indices:
                pdf_reader = PyPDF2.PdfReader(file_path)
                pdf_writer.add_page(pdf_reader.pages[index])

            output_filename = f"{barcode_data}.pdf"
            output_path = os.path.join(settings.UPLOAD_DIR, output_filename)
            with open(output_path, 'wb') as output_pdf:
                pdf_writer.write(output_pdf)

            saved_files.append(output_filename)

            # 保存生成的PDF文件信息到数据库
            order_obj = OrderTable.objects.get(order_number=request.data.get('order_number'))
            customer_name_obj = CustomerTable.objects.get(customer_name=request.data.get('customer_name_id'))
            file_type = request.data.get('file_type')
            db_fileinfo = {
                'customer_name': customer_name_obj,
                'order_number': order_obj,
                'filename': output_filename,
                'new_filename': output_filename,
                'file_size': os.path.getsize(output_path),
                'file_suffix': 'pdf',
                'file_type': file_type
            }
            FileTable.objects.create(**db_fileinfo)

        resp = {'code': API_OK, 'msg': 'success', 'data': saved_files}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/vue-element-admin/backend/upload_file/
    @action(methods=['post'], detail=False)
    def upload_file(self, request):
        if not request.FILES['file']:
            return JsonResponse({'code': API_PARAM_ERR, 'msg': 'no file in request'})
        extra_data = request.data.get('extra_data', '')
        query_extra_data = request.query_params.get('extra_data', '')
        if 'upload_pdf' == query_extra_data:
            return self.__upload_pdf(request)
        if 'upload_plan' == extra_data:
            return self.__upload_plan_file(request)
        if 'batch_add_products' == extra_data:
            return self.__batch_add_products(request)
        if 'normal' == query_extra_data:
            return self.__normal_upload_file(request)
        if 'picture' == query_extra_data:
            return self.__upload_picture(request)
        file_obj = request.FILES['file']
        file_suffix = file_obj.name.split(".").pop()                         # 文件后缀
        new_filename = '%s.%s' % (uuid.uuid4(), file_suffix)                 # 重命名文件，这样可以上传同名文件
        file_path = os.path.join(settings.UPLOAD_DIR, new_filename)          # 文件保存路径（包含文件名）
        fs = FileSystemStorage()
        fs.save(file_path, file_obj)
        ## 保存文件信息到数据库
        order_obj = OrderTable.objects.get(order_number=request.data.get('order_number'))
        customer_name_obj = CustomerTable.objects.get(customer_name=request.data.get('customer_name_id'))
        file_type = request.data.get('file_type')
        db_fileinfo = {'customer_name': customer_name_obj,
                       'order_number': order_obj,
                       'filename': file_obj.name,
                       'new_filename': new_filename,
                       'file_size': file_obj.size,
                       'file_suffix': file_suffix,
                       'file_type': file_type}
        FileTable.objects.create(**db_fileinfo)
        resp = {'code': API_OK, 'msg': 'success', 'data': new_filename}
        return JsonResponse(resp)
    #下载送货单PDF
    def __download_shipping_file(self, shippingid,file_type):
        return ShippingTableView.downloadRecord(shippingid, file_type)

        # file_name = f'shipping_{shippingid}.pdf'
        # file_path = os.path.join(settings.PDF_DIR, file_name)
        # if not os.path.exists(file_path):
        #     return JsonResponse({'code': API_SYS_ERR, 'msg': 'file not found in server'})
        # with open(file_path, 'rb') as f:
        #     file_data = f.read()
        # headers = {
        #     'Access-Control-Expose-Headers': '*',  # 允许前端获取所有响应头信息
        #     'Content-Disposition': 'attachment;filename=%s' % file_name,  # 告诉浏览器下载时使用的文件名
        #     'my_file_type': 'pdf',
        #     'my_file_name_no_suffix': file_name.split('.')[0],
        #     'Content-Length': str(len(file_data)),  # 设置文件长度
        # }
        # response = HttpResponse(content_type='application/octet-stream', headers=headers)
        # response.write(file_data)
        # return response

    def __download_shipping_excel(self, shippingid):
        print(shippingid)
        return ShippingTableView.make_response(shippingid)

    def __download_purchase_file(self, purchase_number):
        file_name = f'purchase_{purchase_number}.pdf'
        file_path = os.path.join(settings.PDF_DIR, file_name)
        if not os.path.exists(file_path):
            return JsonResponse({'code': API_SYS_ERR, 'msg': 'file not found in server'})
        with open(file_path, 'rb') as f:
            file_data = f.read()
        headers = {
            'Access-Control-Expose-Headers': '*',   # 允许前端获取所有响应头信息，不加该头信息，前端只能获取部分常见响应头。
            'Content-Disposition': 'attachment;filename=%s' % file_name,  # 给浏览器使用
            'my_file_type': 'pdf',
            'my_file_name_no_suffix': file_name.split('.')[0],
        }
        response = HttpResponse(content_type='application/octet-stream', headers=headers)
        response.write(file_data)
        return response
    def __download_purchase_excel(self, purchase_number):
        ComplexView.downloadExcel(purchase_number)
        file_name = f'purchase_{purchase_number}.xlsx'
        file_path = os.path.join(settings.PDF_DIR, file_name)
        if not os.path.exists(file_path):
            return JsonResponse({'code': API_SYS_ERR, 'msg': 'file not found in server'})
        with open(file_path, 'rb') as f:
            file_data = f.read()
        headers = {
            'Access-Control-Expose-Headers': '*',   # 允许前端获取所有响应头信息，不加该头信息，前端只能获取部分常见响应头。
            'Content-Disposition': 'attachment;filename=%s' % file_name,  # 给浏览器使用
            'my_file_type': 'xlsx',
            'my_file_name_no_suffix': file_name.split('.')[0],
        }
        response = HttpResponse(content_type='application/octet-stream', headers=headers)
        response.write(file_data)
        return response
    def __download_order_excel(self, order_excel):
        print(order_excel)
        """GET  download?order_excel=xxxxx  —— 和采购单下载写法一致"""
        file_name  = f'{order_excel}.xlsx'
        file_path  = os.path.join(settings.PDF_DIR, file_name)
        if not os.path.exists(file_path):
            return JsonResponse({'code': 404, 'msg': 'file not found'})
        with open(file_path, 'rb') as f:
            data = f.read()

        headers = {
            'Access-Control-Expose-Headers': '*',
            'Content-Disposition': f'attachment;filename={file_name}',
            'my_file_type': 'xlsx',
            'my_file_name_no_suffix': order_excel,
        }
        resp = HttpResponse(content_type='application/octet-stream', headers=headers)
        resp.write(data)
        return resp
    def __download_cutting_reference_image_file(
            self,
            cutting_reference_image=None,
            image_1_name=None,
            image_2_name=None,
            image_3_name=None
    ):
        """
        后端一次只能接收四者中的一个:
          1) cutting_reference_image => InspectionCuttingRecord.reference_image
          2) image_1_name => InspectionCuttingDetailRecord.image_1
          3) image_2_name => InspectionCuttingDetailRecord.image_2
          4) image_3_name => InspectionCuttingDetailRecord.image_3
        """
        record = None
        file_field = None  # 最终要读的 FileField

        # 1. 根据参数查询数据库 & 指定文件字段
        if cutting_reference_image:
            record = InspectionCuttingRecord.objects.filter(
                reference_image__endswith=cutting_reference_image
            ).first()
            if record:
                file_field = record.reference_image

        elif image_1_name:
            detail = InspectionCuttingDetailRecord.objects.filter(
                image_1__endswith=image_1_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_1

        elif image_2_name:
            detail = InspectionCuttingDetailRecord.objects.filter(
                image_2__endswith=image_2_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_2

        elif image_3_name:
            detail = InspectionCuttingDetailRecord.objects.filter(
                image_3__endswith=image_3_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_3

        # 2. 判断是否找到记录及文件
        if not record or not file_field:
            logger.error("File record not found in DB or file_field is empty.")
            return JsonResponse({
                'code': 400,
                'msg': 'File record not found in DB or no valid param'
            })

        # 3. 获取物理路径
        file_path = file_field.path
        if not os.path.exists(file_path):
            logger.error(f"File not found on server path: {file_path}")
            return JsonResponse({'code': 404, 'msg': 'File not found on server'})

        # 4. 读取文件
        with open(file_path, 'rb') as f:
            file_data = f.read()

        base_name = os.path.basename(file_path)  # 如 "xxx.jpg"
        name_no_ext, ext = os.path.splitext(base_name)

        # 5. 猜测 MIME 类型
        content_type, encoding = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'

        # 6. 构造 HttpResponse
        response = HttpResponse(file_data, content_type=content_type)
        response['Access-Control-Expose-Headers'] = '*'
        response['Content-Disposition'] = f'attachment; filename="{base_name}"'
        # 如果你想把扩展名去掉前面的 ".", 可以 ext[1:]
        response['my_file_type'] = ext
        response['my_file_name_no_suffix'] = name_no_ext

        return response

    def __download_assembly_reference_image_file(
            self,
            assembly_reference_image=None,
            image_1_name=None,
            image_2_name=None,
            image_3_name=None
    ):
        """
        后端一次只能接收四者中的一个:
          1) assembly_reference_image => InspectionAssemblyRecord.reference_image
          2) image_1_name => InspectionAssemblyDetailRecord.image_1
          3) image_2_name => InspectionAssemblyDetailRecord.image_2
          4) image_3_name => InspectionAssemblyDetailRecord.image_3
        """

        record = None
        file_field = None  # 最终要读取的 FileField

        # 1. 根据参数查询数据库 & 指定文件字段
        if assembly_reference_image:
            # 原 cutting_reference_image => assembly_reference_image
            record = InspectionAssemblyRecord.objects.filter(
                reference_image__endswith=assembly_reference_image
            ).first()
            if record:
                file_field = record.reference_image

        elif image_1_name:
            detail = InspectionAssemblyDetailRecord.objects.filter(
                image_1__endswith=image_1_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_1

        elif image_2_name:
            detail = InspectionAssemblyDetailRecord.objects.filter(
                image_2__endswith=image_2_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_2

        elif image_3_name:
            detail = InspectionAssemblyDetailRecord.objects.filter(
                image_3__endswith=image_3_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_3

        # 2. 判断是否找到记录及文件
        if not record or not file_field:
            logger.error("Assembly file record not found in DB or file_field is empty.")
            return JsonResponse({
                'code': 400,
                'msg': 'Assembly file record not found in DB or no valid param'
            })

        # 3. 获取物理路径
        file_path = file_field.path
        if not os.path.exists(file_path):
            logger.error(f"File not found on server path: {file_path}")
            return JsonResponse({'code': 404, 'msg': 'File not found on server'})

        # 4. 读取文件
        with open(file_path, 'rb') as f:
            file_data = f.read()

        base_name = os.path.basename(file_path)  # eg "xxx.jpg"
        name_no_ext, ext = os.path.splitext(base_name)

        # 5. 猜测 MIME 类型
        content_type, encoding = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'

        # 6. 构造响应
        response = HttpResponse(file_data, content_type=content_type)
        response['Access-Control-Expose-Headers'] = '*'
        response['Content-Disposition'] = f'attachment; filename="{base_name}"'
        response['my_file_type'] = ext
        response['my_file_name_no_suffix'] = name_no_ext

        return response

    def __download_welding_reference_image_file(
            self,
            welding_reference_image=None,
            image_1_name=None,
            image_2_name=None,
            image_3_name=None
    ):
        """
        后端一次只能接收四者中的一个:
          1) welding_reference_image => InspectionWeldingRecord.reference_image
          2) image_1_name => InspectionWeldingDetailRecord.image_1
          3) image_2_name => InspectionWeldingDetailRecord.image_2
          4) image_3_name => InspectionWeldingDetailRecord.image_3
        """

        record = None
        file_field = None  # 最终要读取的 FileField

        # 1. 根据参数查询数据库 & 指定文件字段
        if welding_reference_image:
            # 对应 InspectionWeldingRecord 的 reference_image
            record = InspectionWeldingRecord.objects.filter(
                reference_image__endswith=welding_reference_image
            ).first()
            if record:
                file_field = record.reference_image

        elif image_1_name:
            detail = InspectionWeldingDetailRecord.objects.filter(
                image_1__endswith=image_1_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_1

        elif image_2_name:
            detail = InspectionWeldingDetailRecord.objects.filter(
                image_2__endswith=image_2_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_2

        elif image_3_name:
            detail = InspectionWeldingDetailRecord.objects.filter(
                image_3__endswith=image_3_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_3

        # 2. 判断是否找到记录及文件
        if not record or not file_field:
            logger.error("Welding file record not found in DB or file_field is empty.")
            return JsonResponse({
                'code': 400,
                'msg': 'Welding file record not found in DB or no valid param'
            })

        # 3. 获取物理路径
        file_path = file_field.path
        if not os.path.exists(file_path):
            logger.error(f"File not found on server path: {file_path}")
            return JsonResponse({'code': 404, 'msg': 'File not found on server'})

        # 4. 读取文件
        with open(file_path, 'rb') as f:
            file_data = f.read()

        base_name = os.path.basename(file_path)  # eg "xxx.jpg"
        name_no_ext, ext = os.path.splitext(base_name)

        # 5. 猜测 MIME 类型
        content_type, encoding = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'

        # 6. 构造响应
        response = HttpResponse(file_data, content_type=content_type)
        response['Access-Control-Expose-Headers'] = '*'
        response['Content-Disposition'] = f'attachment; filename="{base_name}"'
        response['my_file_type'] = ext
        response['my_file_name_no_suffix'] = name_no_ext

        return response


    def __download_finish_reference_image_file(
            self,
            finish_reference_image=None,
            image_1_name=None,
            image_2_name=None,
            image_3_name=None,
    ):
        """
        后端一次只能接收四者中的一个:
          1) welding_reference_image => InspectionWeldingRecord.reference_image
          2) image_1_name => InspectionWeldingDetailRecord.image_1
          3) image_2_name => InspectionWeldingDetailRecord.image_2
          4) image_3_name => InspectionWeldingDetailRecord.image_3
        """

        record = None
        file_field = None  # 最终要读取的 FileField

        # 1. 根据参数查询数据库 & 指定文件字段
        if finish_reference_image:
            # 对应 InspectionWeldingRecord 的 reference_image
            record = InspectionFinishRecord.objects.filter(
                reference_image__endswith=finish_reference_image
            ).first()
            if record:
                file_field = record.reference_image

        elif image_1_name:
            detail = InspectionFinishDetailRecord.objects.filter(
                image_1__endswith=image_1_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_1

        elif image_2_name:
            detail = InspectionFinishDetailRecord.objects.filter(
                image_2__endswith=image_2_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_2

        elif image_3_name:
            detail = InspectionFinishDetailRecord.objects.filter(
                image_3__endswith=image_3_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_3
        # 2. 判断是否找到记录及文件
        if not record or not file_field:
            logger.error("Welding file record not found in DB or file_field is empty.")
            return JsonResponse({
                'code': 400,
                'msg': 'Welding file record not found in DB or no valid param'
            })

        # 3. 获取物理路径
        file_path = file_field.path
        if not os.path.exists(file_path):
            logger.error(f"File not found on server path: {file_path}")
            return JsonResponse({'code': 404, 'msg': 'File not found on server'})

        # 4. 读取文件
        with open(file_path, 'rb') as f:
            file_data = f.read()

        base_name = os.path.basename(file_path)  # eg "xxx.jpg"
        name_no_ext, ext = os.path.splitext(base_name)

        # 5. 猜测 MIME 类型
        content_type, encoding = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'

        # 6. 构造响应
        response = HttpResponse(file_data, content_type=content_type)
        response['Access-Control-Expose-Headers'] = '*'
        response['Content-Disposition'] = f'attachment; filename="{base_name}"'
        response['my_file_type'] = ext
        response['my_file_name_no_suffix'] = name_no_ext

        return response

    def __download_incoming_reference_image_file(
            self,
            image_1_name=None,
            image_2_name=None,
            image_3_name=None,
            image_4_name=None,
    ):
        """
        后端一次只能接收四者中的一个:
          1) welding_reference_image => InspectionWeldingRecord.reference_image
          2) image_1_name => InspectionWeldingDetailRecord.image_1
          3) image_2_name => InspectionWeldingDetailRecord.image_2
          4) image_3_name => InspectionWeldingDetailRecord.image_3
        """

        record = None
        file_field = None  # 最终要读取的 FileField

        # 1. 根据参数查询数据库 & 指定文件字段
        if image_1_name:
            detail = IncomingInspectionDetail.objects.filter(
                image1__endswith=image_1_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image1

        elif image_2_name:
            detail = IncomingInspectionDetail.objects.filter(
                image2__endswith=image_2_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image2

        elif image_3_name:
            detail = IncomingInspectionDetail.objects.filter(
                image3__endswith=image_3_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image3
        elif image_4_name:
            detail = IncomingInspectionDetail.objects.filter(
                image4__endswith=image_4_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image4
        # 2. 判断是否找到记录及文件
        if not record or not file_field:
            logger.error("Welding file record not found in DB or file_field is empty.")
            return JsonResponse({
                'code': 400,
                'msg': 'Welding file record not found in DB or no valid param'
            })

        # 3. 获取物理路径
        file_path = file_field.path
        if not os.path.exists(file_path):
            logger.error(f"File not found on server path: {file_path}")
            return JsonResponse({'code': 404, 'msg': 'File not found on server'})

        # 4. 读取文件
        with open(file_path, 'rb') as f:
            file_data = f.read()

        base_name = os.path.basename(file_path)  # eg "xxx.jpg"
        name_no_ext, ext = os.path.splitext(base_name)

        # 5. 猜测 MIME 类型
        content_type, encoding = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'

        # 6. 构造响应
        response = HttpResponse(file_data, content_type=content_type)
        response['Access-Control-Expose-Headers'] = '*'
        response['Content-Disposition'] = f'attachment; filename="{base_name}"'
        response['my_file_type'] = ext
        response['my_file_name_no_suffix'] = name_no_ext

        return response
    def __download_surface_image_file(
            self,
            image_4_name=None,
    ):
        record = None
        file_field = None  # 最终要读取的 FileField
        if image_4_name:
            detail = InspectionFinishSurfaceRecord.objects.filter(
                image_1__endswith=image_4_name
            ).first()
            if detail:
                record = detail
                file_field = detail.image_1
        # 2. 判断是否找到记录及文件
        if not record or not file_field:
            logger.error("Welding file record not found in DB or file_field is empty.")
            return JsonResponse({
                'code': 400,
                'msg': 'Welding file record not found in DB or no valid param'
            })

        # 3. 获取物理路径
        file_path = file_field.path
        if not os.path.exists(file_path):
            logger.error(f"File not found on server path: {file_path}")
            return JsonResponse({'code': 404, 'msg': 'File not found on server'})

        # 4. 读取文件
        with open(file_path, 'rb') as f:
            file_data = f.read()

        base_name = os.path.basename(file_path)  # eg "xxx.jpg"
        name_no_ext, ext = os.path.splitext(base_name)

        # 5. 猜测 MIME 类型
        content_type, encoding = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'

        # 6. 构造响应
        response = HttpResponse(file_data, content_type=content_type)
        response['Access-Control-Expose-Headers'] = '*'
        response['Content-Disposition'] = f'attachment; filename="{base_name}"'
        response['my_file_type'] = ext
        response['my_file_name_no_suffix'] = name_no_ext

        return response
    # http://127.0.0.1:8000/vue-element-admin/backend/download_file/
    @action(methods=['get'], detail=False)
    def download_file(self, request):
        zip_name = request.GET.get('zip_name')
        if zip_name:  # 批量 ZIP
            file_path = os.path.join(settings.PDF_DIR, zip_name)
            if not os.path.exists(file_path):
                return JsonResponse({'code': 1, 'msg': '文件不存在'})

            resp = FileResponse(open(file_path, 'rb'), as_attachment=True)
            resp['Content-Disposition'] = f'attachment; filename="{zip_name}"'
            resp['Content-Type'] = 'application/zip'
            resp['my_file_type'] = 'zip'  # ★★ 这行最关键 ★★
            return resp
        shippingid = request.query_params.get('shippingid_pdf', '')
        file_type = request.query_params.get('file_type', '')
        if shippingid:
            return self.__download_shipping_file(shippingid,file_type)

        shippingid_excel = request.query_params.get('shippingid_excel','')
        if shippingid_excel:
            return self.__download_shipping_excel(shippingid_excel)

        order_excel = request.query_params.get('order_excel')
        print(request.query_params)
        if order_excel:
            return self.__download_order_excel(order_excel)

        purchase_excel = request.query_params.get('purchase_excel','')
        if purchase_excel:
            return self.__download_purchase_excel(purchase_excel)

        purchase_number = request.query_params.get('purchase_number', '')
        if purchase_number:
            return self.__download_purchase_file(purchase_number)
        image_1_name = request.query_params.get('incoming_image_1_name', '')
        image_2_name = request.query_params.get('incoming_image_2_name', '')
        image_3_name = request.query_params.get('incoming_image_3_name', '')
        image_4_name = request.query_params.get('incoming_image_3_name', '')

        if image_1_name or image_2_name or image_3_name or image_4_name:
            return self.__download_incoming_reference_image_file(
                image_1_name if image_1_name else None,
                image_2_name if image_2_name else None,
                image_3_name if image_3_name else None,
                image_4_name if image_4_name else None,
            )
        # 新增: cutting_reference_image / image_1_name / image_2_name / image_3_name
        cutting_reference_image = request.query_params.get('cutting_reference_image', '')
        image_1_name = request.query_params.get('cutting_image_1_name', '')
        image_2_name = request.query_params.get('cutting_image_2_name', '')
        image_3_name = request.query_params.get('cutting_image_3_name', '')
        if cutting_reference_image or image_1_name or image_2_name or image_3_name:
            # 调用上面的方法, 一次只能传一个
            return self.__download_cutting_reference_image_file(
                cutting_reference_image if cutting_reference_image else None,
                image_1_name if image_1_name else None,
                image_2_name if image_2_name else None,
                image_3_name if image_3_name else None
            )
        assembly_reference_image = request.query_params.get('assembly_reference_image', '')
        image_1_name = request.query_params.get('assembly_image_1_name', '')
        image_2_name = request.query_params.get('assembly_image_2_name', '')
        image_3_name = request.query_params.get('assembly_image_3_name', '')

        if assembly_reference_image or image_1_name or image_2_name or image_3_name:
            return self.__download_assembly_reference_image_file(
                assembly_reference_image if assembly_reference_image else None,
                image_1_name if image_1_name else None,
                image_2_name if image_2_name else None,
                image_3_name if image_3_name else None
            )
        welding_reference_image = request.query_params.get('welding_reference_image', '')
        image_1_name = request.query_params.get('welding_image_1_name', '')
        image_2_name = request.query_params.get('welding_image_2_name', '')
        image_3_name = request.query_params.get('welding_image_3_name', '')

        if welding_reference_image or image_1_name or image_2_name or image_3_name:
            return self.__download_welding_reference_image_file(
                welding_reference_image if welding_reference_image else None,
                image_1_name if image_1_name else None,
                image_2_name if image_2_name else None,
                image_3_name if image_3_name else None
            )
        finish_reference_image = request.query_params.get('finish_reference_image', '')
        image_1_name = request.query_params.get('product_check_image_1_name', '')
        image_2_name = request.query_params.get('product_check_image_2_name', '')
        image_3_name = request.query_params.get('product_check_image_3_name', '')


        if finish_reference_image or image_1_name or image_2_name or image_3_name:
            return self.__download_finish_reference_image_file(
                finish_reference_image if finish_reference_image else None,
                image_1_name if image_1_name else None,
                image_2_name if image_2_name else None,
                image_3_name if image_3_name else None
            )
        image_4_name = request.query_params.get('surface_image_1_name', '')
        if image_4_name:
            return self.__download_surface_image_file(
                image_4_name if image_4_name else None
            )
        # 下载其他文件
        fileid = request.query_params.get('fileid', '')
        print(fileid)
        if not fileid:
            return JsonResponse({'code': API_PARAM_ERR, 'msg': 'no fileid in request'})
        file_obj = FileTable.objects.filter(fileid=fileid).first()
        if not file_obj:
            return JsonResponse({'code': API_PARAM_ERR, 'msg': 'file not found in db'})
        file_path = os.path.join(settings.UPLOAD_DIR, file_obj.new_filename)
        if not os.path.exists(file_path):
            return JsonResponse({'code': API_SYS_ERR, 'msg': 'file not found in server'})
        with open(file_path, 'rb') as f:
            file_data = f.read()
        # headers还可添加自定义信息，headers中有中文会出错，可能跟content_type有关
        headers = {
            'Access-Control-Expose-Headers': '*',   # 允许前端获取所有响应头信息，不加该头信息，前端只能获取部分常见响应头。
            'Content-Disposition': 'attachment;filename=%s' % file_obj.new_filename,  # 给浏览器使用
            'my_file_type': file_obj.file_suffix,
            'my_file_name_no_suffix': file_obj.new_filename.split('.')[0],
        }
        response = HttpResponse(content_type='application/octet-stream', headers=headers)
        response.write(file_data)
        return response

    @action(methods=['get'], detail=False)
    def get_test(self, request):
        return JsonResponse({'code': API_OK, 'msg': 'test success', 'data': 'test data'})

    @action(methods=['post'], detail=False)
    def post_test(self, request):
        return JsonResponse({'code': API_OK, 'msg': 'posttest success', 'data': 'test data'})

    @action(methods=['get'], detail=False)
    def get_db_test(self, request):
        sql = "SELECT sum(b.commodity_quantity), sum(c.process_quantity), c.process_name FROM order_detail_tb a JOIN production_process_tb b " \
              "ON a.detailid = b.detailid_id WHERE a."
        db_util = DBUtil()
        data = db_util.query(sql)
        return JsonResponse({'code': API_OK, 'msg': 'get_db_test success', 'data': data})

    # http://127.0.0.1:8000/vue-element-admin/backend/inspection/
    @action(methods=['post'], detail=False)
    def inspection(self, request):
        data_str = request.data.get('modalForm', None)
        print(data_str)
        if not data_str:
            logger.error('No "modalForm" field found or empty.')
            return JsonResponse({'code': 50000, 'msg': 'No modalForm data', 'data': ''})
        try:
            data_dict = json.loads(data_str)
        except json.JSONDecodeError as e:
            logger.error(f'"modalForm" JSON parse error: {e}')
            return JsonResponse({'code': 50000, 'msg': 'modalForm not valid JSON', 'data': ''})
        action = data_dict.get('action', 'default')
        subaction = data_dict.get('subaction', '')
        logger.info('process action:' + action)
        if '' == subaction:
            logger.error('subaction is empty')
            return JsonResponse({'code': 50000, 'msg': 'subaction is empty', 'data': ''})
        if 'inspection_cutting_record_view' == action:
            obj = InspectionCuttingRecordView()
        elif 'inspection_cutting_detail_view' == action:
            obj = InspectionCuttingDetailView()
        elif 'inspection_assembly_record_view' == action:
            obj = InspectionAssemblyRecordView()
        elif 'inspection_assembly_detail_view' == action:
            obj = InspectionAssemblyDetailView()
        elif 'inspection_welding_record_view' == action:
            obj = InspectionWeldingRecordView()
        elif 'inspection_welding_detail_view' == action:
            obj = InspectionWeldingDetailView()
        elif 'inspection_finish_record_view' == action:
            obj = InspectionFinishRecordView()
        elif 'inspection_finish_detail_view' == action:
            obj = InspectionFinishDetailView()
        elif 'inspection_finish_surface_view' == action:
            obj = InspectionFinishSurfaceRecordView()
        elif 'inspection_incoming_record_view' == action:
            obj = InspectionIncomingRecordView()
        elif 'inspection_incoming_detail_view' == action:
            obj = InspectionIncomingDetailView()
        else:
            msg = f'action is not defined, action: {action}'
            logger.error(msg)
            return JsonResponse({'code': 50000, 'msg': msg, 'data': ''})
        if not hasattr(obj, subaction):
            logger.error(f'No such method: {subaction} on {obj.__class__.__name__}')
            return JsonResponse({'code': 50000, 'msg': f'Invalid subaction: {subaction}', 'data': ''})
        method = getattr(obj, subaction)
        return method(request)


    # ------------------  process  ------------------
    @action(methods=["post"], detail=False)
    def process(self, request):
        action_name = request.data.get("action", "default")
        subaction = request.data.get("subaction")
        logger.info("process action: %s", action_name)

        if not subaction:
            return JsonResponse({"code": API_SYS_ERR, "msg": "subaction is empty", "data": ""})

        view_cls = ACTION_MAP.get(action_name)
        if view_cls is None:
            msg = f"action is not defined: {action_name}"
            logger.error(msg)
            return JsonResponse({"code": API_SYS_ERR, "msg": msg, "data": ""})

        view_obj = view_cls()
        if not hasattr(view_obj, subaction):
            msg = f"invalid subaction: {subaction}"
            logger.error(msg)
            return JsonResponse({"code": API_SYS_ERR, "msg": msg, "data": ""})

        return getattr(view_obj, subaction)(request)

        # try:
        #     method = getattr(obj, subaction)
        #     return method(request)
        # except Exception as e:
        #     msg = 'subaction fail, ' + str(e)
        #     logger.error(msg)
        # return JsonResponse({'code': API_SYS_ERR, 'msg': msg, 'data': ''})
