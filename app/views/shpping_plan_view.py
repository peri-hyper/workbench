from __future__ import annotations

import os
import pandas as pd
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Cast
from app.models import ShippingDetailTable
from app.views.user_table_view import UserTableView
import datetime, logging
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────
def _clean(txt: str | None) -> str:
    """去掉空白与零宽空格，None → ''"""
    return (txt or "").strip().replace("\u200b", "")

class ShppingPlanView:
    def query(self, request):
        # 读取 Excel 文件
        excel_file = os.path.join(settings.BASE_DIR, 'templates', 'ShppingPlan.xlsx')
        df = pd.read_excel(excel_file)

        # 转换 DataFrame 中的日期和缺失值
        def convert_value(value):
            # 检查是否为 Timestamp 类型，并转换为 'YYYY-MM-DD' 格式字符串
            if isinstance(value, pd.Timestamp):
                if pd.isna(value):
                    return ''
                return value.strftime('%Y-%m-%d')  # 将日期转换为 'YYYY-MM-DD' 格式

            # 转换 nan 和 None 为 ''
            if pd.isna(value) or value is None:
                return ''

            # 保持其他数据类型不变
            return value

        # 应用转换函数
        df = df.applymap(convert_value)

        # 将 DataFrame 转换为字典列表
        data = df.to_dict(orient='records')
        print(data)

        # 返回 JSON 响应
        resp = {'code': 0, 'msg': 'success', 'data': data}
        return JsonResponse(resp)

    def query_shipping_data(self, request):
        """
        模糊字段：
          - 客户名           (detailid__customer_name__icontains)
          - 订单号           (detailid__order_number__icontains)
          - 发货日期         (delivery_date→字符串后 icontains)
          - 品名             (detailid__commodity_details__icontains)
          - 规格             (detailid__commodity_size__icontains)
          - Control No.      (detailid__control_no__icontains)
        其它字段保持精准 / 范围过滤
        """
        page_num = int(request.data.get("pageNum", 1))
        page_size = int(request.data.get("pageSize", 10))
        sf = request.data.get("searchForm", {}) or {}

        # ── 1. 角色控制 ───────────────────────────────────────────
        role = UserTableView().getRole(sf.get("username"))

        # ── 2. 精准 / 范围过滤 dict ───────────────────────────────
        filters = {}
        if dr := sf.get("delivery_date__range"):
            try:
                filters["shippingid__delivery_date__range"] = (
                    datetime.datetime.strptime(dr[0], "%Y-%m-%d").date(),
                    datetime.datetime.strptime(dr[1], "%Y-%m-%d").date(),
                )
            except Exception:
                logger.warning("非法日期范围: %s", dr)

        if on := sf.get("order_number"):
            filters["detailid__order_number"] = on

        if cid := sf.get("customer_name_id"):
            filters["detailid__customer_name_id"] = cid

        if un := sf.get("username"):
            filters["shippingid__username"] = un
            if role == 1:  # 某些角色不许按用户名查
                filters.pop("shippingid__username", None)

        # ── 3. 模糊查询 (6 字段 OR) ───────────────────────────────
        kw_raw = (sf.get("search_data") or "").strip().replace("\u200b", "")
        q_obj = Q()
        if kw_raw:
            # 允许空格分开多个关键字
            for kw in kw_raw.split():
                q_kw = (
                        Q(detailid__customer_name__customer_name__icontains=kw) |  # ← 修正
                        Q(detailid__order_number__order_number__icontains=kw) |
                        Q(detailid__commodity_details__icontains=kw) |
                        Q(detailid__commodity_size__icontains=kw) |
                        Q(detailid__control_no__icontains=kw) |
                        Q(shipping_id_str__icontains=kw) |
                        Q(delivery_date_str__icontains=kw)
                )
                q_obj &= q_kw

        # ── 4. 查询 & 分页 ───────────────────────────────────────
        qs = (
            ShippingDetailTable.objects
            .filter(**filters)
            .annotate(
                delivery_date_str=Cast("shippingid__delivery_date", CharField()),
                # 若 shippingid 已经是 CharField，可直接省掉这行，在上面写
                # Q(shippingid__shippingid__icontains=kw)，不用额外字符串化
                shipping_id_str=Cast("shippingid__shippingid", CharField())
            )
            .filter(q_obj)
            .select_related("shippingid", "detailid")
            .order_by("-shippingid")
        )

        paginator = Paginator(qs, page_size)
        page = paginator.get_page(page_num)

        # ── 5. 序列化 ────────────────────────────────────────────
        data = [
            {
                "customer_name_id": sd.detailid.customer_name_id,
                "order_number_id": sd.detailid.order_number_id,
                "delivery_date": sd.shippingid.delivery_date,
                "shippingdetailid": sd.shippingdetailid,
                "shippingid": sd.shippingid.shippingid,
                "shipping_quantity": sd.shipping_quantity,
                "shipping_weight": sd.shipping_weight,
                "detailid": sd.detailid.detailid,
                "commodity_details": sd.detailid.commodity_details,
                "commodity_size": sd.detailid.commodity_size,
                "control_no": sd.detailid.control_no,
                "commodity_units": sd.detailid.commodity_units,
            }
            for sd in page
        ]

        return JsonResponse({
            "code": 0,
            "msg": "success",
            "data": data,
            "total": paginator.count,
        })
