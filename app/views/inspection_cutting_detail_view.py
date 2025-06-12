import json
import os

from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import API_OK, API_SYS_ERR
from app.models import InspectionCuttingDetailRecord,InspectionCuttingRecord
from loguru import logger
from django.db.models import Q
import sys


class InspectionCuttingDetailView(object):
    """
    切割质检单详情 API 视图
    """

    def query(self, request):
        """
        查询 InspectionCuttingDetailRecord 列表（分页 & 简单搜索）
        - 对于 image_1, image_2, image_3，只返回文件名，而不是完整路径
        """
        try:
            page_num = int(request.data.get('pageNum', 1))
            page_size = int(request.data.get('pageSize', 10))
            # 前端传入的搜索条件 (假设是一个 dict)，可以灵活处理
            search_form = request.data.get('search_data', {})

            # 根据 search_form 动态过滤, 类似 Q(**search_form)
            # 如果需要更复杂的模糊搜索，可自行拼接 Q 对象
            query_set = InspectionCuttingDetailRecord.objects.filter(
                inspection_number_id=search_form
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

                    # 外键: InspectionCuttingRecord, 取出它的 inspection_number 字段
                    "inspection_number": record.inspection_number.inspection_number
                    if record.inspection_number else None,

                    "pointX": record.pointX,
                    "pointY": record.pointY,
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


        except Exception as e:
            logger.error(str(e))
            return JsonResponse({"code": API_SYS_ERR, "msg": "查询失败", "error": str(e)})

    def addRecord(self, request):
        try:
            # 1. 从表单中获取 "modalForm" 字段 (JSON 字符串)
            data_str = request.POST.get("modalForm", "{}")
            logger.info(f"raw modalForm => {data_str}")

            # 2. 解析 JSON
            try:
                data_dict = json.loads(data_str)
            except json.JSONDecodeError:
                data_dict = {}
                logger.warning("modalForm not valid JSON, fallback to empty dict.")

            data_list = data_dict.get("dataList", [])
            if not isinstance(data_list, list):
                data_list = []  # 确保 data_list 是列表

            created_ids = []  # 用于存放新建记录ID

            # 3. 遍历 dataList，每个 item 对应一条记录
            for i, item in enumerate(data_list):
                # (a) 读取普通字段
                checkpoint = item.get("checkpoint", 0)
                required_value = item.get("required_value", 0.0)
                tolerance = item.get("tolerance", "")
                actual_value = item.get("actual_value", 0.0)
                pointX = item.get("pointX", 0.0)
                pointY = item.get("pointY", 0.0)

                # (b) 外键: inspection_number_id => 对应 InspectionCuttingRecord.inspection_number
                ins_num_str = item.get("inspection_number_id", "")
                if not ins_num_str:
                    logger.error("inspection_number_id is missing or empty, skip this item.")
                    continue  # 或者 return JsonResponse(...) 报错

                try:
                    cutting_record = InspectionCuttingRecord.objects.get(inspection_number=ins_num_str)
                except InspectionCuttingRecord.DoesNotExist:
                    logger.error(
                        f"InspectionCuttingRecord not found for inspection_number={ins_num_str}, skip this item.")
                    continue  # 或者 return JsonResponse(...) 报错

                # (c) 如果有文件上传: "image_1_i", "image_2_i", ...
                image_1 = request.FILES.get(f"image_1_{i}", None)
                image_2 = request.FILES.get(f"image_2_{i}", None)
                image_3 = request.FILES.get(f"image_3_{i}", None)

                # 4. 插入数据库
                new_record = InspectionCuttingDetailRecord.objects.create(
                    checkpoint=checkpoint,
                    required_value=required_value,
                    tolerance=tolerance,
                    actual_value=actual_value,
                    image_1=image_1,
                    image_2=image_2,
                    image_3=image_3,
                    inspection_number=cutting_record,  # 传入外键对象
                    pointX=pointX,
                    pointY=pointY,
                )
                created_ids.append(new_record.id)

            # 5. 返回处理结果
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

        except Exception as e:
            logger.error(str(e))
            return JsonResponse({
                "code": API_SYS_ERR,
                "msg": "添加失败",
                "error": str(e)
            })
    def deleteRecord(self, request):
        """
        删除切割质检单详情记录
        """
        try:
            idmap = request.data.get("idmap", {})
            InspectionCuttingDetailRecord.objects.filter(**idmap).delete()

            return JsonResponse({"code": API_OK, "msg": "删除成功"})

        except Exception as e:
            logger.error(str(e))
            return JsonResponse({"code": API_SYS_ERR, "msg": "删除失败", "error": str(e)})

    def editRecord(self, request):
        """
        编辑切割质检单详情记录
        """
        try:
            editForm = request.data.get("modalEditForm", {})
            idmap = request.data.get("idmap", {})

            InspectionCuttingDetailRecord.objects.filter(**idmap).update(**editForm)

            return JsonResponse({"code": API_OK, "msg": "修改成功"})

        except Exception as e:
            logger.error(str(e))
            return JsonResponse({"code": API_SYS_ERR, "msg": "修改失败", "error": str(e)})

