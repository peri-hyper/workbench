from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from app.api_code import *
from app.models import InventoryTable

from loguru import logger


class InventoryTableView(object):
    def query(self, request):
        """
        支持多关键字模糊搜索：前端传入的 product_name__icontains 字符串，
        如果包含空格，则按空格拆分成多个关键字，逐个做 AND 级联，每个关键字在
        product_name、product_size、brand、material_type 四个字段上做 OR 模糊匹配。

        如果没有搜索关键字，而 material_type == "耗材"，则按 search_form 里的所有精确条件过滤并按 quantity 排序。
        其它情况，则按 search_form 做精确过滤（等号匹配）。
        """
        # 1. 解析分页参数
        try:
            page_num = int(request.data.get("pageNum", 1))
            page_size = int(request.data.get("pageSize", 20))
        except (ValueError, TypeError):
            return JsonResponse({"code": 1, "msg": "分页参数必须是数字"}, status=400)

        # 2. 取出 searchForm
        search_form = request.data.get("searchForm", {}) or {}
        search_data = (search_form.get("product_name__icontains") or "").strip()
        material_type = search_form.get("material_type")

        # 3. 构造 QuerySet
        if search_data:
            # 3.1 如果存在搜索关键字，按空格拆分成多个关键词
            keywords = [kw for kw in search_data.split() if kw]
            base_q = Q()
            for kw in keywords:
                # 每个关键词在以下四个字段做 OR 模糊
                sub_q = (
                        Q(product_name__icontains=kw) |
                        Q(product_size__icontains=kw) |
                        Q(brand__icontains=kw) |
                        Q(material_type__icontains=kw)
                )
                base_q &= sub_q

            query_set = InventoryTable.objects.filter(base_q).order_by("inventoryid").values()
        elif material_type == "耗材":
            # 3.2 no search_data but material_type == "耗材"，按精确 filter(search_form)，按 quantity 排序
            #    先移除 product_name__icontains 键，确保 search_form 只包含模型字段
            sf = search_form.copy()
            sf.pop("product_name__icontains", None)
            query_set = (
                InventoryTable.objects
                .filter(**sf)
                .order_by("quantity")
                .values()
            )
        else:
            # 3.3 其它情况，按 search_form 做精确过滤
            sf = search_form.copy()
            sf.pop("product_name__icontains", None)
            query_set = (
                InventoryTable.objects
                .filter(**sf)
                .order_by("inventoryid")
                .values()
            )

        # 4. 分页
        paginator = Paginator(query_set, page_size)
        try:
            page_data = paginator.page(page_num)
        except:
            page_data = paginator.page(paginator.num_pages)

        # 5. 枚举映射：将 unit 和 material_type 转成对应的中文标签
        unit_choices_map = {
            "1": "件", "2": "套", "3": "批", "4": "千克",
            "5": "吨", "6": "包", "7": "盒", "8": "其他"
        }
        material_type_choices_map = {
            "1": "原材料", "2": "焊材", "3": "耗材",
            "4": "工具", "5": "配件", "6": "螺丝", "7": "钻铣"
        }

        data_list = []
        for item in page_data:
            # 加上 unit_label 和 material_type_label
            item["unit_label"] = unit_choices_map.get(str(item.get("unit")), "")
            item["material_type_label"] = material_type_choices_map.get(str(item.get("material_type")), "")
            data_list.append(item)

        # 6. 返回结果
        resp = {
            "code": 0,
            "msg": "success",
            "data": data_list,
            "total": paginator.count
        }
        return JsonResponse(resp)

    def addRecord(self, request):
        foreign_key_fields = {}
        for field in InventoryTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        addForm = {}
        modalForm = request.data.get('modalForm')
        for key, value in modalForm.items():
            if key == 'quantity':
                continue  # 跳过 "quantity" 字段
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                addForm[key[:-3]] = obj
            else:
                addForm[key] = value
        try:
            InventoryTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        try:
            InventoryTable.objects.filter(**idmap).delete()
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in InventoryTable._meta.get_fields():
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
            InventoryTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)
