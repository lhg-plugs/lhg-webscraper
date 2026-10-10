> **合规声明（置顶，不可绕过）**：本插件只采集**公开可访问**的数据；遵守目标站点的 robots.txt 与服务条款（ToS）；**不**绕过登录、付费墙、验证码（CAPTCHA）；采集频率限流，不给目标站造成负担；使用者自行承担法律责任。任一环节触碰红线，插件将**直接拒绝并说明原因**，不提供变通方案。

<!-- About 简介（推送后填写到仓库 About 栏）：
爬虫采集专家：目标站点→采集方案→反爬应对→数据清洗→交付，合规优先红线拒绝 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-webscraper
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, web-scraping, data-collection -->

# lhg-webscraper：爬虫采集专家

> **一句话介绍**：给 AI 编程助手装上"爬虫采集专家"——目标站点→采集方案（请求/解析/翻页/增量）→反爬应对清单→数据清洗→交付，合规优先：只采公开数据，红线环节直接拒绝。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-webscraper
> /plugin install lhg-webscraper@lhg-plugs
> ```

## 它是什么

`lhg-webscraper` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **4 个命令**（小白入口）：`scrape` 采集全流程（合规预检→方案→反爬→清洗→交付），`check-robots` robots.txt 合规预检，`clean` 数据清洗，`audit` 采集代码体检
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：采集方案设计、合规红线、反爬应对清单、数据清洗
- **3 个专家 agent**：方案设计、脚本构建、合规审计
- **1 个硬门 hook**：检测到登录绕过/CAPTCHA绕过/付费墙绕过意图时告警（可一键豁免）
- **14 条确定性审计规则**：robots合规、限流、UA、超时、敏感字段、绕过意图，纯 Python、零第三方依赖

## 4 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-webscraper:scrape` | 目标站点→采集方案→反爬应对→清洗→交付（合规预检先行） | `/lhg-webscraper:scrape https://example.com "每天抓头条标题和发布时间"` |
| `/lhg-webscraper:check-robots` | 拉取目标站 robots.txt，给出允许/禁止结论 | `/lhg-webscraper:check-robots example.com` |
| `/lhg-webscraper:clean` | 数据清洗：去重去噪归一化 + 敏感字段二次扫描 | `/lhg-webscraper:clean raw.csv` |
| `/lhg-webscraper:audit` | 采集代码体检：14 条规则，blocker 拦截 | `/lhg-webscraper:audit ./my-scraper` |

## 合规红线（再说一遍，因为重要）

1. 只采集**公开可访问**的数据
2. 遵守目标站 **robots.txt** 与 **ToS**
3. **不**绕过登录、付费墙、验证码——"想办法绕过"类需求直接拒绝
4. 采集频率限流：默认请求间隔 ≥1 秒，并发 ≤3
5. 不采集身份证号、手机号、密码等个人敏感信息
6. 使用者自行承担法律责任

## 目录结构

