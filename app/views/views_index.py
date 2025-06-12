from django.shortcuts import render
from rest_framework import viewsets
from django.http import JsonResponse


class ViewsIndex(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = []

    def index(self, request):
        return render(request, "index.html")


# 调试用，用于request方法联想
def fun_test(request):
    request.method
    request.get_full_path()
