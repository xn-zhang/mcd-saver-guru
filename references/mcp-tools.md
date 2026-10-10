# 麦当劳 MCP 工具契约（省钱军师专用）

动手前必读。这里是参数传递规则和易错点，**不是**工具全量文档的复述。

---

## 1. 渠道参数规则表（最高频出错点）

麦当劳 MCP 里所有商品/价格/下单类工具都靠这三个参数确定「在哪个门店、走哪条链路」：

| 渠道 | beType | orderType | beCode | 门店来源 |
|---|---|---|---|---|
| 到店自取 | `1` | `1` | **不传**（传了报错） | `query-nearby-stores` (beType=1) |
| 得来速 DT | `5` | `1` | **必传** | `query-nearby-stores` (beType=5) → 返回的 `beCode` |
| 麦乐送 | `2` | `2` | **必传** | `delivery-query-addresses` → `delivery-query-stores` |
| 企业团餐 | `6` | `2` | **必传** | `delivery-query-addresses` → `delivery-query-stores` |

记忆口诀：**到店自取 beCode 是哑参数，传了会报错；其余场景 beCode 必须从对应查店接口原样带回。**

其他通用约定：
- `storeCode` 是门店唯一编码，`beCode` 与 `storeCode` 配对使用。
- 预约场景才传 `reservationDate`，格式 `yyyy-MM-dd HH:mm`；非预约**不要传**。
- 团餐场景（beType=6）在 `calculate-price` 前，若要用助餐服务需先 `query-meal-assistance` 拿 `gmServiceCode`。

---

## 2. 价格与金额口径

- `calculate-price` 返回的所有金额单位是**分**，展示时 **÷100 转元**。
- `calculate-price` 返回的 `data.takeWayList[].code` 是到店/得来速下单必传的 `takeWayCode`。
- 未调用 `calculate-price` 不得给出任何金额。

---

## 3. 省钱链路涉及的工具（按工作流顺序）

### 3.1 券
| 工具 | 入参 | 用途 | 关键注意 |
|---|---|---|---|
| `available-coupons` | 无 | 当前**可领取**的麦麦省券 | 只读，用于"有什么能领" |
| `auto-bind-coupons` | 无 | 一键领取所有可领券 | **有副作用**，需用户确认 |
| `query-my-coupons` | `page`/`pageSize` | 用户**卡包拥有**的券 | 不校验门店/渠道，**不保证可用** |
| `query-store-coupons` | `storeCode`/`orderType`/`beType`(+`beCode`) | **指定门店+渠道可用**的券 | 判断"这单能用什么券"必须用它 |
| `query-survey-coupon` | `orderId` | 按订单号查满意度问卷关联奖券 | 仅在用户给订单号时用 |

### 3.2 商品与价格
| 工具 | 入参 | 用途 |
|---|---|---|
| `query-meals` | `storeCode`/`orderType`/`beType`(+`beCode`) | 商品列表、售价、`productCode` |
| `query-meal-detail` | 上述 + `code` | 餐品组成、特调选项 `modification` |
| `calculate-price` | 上述 + `items[]` | 含券试算，返回分单位金额 + `takeWayList` |
| `create-order` | 上述 + `items[]` + `takeWayCode`/`addressId` | 真实下单 |

`items[]` 结构：`productCode`（必填）、`quantity`（≥1）、`couponId`/`couponCode`（用券时）、`modification.values[]`。

> **特调 `modification` 的 key 规则**（易错）：一组特调里，**选中的项用 `selectedKey`，未选中的项若 `unselectedKey` 非空则用 `unselectedKey`**——即含 `unselectedKey` 的特调组必须把**组内所有项**都传入。

### 3.3 积分与奖品
| 工具 | 入参 | 用途 |
|---|---|---|
| `query-my-account` | 无 | 积分账户：`availablePoint`（可用）、`currentMouthExpirePoint`（本月将过期）、`expiredPoint` |
| `mall-points-products` | `catRuleIds` | 积分商城可兑换商品（`1>4`=商品券，`2`=实物…） |
| `mall-product-detail` | `spuId` | 商品 SKU 详情，拿 `skuId`/`shopId`/`spuCategory` |
| `mall-create-order` | `skuId`/`spuCategory`(+`addressId`) | 积分兑换下单（**禁止**直接返回"兑换成功"，必须真调工具） |
| `query-lottery-info` | 无 | 抽奖活动信息 + `drawDecision` |
| `draw-lottery` | 无 | 抽奖（**必须先展示 `nextConsumption` 并获确认**） |
| `query-my-prizes` | `pageNum`/`pageSize` | 已中奖品（可用/已用/过期） |

