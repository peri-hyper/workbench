import json
import os

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from loguru import logger

from app.api_code import API_OK, API_SYS_ERR
from app.models import IncomingInspectionDetail, IncomingInspectionRecord


class InspectionIncomingDetailView(object):
    """
    来料检验 - 明细 API 视图
    action = inspection_incoming_detail_view
    与前端 UploadDetailInfo / 查询逻辑保持一致
    """

    # ------------------------------------------------------------------
    # 1. 查询
    # ------------------------------------------------------------------
    def query(self, request):
        """分页 + 按检验单号模糊搜索"""
        try:
            page_num  = int(request.data.get('pageNum', 1))
            page_size = int(request.data.get('pageSize', 10))
            ins_number = request.data.get('search_data', '')

            qs = IncomingInspectionDetail.objects.filter(
                inspection_number__inspection_number__icontains=ins_number
            ).order_by('id')

            paginator = Paginator(qs, page_size)
            page_data = paginator.page(page_num)

            result = []
            for r in page_data:
                result.append({
                    'id'            : r.id,
                    'inspection_number': r.inspection_number.inspection_number,
                    'material_name' : r.material_name,
                    'spec'          : r.spec,
                    'material'      : r.material,
                    'quantity'      : r.quantity,
                    'length'        : float(r.length),
                    'width'         : float(r.width),
                    'thickness'     : float(r.thickness),
                    'height'        : float(r.height),
                    'heat_no'       : r.heat_no,
                    'mtc_no'        : r.mtc_no,

                    # 仅返回文件名，前端可自行拼接 URL
                    'image1_name'   : os.path.basename(r.image1.name) if r.image1 else None,
                    'image2_name'   : os.path.basename(r.image2.name) if r.image2 else None,
                    'image3_name'   : os.path.basename(r.image3.name) if r.image3 else None,
                    'image4_name'   : os.path.basename(r.image4.name) if r.image4 else None,
                })

            return JsonResponse({
                'code' : API_OK,
                'msg'  : 'success',
                'data' : result,
                'total': paginator.count
            })
        except Exception as e:
            logger.error(f"query error: {e}")
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

    # ------------------------------------------------------------------
    # 2. 批量新增（支持图片）
    # ------------------------------------------------------------------
    def addRecord(self, request):
        """
        前端使用 multipart/form-data
        - 字段 modalForm: 外层 JSON，结构 { "dataList": [ {...}, ... ] }
        - 每条记录最多 4 张图：image_1_0 / image_2_0 / ... image_4_0
        """
        try:
            data_str = request.POST.get('modalForm', '{}')
            logger.info(f"raw modalForm => {data_str}")
            try:
                data_dict = json.loads(data_str)
            except json.JSONDecodeError:
                data_dict = {}
                logger.warning("modalForm not valid JSON, use empty dict")

            data_list = data_dict.get('dataList', []) if isinstance(data_dict.get('dataList'), list) else []
            created_ids = []

            for idx, item in enumerate(data_list):
                try:
                    rec = IncomingInspectionRecord.objects.get(
                        inspection_number=item.get('inspection_number_id', ''))
                except IncomingInspectionRecord.DoesNotExist:
                    logger.error(f"header not found for inspection_number={item.get('inspection_number_id')}")
                    continue

                img_kwargs = {
                    'image1': request.FILES.get(f'image_1_{idx}', None),
                    'image2': request.FILES.get(f'image_2_{idx}', None),
                    'image3': request.FILES.get(f'image_3_{idx}', None),
                    'image4': request.FILES.get(f'image_4_{idx}', None),
                }

                new_obj = IncomingInspectionDetail.objects.create(
                    inspection_number = rec,
                    material_name = item.get('material_name', ''),
                    spec          = item.get('spec', ''),
                    material      = item.get('material', ''),
                    quantity      = item.get('quantity', 0),
                    length        = item.get('length', 0),
                    width         = item.get('width', 0),
                    thickness     = item.get('thickness', 0),
                    height        = item.get('height', 0),
                    heat_no       = item.get('heat_no', ''),
                    mtc_no        = item.get('mtc_no', ''),
                    **img_kwargs
                )
                created_ids.append(new_obj.id)

            return JsonResponse({'code': API_OK, 'msg': '添加成功', 'data': {'created_ids': created_ids}})
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

    # ------------------------------------------------------------------
    # 3. 删除
    # ------------------------------------------------------------------
    def deleteRecord(self, request):
        try:
            idmap = request.data.get('idmap', {})
            IncomingInspectionDetail.objects.filter(**idmap).delete()
            return JsonResponse({'code': API_OK, 'msg': '删除成功'})
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': '删除失败', 'error': str(e)})

    # ------------------------------------------------------------------
    # 4. 编辑（单条）
    # ------------------------------------------------------------------
    def editRecord(self, request):
        try:
            idmap      = request.data.get('idmap', {})
            edit_form  = request.data.get('modalEditForm', {})
            IncomingInspectionDetail.objects.filter(**idmap).update(**edit_form)
            return JsonResponse({'code': API_OK, 'msg': '修改成功'})
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'code': API_SYS_ERR, 'msg': '修改失败', 'error': str(e)})
