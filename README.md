# 峰哥亡命天涯 微博自动存档

每小时自动抓取微博用户「峰哥亡命天涯」（UID: 2397417584）的最新发言，
按微博 ID 增量去重后存档到本仓库，全程由 GitHub Actions 自动运行，无需开自己的电脑。

## 文件说明

| 文件 | 作用 |
|---|---|
| `weibo_crawler.py` | 爬虫脚本（纯 Python 标准库，无第三方依赖） |
| `weibo_posts.jsonl` | 数据存档，每行一条微博（追加式，永不重复） |
| `archive.md` | 按时间倒序的可读存档（自动生成，勿手改） |
| `.github/workflows/crawl.yml` | 定时任务：每小时第 17 分（UTC）自动运行 |

## 部署步骤（一次性，约 5 分钟）

### 1. 创建私有仓库

在 GitHub 新建一个 **Private** 仓库（例如 `weibo-fengge`），不要勾选初始化 README。

### 2. 把本项目推送到仓库

在本目录执行：

```bash
git init
git add .
git commit -m "初始化：峰哥微博存档"
git branch -M main
git remote add origin https://github.com/你的用户名/weibo-fengge.git
git push -u origin main
```

### 3. 配置微博 Cookie（Secret）

1. 电脑上打开浏览器登录微博，访问 <https://m.weibo.cn>
2. 按 `F12` 打开开发者工具 → **Network（网络）** 标签
3. 刷新页面，点击列表中任意一个对 `m.weibo.cn` 的请求
4. 在 **Headers → Request Headers** 里找到 `Cookie:`，复制它后面**整串**内容
5. 到仓库页面 → **Settings → Secrets and variables → Actions → New repository secret**
   - Name：`WEIBO_COOKIE`
   - Secret：粘贴刚才复制的整串 Cookie

### 4. 验证运行

仓库页面 → **Actions** → 左侧选「每小时抓取峰哥微博」→ 右上 **Run workflow** 手动跑一次。
成功后 `weibo_posts.jsonl` 和 `archive.md` 会自动出现在仓库里，之后每小时自动更新。

## 维护说明

- **Cookie 过期**：微博 Cookie 通常几周到几个月过期一次。过期后 Actions 日志里会出现
  「Cookie 失效或被风控」警告，按第 3 步重新复制一次更新 Secret 即可。
- **改频率**：编辑 `.github/workflows/crawl.yml` 里的 cron 表达式（注意是 UTC 时间）。
- **抓别人**：改 `weibo_crawler.py` 顶部的 `UID` 即可（`CONTAINER_ID` 自动拼）。
