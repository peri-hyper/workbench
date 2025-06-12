"""
接口路径示例：
POST  /backend/remarks_template_view/query
POST  /backend/remarks_template_view/addRecord
POST  /backend/remarks_template_view/deleteRecord
POST  /backend/remarks_template_view/editRecord
POST  /backend/remarks_template_view/getOptions
"""

from django.http import JsonResponse
from django.core.paginator import Paginator
from loguru import logger
from app.api_code import API_OK, API_SYS_ERR, API_PARAM_ERR          # 与现有保持一致
from app.models import RemarksTemplateTable


class RemarksTemplateTableView(object):

    # -------------------- 查询 --------------------
    def query(self, request):
        page_num   = int(request.data.get('pageNum', 1))
        page_size  = int(request.data.get('pageSize', 20))
        searchForm = request.data.get('searchForm', {})

        # 简单按创建人 / 日期过滤，可按需扩展
        qs = RemarksTemplateTable.objects.filter(**searchForm).order_by('-creat_date').values()
        paginator = Paginator(qs, page_size)
        page_data = paginator.page(page_num)

        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': qs.count()}
        return JsonResponse(resp)

    # -------------------- 新增 --------------------
    def addRecord(self, request):
        form = request.data.get('modalForm', {})
        try:
            RemarksTemplateTable.objects.create(**form)
            return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': ''})
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

    # -------------------- 删除 --------------------
    def deleteRecord(self, request):
        idmap = request.data.get('idmap')           # 例：{'templateid': 3}
        if not idmap:
            return JsonResponse({'code': API_PARAM_ERR, 'msg': '缺少 idmap', 'data': ''})

        try:
            RemarksTemplateTable.objects.filter(**idmap).delete()
            return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': ''})
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

    # -------------------- 编辑 --------------------
    def editRecord(self, request):
        idmap        = request.data.get('idmap')
        modalEditForm = request.data.get('modalEditForm', {})

        if not idmap:
            return JsonResponse({'code': API_PARAM_ERR, 'msg': '缺少 idmap', 'data': ''})

        try:
            RemarksTemplateTable.objects.filter(**idmap).update(**modalEditForm)
            return JsonResponse({'code': API_OK, 'msg': 'succ', 'data': ''})
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': API_SYS_ERR, 'msg': str(e), 'data': ''})

    # -------------------- 下拉选项（模板列表） --------------------
    # def getOptions(self, request):
    #     """
    #     前端做 <el-select> 时可直接用：
    #     [{label:'模板 2025-05-17', value:3}, …]
    #     """
    #     options = [
    #         {
    #             'label': f"{rec['creat_date']} - {rec['creat_user']}\",
    #             'value': rec['templateid']
    #         }
    #         for rec in RemarksTemplateTable.objects.order_by('-creat_date').values('templateid', 'creat_date', 'creat_user')
    #     ]
    #     return JsonResponse({'code': 0, 'msg': 'success', 'data': {'template_options': options}})
