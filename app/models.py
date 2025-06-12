import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation

"""
python manage.py makemigrations app
python manage.py migrate
"""


class KVTable(models.Model):
    key = models.CharField(max_length=254, null=False, help_text='key', primary_key=True)
    value = models.TextField(null=True, help_text='value')

    class Meta:
        db_table = 'kv_tb'


class ManagedTable(models.Model):
    """
    https://blog.csdn.net/Mikowoo007/article/details/98203653
    1. orm中的default对原生sql不生效，即只要没指明null=True，原生sql插入时就必须给值；
       而orm使用时若设置了default，可以不对该字段赋值。
    2. DecimalField() max_digits:总位数， decimal_places:小数位数
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(null=True, max_length=50, help_text='名称')
    nickname = models.CharField(null=True, max_length=50, help_text='昵称')
    email = models.CharField(null=True, max_length=50, help_text='邮箱', unique=True)
    age = models.IntegerField(null=True, default=0, help_text='年龄')
    score = models.DecimalField(null=True, default=0.0, help_text='分数', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'managed_tb'


# 用户列表
class UserTable(models.Model):
    userid = models.AutoField(primary_key=True, verbose_name="主键")
    username = models.CharField(verbose_name="用户名", max_length=20, unique=True)
    password = models.CharField(verbose_name="密码", max_length=32)
    role_choices = [
        (1, "管理员"),
        (2, "跟单员"),
        (3, "质检员"),
        (4, "仓管员")
    ]
    role = models.SmallIntegerField(verbose_name="角色", choices=role_choices)

    class Meta:
        db_table = 'user_tb'


# 客户列表
class CustomerTable(models.Model):
    customerid = models.AutoField(primary_key=True, verbose_name="主键")
    customer_name = models.CharField(verbose_name="客户名称", max_length=150, unique=True)
    customer_address = models.CharField(verbose_name="客户地址", max_length=200, blank=True, null=True)
    contact_username = models.CharField(verbose_name="联络人姓名", max_length=20, blank=True, null=True)
    contact_phone = models.CharField(verbose_name="联络人电话", max_length=80, blank=True, null=True)
    fax_number = models.CharField(verbose_name="传真号码", max_length=80, blank=True, null=True)
    district = models.CharField(verbose_name="地区", max_length=10)
    remarks = models.CharField(verbose_name="备注", max_length=30, blank=True, null=True)

    class Meta:
        db_table = 'customer_tb'


# 司机列表
class DriverTable(models.Model):
    driverid = models.AutoField(primary_key=True, verbose_name="主键")
    driver_name = models.CharField(verbose_name="司机姓名", max_length=10, unique=True)
    driver_phone = models.CharField(verbose_name="司机电话", max_length=30)
    licence_plate = models.CharField(verbose_name="车牌", max_length=10, unique=True)

    class Meta:
        db_table = 'driver_tb'


# 项目列表
class ProjectTable(models.Model):
    projectid = models.AutoField(primary_key=True, verbose_name="主键")
    project_name = models.CharField(verbose_name="项目名称", max_length=50)
    shipping_address = models.CharField(verbose_name="送货地点", max_length=200)
    project_contact_name = models.CharField(verbose_name="联络人姓名", max_length=20)
    project_contact_phone = models.CharField(verbose_name="联络人电话", max_length=80)
    def __str__(self):
        return self.project_name
    class Meta:
        db_table = 'project_tb'


#  以下为供应商列表
class SupplierTable(models.Model):
    supplierid = models.AutoField(primary_key=True, verbose_name="主键")
    supplier_name = models.CharField(verbose_name="供应商名", max_length=110, unique=True)
    supplier_contact_name = models.CharField(verbose_name="联络人姓名", max_length=10, blank=True, null=True)
    supplier_contact_phone = models.CharField(verbose_name="联络人电话", max_length=15, blank=True, null=True)
    supplier_address = models.CharField(verbose_name="地址", max_length=110, blank=True, null=True)
    service_content = models.CharField(verbose_name="服务内容", max_length=50)
    approval_date = models.DateField(verbose_name="录入时间", auto_now_add=True)
    username = models.ForeignKey(UserTable, verbose_name="经办人", to_field="username", on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'supplier_tb'


# 订单列表
class OrderTable(models.Model):
    orderid = models.AutoField(primary_key=True, verbose_name="主键")
    order_number = models.CharField(verbose_name="订单号码", max_length=50, unique=True)
    attachments = GenericRelation('app.AttachmentFileTable', related_query_name='ordertable')
    customer_name = models.ForeignKey(CustomerTable, verbose_name="客户名称", to_field="customer_name", null=True,
                                      on_delete=models.DO_NOTHING)
    project_name = models.CharField(verbose_name="项目名称", max_length=50)
    username = models.ForeignKey(UserTable, verbose_name="跟单员", to_field="username",
                                 on_delete=models.DO_NOTHING)
    order_date = models.DateField(verbose_name="订单日期", max_length=10)
    manufacture_date = models.DateField(verbose_name="计划生产日期", max_length=10, null=False, blank=False, default=datetime.date.today)
    delivery_date = models.DateField(verbose_name="预出货日期", max_length=10)
    invoice_date = models.DateField(verbose_name="对账日期", max_length=10,blank=True, null=True)
    order_choices = [
        (1, "生产中"),
        (2, "已完成"),
        (0, "已暂停")
    ]
    order_status = models.SmallIntegerField(verbose_name="订单状态", choices=order_choices, default=1)
    shpping_date = models.DateField(verbose_name="出货日期", max_length=10,blank=True, null=True, default=datetime.date(1900, 1, 1))
    quote_date = models.DateField(verbose_name="报价日期", max_length=10, blank=True, null=True,default=datetime.date(1900, 1, 1))
    order_details = models.CharField(verbose_name="订单内容", max_length=50)
    remarks = models.CharField(verbose_name="备注", max_length=30, blank=True, null=True)
    def __str__(self):
        return self.order_number
    class Meta:
        db_table = 'order_tb'


# 订单明细表（产品列表，一个订单对应多个产品）
class OrderDetailTable(models.Model):
    # detailid是产品编号
    detailid = models.BigAutoField(primary_key=True, verbose_name="主键")
    customer_name = models.ForeignKey(CustomerTable, verbose_name="客户名称", to_field="customer_name", null=True,
                                      on_delete=models.DO_NOTHING)
    order_number = models.ForeignKey(OrderTable, verbose_name="订单号码", to_field="order_number",
                                      on_delete=models.CASCADE)
    commodity_details = models.CharField(verbose_name="品名", max_length=25)
    commodity_size = models.CharField(verbose_name="规格", max_length=100)
    control_no = models.CharField(verbose_name="编号", max_length=50)
    commodity_units = models.CharField(verbose_name="单位", max_length=5)
    commodity_quantity = models.IntegerField(verbose_name="产品数量")
    unit_weight = models.DecimalField(verbose_name="单件重量", max_digits=10, decimal_places=2, default=0, blank=True,
                                           null=True)
    commodity_weight = models.DecimalField(verbose_name="重量", max_digits=10, decimal_places=2, default=0, blank=True,
                                           null=True)
    username = models.CharField(verbose_name="用户名", max_length=20)
    remarks = models.CharField(verbose_name="备注", max_length=30, blank=True, null=True)

    class Meta:
        db_table = 'order_detail_tb'


# 工艺流程（一个产品对应多个工艺流程）
class ProductionProcessTable(models.Model):
    processid = models. BigAutoField(primary_key=True, verbose_name="主键")
    detailid = models.ForeignKey(to=OrderDetailTable, verbose_name="产品号码", to_field="detailid",
                                 on_delete=models.CASCADE)
    process_name = models.CharField(verbose_name="工艺名称", max_length=50)
    process_quantity = models.IntegerField(verbose_name="当前完成数量", null=True, default=0)

    class Meta:
        db_table = 'production_process_tb'
        constraints = [
            models.UniqueConstraint(fields=['detailid', 'process_name'], name='unique_detailid_process_name')
        ]


# 送货单列表
class ShippingTable(models.Model):
    shippingid = models.AutoField(primary_key=True, verbose_name="主键")
    shipping_address = models.CharField(verbose_name="送货地址", max_length=50)
    attachments = GenericRelation('app.AttachmentFileTable', related_query_name='shipping_table')
    driver_name = models.ForeignKey(to=DriverTable, verbose_name="司机姓名", to_field="driver_name",
                                    on_delete=models.DO_NOTHING)
    username = models.ForeignKey(to=UserTable, verbose_name="发货人", to_field="username", on_delete=models.DO_NOTHING)
    customer_name = models.ForeignKey(to=CustomerTable, verbose_name="客户名", to_field="customer_name", on_delete=models.DO_NOTHING)
    delivery_date = models.DateField(verbose_name="出货日期", max_length=10)
    sign_back_choices = [
        (1, "否"),
        (2, "是")
    ]
    sign_back = models.SmallIntegerField(verbose_name="是否上传回单", choices=sign_back_choices, default=1)
    class Meta:
        db_table = 'shipping_tb'


# 送货单详情（一个送货单对应多个产品）
class ShippingDetailTable(models.Model):
    shippingdetailid = models.AutoField(primary_key=True, verbose_name="主键")
    shippingid = models.ForeignKey(to=ShippingTable, verbose_name="送货单号", to_field="shippingid",
                                    on_delete=models.CASCADE)
    detailid = models.ForeignKey(to=OrderDetailTable, verbose_name="产品编号", to_field="detailid",
                                 on_delete=models.CASCADE)
    shipping_quantity = models.BigIntegerField(verbose_name="发货数量", blank=True, null=True, default=0)
    shipping_weight = models.DecimalField(verbose_name="出货重量", max_digits=10, decimal_places=2, default=0, blank=True,
                                           null=True)
    class Meta:
        db_table = 'shipping_detail_tb'


# 外发记录
class OutwardProcessing(models.Model):
    outwardid = models.AutoField(primary_key=True, verbose_name="主键")
    outward_number = models.CharField(verbose_name="外发清单编号", max_length=20, unique=True)
    outward_processing_number = models.ForeignKey(to=SupplierTable, verbose_name="供应商id", to_field="supplierid",
                                                  on_delete=models.DO_NOTHING)
    requested_by = models.ForeignKey(to=UserTable, verbose_name="申请人", to_field="username", on_delete=models.DO_NOTHING)
    outwardprocess_date = models.DateField(verbose_name="日期", max_length=10)
    remarks = models.CharField(verbose_name="备注", max_length=30, null=True)

    class Meta:
        db_table = 'outward_process_tb'


# 外发清单详情
class OutwardDetail(models.Model):
    outwarddetailid = models.AutoField(primary_key=True, verbose_name="主键")
    outward_number = models.ForeignKey(to=OutwardProcessing, verbose_name="外发清单编号", to_field="outward_number",
                                       on_delete=models.CASCADE)
    description = models.CharField(verbose_name="描述", max_length=100)
    commodity_qty = models.IntegerField(verbose_name="数量")
    currency = models.CharField(verbose_name="币种", max_length=5)
    unit_price = models.DecimalField(verbose_name="单价",default=0, max_digits=10, decimal_places=2, blank=True, null=True)
    total_price = models.DecimalField(verbose_name="总价",default=0, max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'outward_detail_tb'


# 请求采购清单
class RequestBuyTable(models.Model):
    requestid = models.AutoField(primary_key=True, verbose_name="主键")
    product_name = models.CharField(verbose_name="产品名称", max_length=100)
    product_size = models.CharField(verbose_name="产品规格", max_length=100)
    material = models.CharField(verbose_name="材质", max_length=10, blank=True, null=True)
    quantity = models.DecimalField(
        verbose_name="数量",
        max_digits=10,  # 一共最多 10 位（含小数位）
        decimal_places=2  # 保留 2 位小数
    )
    unit = models.CharField(verbose_name="单位", max_length=5)
    unit_price = models.DecimalField(verbose_name="单价", max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    total_price = models.DecimalField(verbose_name="总价", max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    username = models.ForeignKey(to=UserTable, verbose_name="申请人", to_field="username", on_delete=models.DO_NOTHING)
    requestdate = models.DateField(verbose_name="申请时间", auto_now_add=True)
    whether_buy = models.SmallIntegerField(verbose_name="是否采购", choices=((1, "是"), (2, "否")))
    remarks = models.CharField(verbose_name="备注", max_length=30, blank=True, null=True)

    class Meta:
        db_table = 'request_buy_tb'

# 采购单
class PurchaseTable(models.Model):
    purchaseid = models.AutoField(primary_key=True, verbose_name="主键")
    purchase_number = models.CharField(verbose_name="采购单号", max_length=50, unique=True)
    attachments = GenericRelation('app.AttachmentFileTable', related_query_name='purchase')
    username = models.ForeignKey(to=UserTable, verbose_name="采购员", to_field="username", on_delete=models.DO_NOTHING)
    supplier_name = models.ForeignKey(to=SupplierTable, verbose_name="供应商名称", to_field="supplier_name",
                                      on_delete=models.CASCADE)
    contact_person = models.CharField(verbose_name="联系人", max_length=20, default=0, blank=True, null=True)
    contact_number = models.CharField(verbose_name="联系方式", max_length=20, default=0, blank=True, null=True)
    purchase_date = models.DateField(verbose_name="采购日期", max_length=10)
    currency = models.CharField(verbose_name="币种", max_length=5)
    AOG_choices = [
        (1, "未到货"),
        (2, "已到货")
    ]
    AOG_status = models.SmallIntegerField(verbose_name="到货状态", choices=AOG_choices, default=1)
    remark = models.CharField(verbose_name="备注", max_length=5000, blank=True, null=True)

    class Meta:
        db_table = 'purchase_tb'

# 采购单详情
class PurchaseDetailTable(models.Model):
    purchasedetailid = models.AutoField(primary_key=True, verbose_name="主键")
    requestid = models.ForeignKey(to=RequestBuyTable,verbose_name="待采表ID",to_field="requestid",on_delete=models.DO_NOTHING)
    purchase_number = models.ForeignKey(to=PurchaseTable, verbose_name="采购单号", to_field="purchase_number",
                                        on_delete=models.CASCADE)
    product_name = models.CharField(verbose_name="产品名称", max_length=100)
    product_size = models.CharField(verbose_name="产品规格", max_length=100)
    material = models.CharField(verbose_name="材质", max_length=10, blank=True, null=True)
    quantity = models.DecimalField(
        verbose_name="数量",
        max_digits=10,  # 一共最多 10 位（含小数位）
        decimal_places=2  # 保留 2 位小数
    )
    unit = models.CharField(verbose_name="单位", max_length=5)
    unit_price = models.DecimalField(verbose_name="单价", default=0, max_digits=10, decimal_places=2, blank=True, null=True)
    total_price = models.DecimalField(verbose_name="总价", default=0, max_digits=10, decimal_places=2, blank=True, null=True)
    remark = models.CharField(verbose_name="备注", max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'purchase_detail_tb'

# 证书
class CertificateTable(models.Model):
    certificateid = models.AutoField(primary_key=True, verbose_name="主键")
    product_name = models.CharField(verbose_name="产品名称", max_length=15)
    product_size = models.CharField(verbose_name="产品规格", max_length=110)
    material = models.CharField(verbose_name="材质", max_length=10, blank=True, null=True, default=0)
    quantity = models.IntegerField(verbose_name="数量", blank=True, null=True, default=0)
    heat_number = models.CharField(verbose_name="炉号", max_length=10, blank=True, null=True, default=0)
    certificate_number = models.CharField(verbose_name="证书编号", max_length=10, blank=True, null=True, default=0)
    certificate_date = models.DateField(verbose_name="证书日期", max_length=10)
    certificate_file = models.CharField(verbose_name="证书文件", max_length=110)
    cover_file = models.CharField(verbose_name="封面文件", max_length=110)

    class Meta:
        db_table = 'certificate_tb'

# 发票列表
class InvoicesTable(models.Model):
    invoicesid = models.AutoField(primary_key=True, verbose_name="主键")
    invoices_number = models.CharField(verbose_name="发票号码", max_length=50, unique=True)
    customer_name = models.ForeignKey(to=CustomerTable, verbose_name="客户名称", to_field="customer_name",
                                      on_delete=models.CASCADE)
    order_number = models.ForeignKey(to=OrderTable, verbose_name="订单号码", to_field="order_number",
                                     on_delete=models.CASCADE)
    shippingid = models.ForeignKey(to=ShippingTable, verbose_name="货单编号", to_field="shippingid",
                                             on_delete=models.CASCADE)
    total_price = models.DecimalField(verbose_name="总价", max_digits=10, decimal_places=2)
    batch = models.CharField(verbose_name="批次", max_length=10, blank=True, null=True)

    class Meta:
        db_table = 'invoices_tb'


# 发票内容
class InvoicesDetailTable(models.Model):
    invoicesdetailid = models.AutoField(primary_key=True, verbose_name="主键")
    invoices_number = models.ForeignKey(to=InvoicesTable, verbose_name="发票号码", to_field="invoices_number",
                                        on_delete=models.CASCADE)
    detail = models.CharField(verbose_name="内容", max_length=100)
    unit = models.CharField(verbose_name="单位", max_length=5)
    currency = models.CharField(verbose_name="币种", max_length=5)
    unit_price = models.DecimalField(verbose_name="单价", max_digits=10, decimal_places=2)
    quantity = models.IntegerField(verbose_name="数量")
    total_price = models.DecimalField(verbose_name="总价", max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'invoices_detail_tb'


# 库存表
class InventoryTable(models.Model):
    inventoryid = models.AutoField(primary_key=True, verbose_name="主键")
    product_name = models.CharField(verbose_name="产品名称", max_length=100)
    product_size = models.CharField(verbose_name="产品规格", max_length=100)
    unit_choices = (
        (1, "件"),
        (2, "套"),
        (3, "批"),
        (4, "千克"),
        (5, "吨"),
        (6, "包"),
        (7, "盒"),
        (8, "其他"),
    )
    unit = models.SmallIntegerField(verbose_name="单位", choices=unit_choices)
    quantity = models.IntegerField(verbose_name="数量",default=0)
    brand = models.CharField(verbose_name="品牌", max_length=10, blank=True, null=True)
    material_certificate = models.CharField(verbose_name="材质", max_length=100, blank=True, null=True)
    material_type = models.CharField(verbose_name="类型", max_length=5)
    remark = models.CharField(verbose_name="备注", max_length=30, blank=True, null=True)

    class Meta:
        db_table = 'inventory_tb'


#订单文件列表
class FileTable(models.Model):
    fileid = models.AutoField(primary_key=True, verbose_name="主键")
    customer_name = models.ForeignKey(CustomerTable, verbose_name="客户名称", to_field="customer_name", null=True,
                                      on_delete=models.DO_NOTHING)
    order_number = models.ForeignKey(to=OrderTable, verbose_name="订单号码", to_field="order_number",
                                     on_delete=models.CASCADE)
    filename = models.CharField(verbose_name="文件名", max_length=150)
    new_filename = models.CharField(verbose_name="新文件名", max_length=50)
    upload_time = models.DateField(verbose_name="上传时间", auto_now_add=True)
    file_size = models.IntegerField(verbose_name="文件大小")
    file_suffix = models.CharField(verbose_name="文件后缀", max_length=20)
    file_choices = (
        (1, "合同/订单"),
        (2, "图纸"),
        (3, "已签收发货单"),
        (4, "验焊报告"),
        (5, "质检报告"),
        (6, "镀锌报告"),
        (7, "其他"),
    )
    file_type = models.SmallIntegerField(verbose_name="文件类型", choices=file_choices)

    class Meta:
        db_table = 'file_tb'
def upload_to(instance, filename):
    model = instance.content_type.model   # 例如 purchase、delivery
    return f'attachments/{model}/{instance.object_id}/{filename}'
#附件列表
class AttachmentFileTable(models.Model):
    attachmentid = models.AutoField(primary_key=True, verbose_name="主键")

    # —— 新增：泛型外键 ————————————————————
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        related_name='attachments', verbose_name='所属模型')
    object_id = models.PositiveIntegerField(verbose_name='所属记录 PK')
    parent = GenericForeignKey('content_type', 'object_id')

    # —— 文件字段 ————————————————————————
    file = models.FileField(upload_to=upload_to, verbose_name='文件')
    filename = models.CharField(max_length=150, verbose_name='文件名')
    file_size = models.PositiveIntegerField(verbose_name='文件大小')
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')

    class Meta:
        db_table = 'attachment_file_tb'
        index_together = ('content_type', 'object_id')
# 开料检验列表
# 通用公差
# 检验数量
# 检验地点
# 检验标准
# 检验单号
# 订单号码
# 客户名称
# 材料
# 切割数量
from django.core.files.storage import FileSystemStorage
import os

class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        # 如果文件已存在则删除，达到覆盖效果
        if self.exists(name):
            self.delete(name)
        return name
class InspectionCuttingRecord(models.Model):
    """
    质量检验记录模型
    """
    inspection_quantity = models.PositiveIntegerField(verbose_name="检验数量")  # 3
    inspection_location = models.CharField(max_length=100, verbose_name="检验地点")  # 车间
    inspection_standard = models.CharField(max_length=255, verbose_name="检验标准")  # 跟图纸
    general_tolerance = models.CharField(max_length=255, verbose_name="通用公差")  # 公差
    inspection_number = models.CharField(max_length=50, unique=True, verbose_name="检验单号")  # CT202503131718363100 (唯一)
    order_number = models.ForeignKey(to=OrderTable, verbose_name="订单号码", to_field="order_number",on_delete=models.CASCADE)  # SQ649764 (唯一)
    customer_name = models.ForeignKey(to=CustomerTable, verbose_name="客户名称", to_field="customer_name",on_delete=models.CASCADE)
    material = models.CharField(max_length=255, verbose_name="材料")  # 50×50×5mm 角钢
    cutting_quantity = models.PositiveIntegerField(verbose_name="切割数量")  # 20
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")  # 记录创建时间
    reference_image = models.FileField(verbose_name="参考图片", upload_to='images/reference_image/')
    inspector_name = models.CharField(max_length=10, verbose_name="检验员")  # ±3 (可为空)
    # 新增字段
    deformation_status = models.BooleanField(default=False, verbose_name="变形")  # True 代表合格，False 代表不合格
    cutting_perpendicularity = models.BooleanField(default=False,verbose_name="切口垂直度")  #
    slag_residue = models.BooleanField(default=False, verbose_name="是否有熔渣残留")  # True 代表有残留，False 代表无残留
    cutting_roughness = models.BooleanField(default=False,verbose_name="切口粗糙度")  #
    class Meta:
        db_table = 'inspection_cutting_record_tb'

# 切割质检单详情
class InspectionCuttingDetailRecord(models.Model):
    checkpoint = models.IntegerField(verbose_name="检查点")  # 检查点
    required_value = models.FloatField(verbose_name="要求值")  # 要求值
    tolerance = models.CharField(max_length=50, verbose_name="公差")  # 公差
    actual_value = models.FloatField(verbose_name="实际值")  # 实际值

    image_1 = models.ImageField(upload_to="images/reference_image/", null=True, blank=True, verbose_name="图片1")
    image_2 = models.ImageField(upload_to="images/reference_image/", null=True, blank=True, verbose_name="图片2")
    image_3 = models.ImageField(upload_to="images/reference_image/", null=True, blank=True, verbose_name="图片3")
    inspection_number = models.ForeignKey(to=InspectionCuttingRecord, verbose_name="检验单号", to_field="inspection_number",on_delete=models.CASCADE)  # 检验单号
    # inspection_number_id = models.CharField(max_length=50, verbose_name="检验单号")  # 检验单号
    pointX = models.FloatField(verbose_name="X 坐标")  # X 坐标
    pointY = models.FloatField(verbose_name="Y 坐标")  # Y 坐标
    class Meta:
        db_table = 'inspection_cutting_record_detail_tb'


# 组装检验记录表
class InspectionAssemblyRecord(models.Model):
    """
    钢结构组装检验 - 记录表
    (原 InspectionCuttingRecord)
    """

    # 基本字段
    inspection_quantity = models.PositiveIntegerField(verbose_name="检验数量")
    inspection_location = models.CharField(max_length=100, verbose_name="检验地点")
    inspection_standard = models.CharField(max_length=255, verbose_name="检验标准")
    general_tolerance = models.CharField(max_length=255, verbose_name="通用公差")
    inspection_number = models.CharField(max_length=50, unique=True, verbose_name="检验单号")

    # 外键示例（订单、客户）
    order_number = models.ForeignKey(
        to=OrderTable,
        verbose_name="订单号码",
        to_field="order_number",
        on_delete=models.CASCADE
    )
    customer_name = models.ForeignKey(
        to=CustomerTable,
        verbose_name="客户名称",
        to_field="customer_name",
        on_delete=models.CASCADE
    )

    # 原 material -> component_number
    component_number = models.CharField(
        max_length=255,
        verbose_name="构件编号"
    )
    # 原 cutting_quantity -> assembly_quantity
    assembly_quantity = models.PositiveIntegerField(
        verbose_name="构件数量"
    )

    # 时间、参考图片
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    reference_image = models.FileField(upload_to='images/reference_image/', verbose_name="参考图片")

    inspector_name = models.CharField(max_length=10, verbose_name="检验员", blank=True, null=True)

    # 原 deform_status / cutting_* => 新含义
    # 「变形」->「坡口质量(若适用)」，例：bevel_quality
    bevel_quality = models.BooleanField(default=False, verbose_name="坡口质量")
    # 「切口垂直度」->「母材清洁」
    materiel_cleanliness = models.BooleanField(default=False, verbose_name="母材清洁")
    # 「熔渣残留」->「角度与对称性」
    angle_symmetry = models.BooleanField(default=False, verbose_name="角度与对称性")
    # 「切口粗糙度」->「错位量」
    misalignment = models.BooleanField(default=False, verbose_name="错位量")

    class Meta:
        # 原 db_table = 'inspection_cutting_record_tb'
        db_table = 'inspection_assembly_record_tb'
        verbose_name = "组装检验记录表"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.inspection_number


# 组装检验 - 记录详情表
class InspectionAssemblyDetailRecord(models.Model):
    """
    钢结构组装检验 - 记录详情表
    (原 InspectionCuttingDetailRecord)
    """
    # 原 checkpoint / required_value / tolerance / actual_value
    checkpoint = models.IntegerField(verbose_name="检查点")
    required_value = models.FloatField(verbose_name="要求值")
    tolerance = models.CharField(max_length=50, verbose_name="公差")
    actual_value = models.FloatField(verbose_name="实际值")

    # 图片
    image_1 = models.ImageField(
        upload_to="images/reference_image/",
        null=True, blank=True,
        verbose_name="图片1"
    )
    image_2 = models.ImageField(
        upload_to="images/reference_image/",
        null=True, blank=True,
        verbose_name="图片2"
    )
    image_3 = models.ImageField(
        upload_to="images/reference_image/",
        null=True, blank=True,
        verbose_name="图片3"
    )

    # 外键指向上方记录表
    inspection_number = models.ForeignKey(
        to=InspectionAssemblyRecord,
        verbose_name="检验单号",
        to_field="inspection_number",
        on_delete=models.CASCADE
    )

    # 坐标
    pointX = models.FloatField(verbose_name="X 坐标")
    pointY = models.FloatField(verbose_name="Y 坐标")

    class Meta:
        # 原 db_table = 'inspection_cutting_record_detail_tb'
        db_table = 'inspection_assembly_record_detail_tb'
        verbose_name = "组装检验详情表"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Detail for {self.inspection_number} - checkpoint {self.checkpoint}"
# 焊接检验记录表
class InspectionWeldingRecord(models.Model):
    """
    钢结构焊接检验 - 记录表
    (原 InspectionAssemblyRecord)
    """

    # 基本字段
    inspection_quantity = models.PositiveIntegerField(verbose_name="检验数量")
    inspection_location = models.CharField(max_length=100, verbose_name="检验地点")
    inspection_standard = models.CharField(max_length=255, verbose_name="检验标准")
    general_tolerance   = models.CharField(max_length=255, verbose_name="通用公差")
    inspection_number   = models.CharField(max_length=50, unique=True, verbose_name="检验单号")

    # 外键示例（订单、客户）
    order_number = models.ForeignKey(
        to=OrderTable,
        verbose_name="订单号码",
        to_field="order_number",
        on_delete=models.CASCADE
    )
    customer_name = models.ForeignKey(
        to=CustomerTable,
        verbose_name="客户名称",
        to_field="customer_name",
        on_delete=models.CASCADE
    )

    # 构件编号
    component_number = models.CharField(
        max_length=255,
        verbose_name="构件编号"
    )

    # 原 assembly_quantity => welding_quantity
    welding_quantity = models.PositiveIntegerField(
        verbose_name="构件数量"
    )

    # 时间、参考图片
    created_date     = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    reference_image  = models.FileField(
        upload_to='images/reference_image/',
        verbose_name="参考图片",
        blank=True,
        null=True
    )

    inspector_name   = models.CharField(max_length=10, verbose_name="检验员", blank=True, null=True)

    # 焊接方法（6个布尔字段 + 1个“其他文本”）
    ck_in_line_butt_joint = models.BooleanField(default=False, verbose_name="对接接头(直通)")
    ck_tee_joint          = models.BooleanField(default=False, verbose_name="T字接头")
    ck_node_tky_joint     = models.BooleanField(default=False, verbose_name="节点(TKY)接头")
    ck_cruciform_joint    = models.BooleanField(default=False, verbose_name="十字接头")
    ck_corner_joint       = models.BooleanField(default=False, verbose_name="角接接头")
    ck_other_joint        = models.BooleanField(default=False, verbose_name="其他")
    other_joint_text      = models.CharField(max_length=255, blank=True, null=True, verbose_name="其他接头说明")

    class Meta:
        db_table            = 'inspection_welding_record_tb'
        verbose_name        = "焊接检验记录表"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.inspection_number



# 焊接检验 - 记录详情表
class InspectionWeldingDetailRecord(models.Model):
    """
    钢结构焊接检验 - 记录详情表
    (原 InspectionAssemblyDetailRecord)
    """

    checkpoint = models.IntegerField(verbose_name="检查点")
    required_value = models.FloatField(verbose_name="要求值")
    tolerance = models.CharField(max_length=50, verbose_name="公差")
    actual_value = models.FloatField(verbose_name="实际值")

    # 最多 3 张图片
    image_1 = models.ImageField(
        upload_to="images/reference_image/",
        null=True, blank=True,
        verbose_name="图片1"
    )
    image_2 = models.ImageField(
        upload_to="images/reference_image/",
        null=True, blank=True,
        verbose_name="图片2"
    )
    image_3 = models.ImageField(
        upload_to="images/reference_image/",
        null=True, blank=True,
        verbose_name="图片3"
    )

    # 外键：指向焊接检验记录表
    inspection_number = models.ForeignKey(
        to="InspectionWeldingRecord",
        verbose_name="检验单号",
        to_field="inspection_number",
        on_delete=models.CASCADE
    )
    visual_check = models.BooleanField(default=False, verbose_name="外观检查")
    weld_process = models.CharField(max_length=20, verbose_name="焊接工艺")
    # 坐标
    pointX = models.FloatField(verbose_name="X 坐标")
    pointY = models.FloatField(verbose_name="Y 坐标")



    class Meta:
        db_table            = 'inspection_welding_record_detail_tb'  # 新表名
        verbose_name        = "焊接检验详情表"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Detail for {self.inspection_number} - checkpoint {self.checkpoint}"

# 成品检验记录表
class InspectionFinishRecord(models.Model):
    """
    成品检验记录表
    """
    # 基本字段
    inspection_quantity = models.PositiveIntegerField(verbose_name="检验数量")
    inspection_location = models.CharField(max_length=100, verbose_name="检验地点")
    inspection_standard = models.CharField(max_length=255, verbose_name="检验标准")
    general_tolerance   = models.CharField(max_length=255, verbose_name="通用公差")
    film_thickness = models.CharField(max_length=255, verbose_name="通用膜厚")
    inspection_number   = models.CharField(max_length=50, unique=True, verbose_name="检验单号")

    # 外键：订单和客户（根据你原有的 OrderTable、CustomerTable 定义）
    order_number = models.ForeignKey(
        to=OrderTable,
        verbose_name="订单号码",
        to_field="order_number",
        on_delete=models.CASCADE
    )
    customer_name = models.ForeignKey(
        to=CustomerTable,
        verbose_name="客户名称",
        to_field="customer_name",
        on_delete=models.CASCADE
    )

    # 构件编号、产品数量
    component_number = models.CharField(max_length=255, verbose_name="构件编号")
    product_quantity = models.PositiveIntegerField(verbose_name="产品数量")

    # 时间和参考图片
    created_date    = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    reference_image = models.FileField(
        upload_to='images/reference_image/',
        verbose_name="参考图片",
        blank=True,
        null=True
    )

    inspector_name  = models.CharField(max_length=10, verbose_name="检验员", blank=True, null=True)

    # 表面处理选项（5个布尔字段）
    ck_none               = models.BooleanField(default=False, verbose_name="无")
    ck_hot_dip_galvanizing= models.BooleanField(default=False, verbose_name="热浸锌")
    ck_spray              = models.BooleanField(default=False, verbose_name="喷涂")
    ck_cold_galvanizing   = models.BooleanField(default=False, verbose_name="冷镀锌")
    ck_other_surface      = models.BooleanField(default=False, verbose_name="其他")

    class Meta:
        db_table            = 'inspection_finish_record_tb'
        verbose_name        = "成品检验记录表"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.inspection_number

# 成品检验详情表（尺寸数据）
class InspectionFinishDetailRecord(models.Model):
    """
    成品检验 - 尺寸数据详情表
    """
    checkpoint      = models.IntegerField(verbose_name="检查点")
    required_value  = models.FloatField(verbose_name="要求值")
    tolerance       = models.CharField(max_length=50, verbose_name="公差")
    actual_value    = models.FloatField(verbose_name="实际值")
    judgment        = models.FloatField(verbose_name="判断值")  # 可直接存实际值与要求值的差值

    # 最多支持上传 3 张图片
    image_1 = models.ImageField(
        upload_to="images/reference_image/",
        null=True,
        blank=True,
        verbose_name="图片1"
    )
    image_2 = models.ImageField(
        upload_to="images/reference_image/",
        null=True,
        blank=True,
        verbose_name="图片2"
    )
    image_3 = models.ImageField(
        upload_to="images/reference_image/",
        null=True,
        blank=True,
        verbose_name="图片3"
    )

    # 外键关联成品检验记录
    inspection_number = models.ForeignKey(
        InspectionFinishRecord,
        verbose_name="检验单号",
        to_field="inspection_number",
        on_delete=models.CASCADE
    )
    # 坐标
    pointX = models.FloatField(verbose_name="X 坐标")
    pointY = models.FloatField(verbose_name="Y 坐标")

    # 可选：是否通过视觉检查、焊接工艺等信息
    visual_check = models.BooleanField(default=False, verbose_name="外观检查")
    weld_process = models.CharField(max_length=20, verbose_name="焊接工艺", blank=True, null=True)

    class Meta:
        db_table            = 'inspection_finish_detail_record_tb'
        verbose_name        = "成品检验详情表（尺寸数据）"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Detail for {self.inspection_number} - checkpoint {self.checkpoint}"

# 成品检验详情表（表面参数）
class InspectionFinishSurfaceRecord(models.Model):
    """
    成品检验 - 表面参数详情表
    """
    checkpoint     = models.IntegerField(verbose_name="检查点")
    required_value = models.FloatField(verbose_name="要求值")
    actual_value   = models.FloatField(verbose_name="实际值")
    coating_type   = models.CharField(max_length=50, verbose_name="表面处理类型")
    judgment       = models.FloatField(verbose_name="判断值")

    # 可支持上传图片，如有需要
    image_1 = models.ImageField(
        upload_to="images/reference_image/",
        null=True,
        blank=True,
        verbose_name="图片"
    )

    # 外键关联成品检验记录
    inspection_number = models.ForeignKey(
        InspectionFinishRecord,
        verbose_name="检验单号",
        to_field="inspection_number",
        on_delete=models.CASCADE
    )
    # 坐标
    pointX = models.FloatField(verbose_name="X 坐标")
    pointY = models.FloatField(verbose_name="Y 坐标")

    class Meta:
        db_table            = 'inspection_finish_surface_record_tb'
        verbose_name        = "成品检验详情表（表面参数）"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Surface detail for {self.inspection_number} - checkpoint {self.checkpoint}"
class MaterialList(models.Model):
    """
    Excel 材料清单模型
    ────────────────
    Product_name | Specifications | Material | Quantity | Heat_number__Batch_number
    Certificate_number | date | id
    """
    product_name       = models.CharField('品名', max_length=100)
    specifications     = models.CharField('规格', max_length=120)
    material           = models.CharField('材质', max_length=50)

    quantity           = models.PositiveIntegerField('数量', default=0)

    heat_batch_number  = models.CharField('炉号 / 批号', max_length=60)
    certificate_number = models.CharField('材质证明书编号', max_length=60, blank=True, null=True)

    received_date      = models.DateField('收货日期')
    record_code        = models.CharField('记录编号', max_length=20, unique=True)

    class Meta:
        db_table = 'material_list'          # 数据库真实表名
        verbose_name = '材料清单'
        verbose_name_plural = verbose_name
        ordering = ['-received_date']
        indexes = [
            models.Index(fields=['record_code']),
            models.Index(fields=['certificate_number']),
        ]

    def __str__(self):
        return f'{self.record_code} - {self.product_name} {self.specifications}'
# 质检单列表
class CheckContentsTable(models.Model):
    checkid = models.AutoField(primary_key=True, verbose_name="主键")
    gender_choices = (
        (1, "首次检验"),
        (2, "巡查检验"),
        (3, "终次检验"),
    )
    in_process_inspection = models.SmallIntegerField(verbose_name="检验次数", choices=gender_choices)
    inspection_number = models.CharField(verbose_name="检验单号", max_length=50, unique=True)
    order_number = models.ForeignKey(OrderTable, verbose_name="订单号码", to_field="order_number", on_delete=models.CASCADE)
    detailid = models.ForeignKey(OrderDetailTable, verbose_name="构件ID", to_field="detailid", on_delete=models.CASCADE)
    inspection_quantity = models.IntegerField(verbose_name="检验数量")
    inspector_name = models.CharField(verbose_name="检验员姓名", max_length=10)
    reference_image = models.FileField(verbose_name="参考图片", upload_to='images/reference_image/')
    inspection_adress = models.CharField(verbose_name="检验地点", max_length=10)
    inspection_date = models.DateField(verbose_name="检验时间")
    inspection_standard = models.CharField(verbose_name="检验标准", max_length=20)
    gender_choices_type = (
        (1, "来料检验"),
        (2, "开料检验"),
        (3, "组装检验"),
        (4, "焊接检验"),
        (5, "锌层检验"),
        (6, "涂层检验"),
    )
    inspection_type = models.SmallIntegerField(verbose_name="检验类型", choices=gender_choices_type)

    class Meta:
        db_table = 'check_contents_tb'

class IncomingInspectionRecord(models.Model):
    """
    对应  GatherHeaderInfo() 里 modalForm 字段
    """
    inspection_number  = models.CharField('检验单号', max_length=32, primary_key=True)  # ASM240325..
    inspection_location = models.CharField('检验地点', max_length=60)
    inspection_standard = models.CharField('检验标准', max_length=120)

    order_number   = models.ForeignKey(
        OrderTable, to_field='order_number',
        on_delete=models.PROTECT, verbose_name='订单号')
    customer_name  = models.ForeignKey(
        CustomerTable, to_field='customer_name',
        on_delete=models.PROTECT, verbose_name='客户名称')

    inspector_name = models.CharField(max_length=10, verbose_name="检验员")              # 对应 inspector_name

    created_date   = models.DateField('创建日期')  # yyyy-MM-dd

    class Meta:
        db_table = 'incoming_inspection_record'
        verbose_name = '来料检验-表头'
        verbose_name_plural = verbose_name
        ordering = ['-created_date']

    def __str__(self):
        return f'{self.inspection_number} ({self.customer_name})'


# ====================== 2. 来料检验【明细】 ======================
def incoming_image_path(instance, filename):
    # 存储路径：incoming/<inspection_number>/<行id>_<原文件名>
    return f'incoming/{instance.record.inspection_number}/{instance.id}_{filename}'

class IncomingInspectionDetail(models.Model):
    """
    对应 UploadDetailInfo() 中每个 row
    """
    # record = models.ForeignKey(
    #     IncomingInspectionRecord,
    #     related_name='details',
    #     on_delete=models.CASCADE,
    #     verbose_name='所属表头')                     # ↔ inspection_number_id

    # -------- 基本信息 --------
    # 外键关联成品检验记录
    inspection_number = models.ForeignKey(
        IncomingInspectionRecord,
        verbose_name="检验单号",
        to_field="inspection_number",
        on_delete=models.CASCADE
    )
    material_name  = models.CharField('品名', max_length=100)
    spec           = models.CharField('规格', max_length=120)
    material       = models.CharField('材质', max_length=50)
    quantity       = models.PositiveIntegerField('数量')

    # -------- 尺寸 --------
    length         = models.DecimalField('长度(mm)', max_digits=10, decimal_places=3, default=0)
    width          = models.DecimalField('宽度(mm)', max_digits=10, decimal_places=3, default=0)
    thickness      = models.DecimalField('厚度(mm)', max_digits=10, decimal_places=3, default=0)
    height         = models.DecimalField('高度(mm)', max_digits=10, decimal_places=3, default=0)

    # -------- 炉号 / MTC --------
    heat_no        = models.CharField('炉号', max_length=60, blank=True, null=True)
    mtc_no         = models.CharField('材质证明书编号', max_length=60, blank=True, null=True)

    # -------- 图片（最多 4 张，可按需裁减）--------
    image1 = models.ImageField('图片1', upload_to="images/reference_image/", blank=True, null=True)
    image2 = models.ImageField('图片2', upload_to="images/reference_image/", blank=True, null=True)
    image3 = models.ImageField('图片3', upload_to="images/reference_image/", blank=True, null=True)
    image4 = models.ImageField('图片4', upload_to="images/reference_image/", blank=True, null=True)

    class Meta:
        db_table = 'incoming_inspection_detail'
        verbose_name = '来料检验-明细'
        verbose_name_plural = verbose_name


    def __str__(self):
        return f'{self.record.inspection_number} - {self.material_name}'
#  以下为库存明细表
class WarehouseTable(models.Model):
    warehouseid = models.AutoField(primary_key=True, verbose_name="主键")
    product_name = models.CharField(verbose_name="产品名称", max_length=15)
    product_size = models.CharField(verbose_name="产品规格", max_length=110)
    unit_choices = (
        (1, "件"),
        (2, "套"),
        (3, "批"),
        (4, "千克"),
        (5, "吨"),
        (6, "包"),
        (7, "盒"),
        (8, "其他"),
    )
    unit = models.SmallIntegerField(verbose_name="单位", choices=unit_choices)
    quantity = models.DecimalField(verbose_name="数量", max_digits=15, decimal_places=2, blank=True, default=0)
    brand = models.CharField(verbose_name="品牌", max_length=25, blank=True, null=True)
    material_certificate = models.CharField(verbose_name="材质", max_length=800, blank=True, null=True)
    material_choices = (
        (1, "原材料"),
        (2, "焊材"),
        (3, "耗材"),
        (4, "工具"),
        (5, "配件"),
        (6, "螺丝"),
        (7, "钻铣"),
    )
    material_type = models.SmallIntegerField(verbose_name="类型", choices=material_choices)
    remark = models.CharField(verbose_name="备注", max_length=30, blank=True, null=True)

    class Meta:
        db_table = 'warehouse_tb'


# 入库单
# 一个入库单对应多个入库记录
class WarehousEntryTable(models.Model):
    entryid = models.AutoField(primary_key=True, verbose_name="主键")
    entry_number = models.CharField(verbose_name="入库单号", max_length=30, unique=True)
    attachments = GenericRelation('app.AttachmentFileTable', related_query_name='warehousentry')
    supplier_name = models.ForeignKey(to=SupplierTable, verbose_name="供应商", to_field="supplier_name",
                                   on_delete=models.CASCADE)
    username = models.ForeignKey(UserTable, verbose_name="经办人", to_field="username", on_delete=models.DO_NOTHING)
    filename = models.CharField(verbose_name="入库单", max_length=100,null=True,blank=True)
    entry_date = models.DateField(verbose_name="录入时间", auto_now_add=True)

    class Meta:
        db_table = 'warehouse_entry_tb'


# 入库记录表
class IncomingWarehouseTable(models.Model):
    incomeid = models.AutoField(primary_key=True, verbose_name="主键")
    entry_number = models.ForeignKey(to=WarehousEntryTable, verbose_name="入库单号", to_field="entry_number",
                                    on_delete=models.CASCADE)
    inventoryid = models.ForeignKey(to=InventoryTable, verbose_name="库存ID", to_field="inventoryid",
                                    on_delete=models.CASCADE)
    quantity = models.DecimalField(verbose_name="数量", max_digits=15, decimal_places=2)
    remark = models.CharField(verbose_name="备注", max_length=30, blank=True, null=True)

    class Meta:
        db_table = 'incoming_warehouse_tb'


# 出库记录表
class OutgoingWarehouseTable(models.Model):
    outid = models.AutoField(primary_key=True, verbose_name="主键")
    outdate = models.DateField(verbose_name="出库日期")
    inventoryid = models.ForeignKey(to=InventoryTable, verbose_name="库存ID", to_field="inventoryid",
                                    on_delete=models.CASCADE)
    quantity = models.DecimalField(verbose_name="数量", max_digits=15, decimal_places=2)
    person_name = models.CharField(verbose_name="领料人", max_length=10)

    class Meta:
        db_table = 'outgoing_warehouse_tb'
# 备注模版
class RemarksTemplateTable(models.Model):
    templateid = models.AutoField(primary_key=True, verbose_name="主键")
    template_name = models.CharField(verbose_name="模版名称", max_length=30)
    creat_date = models.DateField(verbose_name="创建日期", auto_now_add=True)
    creat_user = models.CharField(verbose_name="领料人", max_length=10)
    remarks_data = models.CharField(verbose_name="内容", max_length=5000)

    class Meta:
        db_table = 'remarks_template_tb'