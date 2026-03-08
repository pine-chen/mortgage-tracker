# 房贷记账 Mortgage Tracker

个人房贷记账 Web 应用，支持手动记账、CSV 导入、自动月供记录、统计图表展示，并提供 REST API 供 Telegram Bot 对接。移动端友好，适合手机上通过 Bot 记账后随时查看。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 导入历史数据（钱迹导出的 CSV）
python import_csv.py /path/to/房贷账单.csv

# 启动应用
python app.py
# 访问 http://localhost:5001
```

## 项目结构

```
mortgage-tracker/
├── app.py                    # Flask 应用入口（含 Basic Auth、日志、Scheduler 开关）
├── config.py                 # 配置（数据库、API Key、Web 登录、定时任务）
├── models.py                 # 数据模型（Payment, SchedulerConfig）
├── import_csv.py             # CSV 导入脚本
├── deploy.sh                 # 一键部署脚本（PM2 管理：init/start/stop/restart/backup/logs）
├── ecosystem.config.js       # PM2 进程配置（Gunicorn 单 worker，自动加载 .env）
├── nginx.conf.example        # Nginx 反向代理配置模板
├── requirements.txt          # flask, flask-sqlalchemy, apscheduler, pandas, gunicorn
├── .gitignore
├── routes/
│   ├── __init__.py           # Blueprint 注册
│   ├── auth.py               # 登录 / 退出路由（session 管理）
│   ├── views.py              # 页面路由（仪表盘、账单、设置）
│   └── api.py                # REST API（X-API-Key 认证，统一 JSON 响应格式）
├── services/
│   ├── __init__.py
│   ├── payment_service.py    # 业务逻辑（CRUD、统计、金额变更检测）
│   └── scheduler_service.py  # APScheduler 自动月供记录
├── templates/
│   ├── base.html             # 公共布局（响应式导航栏 + 退出按钮）
│   ├── login.html            # 登录页面
│   ├── index.html            # 统计仪表盘（Chart.js，移动端适配）
│   ├── records.html          # 账单列表（桌面表格 / 手机卡片双视图）
│   └── settings.html         # 定时任务配置 + CSV 导入
├── static/
│   └── style.css             # 响应式样式（含移动端断点）
├── data/                     # SQLite 数据库（运行时创建）
├── logs/                     # 日志文件（RotatingFileHandler）
└── backups/                  # 数据库备份（deploy.sh backup）
```

## 功能说明

### 统计仪表盘 `/`

- 汇总卡片：累计还款总额、月供笔数/总额、提前还款总额、当前月供金额
- 折线图：月供金额走势（阶梯线）+ 提前还款/契税柱状图（共用 Y 轴，柱上标注金额）
- 饼图：还款类型占比
- 柱状图：年度还款对比（堆叠）
- 近期记录（桌面端表格，手机端卡片列表）

### 账单记录 `/records`

- 桌面端：标准表格视图，含编辑/删除操作列
- 手机端：卡片列表视图，左侧色条标识类型，按钮全宽易点击
- 按年份、类型筛选，分页展示
- 添加记录（展开表单）、编辑（弹窗）、删除（确认提示）
- 手动添加月供时，如果金额与当前配置不同，会提示"月供金额变更"

### 设置 `/settings`

- 定时任务配置：月供金额、扣款日、启用/禁用
- CSV 文件上传导入（Web 界面）
- API 端点参考表

### 定时自动记账

每天 08:00 检查：
1. 今天是否为扣款日（默认 18 号）
2. 本月是否已有月供记录（幂等，不重复）
3. 按配置金额自动创建 `source=auto` 的记录
4. `misfire_grace_time=86400`：服务重启后自动补录

可通过环境变量 `SCHEDULER_ENABLED=0` 禁用（多 worker 部署时避免重复执行）。

### 移动端适配

主要使用场景：通过 TG Bot 在手机上操作，Web 界面用于查看。因此做了以下移动端优化：

- **统计卡片**：2x2 网格布局，紧凑字号
- **图表**：全宽显示，字体/标签自动缩小，Y 轴自动用"万"为单位
- **账单列表**：自动切换为卡片视图，左侧色条标识类型（蓝=月供，绿=提前还款，黄=契税），编辑/删除按钮全宽
- **筛选栏**：下拉框自动撑满屏幕宽度
- **分页**：使用小尺寸分页器

### 安全特性

- **Web 登录页面**：设置 `MORTGAGE_WEB_USER` + `MORTGAGE_WEB_PASS` 环境变量即启用，未登录访问任何页面会跳转到 `/login`。登录后 session 保持 30 天。导航栏右侧显示"退出"按钮。未配置用户名密码时免登录（本地开发）。
- **TG 白名单免密登录**：Bot 调用 `POST /api/v1/auth/token` 为白名单用户生成一次性链接，用户点击即自动登录，无需输密码。Token 5 分钟过期，用后即毁。白名单通过环境变量 `TG_WHITELIST` 配置（逗号分隔），默认含 `1308785881`。
- **API Key 认证**：所有 `/api/v1/*` 端点需 `X-API-Key` 请求头
- **日志审计**：RotatingFileHandler，5MB 自动轮转保留 3 份，写入 `logs/app.log`

## 服务器部署（腾讯云 Ubuntu + PM2）

> 使用 PM2 统一管理所有进程（与现有 OpenClaw 等服务一致），Gunicorn 仅作为 WSGI 服务器（不开 daemon），PM2 负责守护、重启、日志、开机自启。

### 前置条件

```bash
# 确认 PM2 已安装
pm2 --version

# 如果没有：
npm install -g pm2
```

### 第一步：上传项目

```bash
# 本地：初始化 Git 并推送
cd mortgage-tracker
git init && git add -A && git commit -m "init"
# 推送到 GitHub/Gitee 私有仓库

# 服务器：clone
ssh root@your-server
cd /opt
git clone https://your-repo/mortgage-tracker.git
cd mortgage-tracker
```

### 第二步：初始化

```bash
chmod +x deploy.sh
./deploy.sh init
```

这会：创建 Python 虚拟环境、安装依赖（含 Gunicorn）、生成 `.env` 配置模板。

### 第三步：编辑配置

```bash
vim .env
```

```bash
SECRET_KEY=随机字符串           # openssl rand -hex 32
MORTGAGE_API_KEY=你的API密钥    # TG Bot 调用时使用

# Web 界面登录（留空则不需要登录）
MORTGAGE_WEB_USER=admin
MORTGAGE_WEB_PASS=你的密码

# TG 白名单（逗号分隔，这些用户可通过 Bot 生成免密登录链接）
TG_WHITELIST=1308785881

# 定时任务开关（1=开启，单 worker 模式安全）
SCHEDULER_ENABLED=1
```

### 第四步：导入历史数据 & 启动

```bash
./deploy.sh import /path/to/房贷账单.csv   # 导入 CSV
./deploy.sh start                          # PM2 启动 Gunicorn
./deploy.sh status                         # 查看状态
```

`start` 实际执行的是：

```bash
pm2 start ecosystem.config.js   # 读取 ecosystem.config.js 配置
pm2 save                        # 持久化进程列表
```

### 第五步：Nginx 反向代理

```bash
cp nginx.conf.example /etc/nginx/sites-available/mortgage-tracker
vim /etc/nginx/sites-available/mortgage-tracker   # 修改 server_name
ln -s /etc/nginx/sites-available/mortgage-tracker /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

HTTPS（可选）：

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

### 第六步：开机自启 + 自动备份

```bash
# PM2 开机自启（只需执行一次）
pm2 startup
# 执行它输出的 sudo 命令，然后：
pm2 save

# 自动备份（每周日凌晨）
crontab -e
# 添加：
0 0 * * 0 cd /opt/mortgage-tracker && ./deploy.sh backup
```

### 日常运维

```bash
./deploy.sh status    # 查看进程详情
./deploy.sh logs      # 实时日志（PM2 日志流）
./deploy.sh restart   # 重启并重新加载 .env
./deploy.sh stop      # 停止
./deploy.sh backup    # 手动备份数据库（保留最近 10 份）
./deploy.sh update    # git pull + 重装依赖

# 也可以直接用 PM2 命令
pm2 status            # 查看所有进程（含 OpenClaw 等）
pm2 monit             # 实时监控 CPU/内存
pm2 logs mortgage-tracker --lines 100
```

## REST API

所有 API 端点需要在请求头中携带 `X-API-Key`。

统一响应格式：

```json
{"ok": true, "data": {...}}           // 成功
{"ok": true, "message": "已删除"}     // 成功（无数据）
{"ok": false, "error": "错误信息"}     // 失败
```

### 还款记录

```bash
# 查询所有记录（支持 ?year=2025&type=monthly 筛选）
curl -H "X-API-Key: your-key" http://localhost:5001/api/v1/payments

# 新增记录
curl -X POST -H "X-API-Key: your-key" -H "Content-Type: application/json" \
  -d '{"date":"2026-03-18","amount":4230,"payment_type":"monthly","notes":""}' \
  http://localhost:5001/api/v1/payments
# 返回 data 中含 amount_changed 字段，TG Bot 可据此提示用户更新月供配置

# 修改记录
curl -X PUT -H "X-API-Key: your-key" -H "Content-Type: application/json" \
  -d '{"amount":4200}' \
  http://localhost:5001/api/v1/payments/1

# 删除记录
curl -X DELETE -H "X-API-Key: your-key" http://localhost:5001/api/v1/payments/1
```

### 统计

```bash
# 汇总统计
curl -H "X-API-Key: your-key" http://localhost:5001/api/v1/stats/summary

# 月度趋势
curl -H "X-API-Key: your-key" http://localhost:5001/api/v1/stats/trend
```

### 定时任务配置

```bash
# 查看配置
curl -H "X-API-Key: your-key" http://localhost:5001/api/v1/scheduler/config

# 更新配置
curl -X PUT -H "X-API-Key: your-key" -H "Content-Type: application/json" \
  -d '{"current_monthly_amount":4230,"payment_day":18,"is_enabled":true}' \
  http://localhost:5001/api/v1/scheduler/config
```

### TG 免密登录

```bash
# Bot 为白名单用户生成一次性登录链接（5 分钟有效，用后即毁）
curl -X POST -H "X-API-Key: your-key" -H "Content-Type: application/json" \
  -d '{"tg_id":"1308785881","next":"/records"}' \
  http://localhost:5001/api/v1/auth/token
# 返回: {"ok":true,"data":{"url":"/auth/tg?token=xxx"}}

# 非白名单用户 → 403
# 拼接完整 URL 发给用户：https://your-domain.com/auth/tg?token=xxx
```

### Telegram Bot 对接

Bot 通过 REST API 与本应用通信，典型交互场景：

```
用户: "记一笔提前还款 10000"
Bot → POST /api/v1/payments {"date":"2026-03-08","amount":10000,"payment_type":"prepayment"}
Bot → 用户: "已记录提前还款 ¥10,000"

用户: "月供从下月开始改为 4100"
Bot → PUT /api/v1/scheduler/config {"current_monthly_amount":4100}
Bot → 用户: "已更新，下次自动记账金额为 ¥4,100"

用户: "查看最近账单"
Bot → POST /api/v1/auth/token {"tg_id":"1308785881","next":"/"}
Bot → 用户: "点击查看：https://your-domain.com/auth/tg?token=xxx"
     （用户点击链接 → 自动登录 → 进入仪表盘）

用户: "删除刚刚的记录"
Bot → DELETE /api/v1/payments/{last_id}
Bot → 用户: "已删除"
```

## 数据模型

### payment 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| date | DATE | 还款日期 |
| amount | DECIMAL(10,2) | 金额（元） |
| payment_type | VARCHAR(20) | `monthly` / `prepayment` / `deed_tax` / `other` |
| notes | TEXT | 备注 |
| source | VARCHAR(20) | `import` / `manual` / `auto` |
| original_id | VARCHAR(64) UNIQUE | 防重复导入标识 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### scheduler_config 表

| 字段 | 类型 | 说明 |
|------|------|------|
| current_monthly_amount | DECIMAL | 当前月供金额 |
| payment_day | INTEGER | 扣款日（默认 18） |
| is_enabled | BOOLEAN | 是否启用自动记账 |
| last_run_at | DATETIME | 上次执行时间 |

## 数据备份

```bash
# 手动备份
./deploy.sh backup

# 自动备份（crontab，每周日凌晨，保留最近 10 份）
0 0 * * 0 cd /opt/mortgage-tracker && ./deploy.sh backup
```

---

## 后续扩展规划：多平台账单导入

当前系统仅支持钱迹 CSV 导入房贷数据。后续计划接入招商银行（信用卡 + 储蓄卡）、支付宝、微信的账单，统一导入并生成综合财务数据。

### 整体架构

```
                  ┌─────────────┐
                  │  Scheduler  │  定时触发（每日/每周）
                  └──────┬──────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌─────────────┐ ┌──────────┐ ┌─────────────┐
   │ CMB Fetcher │ │ AliPay   │ │  WeChat     │
   │ (招商银行)   │ │ Fetcher  │ │  Fetcher    │
   └──────┬──────┘ └────┬─────┘ └──────┬──────┘
          │              │              │
          ▼              ▼              ▼
   ┌─────────────────────────────────────────┐
   │         Unified Parser / Normalizer     │
   │   统一解析层：各平台 → 标准 Transaction   │
   └──────────────────┬──────────────────────┘
                      ▼
              ┌───────────────┐
              │   Database    │
              │  (SQLite)     │
              └───────────────┘
```

### 新增数据模型设计

```python
# models.py 扩展

class Account(db.Model):
    """账户表 — 标识资金来源"""
    __tablename__ = 'account'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))          # "招行信用卡"、"招行储蓄卡"、"支付宝"、"微信"
    platform = db.Column(db.String(20))      # cmb_credit / cmb_debit / alipay / wechat
    account_no = db.Column(db.String(30))    # 脱敏卡号尾号，如 "**** 6789"
    is_active = db.Column(db.Boolean, default=True)

class Transaction(db.Model):
    """通用交易记录表 — 统一各平台账单"""
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    date = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Numeric(12, 2))
    direction = db.Column(db.String(10))     # income / expense / transfer
    category = db.Column(db.String(30))      # 餐饮、交通、房贷、转账...
    counterpart = db.Column(db.String(100))  # 交易对方
    description = db.Column(db.Text)         # 原始摘要
    original_id = db.Column(db.String(128), unique=True)  # 平台原始流水号（去重）
    source = db.Column(db.String(20))        # cmb_credit / cmb_debit / alipay / wechat / manual
    raw_data = db.Column(db.JSON)            # 保留原始数据，便于调试

class FetchLog(db.Model):
    """拉取日志 — 记录每次账单拉取的状态"""
    __tablename__ = 'fetch_log'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(20))
    fetch_time = db.Column(db.DateTime)
    status = db.Column(db.String(10))        # success / failed / partial
    record_count = db.Column(db.Integer)
    error_message = db.Column(db.Text)
```

### 各平台接入方案

#### 1. 招商银行（信用卡 + 储蓄卡）

招行没有开放 API，账单获取有以下几种路径：

| 方案 | 说明 | 推荐度 |
|------|------|--------|
| **邮箱账单解析** | 招行每月发送账单邮件到邮箱，用 IMAP 拉取并解析 HTML/PDF | 推荐，稳定 |
| **掌上生活 H5 抓包** | 通过 mitmproxy 抓取掌上生活 App 请求，模拟调用 | 可行但易失效 |
| **手动导出 CSV** | 从招行网银/App 导出交易明细 CSV，上传导入 | 最稳定，但需手动 |
| **招行开放平台** | 企业级 API，个人用户无法申请 | 不适用 |

**推荐方案：邮箱账单 + 手动 CSV 兜底**

```python
# services/fetchers/cmb_fetcher.py（规划）

class CMBFetcher:
    """招商银行账单获取器"""

    def fetch_from_email(self, imap_config):
        """
        从邮箱拉取招行账单邮件
        - 连接 IMAP（支持 QQ邮箱、Gmail、163）
        - 搜索发件人为招行的邮件
        - 解析 HTML 表格提取交易明细
        - 返回标准 Transaction 列表
        """
        pass

    def parse_csv(self, csv_path, card_type='credit'):
        """
        解析招行导出的 CSV
        - 信用卡格式：交易日, 记账日, 交易摘要, 交易金额(人民币), ...
        - 储蓄卡格式：交易日期, 摘要, 交易金额, 余额, ...
        """
        pass
```

**招行信用卡 CSV 字段映射：**
```
交易日       → date
交易摘要     → description + counterpart
人民币金额   → amount
卡号后四位   → account_no 匹配
```

**招行储蓄卡 CSV 字段映射：**
```
交易日期     → date
摘要         → description
交易金额     → amount（正=收入，负=支出）
余额         → 可选记录
```

#### 2. 支付宝

| 方案 | 说明 | 推荐度 |
|------|------|--------|
| **官方账单导出** | 支付宝 App → 账单 → 导出交易记录（ZIP/CSV） | 推荐 |
| **开放平台 API** | 需要企业资质，个人不适用 | 不适用 |

**支付宝 CSV 字段映射：**
```
交易创建时间  → date
商品名称      → description
交易对方      → counterpart
金额(元)      → amount
收/支         → direction
交易状态      → 过滤"交易关闭"
交易订单号    → original_id
```

```python
# services/fetchers/alipay_fetcher.py（规划）

class AlipayFetcher:
    def parse_csv(self, csv_path):
        """
        解析支付宝导出的 CSV
        - 编码：GBK（支付宝默认导出编码）
        - 跳过头部说明行（前几行非数据行）
        - 过滤交易状态为"交易关闭"的记录
        - 按交易订单号去重
        """
        pass
```

#### 3. 微信

| 方案 | 说明 | 推荐度 |
|------|------|--------|
| **官方账单导出** | 微信 → 我 → 服务 → 钱包 → 账单 → 导出（邮件 CSV） | 推荐 |

**微信 CSV 字段映射：**
```
交易时间      → date
交易类型      → category 辅助分类
交易对方      → counterpart
商品         → description
收/支        → direction
金额(元)     → amount（带 ¥ 前缀需清洗）
交易单号     → original_id
```

```python
# services/fetchers/wechat_fetcher.py（规划）

class WeChatFetcher:
    def parse_csv(self, csv_path):
        """
        解析微信导出的 CSV
        - 编码：UTF-8-BOM
        - 金额字段带 ¥ 前缀，需 strip
        - 过滤"已退款"/"已全额退款"记录
        - 按交易单号去重
        """
        pass
```

### Fetcher 统一接口

```python
# services/fetchers/base.py（规划）

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

@dataclass
class RawTransaction:
    """各平台解析后的标准中间格式"""
    date: datetime
    amount: Decimal
    direction: str            # income / expense / transfer
    category: Optional[str]
    counterpart: Optional[str]
    description: str
    original_id: str          # 平台唯一标识，用于去重
    raw_data: dict            # 原始行数据

class BaseFetcher(ABC):
    platform: str             # cmb_credit / cmb_debit / alipay / wechat

    @abstractmethod
    def fetch(self, **kwargs) -> List[RawTransaction]:
        """拉取/解析账单，返回标准格式列表"""
        pass

    def save(self, transactions: List[RawTransaction]):
        """统一入库逻辑，基于 original_id 去重"""
        # 由基类统一实现
        pass
```

### 分类策略

各平台原始分类不统一，需要一个映射层：

```python
# services/category_mapper.py（规划）

# 规则示例：关键词 → 统一分类
CATEGORY_RULES = [
    ({'keywords': ['房贷', '贷款', '月供', '公积金贷款'], 'category': '房贷'}),
    ({'keywords': ['美团', '饿了么', '麦当劳', '星巴克', '餐厅'], 'category': '餐饮'}),
    ({'keywords': ['滴滴', '地铁', '公交', '加油', '停车'], 'category': '交通'}),
    ({'keywords': ['淘宝', '京东', '拼多多', '天猫'], 'category': '购物'}),
    ({'keywords': ['转账', '余额宝', '理财'], 'category': '转账'}),
]

class CategoryMapper:
    def classify(self, description: str, counterpart: str, platform_category: str) -> str:
        """基于多个字段综合判断分类"""
        pass
```

### 扩展后的项目结构

```
mortgage-tracker/
├── ...（现有文件不变）
├── services/
│   ├── payment_service.py        # 房贷业务（现有）
│   ├── scheduler_service.py      # 定时任务（现有，扩展为统一调度）
│   ├── category_mapper.py        # 分类映射（新增）
│   └── fetchers/                 # 各平台账单获取器（新增）
│       ├── __init__.py
│       ├── base.py               # BaseFetcher 抽象类
│       ├── cmb_fetcher.py        # 招商银行
│       ├── alipay_fetcher.py     # 支付宝
│       └── wechat_fetcher.py     # 微信
├── routes/
│   ├── ...（现有）
│   └── import_routes.py          # 多平台导入页面路由（新增）
└── templates/
    ├── ...（现有）
    └── import.html               # 多平台导入管理页面（新增）
```

### 扩展开发顺序建议

1. **新增 Transaction + Account 模型**，与现有 Payment 表并存（房贷专用逻辑不受影响）
2. **实现 BaseFetcher 抽象类**和统一入库逻辑
3. **支付宝 CSV 解析**（最简单，格式稳定，优先验证架构）
4. **微信 CSV 解析**
5. **招行 CSV 解析**（信用卡 + 储蓄卡两种格式）
6. **招行邮箱账单自动拉取**（可选，需 IMAP 配置）
7. **分类映射器** + 综合统计仪表盘
8. **定时自动拉取调度**（复用现有 APScheduler 基础设施）

### 配置扩展（config.py 预留）

```python
# 后续新增配置项
class Config:
    # ...现有配置...

    # 邮箱 IMAP（招行账单邮件拉取）
    IMAP_SERVER = os.environ.get('IMAP_SERVER', '')       # imap.qq.com
    IMAP_USER = os.environ.get('IMAP_USER', '')
    IMAP_PASSWORD = os.environ.get('IMAP_PASSWORD', '')

    # 各平台拉取开关
    FETCH_CMB_ENABLED = False
    FETCH_ALIPAY_ENABLED = False
    FETCH_WECHAT_ENABLED = False
```
