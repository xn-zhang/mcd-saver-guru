# WorkBuddy 开发对话上下文

本文件记录使用**腾讯 WorkBuddy** 开发「麦麦省钱军师」Skill 的过程，用于核验 WorkBuddy 专项奖励条件。

## 开发环境

| 项 | 值 |
|---|---|
| 开发工具 | 腾讯 WorkBuddy（Agent 模式） |
| 开发日期 | 2026-10-09 |
| 使用的 Skill 工具链 | `skill-creator`（`init_skill.py` / `quick_validate.py` / `package_skill.py`） |
| 使用的 MCP | `mcd-mcp`（麦当劳中国 MCP Server） |
| Skill 目录 | `~/.workbuddy/skills/mcd-saver-guru/` |

## 对话上下文摘要

### 第 1 轮 · 需求确认

**用户**：基于麦当劳 MCP 能力帮我开发一个创意 Skill：如麦麦点餐助手、省钱助手、活动推荐助手等。

**WorkBuddy**：先梳理了麦当劳 MCP 的全部可用 Tool（点餐、优惠券、积分、活动、营养、订单管理），列出 35 个 Tool 的能力边界；随后就四个创意方向（省钱军师 / 点餐搭子 / 活动雷达 / 健康搭子）向用户确认方向。

**用户选择**：麦麦省钱军师。

### 第 2 轮 · 能力勘探

WorkBuddy 调用麦当劳 MCP 的**只读**接口，摸清真实返回结构，作为 Skill 设计的依据：

- `available-coupons` → 拿到在售可领券（9.9 元冰美式、麦旋风买一送一等）
- `campaign-calendar` → 拿到营销活动日历及活动正文（含价格、日期范围、适用星期）
- `query-my-account` → **关键发现**：`availablePoint = 0`、`expiredPoint = 890.4`，即积分已全部过期
- `mall-points-products` → 拿到积分商城兑换项与所需积分，据此推算兑换率
- `query-lottery-info` → 拿到抽奖单次成本（24 积分）与奖池（立减券 / 折扣券 / 积分奖）
- `query-nearby-stores` → 验证到店门店链路与 `searchType` 行为

这一步决定了 Skill 的两个核心设计：**过期资源优先原则** 与 **积分兑换率排序**。

### 第 3 轮 · Skill 构建

WorkBuddy 使用 `skill-creator` 的 `init_skill.py` 生成脚手架，随后重写全部内容：

1. 删除脚手架示例文件（`scripts/example.py`、`references/api_reference.md`、`assets/example_asset.txt`）
2. 编写 `SKILL.md`：7 条铁律 + 7 步工作流 + 省钱方案卡输出格式
3. 编写 `references/mcp-tools.md`：工具契约、渠道参数规则表、实测响应样例
4. 编写 `references/saving-strategy.md`：三条省钱线、积分兑换率折算、抽奖 ROI、决策树
5. 编写 `scripts/savings_rank.py`：多方案排序与对比表生成
6. 编写 `assets/savings-report.html`：可分享的省钱报告模板

### 第 4 轮 · 验证与打包

- 实测 `scripts/savings_rank.py`：以三个候选方案输入，正确输出按实付升序的对比表、推荐结论与过期资源提示
- 运行 `quick_validate.py`：输出 `Skill is valid!`
- 运行 `package_skill.py`：成功打包为 `mcd-saver-guru.zip`

### 第 5 轮 · 参赛适配

**用户**：询问是否符合麦当劳程序员创意开发大赛参赛条件。

**WorkBuddy**：拉取活动官方规则（README / activityGuidelines / CONTEST_DECLARATION），逐条比对报名条件，识别出缺失的必需文件（`README.md`、`CONTEST_DECLARATION.md`、`MCP_INTEGRATION.md`、`mcp-config.example.json`），并补齐提交包。

## 开发过程中产出并验证的关键结论

1. **渠道参数规则**：到店自取 `beCode` 是哑参数（传了报错），得来速/外送/团餐必传——这是 MCP 调用最高频的出错点，已固化为规则表。
2. **金额单位为分**：`calculate-price` 返回分，需 ÷100，已写入铁律。
3. **积分可能全部过期**：实测账户可用积分为 0，Skill 因此不能默认「用户有积分可花」。
4. **积分兑换率差异可达 5 倍**：50 积分换 6.9 元商品 vs 800 积分换 21.9 元商品，Skill 据此做排序推荐。

## 复现方式

在新会话中向 WorkBuddy 提出：

> 基于麦当劳 MCP 开发一个「省钱军师」Skill，要求：先用 get 接口勘探真实数据结构，再用 calculate-price 对「券线 / 积分线 / 活动线」三个方案做真实试算，最后产出方案卡。

即可复现本项目的开发路径。
