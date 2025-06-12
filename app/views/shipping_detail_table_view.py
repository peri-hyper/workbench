from decimal import Decimal

from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from app.api_code import *
from app.models import ShippingDetailTable, CustomerTable, DriverTable, ProjectTable, UserTable,OrderTable
from app.models import ShippingTable
from app.models import OrderDetailTable
from loguru import logger
from django.db.models import F, Sum
from app.util.db_util import DBUtil
import logging

logger = logging.getLogger(__name__)


def _clean(text: str) -> str:
    return (text or "").strip().replace("\u200b", "")


def _to_decimal(num) -> Decimal:
    return Decimal(str(num or 0)).quantize(Decimal("0.01"))

class ShippingDetailTableView(object):
    def query(self, request):
        page_num = request.data.get('pageNum')
        page_size = request.data.get('pageSize')
        search_form = request.data.get('searchForm')
        query_set = ShippingDetailTable.objects.filter(**search_form).all().order_by('shippingdetailid').values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)
        resp = {'code': 0, 'msg': 'success', 'data': list(page_data), 'total': len(query_set)}
        return JsonResponse(resp)

    def addRecord(self, request):
        foreign_key_fields = {}
        for field in ShippingDetailTable._meta.get_fields():
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
            ShippingDetailTable.objects.create(**addForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def deleteRecord(self, request):
        idmap = request.data.get('idmap')
        detailid = request.data.get('detailid')
        quantity = request.data.get('quantity')
        try:
            ShippingDetailTable.objects.filter(**idmap).delete()
            OrderDetailTable.objects.filter(detailid=detailid).update(commodity_quantity=F("commodity_quantity") + quantity)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def editRecord(self, request):
        foreign_key_fields = {}
        for field in ShippingDetailTable._meta.get_fields():
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
            ShippingDetailTable.objects.filter(**idmap).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def getOptions(self, request):
        data = {}
        options = []
        for item in ShippingTable.objects.all().values('shippingid'):
            options.append({'label': item['shippingid'], 'value': item['shippingid']})
        data['shippingid_options'] = options
        options = []
        for item in OrderDetailTable.objects.all().values('detailid'):
            options.append({'label': item['detailid'], 'value': item['detailid']})
        data['detailid_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)

    def addProductListByEdit(self, request):
        shippingid = request.data.get('shippingid')
        product_list = request.data.get('product_list')
        print(product_list)
        obj = ShippingTable.objects.get(shippingid=shippingid)
        try:
            for item in product_list:
                detailid = item['detailid']
                detial_obj = OrderDetailTable.objects.get(detailid=detailid)
                ShippingDetailTable.objects.create(shippingid=obj, detailid=detial_obj)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def addProductList(self, request):
        shippingid = request.data.get('shippingid')
        is_exists = ShippingTable.objects.filter(shippingid=shippingid).exists()
        if is_exists:
            ret = self.__updateShippingInfo(request)
        else:
            ret = self.__createShippingInfoReal(request)
        if not ret:
            resp = {'code': API_SYS_ERR, 'msg': '保存失败', 'data': ''}
            return JsonResponse(resp)
        shippingid = request.data.get('shippingid')
        product_list = request.data.get('product_list')
        obj = ShippingTable.objects.get(shippingid=shippingid)
        try:
            for item in product_list:
                detailid = item['detailid']
                detial_obj = OrderDetailTable.objects.get(detailid=detailid)
                ShippingDetailTable.objects.create(shippingid=obj, detailid=detial_obj)
        except Exception as e:
            logger.error(str(e))
            resp = {'code': API_SYS_ERR, 'msg': str(e), 'data': ''}
            return JsonResponse(resp)
        resp = {'code': API_OK, 'msg': 'succ', 'data': ''}
        return JsonResponse(resp)

    def getProductListByShippingId(self, request):
        shippingid = request.data.get('shippingid')
        sql = 'select shipping_detail_tb.*, shipping_tb.*, order_detail_tb.* ' \
              'from shipping_detail_tb, shipping_tb, order_detail_tb ' \
              'where shipping_detail_tb.shippingid_id = %s ' \
              'and shipping_detail_tb.shippingid_id = shipping_tb.shippingid ' \
              'and shipping_detail_tb.detailid_id = order_detail_tb.detailid' % shippingid
        code, msg, data = DBUtil.query(sql, {})
        resp = {'code': code, 'msg': msg, 'data': data}
        return JsonResponse(resp)

    def getShippingOptions(self, request):
        data = {}
        options = []
        for item in UserTable.objects.all().values('username'):
            options.append({'label': item['username'], 'value': item['username']})
        data['username_options'] = options
        options = []
        for item in CustomerTable.objects.all().values('customer_name'):
            options.append({'label': item['customer_name'], 'value': item['customer_name']})
        data['customer_name_options'] = options
        options = []
        for item in DriverTable.objects.all().values('driver_name'):
            options.append({'label': item['driver_name'], 'value': item['driver_name']})
        data['driver_name_options'] = options
        options = []
        for item in ProjectTable.objects.all().values('shipping_address'):
            options.append({'label': item['shipping_address'], 'value': item['shipping_address']})
        data['shipping_address_options'] = options
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)

    def __createShippingInfoReal(self, request):
        shippingid = request.data.get('shippingid')
        delivery_date = request.data.get('delivery_date', '')
        customer_name = request.data.get('customer_name', '')
        driver_name = request.data.get('driver_name', '')
        shipping_address = request.data.get('shipping_address', '')
        username = request.data.get('username', '')
        if not delivery_date or not customer_name or not driver_name or not shipping_address or not username:
            logger.error('缺少必要参数')
            return False
        customer_name_obj = CustomerTable.objects.get(customer_name=customer_name)
        driver_name_obj = DriverTable.objects.get(driver_name=driver_name)
        shipping_address_obj = ProjectTable.objects.filter(shipping_address=shipping_address).first().shipping_address
        username_obj = UserTable.objects.get(username=username)
        try:
            ShippingTable.objects.create(shippingid=shippingid,
                                         delivery_date=delivery_date,
                                         customer_name=customer_name_obj,
                                         driver_name=driver_name_obj,
                                         shipping_address=shipping_address_obj,
                                         username=username_obj)
        except Exception as e:
            print(e)
            logger.error(str(e))
            return False
        return True

    def __updateShippingInfo(self, request):
        shippingid = request.data.get('shippingid')
        delivery_date = request.data.get('delivery_date', '')
        customer_name = request.data.get('customer_name', '')
        driver_name = request.data.get('driver_name', '')
        shipping_address = request.data.get('shipping_address', '')
        username = request.data.get('username', '')
        customer_name_obj = CustomerTable.objects.get(customer_name=customer_name)
        driver_name_obj = DriverTable.objects.get(driver_name=driver_name)
        shipping_address_obj = ProjectTable.objects.get(project_name=shipping_address)
        username_obj = UserTable.objects.get(username=username)
        try:
            ShippingTable.objects.filter(shippingid=shippingid).update(delivery_date=delivery_date,
                                                                        customer_name=customer_name_obj,
                                                                        driver_name=driver_name_obj,
                                                                        shipping_address=shipping_address_obj,
                                                                        username=username_obj)
        except Exception as e:
            logger.error(str(e))
            return False
        return True

    def saveShippingInfo(self, request):
        shippingid = request.data.get('shippingid')
        is_exists = ShippingTable.objects.filter(shippingid=shippingid).exists()
        if is_exists:
            ret = self.__updateShippingInfo(request)
        else:
            ret = self.__createShippingInfoReal(request)
        if not ret:
            resp = {'code': API_SYS_ERR, 'msg': '保存失败', 'data': ''}
            return JsonResponse(resp)

        shippingdetailid_list = request.data.get('shippingdetailid_list')
        for item in shippingdetailid_list:
            shippingdetailid = item['shippingdetailid']
            shipping_quantity = item['shipping_quantity']
            ShippingDetailTable.objects.filter(shippingdetailid=shippingdetailid).update(shipping_quantity=shipping_quantity)
        resp = {'code': 0, 'msg': 'success', 'data': ''}
        return JsonResponse(resp)

    def saveShippingInfoNew(self, request):
        if False == self.__createShippingInfoReal(request):
            resp = {'code': API_SYS_ERR, 'msg': '保存失败', 'data': ''}
            return JsonResponse(resp)
        productlist = request.data.get('productlist')
        delivery_date = request.data.get('delivery_date', '')
        shippingid = request.data.get('shippingid')
        shippingid_obj = ShippingTable.objects.get(shippingid=shippingid)
        order_number_list = []
        for productinfo in productlist:
            detailid = productinfo['detailid']
            shipping_quantity = productinfo['shipping_quantity']
            shipping_weight = productinfo['shipping_weight']
            order_number = (
                productinfo['order_number_id']
                .strip()  # 去首尾空白
                .replace('\u200b', '')  # 去零宽空格（可选）
            )
            order_number_list.append(order_number)
            detailid_obj = OrderDetailTable.objects.get(detailid=detailid)
            OrderDetailTable.objects.filter(detailid=detailid).update(commodity_quantity = F("commodity_quantity") - shipping_quantity)
            OrderDetailTable.objects.filter(detailid=detailid).update(commodity_weight=F("commodity_quantity") * F("unit_weight"))
            ShippingDetailTable.objects.create(shippingid=shippingid_obj, detailid=detailid_obj, shipping_quantity=shipping_quantity,shipping_weight=shipping_weight)
        order_number_list = list(set(order_number_list))
        print("222" + str(order_number_list))
        for order_number in order_number_list:
            self.CheckDatabase(order_number,delivery_date)
        resp = {'code': 0, 'msg': 'success', 'data': ''}
        return JsonResponse(resp)

    def modifyShippingInfo(self, request):
        foreign_key_fields = {}
        for field in ShippingTable._meta.get_fields():
            if field.many_to_one:
                foreign_key_fields[field.name + '_id'] = field.related_model
        editForm = {}
        modalEditForm = request.data.get('shippinginfo')
        for key, value in modalEditForm.items():
            if key in foreign_key_fields:
                mmap = {key[:-3]: value}
                obj = foreign_key_fields[key].objects.get(**mmap)
                editForm[key[:-3]] = obj
            else:
                editForm[key] = value
        shippingid = request.data.get('shippingid')
        try:
            ShippingTable.objects.filter(shippingid=shippingid).update(**editForm)
        except Exception as e:
            logger.error(str(e))
            return False
        return True

    def saveShippingInfoByEdit(self, request):
        if False == self.modifyShippingInfo(request):
            resp = {'code': API_SYS_ERR, 'msg': '保存发货单信息失败', 'data': ''}
            return JsonResponse(resp)
        delivery_date = request.data.get('shippinginfo').get('delivery_date', '')
        shippingdetailid_list = request.data.get('shippingdetailid_list')
        shippingid = request.data.get('shippingid')
        shippingid_obj = ShippingTable.objects.get(shippingid=shippingid)
        datas = ShippingDetailTable.objects.filter(shippingid= shippingid).all()
        order_number_list = []
        # try:
        for item_1 in datas:
                detailid = item_1.detailid.detailid
                quantity = item_1.shipping_quantity
                OrderDetailTable.objects.filter(detailid=detailid).update(commodity_quantity=F("commodity_quantity") + quantity)
        datas.delete()
        for item in shippingdetailid_list:
            #{'detailid': 5133, 'shipping_weight': '0.0', 'shipping_quantity': 1, 'shippingdetailid': 4404,
             #'order_number_id': '#24166 20241022'}],
                shippingdetailid = item['shippingdetailid']
                shipping_quantity = item['shipping_quantity']
                shipping_weight = item['shipping_weight']
                detailid = item['detailid']
                order_number_id = (
                    item['order_number_id']
                    .strip()  # 去首尾空白
                    .replace('\u200b', '')  # 去零宽空格（可选）
                )
                order_number_list.append(order_number_id)
                OrderDetailTable.objects.filter(detailid=detailid).update(commodity_quantity=F("commodity_quantity") - shipping_quantity)
                detailid_obj = OrderDetailTable.objects.get(detailid=detailid)
                # if shippingdetailid != "":
                #     ShippingDetailTable.objects.filter(shippingdetailid=shippingdetailid).update(shipping_quantity=shipping_quantity)
                # else:
                ShippingDetailTable.objects.create(shipping_quantity=shipping_quantity,shipping_weight = shipping_weight,detailid=detailid_obj,shippingid=shippingid_obj)
        order_number_list = list(set(order_number_list))
        for order_number in order_number_list:
                self.CheckDatabase(order_number, delivery_date)
        # except Exception as e:
        #     print(e)
        #     resp = {'code': API_SYS_ERR, 'msg': f'保存发货单信息失败: {str(e)}', 'data': ''}
        #     return JsonResponse(resp)

        resp = {'code': 0, 'msg': 'success', 'data': ''}
        return JsonResponse(resp)

    @transaction.atomic
    def save_shipping_info(self,request, *, is_edit=False):
        """
        创建/编辑发货单（表头 + 明细 + 库存回写）
        is_edit=False  → 创建
        is_edit=True   → 编辑
        """

        data = request.data
        shippingid = data.get("shippingid")
        rows = data.get("productlist") if not is_edit else data.get("shippingdetailid_list")
        header = data.get("shippinginfo") if is_edit else data

        # ── 1. 参数校验 ───────────────────────────────────────────
        required = ["delivery_date", "customer_name", "driver_name", "shipping_address", "username"]
        missing = [f for f in required if not header.get(f)]
        if missing:
            msg = f"缺少必要参数: {','.join(missing)}"
            return JsonResponse({"code": 1, "msg": msg, "data": ""})

        # ── 2. 组装外键对象（一次查询防止 N+1）───────────────────
        try:
            customer = CustomerTable.objects.get(customer_name=header["customer_name"])
            driver = DriverTable.objects.get(driver_name=header["driver_name"])
            projects = ProjectTable.objects.filter(shipping_address=header["shipping_address"])
            if not projects.exists():
                return JsonResponse({"code": 1, "msg": "该地址未找到项目", "data": ""})

            if projects.count() > 1:
                logger.warning("shipping_address=%s 匹配到 %s 条项目，默认取第一条",
                               header["shipping_address"], projects.count())

            project = projects.first()  # 取 id 最小的一条；可改 order_by('-id').first()
            user = UserTable.objects.get(username=header["username"])
        except Exception as e:
            logger.exception(e)
            return JsonResponse({"code": 1, "msg": str(e), "data": ""})

        # ── 3. 创建或更新表头 ─────────────────────────────────────
        head_defaults = dict(
            delivery_date=header["delivery_date"],
            customer_name=customer,
            driver_name=driver,
            shipping_address=project.shipping_address,
            username=user
        )
        if is_edit:
            ShippingTable.objects.filter(shippingid=shippingid).update(**head_defaults)
            shipping_obj = ShippingTable.objects.select_for_update().get(shippingid=shippingid)
        else:
            shipping_obj, _ = ShippingTable.objects.get_or_create(shippingid=shippingid, defaults=head_defaults)

        # ── 4. 准备明细数据 ──────────────────────────────────────
        # 4.1  编辑场景：先把旧库存加回、删除旧明细
        if is_edit:
            old_details = ShippingDetailTable.objects.filter(shippingid=shipping_obj)
            old_ids = [d.detailid_id for d in old_details]
            if old_ids:
                (
                    OrderDetailTable.objects
                    .filter(detailid__in=old_ids)
                    .update(commodity_quantity=F("commodity_quantity") + F("shippingdetail__shipping_quantity"))
                )
            old_details.delete()

        # 4.2  收集本次明细行
        detail_ids = [r["detailid"] for r in rows]
        od_map = OrderDetailTable.objects.in_bulk(detail_ids)  # {id: OrderDetail}
        if len(od_map) != len(detail_ids):
            bad = set(detail_ids) - set(od_map)
            return JsonResponse({"code": 1, "msg": f"找不到明细: {bad}", "data": ""})

        # ── 5. 批量写入 ShippingDetail & 批量扣/还库存 ───────────
        new_details = []
        order_nos = set()
        for r in rows:
            qty = Decimal(r["shipping_quantity"])
            weight = Decimal(r["shipping_weight"])
            od = od_map[r["detailid"]]

            # 扣库存
            od.commodity_quantity -= qty

            new_details.append(
                ShippingDetailTable(
                    shippingid=shipping_obj,
                    detailid=od,
                    shipping_quantity=qty,
                    shipping_weight=weight
                )
            )
            order_nos.add(_clean(r["order_number_id"]))

        # 批量更新库存
        OrderDetailTable.objects.bulk_update(od_map.values(), ["commodity_quantity"])

        # 批量创建明细
        ShippingDetailTable.objects.bulk_create(new_details)

        # ── 6. 业务校验 / 触发额外逻辑 ────────────────────────────
        for on in order_nos:
            self.CheckDatabase(on, header["delivery_date"])  # 原函数保持不变

        return JsonResponse({"code": 0, "msg": "success", "data": ""})
    def CheckDatabase(self,order_number,delivery_date):
        total_quantity = OrderDetailTable.objects.filter(order_number=order_number).aggregate(total_quantity=Sum('commodity_quantity'))["total_quantity"]
        if total_quantity == 0:
            # 如果总和为0，则更新订单状态为已完成
            print(delivery_date)
            OrderTable.objects.filter(order_number=order_number).update(shpping_date=delivery_date)
            OrderTable.objects.filter(order_number=order_number).update(order_status=2)
        else:
            OrderTable.objects.filter(order_number=order_number).update(shpping_date='1900-01-01')
            OrderTable.objects.filter(order_number=order_number).update(order_status=1)