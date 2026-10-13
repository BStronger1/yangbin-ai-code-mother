# turing 用户目录部署

部署单体后端和前端；微服务源码保留，不同时启动另一套微服务。
根目录为 ~/apps/yangbin-ai-code-mother，所有数据库、密钥、生成作品和日志均留在服务器。

## 构建与首次安装

1. 使用 Java 21+ 执行 mvn -Dtest=CodeParserTest package。
2. 前端目录执行 npm ci 与 npm run build。
3. 将后端 JAR 复制为服务器根目录 app.jar，将前端 dist 内容复制到 frontend/。
   同步 deploy/turing/ 与 sql/ 目录。
4. bootstrap.py 使用现有用户目录的 Java 21、Node 22、Redis 和 Chromium。
   如环境路径不同，在 bootstrap.py 的 runtime 配置中调整；系统需有 MariaDB、
   mysql_install_db、tmux 和 Python 3.12。不需要 root 或 Docker。
5. 在服务器运行 python3 deploy/turing/bootstrap.py --model-env 私有模型配置路径 --bind 服务器校园网IP。
   env 文件须包含 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL；也支持包含 MODEL_API_KEY、MODEL_BASE_URL、CHAT_MODEL 的 JSON 配置。安装脚本只读取，不修改原文件。
   初次运行创建随机数据库与 Redis 密码，保存在 0600 权限的 secrets.json 等私有文件中。
6. bash deploy/turing/start.sh，随后访问 http://服务器校园网IP:18824。
7. 可运行 python3 deploy/turing/install-autostart.py 安装用户开机条目。

仅使用本项目进程和数据目录。独立端口为：前端 18824、后端 18125、
MariaDB 13308、Redis 16381；后三者绑定到 127.0.0.1。
校园网入口是 HTTP；也可通过 SSH 转发访问。
公网访问应另外配置 HTTPS 域名和入口。

## 运维

- 启动：bash deploy/turing/start.sh
- 停止：bash deploy/turing/stop.sh
- 健康检查：GET /api/actuator/health
- 日志：logs/，每项最多 5 MB × 4 个文件（数据库内部错误日志单独保留）
- 备份：停止服务后备份 data/、tmp/、secrets.json、mysql*.cnf、redis.conf
- 升级：先停止本项目，备份 app.jar 与 frontend/，替换构建产物再启动
- 数据和密钥均不在 Git 仓库中；不要重新执行 bootstrap.py 覆盖现有环境

截图使用已有 Chromium，结果保存在 tmp/covers/。
发布作品保存在 tmp/code_deploy/，同源代理同时支持 SSE 和页面刷新。
Pexels 与 DashScope 图像工具需另配各自密钥；基础网页生成不依赖这两项。

## GitHub 身份

新仓库以 BStronger1 的 GitHub noreply 邮箱建立独立导入提交。
原始仓库与提交历史保留在本地源目录，来源集中记录在根目录 NOTICE.md。
GitHub Contributors 统计本仓库的提交作者，不表示所有导入源码均由维护者原创。

## 验收命令

python3 deploy/turing/smoke.py 使用独立合成账号进行真实模型验收，产生少量 API 费用。
重启本项目后执行 python3 deploy/turing/smoke.py --verify 检查持久化。
浏览器验收需在 runtime/venv 安装 playwright，然后执行 runtime/venv/bin/python deploy/turing/browser-smoke.py。

访问入口 http://172.16.185.103:18824，需校园网或相应 VPN。可直接注册普通账号使用。

基础验收后，可执行 python3 deploy/turing/smoke-modes.py 对多文件和 Vue 模式各生成一个小型测试应用，产生额外模型调用费用。随后执行浏览器验收可验证全部三种模式的页面交互。
