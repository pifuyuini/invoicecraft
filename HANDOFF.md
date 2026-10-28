# InvoiceCraft 接手说明

本仓库是可继续开发的完整服务端项目，GitHub Pages 只承载合成数据演示。封存后直接 clone `main`，无需恢复旧机器的 worktree 或临时服务。

## 代码与历史

开发顺序为初始 `main → codex/studio-v1 → codex/cassette-console`。初始版本保留在 `archive/original`，两个开发分支也保留供查看迭代；当前 `main` 保存最新源码、静态演示与接手资料。

基础为 FastAPI / Jinja / SQLModel / SQLite。已有中英文 UI 与文档、Decimal 金额、迁移备份、PDF 中文字体、客户/开票方快照、Cassette 控制台和移动端布局。Mac 桌面打包尚未实现；历史 `Cargo.toml` 没有相应 Rust 实现。

## 环境与配置

新机器使用 Python 3.12 与 uv，在仓库根目录执行：

```bash
uv sync --frozen
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

已有环境直接调用 `.venv/bin/`。源码与 `uv.lock` 是环境恢复依据，不复制旧虚拟环境。配置由 `app/config.py` 读取，环境变量优先于根目录 `.env`。

最小本地配置示例，按需写入不提交的 `.env`：

```dotenv
SECRET_KEY=replace-with-your-own-session-secret
DATABASE_URL=sqlite:///./data/app.db
DATABASE_BACKUP_DIR=data/backups
BASE_URL=http://localhost:8000
BILLING_ENABLED=false
```

| 环境变量 | 默认值 | 作用 |
|---|---|---|
| `APP_NAME` | `InvoiceCraft` | 应用名称 |
| `SESSION_COOKIE` | `session` | 会话 cookie 名 |
| `SECRET_KEY` | 开发占位值 | 签名会话；正式运行使用自己的随机值 |
| `DATABASE_URL` | `sqlite:///./data/app.db` | 数据库地址，相对路径基于启动目录 |
| `DATABASE_BACKUP_DIR` | `data/backups` | 旧 SQLite 首次迁移前的备份目录 |
| `BASE_URL` | `http://localhost:8000` | 公开账单及 Stripe 返回链接的服务地址 |
| `BILLING_ENABLED` | `false` | 开启付费界面、订阅入口与免费额度限制 |
| `FREE_INVOICE_LIMIT` | `5` | 启用计费时的免费账单额度 |
| `STRIPE_SECRET_KEY` | 空 | Stripe 服务端密钥 |
| `PRO_PRICE_MONTHLY_ID` | 空 | Stripe recurring Price ID，金额由该 Price 决定 |
| `STRIPE_WEBHOOK_SECRET` | 空 | `/billing/webhook` 的签名密钥 |
| `STRIPE_PUBLISHABLE_KEY` | 空 | 已声明配置，当前 Checkout 使用服务端重定向 |

默认不需要 Stripe。启用订阅时，先在 Stripe 测试模式配置密钥、Price 和 webhook，再验收 Checkout、客户门户及 `checkout.session.completed`、`customer.subscription.updated`、`customer.subscription.deleted` 事件。计费开关不代替 webhook 验签配置。

完整应用从设置页选择 `zh-CN` / `en`，界面语言与文档语言可独立设置。公开账单是带分享令牌的只读文档，“已收款”等状态由用户手工标记。

## SQLite、迁移与备份

启动时调用 `app.db.init_db()`。新数据库创建表；未迁移的旧 SQLite 先通过 SQLite backup API 写入 `DATABASE_BACKUP_DIR`，再增加 Studio 字段、回填 Decimal 字符串、快照与账单序号，并记录 `schema_migrations` 版本 1。已记录该版本时不会重复迁移。

自动迁移备份不是日常备份计划。手工备份正在使用的默认数据库时，可在仓库根目录运行：

```bash
.venv/bin/python - <<'PY'
import sqlite3
from datetime import datetime
from pathlib import Path

source_path = Path("data/app.db")
if not source_path.is_file():
    raise SystemExit("Database not found: set source_path to the active SQLite file")
backup_dir = Path("data/backups")
backup_dir.mkdir(parents=True, exist_ok=True)
target = backup_dir / f"app-manual-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
with sqlite3.connect(source_path) as source, sqlite3.connect(target) as destination:
    source.backup(destination)
print(target)
PY
```

