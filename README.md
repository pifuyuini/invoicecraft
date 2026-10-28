# InvoiceCraft

面向自由职业者与小团队的开票应用，使用 FastAPI、SQLModel、SQLite 和 Jinja2。当前界面采用 Cassette Futurism 控制台风格，支持简体中文与 English。

本仓库保存完整源码、依赖锁文件、开发历史和静态演示，供封存后重新接手。Mac 原生应用与桌面打包尚未实现；保留的 `Cargo.toml` 是历史占位文件。

[在线演示入口](https://pifuyuini.github.io/invoicecraft/) · [接手与恢复说明](HANDOFF.md)

## 当前功能

- 账号注册/登录、独立客户资料、账单创建/编辑/复制和手工状态管理。
- 总览、搜索、筛选、排序、客户关联及账单详情。
- USD / EUR / GBP / CNY / JPY，使用 Decimal 逐项舍入、汇总计税。
- 编辑器实时预览、独立的界面/文档语言、开票方设置及账单资料快照。
- 中文/英文 PDF、无需登录的公开账单链接。
- 本地保存的显示偏好、CRT 效果、亮度和移动端布局。
- 可启用 Stripe 订阅流程与免费额度；默认 `BILLING_ENABLED=false`，账单状态由用户手工维护。

## 静态演示与完整应用

| | GitHub Pages 演示 | 完整 FastAPI 应用 |
|---|---|---|
| 数据 | 固定合成样本 | 自己的 SQLite 数据库 |
| 交互 | 浏览、语言切换、筛选排序、编辑器本页预览 | 账号、客户与账单持久化 |
| 保存 | 编辑仅在当前页内存中，刷新还原 | 保存到数据库 |
| 登录、支付、PDF | 不提供真实操作 | 服务端支持，支付需配置 |
| 部署 | 已提交的 `docs/demo/` | Python 服务及持久数据卷 |

演示不读取原始数据库。显示偏好可保留在浏览器，业务编辑不会写入 localStorage；跨页默认中文。在线入口是否部署完成，以仓库 Actions 中的 Pages 任务与实际访问结果为准。

## 从新机器恢复开发

需要 Git、uv 和 Python 3.12。`pyproject.toml` 声明 Python >=3.12，`.python-version` 固定 3.12，封存环境使用 3.12.11；依赖版本由 `uv.lock` 保存。

```bash
git clone https://github.com/pifuyuini/invoicecraft.git
cd invoicecraft
uv sync --frozen
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`uv sync --frozen` 用于新机器建环境；已有环境直接使用 `.venv/bin/`，不必重建。所有应用命令从仓库根目录运行。打开 <http://localhost:8000>，注册自己的账号；新 clone 不附带原用户、密码或数据库。

配置从环境变量与根目录 `.env` 读取。启动时创建默认数据库 `data/app.db`，必要时执行内置迁移。完整配置、备份与恢复方法见 [HANDOFF.md](HANDOFF.md)。

## 验证

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check app tests scripts/export_pages_demo.py
```

测试覆盖认证、账单、金额、语言、迁移、PDF 与订阅流程。测试通过不等于真实 Stripe 或生产部署已验收。

## 更新 Pages 演示

在现有 Python 环境中重新导出：

```bash
.venv/bin/python scripts/export_pages_demo.py --output docs/demo --base-path /invoicecraft/
```

检查后提交源码改动及 `docs/demo/`，推送 `main`。仓库 Settings → Pages → Source 使用 **GitHub Actions**。`.github/workflows/pages.yml` 也支持手动运行，仅发布 `docs/demo/`，不在 CI 安装依赖或运行应用。

## 关键路径

```text
app/
  main.py, config.py       服务入口与配置
  db.py, models.py         SQLite 迁移、模型与 Decimal 金额
  routers/                认证、账单、客户、偏好与订阅
  services/               文档计算、PDF 与 Stripe
  templates/              Jinja 页面
  static/                 样式、交互、字体、纹理与素材许可
scripts/export_pages_demo.py  合成样本静态导出
docs/demo/                提交到 Git 的 Pages 发布产物
tests/                    自动化测试
pyproject.toml, uv.lock    Python 环境声明与锁定
HANDOFF.md                重新接手、数据恢复与部署
LAUNCH.md, design-qa.md    历史上线设想及界面验收记录
```

`LAUNCH.md` 保留早期商业部署设想，其中默认计费行为、平台操作和部分建议与当前代码可能不同，以当前配置、代码及接手说明为准。`design-qa.md` 的临时服务地址、绝对路径与截图位置是历史记录，不是新机器运行依赖。

原始数据库、用户数据、设计原图与临时验收资料另存私密归档，不进入公开仓库或 Pages。字体和生成素材的来源/许可说明保留在 `app/static/` 对应目录中。
