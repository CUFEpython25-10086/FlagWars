# FlagWars 部署指南

[toc]

## 概述

FlagWars是一款现代化的夺旗游戏，采用Python后端(Tornado + WebSocket)和HTML5前端技术。本指南将帮助您在不同环境中部署FlagWars游戏服务器。

## 系统要求

### 最低要求
- **操作系统**: Windows 10/11, Linux (Ubuntu 18.04+), macOS 10.14+
- **Python**: 3.8 或更高版本
- **内存**: 512MB RAM
- **磁盘空间**: 100MB 可用空间

### 推荐配置
- **CPU**: 双核 2.0GHz 或更高
- **内存**: 2GB RAM 或更高
- **网络**: 稳定的互联网连接

## 部署方式

### 方式一：本地开发环境部署

#### Windows 系统

1. **安装 uv 包管理器**
   ```powershell
   # 使用 PowerShell 安装 uv
   powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **克隆项目**
   ```powershell
   git clone https://github.com/yourusername/FlagWars.git
   cd FlagWars
   ```

3. **安装依赖**
   ```powershell
   uv sync
   ```

4. **启动服务器**
   ```powershell
   # 方式1: 使用批处理脚本
   start_server.bat
   
   # 方式2: 直接运行
   uv run python run_server.py
   ```

5. **访问游戏**
   打开浏览器访问: http://localhost:8888

#### Linux/macOS 系统

1. **安装 uv 包管理器**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **克隆项目**
   ```bash
   git clone https://github.com/yourusername/FlagWars.git
   cd FlagWars
   ```

3. **安装依赖**
   ```bash
   uv sync
   ```

4. **启动服务器**
   ```bash
   uv run python run_server.py
   ```

5. **访问游戏**
   打开浏览器访问: http://localhost:8888

### 方式二：生产环境部署

#### 使用 Docker 部署

1. **创建 Dockerfile**
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   # 安装 uv
   RUN pip install uv

   # 复制项目文件
   COPY . .

   # 安装依赖
   RUN uv sync

   # 暴露端口
   EXPOSE 8888

   # 启动命令
   CMD ["uv", "run", "python", "run_server.py"]
   ```

2. **构建并运行容器**
   ```bash
   # 构建镜像
   docker build -t flagwars .

   # 运行容器
   docker run -d -p 8888:8888 --name flagwars-server flagwars
   ```

#### 使用 Nginx 反向代理 (Linux)

1. **安装 Nginx**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install nginx

   # CentOS/RHEL
   sudo yum install nginx
   ```

2. **配置 Nginx**
   创建 `/etc/nginx/sites-available/flagwars` 文件:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8888;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **启用站点**
   ```bash
   sudo ln -s /etc/nginx/sites-available/flagwars /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

4. **设置系统服务**
   创建 `/etc/systemd/system/flagwars.service` 文件:
   ```ini
   [Unit]
   Description=FlagWars Game Server
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/path/to/FlagWars
   ExecStart=/usr/local/bin/uv run python run_server.py
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

5. **启动服务**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable flagwars
   sudo systemctl start flagwars
   ```

### 方式三：云平台部署

#### Heroku 部署

1. **创建 Procfile**
   ```
   web: uv run python run_server.py
   ```

2. **创建 runtime.txt**
   ```
   python-3.9.16
   ```

3. **部署**
   ```bash
   # 安装 Heroku CLI
   heroku login
   heroku create your-app-name
   git push heroku main
   ```

#### AWS EC2 部署

1. **启动 EC2 实例**
   - 选择 Ubuntu 20.04 LTS
   - 选择至少 t2.micro 实例类型
   - 配置安全组，开放 8888 端口

2. **连接并部署**
   ```bash
   # 连接到实例
   ssh -i your-key.pem ubuntu@your-ec2-ip

   # 安装必要软件
   sudo apt update
   sudo apt install python3 python3-pip git

   # 安装 uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc

   # 克隆并运行项目
   git clone https://github.com/yourusername/FlagWars.git
   cd FlagWars
   uv sync
   uv run python run_server.py
   ```

### 方式四：使用1panel部署

1panel是一款现代化的Linux服务器运维面板，支持一键部署应用。以下是使用1panel部署FlagWars的步骤：