### 3.4 活动与派对
| 工具 | 入参 | 用途 |
|---|---|---|
| `campaign-calendar` | `specifiedDate` | 营销活动日历；传日期则返回该日及最近前后各一天 |
| `mall-points-products` | `catRuleIds=1>6>xx` | 派对类：生日(20)/主题(21)/体验营(22)/品鉴会(25)/读书会(34)/积分活动(40) |
| `query-party-city` → `query-party-store` → `query-party-store-date` → `query-party-store-session` | `spuId` 逐级下钻 | 派对城市→门店→日期→场次 |
| `party-order-create` | 场次信息 + `partyType`(1包场/2拼团) | 派对下单，**仅 shopId=5** |

### 3.5 门店、地址、订单
| 工具 | 入参 | 用途 |
|---|---|---|
| `query-nearby-stores` | `searchType`(1收藏/2搜索)/`beType`(+`city`/`keyword`) | 到店/得来速门店 |
| `delivery-query-addresses` | 无 | 外送地址列表 |
| `delivery-create-address` | `city`/`contactName`/`phone`/`address`/`addressDetail`(+`gender`) | 新建地址 |
| `delivery-query-stores` | `addressId`/`beType` | 该地址可配送门店 |
| `order-list` / `query-order` / `cancel-order` | — / `orderId` / `orderId`+`cancelReasonCode` | 订单管理 |
| `mall-order-list` / `mall-order-detail` | — / `orderId` | 商城订单 |
| `now-time-info` | 无 | 服务器时间，用于活动日期锚定 |

---

## 4. 真实响应样例（实测，用于对齐字段）

### 4.1 `query-my-account`（注意：可用积分可能为 0，但累计/过期积分不为 0）
```json
{"success":true,"code":200,"data":{
  "availablePoint":"0","accumulativePoint":"890.4","currency":"麦享会积分",
  "currentMouthExpirePoint":"0","expiredPoint":"890.4","frozenPoint":"0",
  "usedPoint":"0","nextMouthExpirePoint":"0"}}
```
> 解读：**积分可能全部过期**。军师要给用户明确判断，别默认用户有积分可花。

### 4.2 `query-lottery-info`（`drawDecision` 决定能不能抽）
```json
{"activityName":"麦麦积分抽奖","activityStatusText":"进行中","drawPoint":"24",
 "drawTypeText":"消耗积分抽奖","availablePoint":"0",
 "drawDecision":{"resourceEligible":false,"reason":"积分不足",
   "nextConsumption":{"type":"POINTS","points":"24","chances":0,"text":"本次将消耗 24 积分"}},
 "prizes":[{"name":"下单立减3元券","typeText":"优惠券"},
           {"name":"麦旋风5折券","typeText":"优惠券"},
           {"name":"30积分","typeText":"积分奖"}]}
```
> 解读：单次抽奖 24 积分，奖池含减 3 元券 / 5 折券 / 30 积分。这是**抽奖 ROI 评估**的原料。

### 4.3 `available-coupons`（麦麦省可领券，实测在售示例）
`9.9元中杯冰美式`、`人气麦旋风买一送一`、`免费脆薯饼`、`薯薯任选`、`麦旋风任选`、`巧克力味厚松饼猪柳蛋套餐`
> 解读：含**免费/买一送一/9.9 元固定价**三类，价值排序见 `saving-strategy.md`。

### 4.4 `campaign-calendar`（活动条目结构）
每条活动含 `活动标题` + `活动内容介绍`（正文里通常写明**价格、日期范围、适用星期**）+ 图片。
实测示例：`9.9元早餐两件套`（10/8–10/21，周一至周五）、`49元150天麦金学期卡`、`龙焰鸡腿堡三件套 26.9 元起`。
> 解读：**活动价格要回读正文**，日历本身不返回结构化价格字段。

### 4.5 `mall-points-products`（`catRuleIds=1>4`，积分→券兑换率）
| 商品 | 所需积分 | 类目 |
|---|---|---|
| 6.9元可乐麦炫酷 | 50 | 到店专用 |
| 6.9元香芋派/菠萝派任选 | 50 | 到店专用 |
| 9.9元指定小食任选 | 100 | 到店专用 |
| 3.9元圆筒冰淇淋 | 100 | 到店专用 |
| 10.9元指定小食任选 | 200 | 到店专用 |
| 16.9元2份麦辣鸡翅 | 200 | 到店专用 |
| 21.9元巨无霸可乐组合 | 800 | 到店专用 |
> 解读：`point` 即所需积分，`price` 为额外金额（多数为 `"0"`）。**兑换率 ≈ 积分/元**，用于判断积分该换券还是抽奖。

---

## 5. 错误处理约定

- 工具返回 `success:false` 时，**把 `message` 原样或近义转述给用户**，不要吞掉，也不要自己编原因。
- 常见：`收藏餐厅列表为空，请您提供城市+关键词进行搜索` → 改用 `searchType=2` + 城市 + 关键词重试。
- 渠道参数不匹配（如到店自取误传 `beCode`）→ 严格按第 1 节规则表回退重试一次。
