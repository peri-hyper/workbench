import json
import os

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from loguru import logger

from app.api_code import API_OK, API_SYS_ERR
from app.models import InspectionWeldingDetailRecord, InspectionWeldingRecord


class InspectionWeldingDetailView(object):
    """
    焊接检验 - 记录详情 API 视图
    (原 InspectionAssemblyDetailView)
    """

    def query(self, request):
        """
        查询 InspectionWeldingDetailRecord 列表（分页 & 简单搜索）
        - 对于 image_1, image_2, image_3，只返回文件名，而不是完整路径
        - 新增返回 7 个布尔字段: crack, porosity, undercut, weldBead, depression, spatter, slag
        """
        try:
            page_num = int(request.data.get('pageNum', 1))
            page_size = int(request.data.get('pageSize', 10))
            ins_number = request.data.get('search_data', '')

            query_set = InspectionWeldingDetailRecord.objects.filter(
                inspection_number__inspection_number__icontains=ins_number
            ).order_by("id")

            paginator = Paginator(query_set, page_size)
            page_data = paginator.page(page_num)

            result_list = []
            for record in page_data:
                result_list.append({
                    "id": record.id,
                    "checkpoint": record.checkpoint,
                    "required_value": record.required_value,
                    "tolerance": record.tolerance,
                    "actual_value": record.actual_value,

                    # 只返回文件名
                    "image_1_name": os.path.basename(record.image_1.name) if record.image_1 else None,
                    "image_2_name": os.path.basename(record.image_2.name) if record.image_2 else None,
                    "image_3_name": os.path.basename(record.image_3.name) if record.image_3 else None,

                    "inspection_number": (
                        record.inspection_number.inspection_number
                        if record.inspection_number
                        else None
                    ),
                    "pointX": record.pointX,
                    "pointY": record.pointY,
                    "visual_check": record.visual_check,
                    "weld_process": record.weld_process,

                })

            resp = {
                "code": API_OK,
                "msg": "success",
                "data": result_list,
                "total": paginator.count
            }
            return JsonResponse(resp, safe=False)

        except Exception as e:
            logger.error(f"query error: {e}")
            return JsonResponse({"code": 50000, "msg": str(e), "data": ""})

    def addRecord(self, request):
        """
        新增焊接检验详情记录
        - 支持多条记录 (dataList)，每条可附带3张图片
        - 新增接收7个布尔字段
        """
        try:
            data_str = request.POST.get("modalForm", "{}")
            logger.info(f"raw modalForm => {data_str}")

            try:
                data_dict = json.loads(data_str)
            except json.JSONDecodeError:
                data_dict = {}
                logger.warning("modalForm not valid JSON, fallback to empty dict.")

            data_list = data_dict.get("dataList", [])
            if not isinstance(data_list, list):
                data_list = []

            created_ids = []

            for i, item in enumerate(data_list):
                checkpoint     = item.get("checkpoint", 0)
                required_value = item.get("required_value", 0.0)
                tolerance      = item.get("tolerance", "")
                actual_value   = item.get("actual_value", 0.0)
                pointX         = item.get("pointX", 0.0)
                pointY         = item.get("pointY", 0.0)

                visual_check   = item.get("visual_check", False)
                weld_process   = item.get("weld_process", "")

                ins_num_str = item.get("inspection_number_id", "")
                if not ins_num_str:
                    logger.error("inspection_number_id missing, skip this item.")
                    continue
                try:
                    welding_record = InspectionWeldingRecord.objects.get(
                        inspection_number=ins_num_str
                    )
                except InspectionWeldingRecord.DoesNotExist:
                    logger.error(f"Record not found for inspection_number={ins_num_str}, skip.")
                    continue

                image_1 = request.FILES.get(f"image_1_{i}", None)
                image_2 = request.FILES.get(f"image_2_{i}", None)
                image_3 = request.FILES.get(f"image_3_{i}", None)

                new_record = InspectionWeldingDetailRecord.objects.create(
                    checkpoint=checkpoint,
                    required_value=required_value,
                    tolerance=tolerance,
                    actual_value=actual_value,
                    image_1=image_1,
                    image_2=image_2,
                    image_3=image_3,
                    inspection_number=welding_record,
                    pointX=pointX,
                    pointY=pointY,

                    # ★ 将7个布尔值存进数据库
                    visual_check=visual_check,
                    weld_process=weld_process,
                )
                created_ids.append(new_record.id)

            return JsonResponse({
                "code": API_OK,
                "msg": "添加成功",
                "data": {"created_ids": created_ids}
            })

        except Exception as e:
            logger.error(str(e))
            return JsonResponse({
                "code": 50000,
                "msg": f"添加失败, error: {e}",
                "data": ''
            })

    def deleteRecord(self, request):
        """
        删除焊接检验详情记录
        """
        try:
            idmap = request.data.get("idmap", {})
            InspectionWeldingDetailRecord.objects.filter(**idmap).delete()
            return JsonResponse({"code": API_OK, "msg": "删除成功"})
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({"code": API_SYS_ERR, "msg": "删除失败", "error": str(e)})

    def editRecord(self, request):
        """
        编辑焊接检验详情记录
        - 如果要修改7个布尔字段，也可一并传到 editForm 里
        """
        try:
            editForm = request.data.get("modalEditForm", {})
            idmap = request.data.get("idmap", {})

            # 这里可包含 crack / porosity 等字段 => db将更新
            InspectionWeldingDetailRecord.objects.filter(**idmap).update(**editForm)

            return JsonResponse({"code": API_OK, "msg": "修改成功"})
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({"code": API_SYS_ERR, "msg": "修改失败", "error": str(e)})
