#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦麦省钱军师 —— 方案排序与对比表生成器

把多个候选方案（各含原价与实付）排序，输出 Markdown 对比表 + 省钱摘要。
纯计算工具，不依赖任何 MCP 调用，也不猜价格：金额一律来自 calculate-price 的真实返回。

用法
----
# 1) 从标准输入读取 JSON
echo '{"plans":[{"name":"A 券线","original":4200,"final":2990,"note":"9.9冰美式+免费脆薯饼"}]}' | python savings_rank.py

# 2) 从文件读取，并声明输入单位是「元」
python savings_rank.py plans.json --unit yuan

输入 JSON 结构
-------------
{
  "plans": [
    {
      "name": "A 券线",              # 必填，方案名
      "original": 4200,               # 必填，原价（默认单位：分）
      "final": 2990,                  # 必填，实付（默认单位：分）
      "note": "用了9.9冰美式券",       # 选填，备注
      "expiring_assets": ["本月将过期积分300"]  # 选填，消耗的即将过期资源
    }
  ],
  "unit": "fen"                       # 选填，可用 --unit 覆盖
}

输出：按实付升序排列的对比表；实付相同则省率高的优先。
"""

import argparse
import json
import sys


def to_yuan(value, unit):
    """把金额统一转成元（保留两位）。"""
    return round(value / 100.0, 2) if unit == "fen" else round(float(value), 2)


def fmt(value):
    return f"{value:.2f}"


def load_plans(args):
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            raise SystemExit("错误：未收到输入。请通过管道传入 JSON 或指定文件路径。")
        payload = json.loads(raw)

    if isinstance(payload, list):          # 允许直接给数组
        payload = {"plans": payload}
    plans = payload.get("plans") or []
    if not plans:
        raise SystemExit("错误：输入中没有任何方案（plans 为空）。")

    unit = args.unit or payload.get("unit") or "fen"
    if unit not in ("fen", "yuan"):
        raise SystemExit(f"错误：unit 只能是 fen 或 yuan，收到 {unit!r}")
    return plans, unit


def normalize(plans, unit):
    rows = []
    for idx, p in enumerate(plans, 1):
        if "name" not in p or "original" not in p or "final" not in p:
            raise SystemExit(f"错误：第 {idx} 个方案缺少 name/original/final 字段。")
        original = to_yuan(p["original"], unit)
        final = to_yuan(p["final"], unit)
        saved = round(original - final, 2)
        rate = round(saved / original * 100, 1) if original > 0 else 0.0
        rows.append(
            {
                "name": str(p["name"]),
                "original": original,
                "final": final,
                "saved": saved,
                "rate": rate,
                "note": str(p.get("note", "") or ""),
                "expiring": p.get("expiring_assets") or [],
            }
        )
    # 实付升序；实付相同则省率高者优先
    rows.sort(key=lambda r: (r["final"], -r["rate"]))
    return rows


def render(rows):
    lines = []
    lines.append("## 🍟 省钱方案对比")
    lines.append("")
    lines.append("| 排名 | 方案 | 原价 | 实付 | 省额 | 省率 | 备注 |")
    lines.append("|:---:|---|---:|---:|---:|---:|---|")
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, r in enumerate(rows, 1):
        rank = medals.get(i, str(i))
        lines.append(
            f"| {rank} | {r['name']} | ¥{fmt(r['original'])} | ¥{fmt(r['final'])} "
            f"| ¥{fmt(r['saved'])} | {r['rate']:.1f}% | {r['note']} |"
        )
    lines.append("")

    best = rows[0]
    worst = rows[-1] if len(rows) > 1 else None
    lines.append(f"**推荐：{best['name']}** —— 实付 ¥{fmt(best['final'])}，省 ¥{fmt(best['saved'])}"
                 f"（{best['rate']:.1f}%）。")
    if worst and worst is not best:
        gap = round(worst["final"] - best["final"], 2)
        if gap > 0:
            lines.append(f"比次优/最差方案（{worst['name']}）少花 ¥{fmt(gap)}。")

    expiring = best.get("expiring") or []
    if expiring:
        lines.append("")
        lines.append("⏳ 该方案消耗了即将过期的资源：" + "、".join(str(e) for e in expiring))

    # 无优惠空间时诚实提示
    if best["saved"] <= 0:
        lines.append("")
        lines.append("ℹ️ 本单暂无优惠空间，按原价下单即可。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="麦麦省钱方案排序器")
    parser.add_argument("file", nargs="?", help="方案 JSON 文件路径；省略则从 stdin 读取")
    parser.add_argument("--unit", choices=["fen", "yuan"], default=None,
                        help="输入金额单位，默认 fen（分）")
    args = parser.parse_args()

    plans, unit = load_plans(args)
    rows = normalize(plans, unit)
    print(render(rows))


if __name__ == "__main__":
    main()