```
lhg-webscraper/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 4 个命令：scrape / check-robots / clean / audit
├── skills/                  # 4 个平台中立 skill（plan/compliance/anti/clean）
├── agents/                  # 3 个专家 agent（architect / builder / compliance-auditor）
├── hooks/                   # 1 个硬门（绕过意图告警）+ 豁免说明
├── scripts/audit/           # 14 条确定性审计规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你想定时采集某个公开网站的数据（如新闻标题、商品价格、招投标公示），但不想学整套爬虫技术时 → 用 `/lhg-webscraper:scrape`
- 你不确定某个站点能不能采、会不会触红线时 → 先用 `/lhg-webscraper:check-robots` + 合规五问
- 你手里有一份爬来的脏数据想洗干净 → 用 `/lhg-webscraper:clean`
- 你写了个采集脚本，想确认有没有合规坑（无限流、无UA、敏感字段）→ 跑 `/lhg-webscraper:audit`

**什么时候不用：**

- 数据需要登录后才能看 → 本插件直接拒绝，不提供任何绕过方案（这是红线，不是功能缺失）
- 需要绕过验证码/付费墙 → 同上，拒绝
- 你想采集身份证号、手机号、密码等个人信息 → 拒绝，这是法律红线
- 目标站 ToS 明确禁止自动化采集 → 拒绝，建议走官方 API 或申请授权
- 你只是想要个通用 HTTP 工具库 → 本插件是"带合规大脑的采集流程"，纯工具需求用 requests/httpx 文档即可

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-video-edit](https://github.com/lhg-plugs/lhg-video-edit) | 一句话把口播素材剪成爆款短视频（+口播脚本子命令） | `/plugin install lhg-video-edit@lhg-plugs` |
| [lhg-wechat-article](https://github.com/lhg-plugs/lhg-wechat-article) | 公众号写作专家：选题到排版一气呵成 | `/plugin install lhg-wechat-article@lhg-plugs` |
| [lhg-xiaohongshu](https://github.com/lhg-plugs/lhg-xiaohongshu) | 小红书种草专家：卖点到爆款笔记一键生成 | `/plugin install lhg-xiaohongshu@lhg-plugs` |
| [lhg-resume](https://github.com/lhg-plugs/lhg-resume) | 简历优化专家：ATS诊断到模拟面试一条龙 | `/plugin install lhg-resume@lhg-plugs` |
| [lhg-ppt](https://github.com/lhg-plugs/lhg-ppt) | PPT制作专家：述职融资答辩一键成稿 | `/plugin install lhg-ppt@lhg-plugs` |
| [lhg-excel](https://github.com/lhg-plugs/lhg-excel) | 表格数据专家：清洗透视图表一条龙 | `/plugin install lhg-excel@lhg-plugs` |
| [lhg-thesis](https://github.com/lhg-plugs/lhg-thesis) | 毕业论文助手：开题到盲审的写作流水线 | `/plugin install lhg-thesis@lhg-plugs` |
| [lhg-miniprogram](https://github.com/lhg-plugs/lhg-miniprogram) | 小程序开发专家：一句话生成微信小程序 | `/plugin install lhg-miniprogram@lhg-plugs` |
| [lhg-contract](https://github.com/lhg-plugs/lhg-contract) | 合同审查助手：风险条款标红+修改建议 | `/plugin install lhg-contract@lhg-plugs` |
| [lhg-geo](https://github.com/lhg-plugs/lhg-geo) | AI搜索优化专家：品牌在AI回答里的可见度 | `/plugin install lhg-geo@lhg-plugs` |
| [lhg-poster](https://github.com/lhg-plugs/lhg-poster) | 海报设计专家：一句话生成手机端海报 | `/plugin install lhg-poster@lhg-plugs` |
| [lhg-shopify](https://github.com/lhg-plugs/lhg-shopify) | 独立站建站专家：高转化店铺一键搭建 | `/plugin install lhg-shopify@lhg-plugs` |
| [lhg-fiction](https://github.com/lhg-plugs/lhg-fiction) | 网文写作专家：大纲到逐章+人设一致性检测 | `/plugin install lhg-fiction@lhg-plugs` |
| [lhg-drama-script](https://github.com/lhg-plugs/lhg-drama-script) | 短剧剧本专家：分集大纲到单集剧本 | `/plugin install lhg-drama-script@lhg-plugs` |
| [lhg-lit-review](https://github.com/lhg-plugs/lhg-lit-review) | 文献综述专家：框架到引用校验一条龙 | `/plugin install lhg-lit-review@lhg-plugs` |
| [lhg-salary-talk](https://github.com/lhg-plugs/lhg-salary-talk) | 薪酬谈判专家：策略到话术演练 | `/plugin install lhg-salary-talk@lhg-plugs` |
| [lhg-biz-report](https://github.com/lhg-plugs/lhg-biz-report) | 商业分析专家：数据到图文报告一键生成 | `/plugin install lhg-biz-report@lhg-plugs` |
| [lhg-study-abroad](https://github.com/lhg-plugs/lhg-study-abroad) | 留学文书专家：PS推荐信多轮打磨 | `/plugin install lhg-study-abroad@lhg-plugs` |
| [lhg-meal-plan](https://github.com/lhg-plugs/lhg-meal-plan) | 营养食谱专家：测算到一周食谱+采购单 | `/plugin install lhg-meal-plan@lhg-plugs` |
| [lhg-competitor](https://github.com/lhg-plugs/lhg-competitor) | 竞品分析专家：五维框架+对比矩阵+SWOT+差异化建议报告 | `/plugin install lhg-competitor@lhg-plugs` |
| [lhg-social-ops](https://github.com/lhg-plugs/lhg-social-ops) | 社媒运营专家：定位→日历→分发策略→复盘，策略+复盘闭环 | `/plugin install lhg-social-ops@lhg-plugs` |
| [lhg-headline](https://github.com/lhg-plugs/lhg-headline) | 爆款标题专家：多平台标题公式生成+合规检测+点击率打分 | `/plugin install lhg-headline@lhg-plugs` |
| [lhg-logo](https://github.com/lhg-plugs/lhg-logo) | Logo设计专家：品牌概念→几何规范→多尺寸导出自检 | `/plugin install lhg-logo@lhg-plugs` |
| [lhg-ecom-design](https://github.com/lhg-plugs/lhg-ecom-design) | 电商视觉专家：卖点到高点击主图一键策划 | `/plugin install lhg-ecom-design@lhg-plugs` |
| [lhg-ecom-report](https://github.com/lhg-plugs/lhg-ecom-report) | 电商复盘专家：店铺数据到周/月复盘报告 | `/plugin install lhg-ecom-report@lhg-plugs` |
| [lhg-lesson-plan](https://github.com/lhg-plugs/lhg-lesson-plan) | 课程设计专家：课标对齐→教案课件→知识点覆盖校验 | `/plugin install lhg-lesson-plan@lhg-plugs` |
| [lhg-dashboard](https://github.com/lhg-plugs/lhg-dashboard) | 数据看板专家：指标体系→看板布局→图表规范校验 | `/plugin install lhg-dashboard@lhg-plugs` |
| [lhg-book-translate](https://github.com/lhg-plugs/lhg-book-translate) | 书籍翻译专家：术语锁定→章节翻译→一致性审计 | `/plugin install lhg-book-translate@lhg-plugs` |
| [lhg-infographic](https://github.com/lhg-plugs/lhg-infographic) | 信息图表专家：数据→图表选型→Canvas绘制→可读性审计 | `/plugin install lhg-infographic@lhg-plugs` |
| [lhg-live-script](https://github.com/lhg-plugs/lhg-live-script) | 直播话术专家：开播钩子到逼单成交，话术一次写完 | `/plugin install lhg-live-script@lhg-plugs` |
| [lhg-course-create](https://github.com/lhg-plugs/lhg-course-create) | 课程制作专家：大纲到试听课，一门课从 0 到可交付 | `/plugin install lhg-course-create@lhg-plugs` |
| [lhg-exam-maker](https://github.com/lhg-plugs/lhg-exam-maker) | 出题组卷专家：知识点→蓝图→组卷→覆盖率校验 | `/plugin install lhg-exam-maker@lhg-plugs` |
| [lhg-weekly-review](https://github.com/lhg-plugs/lhg-weekly-review) | 周报复盘专家：记录→结构化周报→亮点→风险预警 | `/plugin install lhg-weekly-review@lhg-plugs` |
| [lhg-money-plan](https://github.com/lhg-plugs/lhg-money-plan) | 理财规划助手：收支→预算→储蓄目标（非投资建议） | `/plugin install lhg-money-plan@lhg-plugs` |
| [lhg-finmodel](https://github.com/lhg-plugs/lhg-finmodel) | 财务建模专家：假设→三表搭建→勾稽校验→敏感性分析 | `/plugin install lhg-finmodel@lhg-plugs` |
| [lhg-mini-game](https://github.com/lhg-plugs/lhg-mini-game) | H5游戏专家：一句话生成可玩H5小游戏 | `/plugin install lhg-mini-game@lhg-plugs` |
| [lhg-browser-ext](https://github.com/lhg-plugs/lhg-browser-ext) | 浏览器插件专家：一句话想法生成MV3插件 | `/plugin install lhg-browser-ext@lhg-plugs` |
| [lhg-bp](https://github.com/lhg-plugs/lhg-bp) | 商业计划书专家：九章BP→投资人自检→路演版 | `/plugin install lhg-bp@lhg-plugs` |
| [lhg-survey](https://github.com/lhg-plugs/lhg-survey) | 问卷分析专家：清洗→统计→图表→结论报告 | `/plugin install lhg-survey@lhg-plugs` |
| [lhg-product-pick](https://github.com/lhg-plugs/lhg-product-pick) | 跨境选品专家：目标市场→五维打分表→供应链 checklist→风险清单 | `/plugin install lhg-product-pick@lhg-plugs` |
| [lhg-labor-rights](https://github.com/lhg-plugs/lhg-labor-rights) | 劳动维权助手：纠纷场景→仲裁流程指引→文书模板→证据清单 | `/plugin install lhg-labor-rights@lhg-plugs` |
| [lhg-community](https://github.com/lhg-plugs/lhg-community) | 社群运营专家：定位→入群SOP→内容日历→转化话术→流失召回 | `/plugin install lhg-community@lhg-plugs` |
| [lhg-taobao](https://github.com/lhg-plugs/lhg-taobao) | 店铺运营专家：选品→上架→标题/主图优化→数据复盘 | `/plugin install lhg-taobao@lhg-plugs` |
| [lhg-sci-figure](https://github.com/lhg-plugs/lhg-sci-figure) | 学术图表专家：数据→期刊配图规范→图表生成→规范脚本校验 | `/plugin install lhg-sci-figure@lhg-plugs` |
| [lhg-sop](https://github.com/lhg-plugs/lhg-sop) | SOP沉淀专家：流程访谈→SOP文档→检查清单→版本管理 | `/plugin install lhg-sop@lhg-plugs` |
| [lhg-podcast](https://github.com/lhg-plugs/lhg-podcast) | 播客制作专家：选题→录制→剪辑→shownotes→分发，一期节目全流程 | `/plugin install lhg-podcast@lhg-plugs` |
| [lhg-motion-video](https://github.com/lhg-plugs/lhg-motion-video) | 动效视频专家：需求→导演brief→纯代码渲染→成片导出 | `/plugin install lhg-motion-video@lhg-plugs` |
| [lhg-webscraper](https://github.com/lhg-plugs/lhg-webscraper) | 爬虫采集专家：目标站点→采集方案→反爬应对→数据清洗→交付（合规优先） | `/plugin install lhg-webscraper@lhg-plugs` |
| *（后续插件在此追加，保持表格格式一致）* | | |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、14 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-webscraper/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
