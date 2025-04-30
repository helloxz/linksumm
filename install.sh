#!/bin/bash

# 安装依赖
install_deps(){
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
    mkdir -p  /opt/linksumm && cd /opt/linksumm
}

# 安装 Python 依赖
install_python_deps(){
    python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt
    # 安装 Chromium
    playwright install chromium
}


# 清理缓存，缩小镜像体积
clean(){
    apt-get clean
    pip3 cache purge
    rm -rf /var/lib/apt/lists/*
}

install_deps && install_python_deps && clean