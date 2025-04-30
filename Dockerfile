# 基于redis镜像构建
FROM redis:7-alpine
# 工作目录
WORKDIR /opt/transmute
# 把当前目录下的所有文件拷贝到工作目录
COPY . .
# 执行安装脚本
RUN sh install.sh
# 暴露端口和目录
EXPOSE 2083
VOLUME /opt/linksumm/app/data
# 启动命令
CMD ["sh", "run.sh"]