from rest_framework.routers import SimpleRouter
from app.views.views_db_orm import ViewsDBORM
from app.views.login import Login
from app.views.vue_element_admin import VueElementAdmin


def register_url(urlpatterns):
    router = SimpleRouter()

    # prefix指的是通过127.0.0.1:8000/prefix/访问该视图集。
    # 若ViewDemo中有方法get_test，则通过127.0.0.1:8000/view_demo/get_test访问。
    router.register(prefix='views_db_orm', viewset=ViewsDBORM, basename='views_db_orm')
    router.register(prefix='vue-element-admin/user', viewset=Login, basename='vue_user_mock')
    router.register(prefix='vue-element-admin/backend', viewset=VueElementAdmin, basename='vue_element_admin')

    urlpatterns += router.urls
