import json
from loguru import logger

class LogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 初始化 traceid
        request.traceid = getattr(request, 'traceid', '')

        # 记录请求
        full_path = request.get_full_path()
        method = request.method.upper()

        if method == 'GET':
            logger.info(f"{request.traceid} Request:GET {full_path}")
        else:
            content_type = request.META.get('CONTENT_TYPE', '')
            json_req = ''

            if 'upload_file' in full_path:
                logger.info(f"{request.traceid} Request:{method} {full_path}")
            else:
                if 'application/json' in content_type.lower():
                    try:
                        json_req = json.loads(request.body)
                    except json.JSONDecodeError:
                        logger.warning(f"{request.traceid} Invalid JSON in {method} {full_path}")
                else:
                    if method not in ['OPTIONS', 'HEAD']:
                        logger.warning(f"{request.traceid} Non-JSON Content-Type:{content_type} for {method} {full_path}")

                logger.info(f"{request.traceid} Request:{method} {full_path} body:{json_req}")

        # 处理响应
        response = self.get_response(request)

        try:
            full_path = request.get_full_path()
            is_download = 'download_file' in full_path
            # 检查响应头是否为附件下载
            if not is_download and hasattr(response, 'headers'):
                content_disposition = response.headers.get('Content-Disposition', '')
                is_download = 'attachment' in content_disposition

            if is_download:
                logger.info(f"{request.traceid} Response[status {response.status_code}] (File Download)")
            elif hasattr(response, 'streaming_content'):
                logger.info(f"{request.traceid} Response[status {response.status_code}] (Streaming Content)")
            else:
                content_type = response.headers.get('Content-Type', '').lower()
                if hasattr(response, 'content'):
                    if 'text' in content_type or 'json' in content_type:
                        content = response.content.decode(errors='replace')
                        logger.info(f"{request.traceid} Response[status {response.status_code}]:\n{content}")
                    else:
                        logger.info(f"{request.traceid} Response[status {response.status_code}] (Binary Data, Content-Type: {content_type})")
                else:
                    logger.info(f"{request.traceid} Response[status {response.status_code}]")
        except Exception as e:
            logger.error(f"{request.traceid} Error logging response: {e}")

        return response