#!/bin/bash


# 复制配置文件
copyConfig(){
    # 检查app/config/config.json文件是否存在
    if [ ! -f "app/data/config/config.json" ]; then
        # 递归创建目录
        mkdir -p app/data/config
        # 复制配置文件
        cp app/config/config.default.json app/data/config/config.json
    fi
}

# 启动redis
runRedis(){
    redis-server app/config/redis.conf --daemonize yes
    # 检查 Redis 是否启动成功
    if [ $? -eq 0 ]; then
        echo "Redis started successfully."
    else
        echo "Failed to start Redis."
        exit 1
    fi
}

# 启动主进程
runMain(){
    # 获取环境变量WORKERS
    WORKERS=${WORKERS}
    # 判断变量是否存在
    if [ -z "$WORKERS" ]; then
        WORKERS=1
    fi
    # 启动主进程
    source venv/bin/activate
    uvicorn app.main:app --workers ${WORKERS} --host 0.0.0.0 --port 2083
}

copyConfig && runRedis && runMain