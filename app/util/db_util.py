from django.db import connection
from django.test import TestCase
from app.api_code import API_DB_ERR, API_OK


class DBUtil(object):
    @staticmethod
    def query(sql, params={}):
        code = API_OK
        msg = 'success'
        data = []
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            msg = str(e)
            print(f"SQL Error, sql: {sql}, params: {params}, msg:{msg}")
            code = API_DB_ERR
        return code, msg, data

    @staticmethod
    def modify(sql, params={}):
        code = API_OK
        msg = 'success'
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                connection.commit()
        except Exception as e:
            code = API_DB_ERR
            msg = str(e)
        return code, msg, []

    @staticmethod
    def executemany(sql, data):
        code = API_OK
        msg = 'success'
        try:
            with connection.cursor() as cursor:
                cursor.executemany(sql, data)
                connection.commit()
        except Exception as e:
            connection.rollback()
            code = API_DB_ERR
            msg = str(e)
        return code, msg, []


class DBTest(TestCase):
    def test_db(self):
        sql = 'select * from managed_tb where id = :id'
        params = {'id': 1}
        code, msg, data = DBUtil.query(sql, params)
        print(code, msg, data)

    def test_db_like(self):
        """ like语句要用两个% """
        year = '2024'
        gzdd = '广东'
        sql = f'select * from gongwuyuan_tb where year = "{year}" and gzdd like "%%{gzdd}%%" and xl like "%%本科%%"'
        code, msg, data = DBUtil.query(sql, {})
        print(code, msg, data)