自定义 `DATABASE_URL` 时先改为对应 SQLite 文件。不要在应用写库时只复制主 `.db` 文件；SQLite backup API 会生成一致快照。

恢复时先停止写入该库的服务、保留现有库，将备份恢复到单独路径。用 `DATABASE_URL` 指向恢复副本、`DATABASE_BACKUP_DIR` 指向独立目录后启动，验证账号、客户数量、账单编号/金额/分享链接及 PDF；通过后再切换正式服务。启动旧库会迁移，先在副本验证。

其他 SQLAlchemy URL 虽可传入，但自动迁移针对 SQLite；迁往 PostgreSQL 需另行规划和验证，不能只改连接串。

## 私密归档恢复

原始 SQLite、迁移备份、设计参考原图、未提交的验收脚本/日志/截图存于仓库外的私密 `invoicecraft-private-backup-YYYYMMDD.tar.gz`。该文件及访问方式私下保管，不上传公开仓库、Release 或 Pages。

先查看归档清单，解压到独立私密目录；仅按需取回数据库副本或设计资料，不将整个归档覆盖到新 clone。数据库恢复按上一节执行，设计资料按历史 QA 说明回溯。归档中的配置、日志及用户内容继续保持私密。

`LAUNCH.md`、`design-qa.md` 留作开发历史，旧临时绝对路径与服务端口不保证存在。运行不依赖这些目录；仓库内字体、WebP 和许可说明足够恢复界面。

## Pages 导出与部署

`scripts/export_pages_demo.py` 使用固定合成样本渲染现有模板，将页面、字体、样式和演示脚本写入 `docs/demo/`；不导出原始用户、数据库、真实配置或 PDF。

```bash
.venv/bin/python scripts/export_pages_demo.py --output docs/demo --base-path /invoicecraft/
```

GitHub 项目站点必须保留 `/invoicecraft/` 前缀。站内链接和资源前缀由导出器处理，双击 HTML 不能可靠复现部署路径。

本机根路径预览可导出到独立任务临时目录（遵循仓库临时目录规则），改用 `--base-path /`，再用 `.venv/bin/python -m http.server` 指向该输出目录。提交前重新用上面的项目路径导出至 `docs/demo/`。

演示编辑仅在当前页内存中，刷新恢复；业务数据不写 localStorage。显示偏好由现有脚本保存。语言可在页内切换，跨页默认中文。完整保存、账号、支付、真实分享和 PDF 都需要 FastAPI 服务。

发布顺序：

1. 修改源码或样本后重新导出，检查站内链接、字体资源、手机布局、语言和编辑预览。
2. 将源码与 `docs/demo/` 一起审阅提交，推送 `main`。
3. 仓库 Settings → Pages → Source 选择 **GitHub Actions**；查看 **Deploy Pages demo** 工作流，或从 Actions 手动运行。
4. 工作流只上传 `docs/demo/`，部署到 `github-pages` 环境，输出部署 URL。
5. 访问 <https://pifuyuini.github.io/invoicecraft/>，验证首页、列表、详情、编辑器，确认保存/登录/支付/PDF 不触发真实服务请求。

Actions 不执行 Python、不安装依赖、不重新生成演示。只改源码而未提交重新导出的产物，线上仍是旧演示。自定义域名或仓库名变更后，需对应更新导出前缀。

## 完整服务部署与验证

GitHub Pages 无法运行 Python 或 SQLite。完整应用需自己的 Python 服务或容器，设置 `BASE_URL`，为 `data/` 提供持久存储，保留私密配置和备份。

仓库有 `Dockerfile`，可按现有 Docker 环境构建运行；容器内默认库为 `/app/data/app.db`，需挂载该数据目录。正式上线需另行验收 HTTPS、会话 cookie 和真实支付配置；当前会话中间件 `https_only=False`。

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check app tests scripts/export_pages_demo.py
```

继续开发前运行以上检查，再手工验证注册/登录、客户 CRUD、账单创建/复制/修改/状态、搜索筛选、中英文文档、PDF、公开链接和旧 SQLite 副本迁移。测试不依赖旧预览账号或原始数据库。

修改金额规则时，同时检查网页预览、保存数据、PDF 和演示的一致性。JPY 为零位小数，其他支持币种为两位小数，逐项 `ROUND_HALF_UP` 后汇总计税。
