from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from loguru import logger

from app.api_code import *          # 保持与原文件一致的返回码常量
from app.models import MaterialList

class MaterialListView(object):
    """
    材料清单（MaterialList）通用增删改查
    """

    # ---------------- 查询 ----------------
    def query(self, request):
        """
        POST 方式：
        {
            "pageNum": 1,
            "pageSize": 20,
            "searchForm": {
                "product_name__icontains": "角钢",
                "material": "S275J0",
                "received_date__range": ["2020-01-01", "2020-12-31"],
                ...
            }
        }
        """
        page_num   = request.data.get('pageNum', 1)
        page_size  = request.data.get('pageSize', 20)
        searchForm = request.data.get('search_data', "")
        # 构造 QuerySet
        try:
            qs = MaterialList.objects.filter(Q(product_name__icontains=searchForm)| Q(specifications__icontains=searchForm) | Q(material__icontains=searchForm)).order_by('-product_name').values()
            paginator = Paginator(qs, page_size)
            page_data = paginator.page(page_num)
            resp = {'code': API_OK, 'msg': 'success',
                    'data': list(page_data), 'total': paginator.count}
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}

        return JsonResponse(resp)

    # ---------------- 新增 ----------------
    def addRecord(self, request):
        """
        modalForm = {
            "product_name": "角钢",
            "specifications": "100×50×6mm×6M",
            "material": "S275J0",
            "quantity": 24,
            "heat_batch_number": "54165",
            "certificate_number": "M1179784",
            "received_date": "2018-01-24",
            "record_code": "xsy0001"
        }
        """
        modalForm = request.data.get('modalForm', {})
        try:
            MaterialList.objects.create(**modalForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)

        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    # ---------------- 删除 ----------------
    def deleteRecord(self, request):
        """
        idmap = {"record_code": "xsy0001"}  或 {"id": 15}
        """
        idmap = request.data.get('idmap', {})
        try:
            MaterialList.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)

        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    # ---------------- 编辑 ----------------
    def editRecord(self, request):
        """
        idmap         = {"record_code": "xsy0001"}
        modalEditForm = {"product_name": "槽钢", ...}
        """
        idmap         = request.data.get('idmap', {})
        modalEditForm = request.data.get('modalEditForm', {})

        try:
            MaterialList.objects.filter(**idmap).update(**modalEditForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)

        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    # ---------------- 下拉选项 ----------------
    def getOptions(self, request):
        """
        返回常用下拉：品名、材质、炉号 / 批号
        """
        data = {
            'product_name_options': [
                {'label': it['product_name'], 'value': it['product_name']}
                for it in MaterialList.objects.values('product_name').distinct()
            ],
            'material_options': [
                {'label': it['material'], 'value': it['material']}
                for it in MaterialList.objects.values('material').distinct()
            ],
            'heat_batch_options': [
                {'label': it['heat_batch_number'], 'value': it['heat_batch_number']}
                for it in MaterialList.objects.values('heat_batch_number').distinct()
            ],
        }
        resp = {'code': API_OK, 'msg': 'success', 'data': data}
        return JsonResponse(resp)
