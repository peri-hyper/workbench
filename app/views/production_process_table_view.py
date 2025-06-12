from django.core.paginator import Paginator
from django.http import JsonResponse
from app.api_code import *
from app.models import ProductionProcessTable, OrderTable
from app.models import OrderDetailTable
from loguru import logger
from django.db.models import F, Sum

class ProductionProcessTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        print(search_form)
        query_set = ProductionProcessTable.objects.filter(**search_form).all().order_by('processid').values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)

        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)

    def addRecord(self, request):
        foreign_key_fields = {}
        for field in ProductionProcessTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        addForm = {}
        modalForm = request.data.get('modalForm')
        for key, value in modalForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                addForm[key[:-3]] = obj
            else:
                addForm[key] = value
        try:
            ProductionProcessTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            ProductionProcessTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in ProductionProcessTable._meta.get_fields():
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
            ProductionProcessTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def getOptions(self, request):
        data = {}
        options = []
        for item in OrderDetailTable.objects.all().values('detailid'):
            options.append({'label': item['detailid'], 'value': item['detailid']})
        data['detailid_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)
    def getProcessListBath(self, request):
        detailid_list = request.data.get('detailid_list')
        print(detailid_list)
        process_names = ProductionProcessTable.objects.filter(detailid__in=detailid_list).values_list('process_name',flat=True).distinct()
        print(list(process_names))
        # process_name_list = []
        # for item in process_names:
        #     process_name_list.append(item['process_name'])
        # print(process_name_list)
        resp = {'code': 0, 'msg': 'success', 'data': list(process_names)}
        return JsonResponse(resp)

    def getProcessList(self, request):
        detailid = request.data.get('detailid')
        obj = OrderDetailTable.objects.get(detailid=detailid)
        process_name_list = []
        for item in ProductionProcessTable.objects.filter(detailid=obj).values('process_name'):
            process_name_list.append(item['process_name'])
        resp = {'code': 0, 'msg': 'success', 'data': process_name_list}
        return JsonResponse(resp)

    def addProcessNameList(self, request):
        # 从前端请求中获取 detailid 和 工艺列表
        process_name_list = request.data.get('processList')
        detailid = request.data.get('detailid')

        # 根据 detailid 获取对应的 OrderDetailTable 对象
        obj = OrderDetailTable.objects.get(detailid=detailid)

        # 获取当前数据库中与该 detailid 关联的所有工艺名称
        existing_processes = list(
            ProductionProcessTable.objects.filter(detailid=obj).values_list('process_name', flat=True))

        # 处理增加操作：添加不存在于数据库的工艺
        for process_name in process_name_list:
            if not ProductionProcessTable.objects.filter(detailid=obj, process_name=process_name).exists():
                try:
                    ProductionProcessTable.objects.create(detailid=obj, process_name=process_name)
                except Exception as e:
                    logger.error(str(e))
                    resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
                    return JsonResponse(resp)

        # 处理删除操作：删除数据库中存在但不在前端传入列表中的工艺
        for process_name in existing_processes:
            if process_name not in process_name_list:
                try:
                    ProductionProcessTable.objects.filter(detailid=obj, process_name=process_name).delete()
                except Exception as e:
                    logger.error(str(e))
                    resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
                    return JsonResponse(resp)

        # 返回成功的响应
        resp = {'code': 0, 'msg': 'success', 'data': ''}
        return JsonResponse(resp)

    def addProcessNameListBatch(self, request):
        detailid_list = request.data.get('detailid_list')
        process_list = request.data.get('process_list')
        print(process_list)

        for detailid in detailid_list:
            # 获取对应的 detailid 实例
            obj = OrderDetailTable.objects.get(detailid=detailid)

            # 获取当前数据库中存在的所有 process_name 列表
            existing_processes = list(ProductionProcessTable.objects.filter(detailid=obj).values_list('process_name', flat=True))
            print(existing_processes)

            # 处理增加操作：添加前端传入的 process_name 中不存在于现有数据库中的工艺
            for process_name in process_list:
                if not process_name:
                    continue
                if process_name not in existing_processes:
                    try:
                        ProductionProcessTable.objects.create(detailid=obj, process_name=process_name)
                    except Exception as e:
                        logger.error(str(e))
                        resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
                        return JsonResponse(resp)

            # 处理删除操作：删除数据库中存在但不在前端传入列表中的工艺
            for process_name in existing_processes:
                if process_name not in process_list:
                    try:
                        ProductionProcessTable.objects.filter(detailid=obj, process_name=process_name).delete()
                    except Exception as e:
                        logger.error(str(e))
                        resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
                        return JsonResponse(resp)

        resp = {'code': 0, 'msg': 'success', 'data': ''}
        return JsonResponse(resp)

    def getProcessNameListBatch(self, request):
            # 例：从请求中获取 detail_ids
            detailid_list = request.data.get('detailid_list')

            if not detailid_list:
                return JsonResponse({'code': 1, 'msg': 'detailid_list is required', 'data': []})

            try:
                # 使用 values() 方法将 QuerySet 转换为字典列表
                data = ProductionProcessTable.objects.filter(detailid__in=detailid_list) \
                    .values('process_name') \
                    .annotate(
                    total_commodity_quantity=Sum(F('detailid__commodity_quantity')),
                    total_process_quantity=Sum('process_quantity')
                )
                print(list(data))
                return JsonResponse({'code': 0, 'msg': 'success', 'data': list(data)})

            except Exception as e:
                return JsonResponse({'code': 2, 'msg': str(e), 'data': []})


    def update_process_quantity_view(self,request):
        # 从请求中获取数据
        request_data = request.data

        # 提取返回的 action 和 subaction，可以根据需要进行处理
        action = request_data.get('action')
        subaction = request_data.get('subaction')
        data_list = request_data.get('data', [])
        print(data_list)

        if action != 'production_process_table_view' or subaction != 'update_process_quantity_view':
            return JsonResponse({'error': '无效的请求'}, status=400)

        # 处理每一个 process_name 的更新请求
        for data in data_list:
            print(data)
            process_name = data.get('process_name')
            detailids = data.get('detailids', [])
            new_total_process_quantity = data.get('total_process_quantity')

            # 查询与当前 process_name 和 detailids 关联的 commodity_quantity 总和
            current_total_quantity = data.get('total_commodity_quantity')

            if current_total_quantity == 0:
                print("当前总的 commodity_quantity 为 0，无法按比例更新")
                continue  # 如果当前的总和为 0，跳过这个 process_name 的更新

            # 获取关联的生产过程记录
            records = ProductionProcessTable.objects.filter(detailid__in=detailids, process_name=process_name)
            # 按比例更新每条记录的 process_quantity
            new_quantity = new_total_process_quantity
            for record in records:
                # 根据 commodity_quantity 的比例计算 process_quantity 的新值
                if 0< new_quantity < record.detailid.commodity_quantity:
                    updated_quantity = new_quantity
                elif new_quantity == 0:
                    updated_quantity = 0
                else:
                    updated_quantity = round(new_total_process_quantity * (record.detailid.commodity_quantity / current_total_quantity))
                new_quantity = new_quantity - updated_quantity
                record.process_quantity = updated_quantity
                record.save()

        return JsonResponse({'code': 0, 'status': 'success', 'message': 'process_quantity 已按比例更新'})

    def batchDelete(self, request):
        detailid_list = request.data.get('detailid_list')
        print(detailid_list)
        for detailid in detailid_list:
            OrderDetailTable.objects.filter(detailid=detailid).delete()
        resp = {'code': 0, 'msg': 'success', 'data': ''}
        return JsonResponse(resp)

    def updateMultiRecords(self, request):
        update_records = request.data.get('update_records')
        for record in update_records:
            idmap = {'processid': record['processid']}
            editForm = {'process_quantity': record['process_quantity']}
            try:
                ProductionProcessTable.objects.filter(**idmap).update(**editForm)
            except Exception as e:
                logger.error(str(e))
                resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
                return JsonResponse(resp)
        resp = {'code': 0, 'msg': 'success', 'data': ''}
        return JsonResponse(resp)
