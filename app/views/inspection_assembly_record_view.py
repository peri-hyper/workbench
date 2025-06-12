# inspection_assembly_record_view.py

import json
import os

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from loguru import logger

from app.api_code import API_OK, API_SYS_ERR
from app.models import InspectionAssemblyRecord  # ★ 原 InspectionCuttingRecord

class InspectionAssemblyRecordView(object):
    """
    针对 InspectionAssemblyRecord 模型(组装检验记录)的增删改查后端示例
    (原 Cutting => Assembly)
    """

    def query(self, request):
        """
        列表查询：支持分页和简单搜索，返回所有记录的字段并包含文件URL
        """
        page_num = request.data.get('pageNum', 1)
        page_size = request.data.get('pageSize', 10)
        search_data = request.data.get('search_data', '')

        try:
            # 模糊匹配 inspection_number 或 order_number
            query_set = InspectionAssemblyRecord.objects.filter(
                Q(inspection_number__icontains=search_data) |
                Q(order_number__order_number__icontains=search_data)
            ).order_by('-created_date')

            # 分页
            paginator = Paginator(query_set, page_size)
            page_data = paginator.page(page_num)

            result_list = []
            for record in page_data:
                # 如果文件字段可能为空，需要判空
                file_name = os.path.basename(record.reference_image.name) if record.reference_image else None

                # 自定义返回字段
                item = {
                    'inspection_quantity': record.inspection_quantity,
                    'inspection_location': record.inspection_location,
                    'inspection_standard': record.inspection_standard,
                    'inspection_number': record.inspection_number,
                    'general_tolerance': record.general_tolerance,
                    'order_number': record.order_number.order_number if record.order_number else None,
                    'customer_name': record.customer_name.customer_name if record.customer_name else None,
                    # 原 material => component_number
                    'component_number': record.component_number,
                    # 原 cutting_quantity => assembly_quantity
                    'assembly_quantity': record.assembly_quantity,
                    'created_date': record.created_date.strftime('%Y-%m-%d')
                        if record.created_date else None,
                    'reference_image_url': file_name,
                    'inspector_name': record.inspector_name,
                    # 原变形 => bevel_quality
                    'bevel_quality': record.bevel_quality,
                    # 原切口垂直度 => materiel_cleanliness
                    'materiel_cleanliness': record.materiel_cleanliness,
                    # 原熔渣残留 => angle_symmetry
                    'angle_symmetry': record.angle_symmetry,
                    # 原切口粗糙度 => misalignment
                    'misalignment': record.misalignment,
                }
                result_list.append(item)

            resp = {
                'code': API_OK,
                'msg': 'success',
                'data': result_list,
                'total': paginator.count
            }
            return JsonResponse(resp)
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': 50000, 'msg': str(e), 'data': ''})

    def addRecord(self, request):
        """
        新增组装检验主记录
        """
        modal_form_str = request.POST.get('modalForm', '{}')
        logger.info(f"raw modalForm => {modal_form_str}")
        try:
            data_dict = json.loads(modal_form_str)
        except json.JSONDecodeError:
            data_dict = {}
            logger.warning("Failed to parse outer modalForm as JSON. Using empty dict.")

        modalForm = data_dict.get("modalForm", {})

        # 获取上传文件 (例如参考图片)
        file_obj = request.FILES.get("reference_image", None)

        # 处理外键字段
        from app.models import OrderTable, CustomerTable
        # gather foreign_key info
        foreign_key_fields = {}
        for field in InspectionAssemblyRecord._meta.get_fields():
            if field.many_to_one:
                fk_model = field.remote_field.model
                fk_field_name = field.remote_field.field_name or fk_model._meta.pk.name
                foreign_key_fields[field.name + '_id'] = (fk_model, fk_field_name)

        addForm = {}
        for key, value in modalForm.items():
            if key in foreign_key_fields:
                model_class, to_field_name = foreign_key_fields[key]
                real_field_name = key[:-3]
                obj = model_class.objects.get(**{to_field_name: value})
                addForm[real_field_name] = obj
            else:
                addForm[key] = value

        if file_obj:
            addForm["reference_image"] = file_obj

        try:
            new_record = InspectionAssemblyRecord.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

        return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': {'id': new_record.id}})

    def deleteRecord(self, request):
        """
        删除组装检验主记录
        """
        idmap = request.data.get('inspection_number', {})
        try:
            InspectionAssemblyRecord.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

        return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': ''})

    def editRecord(self, request):
        """
        简易编辑: 先删除旧记录, 再创建新记录
        """
        modal_form_str = request.POST.get('modalForm', '{}')
        logger.info(f"raw modalForm => {modal_form_str}")
        try:
            data_dict = json.loads(modal_form_str)
        except json.JSONDecodeError:
            data_dict = {}
            logger.warning("Failed to parse outer modalForm. Using empty dict.")

        new_data_dict = data_dict.get('modalForm', {})
        if not new_data_dict:
            return JsonResponse({'code': API_OK, 'msg': 'no new record data', 'data': ''})

        old_number = new_data_dict.get('inspection_number', None)
        if not old_number:
            return JsonResponse({'code': 400, 'msg': 'missing old_inspection_number', 'data': ''})

        try:
            InspectionAssemblyRecord.objects.filter(inspection_number=old_number).delete()
        except Exception as e:
            logger.error(f"editRecord delete error: {str(e)}")
            return JsonResponse({'code': API_SYS_ERR, 'msg': f'delete fail: {str(e)}', 'data': ''})

        # 处理文件
        file_obj = request.FILES.get("reference_image", None)

        # 处理外键
        from app.models import OrderTable, CustomerTable
        foreign_key_fields = {}
        for field in InspectionAssemblyRecord._meta.get_fields():
            if field.many_to_one:
                fk_model = field.remote_field.model
                fk_field_name = field.remote_field.field_name or fk_model._meta.pk.name
                foreign_key_fields[field.name + '_id'] = (fk_model, fk_field_name)

        addForm = {}
        for key, value in new_data_dict.items():
            if key in foreign_key_fields:
                model_class, to_field_name = foreign_key_fields[key]
                real_field_name = key[:-3]
                obj = model_class.objects.get(**{to_field_name: value})
                addForm[real_field_name] = obj
            else:
                addForm[key] = value

        if file_obj:
            addForm["reference_image"] = file_obj

        try:
            new_record = InspectionAssemblyRecord.objects.create(**addForm)
        except Exception as e:
            logger.error(f"editRecord create error: {str(e)}")
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

        return JsonResponse({'code': API_OK, 'msg': 'edit done (delete+create)', 'data': {'new_id': new_record.id}})

