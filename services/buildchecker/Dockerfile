# BuildChecker 服务镜像（A 组）。构建上下文是仓库根目录：docker compose build 或 make build。
#   1. 基础镜像按 digest 固定；升级时只改 BASE_IMAGE 这一行，并在提交说明里写新 digest
#   2. 系统工具和 Python 包的实际版本在构建时写入 /opt/toolchain.lock
#   3. Python 依赖按锁文件和哈希安装
#   4. 以普通用户 app 运行；.env、work/、.git 不会进入镜像（见 .dockerignore）
# 此镜像站提供与 Docker Hub 相同的 OCI 索引摘要；供无法直连 Docker Hub 的 ECS 使用。
ARG BASE_IMAGE=m.daocloud.io/docker.io/library/python@sha256:f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74
FROM ${BASE_IMAGE}

# 构建期软件源：默认用官方源，保证本地 WSL 与 GitHub Actions 都能直接构建。
# 阿里云 ECS 内网访问官方源较慢时，用 --build-arg 换成内网镜像，例如
#   --build-arg APT_MIRROR=mirrors.cloud.aliyuncs.com --build-arg PIP_INDEX=https://mirrors.aliyun.com/pypi/simple
ARG APT_MIRROR=deb.debian.org
ARG PIP_INDEX=https://pypi.org/simple

ENV LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || true; \
    sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list 2>/dev/null || true; \
    apt-get update \
 && apt-get install -y --no-install-recommends gcc make libc6-dev strace git \
 && rm -rf /var/lib/apt/lists/* \
 && dpkg-query -W -f='${Package}=${Version}\n' gcc make libc6-dev strace git > /opt/toolchain.lock \
 && echo "python3=$(python3 -c 'import platform; print(platform.python_version())')" >> /opt/toolchain.lock \
 && echo "arch=$(dpkg --print-architecture)" >> /opt/toolchain.lock

COPY requirements-dev.lock /tmp/requirements-dev.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements-dev.lock --index-url ${PIP_INDEX} \
 && pip freeze | sed 's/^/pip:/' >> /opt/toolchain.lock

# 先建用户和 /app，再复制代码：/app 必须归 app 所有，否则运行时无法写入
RUN useradd --create-home --uid 10001 app && install -d -o app -g app /app
WORKDIR /app
COPY --chown=app:app services/buildchecker/ /app/
COPY --chown=app:app fixtures/ /app/fixtures/
USER app

CMD ["python3", "-m", "buildchecker", "--help"]
