# -*- coding: utf-8 -*-
"""生成《金融产品网络营销管理办法》来源证据页"""
import re
from pathlib import Path

ROOT = Path(r"C:\工作资料\笔记\制度梳理")
RAW = ROOT / "raw/08_消费者保护与销售管理/金融产品网络营销管理办法.md"
OUT = ROOT / "wiki/来源/08_消费者保护与销售管理/金融产品网络营销管理办法.md"

ARTICLE_RE = re.compile(r"(?m)^\s*(第[一二三四五六七八九十百]+条)\s*")
ACTION_WORDS = ["应当", "必须", "不得", "禁止", "可以", "负责", "承担", "建立", "制定",
                "报送", "报告", "披露", "配合", "监督", "检查", "整改", "追究", "处罚", "责令", "终止"]
SUBJECTS = ["金融机构", "第三方互联网平台", "金融管理部门", "网信部门", "电信主管部门",
            "市场监管部门", "知识产权管理部门", "非银行支付机构", "有关金融行业协会",
            "营销人员", "任何机构和个人", "金融消费者和投资者", "保险公司"]

TAGS = [
    (r"支付", "支付清算"), (r"数据|个人信息", "数据安全"), (r"处罚|责令|追究|法律责任", "行政处罚"),
    (r"投诉", "投诉处理"), (r"消费者|投资者", "消费者权益保护"), (r"商标|资质|字样", "市场准入"),
    (r"现场检查|非现场监管|监督管理", "现场检查"), (r"协议|合作", "内部控制"),
    (r"营销|宣传|广告|直播|短视频|推荐|证明", "销售行为"), (r"保险", "保险中介"),
]

TOPIC_MAP = {
    "互联网保险销售和可回溯": {"wiki/专题/互联网保险销售和可回溯", },
}


def topics_for(clause: str, body: str) -> list[str]:
    ts = ["wiki/专题/互联网保险销售和可回溯"]
    if re.search(r"消费者|投资者|权益", body):
        ts.append("wiki/专题/消费者权益保护治理")
    if re.search(r"营销人员|职业资格|资质核验|从业人员", body):
        ts.append("wiki/专题/保险中介机构准入与治理")
    if re.search(r"数据|个人信息", body):
        ts.append("wiki/专题/数据安全和监管统计")
    if re.search(r"处罚|责令|法律责任|监管措施|警示函|监管谈话", body):
        ts.append("wiki/专题/监管检查和行政处罚应对")
    if re.search(r"投诉", body):
        ts.append("wiki/专题/投诉处理和纠纷化解")
    return list(dict.fromkeys(ts))


def structured(clause: str, body: str) -> list[str]:
    flat = re.sub(r"\s+", " ", body).strip()
    subj = [s for s in SUBJECTS if s in flat][:4] or ["金融管理部门"]
    acts = [a for a in ACTION_WORDS if a in flat][:6]
    # 时限
    tl = re.findall(r"(自[^，。；]{0,20}起[^，。；]{0,12})", flat)
    if not tl:
        if "及时" in flat:
            tl = ["及时"]
        elif "持续" in flat:
            tl = ["持续跟踪评估"]
        else:
            tl = ["未明确"]
    # 禁止/后果句
    bans = [s for s in re.split(r"[。；]", flat)
            if re.search(r"不得|禁止|责令|处罚|追究|立即终止|移交", s)]
    ban = "；".join(b.strip() for b in bans[:3])
    if len(ban) > 220:
        ban = ban[:220] + "……"
    scene = flat[:70] + ("……" if len(flat) > 70 else "")
    if "：" in scene[:40]:
        scene = scene.split("：")[0] + "……"
    return [
        f"- 主体：{'、'.join(subj)}",
        f"- 动作/责任：{'、'.join(acts) if acts else '见条款'}",
        f"- 触发场景：{scene}",
        f"- 时限要求：{tl[0]}",
        f"- 禁止/后果：{ban if ban else '未明确'}",
    ]


