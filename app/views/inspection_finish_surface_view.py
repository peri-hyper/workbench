import json
import os

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from loguru import logger

from app.api_code import API_OK, API_SYS_ERR
from app.models import InspectionFinishSurfaceRecord, InspectionFinishRecord


class InspectionFinishSurfaceRecordView(object):
    """
    成品检验 - 表面参数详情 API 视图

    说明：
    - 查询接口返回记录的各项字段，并对图片字段返回图片文件名
    - addRecord 接口支持传多条记录，每条记录可附带一张图片
    """
    def query(self, request):
        """
        查询 InspectionFinishSurfaceRecord 列表（支持分页和简单搜索）
        """
        try:
            page_num = int(request.data.get('pageNum', 1))
            page_size = int(request.data.get('pageSize', 10))
            ins_number = request.data.get('search_data', '')

            query_set = InspectionFinishSurfaceRecord.objects.filter(
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
                    "actual_value": record.actual_value,
                    "coating_type": record.coating_type,
                    "judgment": record.judgment,
                    "inspection_number": (
                        record.inspection_number.inspection_number if record.inspection_number else None
                    ),
                    "pointX": record.pointX,
                    "pointY": record.pointY,
                    "image_1_name": os.path.basename(record.image_1.name) if record.image_1 else None,
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
        新增成品检验 - 表面参数详情记录
        - 支持同时传多条记录，每条记录可附带图片
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
                actual_value   = item.get("actual_value", 0.0)
                coating_type   = item.get("coating_type", "")
                judgment       = item.get("judgment", 0.0)
                pointX         = item.get("pointX", 0.0)
                pointY         = item.get("pointY", 0.0)

                ins_num_str = item.get("inspection_number_id", "")
                if not ins_num_str:
                    logger.error("inspection_number_id missing, skip this item.")
                    continue
                try:
                    finish_record = InspectionFinishRecord.objects.get(
                        inspection_number=ins_num_str
                    )
                except InspectionFinishRecord.DoesNotExist:
                    logger.error(f"Finish record not found for inspection_number={ins_num_str}, skip.")
                    continue

                # 仅支持一张图片
                image_1 = request.FILES.get(f"image_1_{i}", None)
                print(image_1)
                new_record = InspectionFinishSurfaceRecord.objects.create(
                    checkpoint=checkpoint,
                    required_value=required_value,
                    actual_value=actual_value,
                    coating_type=coating_type,
                    judgment=judgment,
                    pointX=pointX,
                    pointY=pointY,
                    image_1=image_1,
                    inspection_number=finish_record,
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
        删除成品检验 - 表面参数记录
        """
        try:
            idmap = request.data.get("idmap", {})
            InspectionFinishSurfaceRecord.objects.filter(**idmap).delete()
            return JsonResponse({"code": API_OK, "msg": "删除成功"})
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({"code": API_SYS_ERR, "msg": "删除失败", "error": str(e)})

    def editRecord(self, request):
        """
        编辑成品检验 - 表面参数记录
        - 修改时将前端提交的 editForm 数据更新到对应记录中
        """
        try:
            editForm = request.data.get("modalEditForm", {})
            idmap = request.data.get("idmap", {})

            InspectionFinishSurfaceRecord.objects.filter(**idmap).update(**editForm)
            return JsonResponse({"code": API_OK, "msg": "修改成功"})
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({"code": API_SYS_ERR, "msg": "修改失败", "error": str(e)})
