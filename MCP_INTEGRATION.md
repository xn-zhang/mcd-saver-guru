# MCP 集成说明

本文说明「麦麦省钱军师」实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值。

## 1. 使用的 MCP Server

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp` |
| 传输方式 | `streamablehttp` |
| 端点 | `https://mcp.mcd.cn` |
| 鉴权 | `Authorization: Bearer <MCD_MCP_TOKEN>` |
| 配置示例 | 见 `mcp-config.example.json`（仅使用环境变量占位符） |

## 2. 使用的 Tool 清单

本项目**真实调用**麦当劳 MCP 的以下 Tool，按省钱工作流的四个阶段分组：

### 阶段一 · 券资产

| Tool | 用途 | 是否必需 |
|---|---|---|
| `available-coupons` | 拉取麦麦省当前**可领取**的券列表 | 是 |
| `auto-bind-coupons` | 一键领取全部可领券（有副作用，需用户确认） | 用户确认后 |
| `query-my-coupons` | 用户**卡包拥有**的券（不保证门店可用） | 是 |
| `query-store-coupons` | **指定门店 + 渠道**真正可用的券 | 是（比价核心） |

### 阶段二 · 积分与奖品资产

| Tool | 用途 |
|---|---|
| `query-my-account` | 积分账户：可用积分、**本月即将过期积分**、已过期积分 |
| `mall-points-products` | 积分商城可兑换商品（用于计算「积分/元」兑换率） |
| `mall-product-detail` | 兑换商品 SKU 详情（拿 `skuId` / `spuCategory`） |
| `query-my-prizes` | 已中奖但未使用的奖品券 |
| `query-lottery-info` | 积分抽奖活动信息与资源决策 `drawDecision` |

### 阶段三 · 活动与门店

| Tool | 用途 |
|---|---|
| `campaign-calendar` | 营销活动日历（可传日期锚定今天） |
| `now-time-info` | 服务器时间，用于活动日期锚定 |
| `query-nearby-stores` | 到店自取 / 得来速门店 |
| `delivery-query-addresses` | 外送地址列表 |
| `delivery-query-stores` | 按地址查可配送门店（麦乐送/团餐） |

### 阶段四 · 商品、试算与下单

| Tool | 用途 |
|---|---|
| `query-meals` | 商品列表与售价，获取 `productCode` |
| `query-meal-detail` | 餐品组成与特调选项 |
| `calculate-price` | **含券真实试算**，返回分单位金额与 `takeWayList` |
| `create-order` | 真实下单 |
| `query-order` / `order-list` / `cancel-order` | 订单查询与取消 |
| `query-meal-assistance` | 企业团餐助餐服务（团餐场景） |

> 兑换类操作另涉及 `mall-create-order`（积分兑换）与派对链路 `query-party-*` / `party-order-create`，本项目在积分兑换方案中会用到 `mall-create-order`。

## 3. 调用流程

核心链路：**先盘点资产，再交叉试算，最后才触达下单**。三个候选方案各跑一次真实价格接口，用实测数据对比，而不是凭经验断言。

```
用户提出需求
   │
   ├─(1) 薅券 ──→ available-coupons ──→ [用户确认] ──→ auto-bind-coupons
   │
   ├─(2) 盘资产 → query-my-coupons
   │              query-my-account          （重点读 currentMouthExpirePoint）
   │              query-my-prizes
   │
   ├─(3) 扫活动 → now-time-info ──→ campaign-calendar(specifiedDate)
   │
   ├─(4) 落门店 → 到店： query-nearby-stores(searchType=2, city, keyword, beType)
   │              外送： delivery-query-addresses ──→ delivery-query-stores
   │
   ├─(5) 券匹配 → query-store-coupons(storeCode, orderType, beType)
   │              query-meals(storeCode, orderType, beType)   → productCode
   │
   ├─(6) 组合试算 → calculate-price ── 方案A 券线
   │                calculate-price ── 方案B 积分线
   │                calculate-price ── 方案C 活动线
   │                     │
   │                     └─→ scripts/savings_rank.py 排序 → 省钱方案卡
   │
   └─(7) 下单   → [用户确认] ──→ create-order ──→ 支付
```

### 关键实现细节

**渠道参数传递**（最高频出错点，已在 `references/mcp-tools.md` 固化为规则表）：

| 渠道 | beType | orderType | beCode |
|---|---|---|---|
| 到店自取 | 1 | 1 | **不传**（传了报错） |
| 得来速 | 5 | 1 | 必传 |
| 麦乐送 | 2 | 2 | 必传 |
| 企业团餐 | 6 | 2 | 必传 |

**金额口径**：`calculate-price` 返回单位是**分**，展示时 ÷100。

## 4. 业务价值

### 4.1 解决了什么真实问题

麦当劳的优惠信息分散在四个互不相通的位置——麦麦省领券页、卡包、积分商城、活动页面。用户要省钱，得自己在四个页面之间来回对照，还要判断「券和活动套餐能不能叠加」。这个判断**靠猜往往出错**：套餐价通常已是折后价，与券不可叠加。

本项目把这件事变成一次确定的试算：**用麦当劳自己的价格接口，把三条路径各算一遍**，用户看到的实付数字来自真实计算，而非估算。

### 4.2 可量化的价值点

- **积分不再白白过期**：实测样例账户 `availablePoint = 0` 而 `expiredPoint = 890.4`，即积分已全部过期归零。本项目把「即将过期积分」作为高优先级资源主动提示，避免此类损失。
- **积分兑换率可视化**：以实测积分商城数据为例，50 积分可换 6.9 元商品（约 7.2 积分/元），而 800 积分换 21.9 元商品（约 36.5 积分/元），相差 5 倍。本项目按兑换率排序推荐，用户不会选到最亏的那个。
- **抽奖 ROI 决策**：实测抽奖单次消耗 24 积分，奖池含「立减 3 元券」「5 折券」「30 积分」等。本项目据此给出「积分够换明确好券就别赌」的判断口径。
- **一券不浪费**：区分「卡包券」与「门店可用券」，避免引导用户去用一张在当前门店根本用不了的券。

### 4.3 集成深度

本项目不是把 MCP 当作「查数据的接口」，而是把 MCP 的**决策链路**用作自身推理的依据：

- 用 `calculate-price` 的返回值作为方案的**唯一价格真相**，而非让模型估算；
- 用 `query-lottery-info` 的 `drawDecision.resourceEligible` 作为能否抽奖的**唯一判据**，而非自行推断；
- 用 `campaign-calendar` 的活动正文解析活动价格与适用日期，而非硬编码活动规则。

这使 Skill 的输出可验证、可复现，且随麦当劳侧规则变化自动保持正确。
