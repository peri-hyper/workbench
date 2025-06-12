""" 返回给前端的返回码 """

""" 成功 """
API_OK = 0

""" 认证鉴权失败 """
# 没传鉴权头
API_MISSING_AUTH_HEADER = 40100
# 鉴权头格式错误
API_AUTH_HEADER_FORMAT_ERR = 40101
# token认证失败
API_TOKEN_AUTH_FAIL = 40102
# 非法token
API_ILLEGAL_TOKEN = 40103
# token过期
API_TOKEN_EXPIRED = 40104

""" 请求参数错误 """
# 请求参数错误
API_PARAM_ERR = 40000
# 请求缺少字段
API_MISSING_FIELD = 40001
# 请求方法错误
API_METHOD_ERR = 40002

""" 系统内部错误 """
# 系统内部错误
API_SYS_ERR = 50000
# DB错误
API_DB_ERR = 50001
