from fastapi import Request
from app.utils.helper import get_client_ip, show_json
from fastapi.responses import JSONResponse
from app.main import *
from datetime import datetime
# 限制请求频率
async def req_limit(request: Request, call_next):
    # 获取当前请求的路由路径
    path = request.url.path
    if path == "/api/get/content" or path == "/api/summ":
        # 获取当前日期并格式化为 YYYYMMDD
        current_date = datetime.now().strftime('%Y%m%d')

        ip = get_client_ip(request)
        key = "linksumm:" + current_date + ":" + ip
        # 读取 Redis 中的 key 值
        value = await request.app.state.redis.get(key)
        if value is None:
            # 放行请求，继续执行后续中间件或路由处理
            res = await call_next(request)
            return res
        else:
            # print(request.app.state.config["app"]["req_limit"])
            # res = await call_next(request)
            # return res
            # 获取配置文件中的次数限制
            req_limit = int(request.app.state.config["app"]["req_limit"])
            value_int = int(value)
            if value_int > req_limit:
                # 返回请求频率过快的错误信息
                # 返回请求频率过快的错误信息
                response_data = show_json(429, "Too Many Requests", None)
                return JSONResponse(status_code=200, content=response_data)
            else:
                res = await call_next(request)
                return res
    else:
        # 对于非 /api/translate 路径的请求，直接放行
        res = await call_next(request)
        return res