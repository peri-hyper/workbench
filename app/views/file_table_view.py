import urlquote as urlquote
from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from django.conf import settings
from loguru import logger
import io, os, zipfile, datetime
from django.http import HttpResponse, JsonResponse
from app.models import FileTable
from app.api_code import API_OK, API_SYS_ERR      # 根据你的常量位置调整

class FileTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        query_set = FileTable.objects.filter(**search_form).all().order_by('-upload_time', 'file_type').values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)
        file_type_choices_map = {'1': '合同/订单', '2': '图纸', '3': '已签收发货单', '4': '验焊报告', '5': '质检报告', '6': '镀锌报告', '7': '其他'}
        for item in page_data:
            item['file_type_label'] = file_type_choices_map.get(str(item['file_type']), '')
        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        print(resp)
        return JsonResponse(resp)

    def addRecord(self, request):
        foreign_key_fields = {}
        for field in FileTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        addForm = {}
        modalForm = request.data.get('modalForm')
        print(modalForm)
        for key, value in modalForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                addForm[key[:-3]] = obj
            else:
                addForm[key] = value
        try:
            FileTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            FileTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in FileTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        editForm = {}
        modalEditForm = request.data.get('modalEditForm')
        for key, value in modalEditForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                editForm[key[:-3]] = obj
            else:
                editForm[key] = value
        idmap = request.data.get('idmap')
        try:
            FileTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def batch_download(self, request):
        """批量打包下载附件"""
        ids = request.data.get('ids', [])
        if not ids:
            return JsonResponse({'code': API_SYS_ERR,
                                 'msg': 'ids is empty', 'data': ''})

        files_qs = FileTable.objects.filter(fileid__in=ids)
        if not files_qs.exists():
            return JsonResponse({'code': API_SYS_ERR,
                                 'msg': 'no file found', 'data': ''})

        # 创建 zip 到内存
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in files_qs:
                real_path = os.path.join(settings.UPLOAD_DIR, f.new_filename)      # 如果你表里存的字段不同，改这里
                print(real_path)  # 添加调试日志
                if os.path.isfile(real_path):
                    zf.write(real_path, arcname=os.path.basename(real_path))
                else:
                    print(f"文件不存在: {real_path}")  # 添加调试日志
        buf.seek(0)

        ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        zip_name = f'attachments_{ts}.zip'
        resp = HttpResponse(buf.getvalue(),
                            content_type='application/zip')
        # 让前端可以拿到自定义响应头
        resp['Access-Control-Expose-Headers'] = '*'
        resp['Content-Disposition'] = f'attachment;filename={zip_name}'
        resp['my_file_type'] = 'zip'
        resp['my_file_name_no_suffix'] = os.path.splitext(zip_name)[0]
        return resp

    # 统一接口，任何模型都通用
    def get_attachments(obj):
        return obj.attachments.all()  # 依赖 GenericRelation