raw_text = RAW.read_text(encoding="utf-8")
parts = ARTICLE_RE.split(raw_text)
articles: list[tuple[str, str]] = []
for i in range(1, len(parts), 2):
    body = parts[i + 1] if i + 1 < len(parts) else ""
    # 剥离章标题残留与文末表格元数据
    body = "\n".join(ln for ln in body.split("\n") if not ln.strip().startswith("## "))
    body = body.split("<table>")[0]
    articles.append((parts[i], body))

blocks: list[str] = []
used_topics: set[str] = set()
for idx, (clause, body) in enumerate(articles, start=1):
    quote = "\n".join("> " + ln.strip() for ln in body.strip().split("\n") if ln.strip())
    tags = [t for pat, t in TAGS if re.search(pat, body)] or ["销售行为"]
    tp = topics_for(clause, body)
    used_topics.update(tp)
    blocks.append(
        f"### {clause}\n\n"
        f"- 证据ID：E{idx:03d}\n"
        f"- 可引用标签：{'、'.join(dict.fromkeys(tags))}\n\n"
        f"原文依据：\n\n{quote}\n\n"
        f"结构化要素：\n\n" + "\n".join(structured(clause, body)) + "\n\n"
        f"关联专题：\n\n" + "\n".join(f"- [[{t}|{t.split('/')[-1]}]]" for t in tp) + "\n"
    )

header = f"""---
type: "来源证据页"
title: "金融产品网络营销管理办法"
rewritten: 2026-09-21
design: "IBM Carbon"
cssclasses: ["ibm-carbon-regulatory"]
category: "08_消费者保护与销售管理"
evidence_count: {len(articles)}
---

# 来源：金融产品网络营销管理办法

## 一、制度身份

- 原始资料：[[raw/08_消费者保护与销售管理/金融产品网络营销管理办法|raw/08_消费者保护与销售管理/金融产品网络营销管理办法.md]]
- 文号：中国人民银行 工业和信息化部 市场监管总局 金融监管总局 中国证监会 国家知识产权局 国家网信办 国家外汇局公告〔2026〕第9号
- 发布机关：中国人民银行、工业和信息化部、市场监管总局、金融监管总局、中国证监会、国家知识产权局、国家网信办、国家外汇局（八部门联合公布）
- 成文/公布日期：2026-04-21；施行日期：2026-09-30
- 所属分类：08_消费者保护与销售管理
- 证据定位：本页按实际条款号建立标题锚点；专题页、场景页、清单页引用时，应链接到本页的具体条款标题。
- raw 原文保持原貌；本页负责提供可跳转、可阅读、可复用的条款依据。
- 证据数量：{len(articles)} 条
- 主要标签：销售行为, 消费者权益保护, 数据安全, 市场准入, 现场检查, 内部控制, 投诉处理, 行政处罚, 保险中介
- 补录说明：2026-09-21 补录。本轮检索发现该办法为历史遗漏项（非近 7 天内发布），财险公司监管法规清单与 raw 目录均无对应条目，而其适用范围明确包含保险产品，对公众号、直播、短视频等保险网络营销形态提出持牌与授权、内容审核、可回溯要求，属财险公司直接适用的现行有效规定，故补录。

## 二、本制度能回答哪些工作问题

- 财险公司的公众号、直播、短视频营销由谁做、需具备什么资格和授权？
- 网络营销内容由谁审核、如何留存，哪些表述属于禁止性内容？
- 第三方互联网平台合作需要履行哪些事前评估、协议和持续跟踪义务？
- 保险产品在第三方平台引流时能否直接跳转、如何提示客户？
- 违反网络营销规定会触发哪些监管措施和处罚，由哪个部门实施？

## 三、条款证据

"""

footer = "\n## 四、可被哪些专题引用\n\n" + \
    "\n".join(f"- [[{t}|{t.split('/')[-1]}]]" for t in sorted(used_topics)) + "\n"

OUT.write_text(header + "\n".join(blocks) + footer, encoding="utf-8")
print("[OK] 写入", OUT)
print("条款锚点:", len(articles), "| 专题链接:", len(used_topics))
for t in sorted(used_topics):
    print("   ", t)
