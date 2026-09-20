# InvoiceCraft 上线手册（LAUNCH）

把本仓库变成一个真实在售产品的完整步骤。代码部分已全部完成；以下带 ⚠️ 的步骤需要你本人的账号操作，AI 无法代办。

## 1. 你需要准备的账号 ⚠️

1. **Stripe 账号**（stripe.com，收款用；需绑定你的银行卡完成实名认证）
2. **一个服务器/平台账号**：推荐 Fly.io 或 Render（都支持直接部署 Dockerfile，带免费额度），或任何一台 VPS
3. **一个域名**（可选但强烈建议，约 $10/年，例如 Namecheap/Cloudflare）

## 2. Stripe 配置（约 10 分钟）⚠️

1. Stripe Dashboard → **Products** → 新建产品 "InvoiceCraft Pro"
2. 添加价格：**$6 / month, recurring**，记下 Price ID（形如 `price_1ABC...`）
3. Dashboard → **Developers → API keys**：记下 Secret key（`sk_live_...`；测试期可用 `sk_test_...`）
4. **Developers → Webhooks → Add endpoint**：
   - URL：`https://你的域名/billing/webhook`
   - 订阅事件：`checkout.session.completed`、`customer.subscription.updated`、`customer.subscription.deleted`
   - 记下 Signing secret（`whsec_...`）

## 3. 配置环境变量 ⚠️

生成会话密钥：

```bash
openssl rand -hex 32
```

部署平台的环境变量里设置：

```
SECRET_KEY=<上面生成的随机串>
BASE_URL=https://你的域名
STRIPE_SECRET_KEY=sk_live_...
PRO_PRICE_MONTHLY_ID=price_1ABC...
STRIPE_WEBHOOK_SECRET=whsec_...
DATABASE_URL=sqlite:///./data/app.db   # 见第 5 节的持久化说明
```

> 没有配置 Stripe 变量时应用照常运行，定价页会显示"支付即将上线"，适合先做内测。

## 4. 部署

### 方案 A：Fly.io（推荐）

```bash
brew install flyctl && fly auth signup
fly launch          # 自动识别 Dockerfile，按提示选区域即可
fly secrets set SECRET_KEY=... STRIPE_SECRET_KEY=... PRO_PRICE_MONTHLY_ID=... STRIPE_WEBHOOK_SECRET=... BASE_URL=https://你的app.fly.dev
fly volumes create data --size 1   # SQLite 持久化（见第 5 节）
fly deploy
```

### 方案 B：Render

Dashboard → New → Web Service → 连接 Git 仓库 → Runtime 选 **Docker** → 填环境变量 → Deploy。

### 方案 C：任意 VPS

```bash
docker build -t invoicecraft .
docker run -d --restart=always -p 8000:8000 \
  -v invoicecraft-data:/app/data \
  --env-file .env invoicecraft
# 前面再放 Caddy/Traefik/Nginx 做 HTTPS 反向代理
```

## 5. 数据持久化与备份 ⚠️

默认使用 SQLite，数据库文件在容器内 `/app/data/app.db`。**必须**挂载持久卷
（Fly: volume；Docker: `-v`；Render: persistent disk），否则重启后用户数据丢失。

- 备份 = 定期复制该文件（如每日 cron 上传 S3）
- 业务量增长后可迁移到 PostgreSQL：改 `DATABASE_URL` 即可，模型层无需改动

## 6. 上线后验收清单

1. 打开 `https://你的域名` → 注册账号 → 创建客户 → 创建发票 → 下载 PDF ✓
2. 复制发票公开链接，在无痕窗口打开 ✓
3. 创建第 6 张发票 → 应被引导到定价页（免费额度 5 张）✓
4. Stripe 测试模式（`sk_test_`）下点 **Upgrade to Pro**，用测试卡 `4242 4242 4242 4242` 付款 → 回到成功页，账号变为 Pro，可无限开发票 ✓
5. 确认 Stripe Dashboard 的 Webhook 显示事件投递成功 ✓
6. 切回 `sk_live_` 密钥，自己真实订阅一次（随后可退款）✓

## 7. 合规与运营提示 ⚠️

- 收款即产生税务义务；Stripe 内置 Stripe Tax 可按需开启
- 服务条款（/terms）与隐私政策（/privacy）页面已内置通用模板；Stripe 激活实名认证时通常要求填写这两个页面的 URL。**上线前请通读并按你的实际业务主体、所在地法律修改模板内容**
- 建议加 `SECURITY` 响应头与限流（如用 Cloudflare 免费版挡在前面）
- 密码已用 Argon2 哈希存储；会话 cookie 已签名。不要在日志中打印用户数据

## 常见问题

- **改价格**：在 Stripe 里新建 Price，更新 `PRO_PRICE_MONTHLY_ID` 即可；老订阅不受影响
- **用户想取消订阅**：定价页 Pro 用户的 "Manage subscription" 会进入 Stripe 客户门户（可在 Stripe Dashboard → Settings → Customer portal 开启取消按钮）
- **本地复现线上问题**：`uv run uvicorn app.main:app` 后用 Stripe CLI `stripe listen --forward-to localhost:8000/billing/webhook` 调试 webhook