#### 安装1panel

1. **安装1panel**
   ```bash
   # 使用官方安装脚本
   curl -sSL https://resource.fit2cloud.com/1panel/package/quick_start.sh -o quick_start.sh && sh quick_start.sh
   ```

2. **登录1panel**
   - 安装完成后，记录显示的访问地址、用户名和密码
   - 通过浏览器访问1panel管理界面

#### 部署FlagWars

1. **创建应用环境**
   - 登录1panel后，进入"容器" > "应用商店"
   - 搜索并安装"Python环境"应用
   - 选择Python 3.9或更高版本

2. **创建Docker应用**
   - 进入"容器" > "应用" > "创建应用"
   - 选择"Docker Compose"方式
   - 填写以下配置：

   ```yaml
   version: '3'
   services:
     flagwars:
       image: python:3.9-slim
       container_name: flagwars-server
       restart: unless-stopped
       ports:
         - "8888:8888"
       volumes:
         - ./FlagWars:/app
       working_dir: /app
       command: ["sh", "-c", "pip install uv && uv sync && uv run python run_server.py"]
   ```

3. **或者使用自定义Dockerfile**
   - 在服务器上创建项目目录
   ```bash
   mkdir -p /opt/1panel/apps/flagwars
   cd /opt/1panel/apps/flagwars
   ```

   - 创建Dockerfile
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   # 安装必要工具
   RUN apt-get update && apt-get install -y \
       curl \
       && rm -rf /var/lib/apt/lists/*

   # 安装 uv
   RUN pip install uv

   # 复制项目文件
   COPY . .

   # 安装依赖
   RUN uv sync

   # 暴露端口
   EXPOSE 8888

   # 启动命令
   CMD ["uv", "run", "python", "run_server.py"]
   ```

   - 创建docker-compose.yml
   ```yaml
   version: '3'
   services:
     flagwars:
       build: .
       container_name: flagwars-server
       restart: unless-stopped
       ports:
         - "8888:8888"
       volumes:
         - .:/app
   ```

4. **部署应用**
   - 在1panel中进入"容器" > "应用"
   - 点击"创建应用"，选择"从Docker Compose文件创建"
   - 上传或粘贴docker-compose.yml内容
   - 设置应用名称为"flagwars"
   - 点击"创建"完成部署

#### 配置反向代理

1. **创建网站**
   - 进入"网站" > "创建网站"
   - 选择"反向代理"
   - 填写域名（可选）
   - 代理地址填写：http://127.0.0.1:8888
   - 开启WebSocket支持

2. **SSL证书配置**
   - 在网站设置中选择"SSL"
   - 可以使用Let's Encrypt免费证书
   - 或上传已有证书

#### 监控与日志

1. **查看日志**
   - 在应用详情页可以查看容器日志
   - 或进入"容器" > "容器"查看flagwars-server容器日志

2. **监控状态**
   - 在1panel仪表板可以查看服务器资源使用情况
   - 设置告警规则，当服务异常时接收通知

#### 备份与恢复

1. **数据备份**
   - 进入"计划任务" > "创建任务"
   - 选择"备份网站"或"备份目录"
   - 设置备份路径为/opt/1panel/apps/flagwars
   - 配置定期备份计划

2. **应用恢复**
   - 如需恢复，进入"备份"页面
   - 选择相应备份文件进行恢复

#### 高级配置

1. **环境变量配置**
   - 在应用设置中可以添加环境变量
   - 例如设置日志级别、游戏配置等

2. **资源限制**
   - 在容器设置中可以限制CPU和内存使用
   - 确保服务器资源合理分配

3. **自动更新**
   - 可以设置Git仓库自动拉取
   - 配置Webhook实现代码更新后自动部署

通过1panel部署FlagWars，您可以享受图形化管理、一键备份、SSL证书自动续期等便利功能，大大简化了运维工作。

## 配置选项

### 服务器配置

可以通过修改 `src/flagwars/server.py` 中的以下参数来调整服务器行为:

```python
# 服务器端口 (默认: 8888)
server.listen(8888)

# 日志级别
logging.basicConfig(level=logging.INFO)
```

### 游戏配置

可以通过修改 `src/flagwars/models.py` 中的以下参数来调整游戏设置:

```python
# 地图大小 (默认: 20x15)
def __init__(self, map_width: int = 20, map_height: int = 15):

# 地形生成数量
# 生成塔楼数量 (默认: 5)
for _ in range(5):

# 生成城墙数量 (默认: 10)
for _ in range(10):

# 生成山脉数量 (默认: 8)
for _ in range(8):

# 生成沼泽数量 (默认: 6)
for _ in range(6):
```

## 性能优化

### 服务器端优化

1. **启用 Gzip 压缩** ✅ 已实现
   ```python
   # 在 make_app() 函数中添加
   settings = {
       "gzip": True,
       "compress_response": True,
       "gzip_min_size": 1024,  # 只压缩大于1KB的响应
   }
   return web.Application(handlers, **settings)
   ```

2. **调整工作进程**
   ```python
   # 使用多进程
   server = httpserver.HTTPServer(app)
   server.bind(8888)
   server.start(0)  # 0 表示自动检测CPU核心数
   ```

### 客户端优化

1. **启用浏览器缓存** ✅ 已实现
   ```python
   # 在 MainHandler 中添加缓存头
   def get(self):
       self.set_header("Cache-Control", "public, max-age=600")
       # 其余代码...
   ```

## 监控与日志

### 日志配置

1. **配置日志文件**
   ```python
   import logging.handlers

   # 配置日志轮转
   handler = logging.handlers.RotatingFileHandler(
       'flagwars.log', maxBytes=10*1024*1024, backupCount=5
   )
   handler.setFormatter(logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   ))
   logging.getLogger().addHandler(handler)
   ```

2. **监控服务器状态**
   ```python
   # 添加状态检查端点
   class StatusHandler(web.RequestHandler):
       def get(self):
           status = {
               "active_games": len(game_manager.games),
               "active_players": sum(len(players) for players in game_manager.players.values()),
               "uptime": time.time() - start_time
           }
           self.write(status)
   
   # 在路由中添加
   (r"/status", StatusHandler),
   ```

## 故障排除

### 常见问题

1. **端口被占用**
   ```
   错误: [Errno 98] Address already in use
   解决: 更改端口号或终止占用端口的进程
   ```

2. **依赖安装失败**
   ```
   错误: Failed to install dependencies
   解决: 确保使用正确的Python版本，更新uv到最新版本
   ```

3. **WebSocket连接失败**
   ```
   错误: WebSocket connection failed
   解决: 检查防火墙设置，确保8888端口开放
   ```

### 调试模式

启用调试模式获取更详细的错误信息:

```python
# 在 server.py 中修改
app = web.Application([
    # 路由配置
], debug=True)  # 启用调试模式
```

## 安全注意事项

1. **限制访问**
   - 使用防火墙限制不必要的访问
   - 考虑使用VPN或白名单机制

2. **定期更新**
   - 定期更新Python和依赖包
   - 监控安全公告

3. **输入验证**
   - 虽然游戏已实现基本输入验证，但在生产环境中应考虑更严格的验证

## 备份与恢复

### 数据备份

虽然游戏状态主要在内存中，但可以考虑:

1. **定期保存游戏状态**
   ```python
   # 在GameManager中添加
   def save_game_state(self, game_id):
       # 实现游戏状态序列化到文件
       pass
   ```

2. **日志备份**
   ```bash
   # 定期备份日志文件
   tar -czf flagwars-logs-$(date +%Y%m%d).tar.gz flagwars.log*
   ```

## 扩展部署

### 多服务器部署

对于大规模部署，可以考虑:

1. **负载均衡**
   - 使用Nginx或HAProxy进行负载均衡
   - 配置多个游戏服务器实例

2. **共享状态**
   - 使用Redis或其他内存数据库共享游戏状态
   - 实现跨服务器的玩家通信

### CDN集成

对于静态资源，可以使用CDN加速:

```html
<!-- 在模板中使用CDN -->
<script src="https://cdn.example.com/brython.js"></script>
```

## 总结

本指南涵盖了FlagWars游戏的多种部署方式，从本地开发环境到生产环境的完整部署流程。根据您的具体需求选择合适的部署方式，并参考性能优化和安全建议来确保服务器稳定运行。

如需更多帮助，请参考项目文档或联系开发团队。