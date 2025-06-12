
from django.core.paginator import Paginator
from rest_framework.decorators import action
from rest_framework import viewsets
from django.http import JsonResponse
from app.models import ManagedTable
from django.forms.models import model_to_dict
from django.db.models import Sum,Avg,Max,Min,Count


class ViewsDBORM(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = []

    # http://127.0.0.1:8000/views_db_orm/add_orm/
    @action(methods=['get'], detail=False)
    def add_orm(self, request):
        """ 增加一条记录 """
        obj = ManagedTable()
        obj.name = 'lucas'
        # obj.age = 20
        obj.score = 98.2
        obj.save()
        data_msg = 'row id:' + str(obj.id)
        resp = {'code': 0, 'msg': 'success', 'data': data_msg}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/add_many/
    @action(methods=['get'], detail=False)
    def add_many(self, request):
        """ 增加多条记录 """
        data = [
            ManagedTable(name='alice', age=20),
            ManagedTable(name='zhangsan', age=21),
            ManagedTable(name='lisi', age=22),
        ]
        obj_list = ManagedTable.objects.bulk_create(data)
        resp = {'code': 0, 'msg': 'success', 'data': obj_list[0].id}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_all/
    @action(methods=['get'], detail=False)
    def query_all(self, request):
        """ 查询所有 """
        # select * from managed_table;
        query_set = ManagedTable.objects.all().values()
        resp = {'code': 0, 'msg': 'success', 'data': list(query_set)}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_limit/
    @action(methods=['get'], detail=False)
    def query_limit(self, request):
        """ 查询指定条数 """
        # select * from managed_table limit 3;
        query_set = ManagedTable.objects.all()[:3].values()
        # select * from managed_table limit 2, 5？
        # query_set = ManagedTable.objects.all()[2:5].values()
        resp = {'code': 0, 'msg': 'success', 'data': list(query_set)}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_all_special_field/
    @action(methods=['get'], detail=False)
    def query_all_special_field(self, request):
        """ 查询所有记录，只返回name字段 """
        # select name from managed_table;
        query_set = ManagedTable.objects.all().values('name')
        resp = {'code': 0, 'msg': 'success', 'data': list(query_set)}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_one/
    @action(methods=['get'], detail=False)
    def query_one(self, request):
        """ 查询一条 """
        # select * from managed_table where id = 1;
        obj = ManagedTable.objects.get(id=1)
        # model_to_dict() 返回的是map
        resp = {'code': 0, 'msg': 'success', 'data': model_to_dict(obj)}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_order_by/
    @action(methods=['get'], detail=False)
    def query_order_by(self, request):
        # select * from managed_table order by id;
        #query_set = ManagedTable.objects.order_by('id').values() # 从小到大
        query_set = ManagedTable.objects.order_by('-id').values() # 从大到小
        resp = {'code': 0, 'msg': 'success', 'data': list(query_set)}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_filter/
    @action(methods=['get'], detail=False)
    def query_filter(self, request):
        # select * from managed_table where name = 'lucas' and age = 18;
        query_set = ManagedTable.objects.filter(name='lucas', age=18).values() # 从大到小
        resp = {'code': 0, 'msg': 'success', 'data': list(query_set)}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_filter2/
    @action(methods=['get'], detail=False)
    def query_filter2(self, request):
        """ > < >= <= 等django提供特定方法实现 """
        # select * from managed_table where age > 18;
        query_set = ManagedTable.objects.filter(age__gt=18).values()  # age大于18的
        resp = {'code': 0, 'msg': 'success', 'data': list(query_set)}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_filter3/
    @action(methods=['get'], detail=False)
    def query_filter3(self, request):
        """ like查询，django提供特定方法实现 """
        # select * from managed_table where name like 'lu%';
        query_set = ManagedTable.objects.filter(name__startswith='lu').values()  # lu%
        #query_set = ManagedTable.objects.filter(name__contains='lu').values()  # %lu%
        resp = {'code': 0, 'msg': 'success', 'data': list(query_set)}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_agregate/
    @action(methods=['get'], detail=False)
    def query_agregate(self, request):
        """ count """
        # select count(id) from managed_table where name = 'lucas';
        result = ManagedTable.objects.filter(name='lucas').aggregate(Count('id')) # {"id__count": 9}
        resp = {'code': 0, 'msg': 'success', 'data': result}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/query_group/
    @action(methods=['get'], detail=False)
    def query_group(self, request):
        """ group """
        # select count(id) as total from managed_table group by name, age;
        query_set = ManagedTable.objects.values('name', 'age').annotate(total=Count('id'))
        resp = {'code': 0, 'msg': 'success', 'data': list(query_set)}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/update_orm/
    @action(methods=['get'], detail=False)
    def update_orm(self, request):
        """ 修改id=6的记录 """
        obj = ManagedTable.objects.get(id=6)
        obj.name = 'lucas'
        obj.age = 30
        obj.save()
        data_msg = 'row id:' + str(obj.id)  # obj.id是6
        resp = {'code': 0, 'msg': 'success', 'data': data_msg}
        return JsonResponse(resp)

    # http://127.0.0.1:8000/views_db_orm/delete_orm/
    @action(methods=['get'], detail=False)
    def delete_orm(self, request):
        """ 删除id=2的记录 """
        obj = ManagedTable.objects.get(id=2)
        obj.delete()
        data_msg = 'row id:' + str(obj.id)  # obj.id是None
        resp = {'code': 0, 'msg': 'success', 'data': data_msg}
        return JsonResponse(resp)

    @action(methods=['get'], detail=False)
    def paginator_test(self, request):
        """ 分页 """
        # 1. 获取分页参数
        page_num = request.GET.get('page_num')
        page_size = request.GET.get('page_size')
        # 2. 获取分页数据
        query_set = ManagedTable.objects.all().values()
        paginator = Paginator(query_set, page_size)
        page_data = paginator.page(page_num)
        resp = {'code': 0, 'msg': 'success', 'data': list(page_data)}
        return JsonResponse(resp)
