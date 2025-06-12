# inspection_cutting_record_view.py
import json
import os

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q, F
from loguru import logger
from app.api_code import API_OK, API_SYS_ERR
from app.models import InspectionCuttingRecord

class InspectionCuttingRecordView(object):
    """
    针对 InspectionCuttingRecord 模型的增删改查后端示例
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
            query_set = InspectionCuttingRecord.objects.filter(
                Q(inspection_number__icontains=search_data) |
                Q(order_number__order_number__icontains=search_data)
            ).order_by('-created_date')

            # 分页
            paginator = Paginator(query_set, page_size)
            page_data = paginator.page(page_num)

            # 构造返回结果
            result_list = []
            for record in page_data:
                # 如果文件字段可能为空，需要判空
                file_name = os.path.basename(record.reference_image.name) if record.reference_image else None

                # 自定义需要返回的字段
                item = {
                    'inspection_quantity': record.inspection_quantity,
                    'inspection_location': record.inspection_location,
                    'inspection_standard': record.inspection_standard,
                    'inspection_number': record.inspection_number,
                    'general_tolerance': record.general_tolerance,
                    'order_number': record.order_number.order_number if record.order_number else None,
                    'customer_name': record.customer_name.customer_name if record.customer_name else None,
                    'material': record.material,
                    'cutting_quantity': record.cutting_quantity,
                    'created_date': record.created_date.strftime('%Y-%m-%d')
                    if record.created_date else None,
                    'reference_image_url': file_name,
                    'inspector_name': record.inspector_name,
                    'deformation_status': record.deformation_status,
                    'cutting_perpendicularity': record.cutting_perpendicularity,
                    'slag_residue': record.slag_residue,
                    'cutting_roughness': record.cutting_roughness,
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
    import json

    def addRecord(self, request):
        # 1. 获取表单字段 "modalForm"（外层 JSON 字符串）
        modal_form_str = request.POST.get('modalForm', '{}')
        logger.info(f"raw modalForm string => {modal_form_str}")
        try:
            data_dict = json.loads(modal_form_str)
        except json.JSONDecodeError:
            data_dict = {}
            logger.warning("Failed to parse outer modalForm as JSON. Using empty dict.")
        modalForm = data_dict.get("modalForm", {})

        # 3. 获取上传文件 (如参考图片)
        file_obj = request.FILES.get("reference_image", None)
        foreign_key_fields = {}
        for field in InspectionCuttingRecord._meta.get_fields():
            if field.many_to_one:
                fk_model = field.remote_field.model
                fk_field_name = field.remote_field.field_name  # 可能是None，表示默认用目标模型的PK

                if fk_field_name is None:
                    fk_field_name = fk_model._meta.pk.name
                foreign_key_fields[field.name + '_id'] = (fk_model, fk_field_name)

        # 5. 组装要写入数据库的字段
        addForm = {}
        for key, value in modalForm.items():
            if key in foreign_key_fields:
                # 这是一个外键字段，需要用 .get(...) 查对应对象
                model_class, to_field_name = foreign_key_fields[key]
                # 去掉 '_id' 得到真实字段名
                real_field_name = key[:-3]
                obj = model_class.objects.get(**{to_field_name: value})
                addForm[real_field_name] = obj
            else:
                # 普通字段，直接赋值
                addForm[key] = value

        # 如果模型中有 FileField，赋值给 addForm
        if file_obj:
            addForm["reference_image"] = file_obj

        # 6. 数据库写入
        try:
            new_record = InspectionCuttingRecord.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

        return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': {'id': new_record.id}})
    def deleteRecord(self, request):
        idmap = request.data.get('inspection_number', {})
        try:
            InspectionCuttingRecord.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

        return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': ''})

    def editRecord(self, request):
        """
        通过 "删除旧记录" + "创建新记录" 的方式来实现编辑功能
        request.body 示例:
        {
          "old_inspection_number": "CT202503180954202450",  # 要删除的记录键
          "newData": {
             "inspection_quantity": 66,
             "inspection_location": "车间A",
             "inspection_standard": "跟图纸",
             "cutting_quantity": 10,
             ...
             # 文件或外键也可以
          }
        }
        """
        # 1. 获取表单字段 "modalForm"（外层 JSON 字符串）
        modal_form_str = request.POST.get('modalForm', '{}')
        logger.info(f"raw modalForm string => {modal_form_str}")
        try:
            data_dict = json.loads(modal_form_str)
        except json.JSONDecodeError:
            data_dict = {}
            logger.warning("Failed to parse outer modalForm as JSON. Using empty dict.")
        # 3. 解析要新建的数据
        new_data_dict = data_dict.get('modalForm', {})
        if not new_data_dict:
            # 如果 newData 里没数据，那就只相当于做了删除动作
            return JsonResponse({'code': API_OK, 'msg': 'deleted old record, no new record data', 'data': ''})
        # 1. 获取要删除的旧 inspection_number
        old_number = new_data_dict.get('inspection_number', None)
        if not old_number:
            return JsonResponse({'code': 400, 'msg': 'missing old_inspection_number', 'data': ''})

        # 2. 执行删除
        try:
            # 用filter(inspection_number=...)删除
            InspectionCuttingRecord.objects.filter(inspection_number=old_number).delete()
        except Exception as e:
            logger.error(f"editRecord delete error: {str(e)}")
            return JsonResponse({'code': API_SYS_ERR, 'msg': f'delete fail: {str(e)}', 'data': ''})



        # 4. 如果有文件(FileField)需要从 request.FILES里获取,
        file_obj = request.FILES.get("reference_image", None)

        # 如果有外键字段, 需要像 addRecord 那样做外键查询
        foreign_key_fields = {}
        for field in InspectionCuttingRecord._meta.get_fields():
            if field.many_to_one:
                fk_model = field.remote_field.model
                fk_field_name = field.remote_field.field_name  # None表示默认主键
                if fk_field_name is None:
                    fk_field_name = fk_model._meta.pk.name
                foreign_key_fields[field.name + '_id'] = (fk_model, fk_field_name)

        # 组装可写入数据库的字典
        addForm = {}
        for key, value in new_data_dict.items():
            if key in foreign_key_fields:
                model_class, to_field_name = foreign_key_fields[key]
                real_field_name = key[:-3]
                # 如果外键用 to_field="order_number" 或类似:
                obj = model_class.objects.get(**{to_field_name: value})
                addForm[real_field_name] = obj
            else:
                addForm[key] = value

        if file_obj:
            addForm["reference_image"] = file_obj

        # 5. 创建新记录
        try:
            new_record = InspectionCuttingRecord.objects.create(**addForm)
        except Exception as e:
            logger.error(f"editRecord create error: {str(e)}")
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

        return JsonResponse({'code': 200, 'msg': 'edit done (delete+create)', 'data': {'new_id': new_record.id}})
