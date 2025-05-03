from typing import Union
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
import redis.asyncio as redis
from app.routers.routers import router
from app.middleware.req_limit import req_limit  # 直接导入函数，而不是整个模块
import json
from fastapi.middleware.cors import CORSMiddleware

# 声明全局变量
config = None

# 定义应用的生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时执行的代码
    with open('app/data/config/config.json', 'r') as file:
        global config
        config = json.load(file)
        app.state.config = config

    redisConfig = config["redis"]
    host = redisConfig["host"]
    port = redisConfig["port"]
    password = redisConfig["password"]
    db = redisConfig["db"]

    app.state.redis = await redis.Redis(host=host, port=port, password=password, db=db, decode_responses=True)
    yield
    # 在应用关闭时执行的代码
    await app.state.redis.close()

app = FastAPI(lifespan=lifespan)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 注册中间件
app.middleware("http")(req_limit)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 将路由添加到应用中
app.include_router(router)
