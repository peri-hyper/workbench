import os
import sys
from pathlib import Path
from loguru import logger

# 生产环境修改为INFO
log_level = "DEBUG"

# 每行日志格式
myformat = "{time:HH:mm:ss.SSS}|{level}|{file}:line{line}:{function}|{message}"
# 滚动条件  每天0点生成新的日志文件
myrotation = "00:00"
# 日志保留时长,在此之后会删除？
myretention = "3 days"

BASE_DIR = Path(__file__).resolve().parent.parent
if not os.path.exists(os.path.join(BASE_DIR, "logs")):
    os.makedirs(os.path.join(BASE_DIR, "logs"))
log_path = os.path.join(BASE_DIR, "logs/")

logger.remove(0)  # 删除默认的控制台输出处理器
# TODO 上线后删除掉
# logger.add(sink=log_path + "error_{time:YYYYMMDD}.log", level=log_level,
#            format=myformat, rotation=myrotation, retention=myretention)
# logger.add(sink=log_path + "all_{time:YYYYMMDD}.log", level=log_level,
#            format=myformat, rotation=myrotation, retention=myretention)
logger.add(sys.stderr, format='<level>' + myformat + '</level>',
           colorize=True, level="TRACE")
logger.level("DEBUG", color="<cyan>")
logger.level("INFO", color="<green>")
logger.level("WARNING", color="<yellow>")
logger.level("ERROR", color="<red>")
logger.level("CRITICAL", color="<red><bold>")
