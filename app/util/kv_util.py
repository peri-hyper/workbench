# -*- coding: utf-8 -*-
from app.models import KVTable
from django.test import TestCase


class KVUtil(object):
    @staticmethod
    def set(key, value):
        """
        插入或更新
        :param key:
        :param value:
        :return:
        """
        KVTable.objects.update_or_create(
            key=key,
            defaults={'value':  value}
        )

    @staticmethod
    def get(key):
        """
        :param key:
        :return: None if no value
        """
        try:
            kv = KVTable.objects.get(key=key)
            value = kv.value
        except KVTable.DoesNotExist:
            value = None
        return value

    @staticmethod
    def delete(key):
        KVTable.objects.filter(key=key).delete()


class KVTest(TestCase):
    """ 注意，单元测试用的是临时数据库，测完自动删除。不能写多个用例测set get，
    若写多个用例，测完set会自动删除数据库，get会查不到值。
    """
    def test_kv(self):
        KVUtil.set('testkey', 'aaa')
        value = KVUtil.get('testkey')
        print(value)
        KVUtil.delete('testkey')
