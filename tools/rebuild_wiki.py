from __future__ import annotations

import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
WIKI = ROOT / "wiki"
WIKI_NEW = ROOT / "wiki_new"
TODAY = "2026-05-25"


ACTION_WORDS = [
    "应当",
    "必须",
    "不得",
    "禁止",
    "严禁",
    "可以",
    "负责",
    "承担",
    "履行",
    "建立",
    "制定",
    "报送",
    "报告",
    "披露",
    "申请",
    "核准",
    "批准",
    "备案",
    "审议",
    "决定",
    "监督",
    "检查",
    "整改",
    "追究",
    "处罚",
    "责令",
]

SANCTION_WORDS = [
    "不得",
    "禁止",
    "严禁",
    "责令",
    "监管谈话",
    "风险提示",
    "警告",
    "通报批评",
    "公开批评",
    "罚款",
    "处罚",
    "撤销",
    "取消",
    "限制",
    "暂停",
    "停止",
    "撤换",
    "追究",
    "移送",
    "刑事",
    "赔偿",
]

SUBJECT_PATTERNS = [
    "董事长",
    "董事会",
    "股东会",
    "股东大会",
    "监事会",
    "高级管理层",
    "高级管理人员",
    "总经理",
    "行长",
    "董事会秘书",
    "独立董事",
    "首席合规官",
    "合规官",
    "审计责任人",
    "内部审计部门",
    "财务负责人",
    "总精算师",
    "保险公司",
    "保险集团",
    "银行保险机构",
    "保险资产管理公司",
    "分支机构",
    "股东",
    "大股东",
    "控股股东",
    "实际控制人",
    "投保人",
    "被保险人",
    "受益人",
    "消费者",
    "监管机构",
]


TAG_RULES: list[tuple[str, list[str]]] = [
    ("董事长职责", ["董事长"]),
    ("董事会职权", ["董事会", "董事会职权", "董事会议", "董事会会议"]),
    ("股东会", ["股东会", "股东大会"]),
    ("总经理职责", ["总经理", "行长"]),
    ("高级管理层", ["高级管理层", "高级管理人员", "高管"]),
    ("监事会职责", ["监事会", "监事"]),
    ("独立董事", ["独立董事"]),
    ("董事会秘书", ["董事会秘书"]),
    ("首席合规官", ["首席合规官", "合规官", "合规负责人"]),
    ("审计责任人", ["审计责任人", "首席审计官"]),
    ("任职资格", ["任职资格", "拟任", "任命", "聘任", "免职", "辞职", "撤职", "履职评价"]),
    ("章程治理", ["章程", "公司章程"]),
    ("公司治理", ["公司治理", "治理结构", "治理机制"]),
    ("股权事务", ["股权", "股份", "股东", "大股东", "控股股东", "实际控制人"]),
    ("关联交易", ["关联交易", "关联方", "关联关系"]),
    ("信息披露", ["信息披露", "披露", "临时信息披露", "公开信息披露"]),
    ("声誉风险", ["声誉风险", "声誉事件", "舆情"]),
    ("操作风险", ["操作风险", "操作风险事件"]),
    ("合规管理", ["合规管理", "合规风险", "违法违规"]),
    ("内部审计", ["内部审计", "审计委员会", "审计报告", "离任审计", "任中审计"]),
    ("财会真实性", ["财会", "会计", "财务报告", "真实性", "完整性", "财务负责人"]),
    ("内部控制", ["内部控制", "内控"]),
    ("消费者权益保护", ["消费者权益", "消费者", "投诉", "纠纷调解"]),
    ("投诉处理", ["投诉", "信访", "纠纷"]),
    ("销售行为", ["销售", "营销宣传", "销售人员", "可回溯"]),
    ("互联网保险", ["互联网保险", "互联网销售", "线上"]),
    ("产品条款费率", ["条款", "费率", "产品", "备案", "审批"]),
    ("车险经营", ["车险", "机动车", "交强险", "报行合一"]),
    ("农业保险", ["农业保险", "生猪", "农户"]),
    ("责任保险", ["责任保险", "安全生产责任保险"]),
    ("非车险", ["非车险", "财产保险"]),
    ("分支机构准入", ["分支机构", "中心支公司", "省级分公司", "设立", "撤销"]),
    ("行政许可", ["行政许可", "申请", "核准", "批准", "许可证"]),
    ("许可证管理", ["许可证", "业务许可证"]),
    ("偿付能力", ["偿付能力", "资本充足", "实际资本", "最低资本"]),
    ("资本管理", ["资本", "资本保证金", "次级债", "资本补充"]),
    ("资金运用", ["资金运用", "投资", "股票", "基础设施", "境外投资", "资产管理产品"]),
    ("资产负债管理", ["资产负债", "资产负债管理"]),
    ("准备金", ["准备金", "责任准备金", "非寿险业务准备金"]),
    ("再保险", ["再保险"]),
    ("反洗钱", ["反洗钱", "客户尽职调查", "客户身份", "可疑交易", "反恐怖融资"]),
    ("数据安全", ["数据安全", "数据处理", "个人信息", "信息科技"]),
    ("监管统计", ["监管统计", "统计", "报表", "数据报送"]),
    ("恢复处置", ["恢复和处置", "处置计划", "风险处置", "接管", "整顿"]),
    ("突发事件", ["突发事件", "应急", "业务连续性"]),
    ("现场检查", ["现场检查", "检查"]),
    ("行政处罚", ["行政处罚", "处罚", "罚款", "裁量"]),
    ("监管评级", ["监管评级", "分类监管", "公司治理监管评估"]),
    ("市场准入", ["市场准入", "准入"]),
    ("境外外资", ["境外", "外资", "外国保险", "驻华代表机构"]),
    ("保险中介", ["保险代理", "保险经纪", "保险公估", "保险中介"]),
    ("业务范围", ["业务范围", "业务转让", "保险业务"]),
]


QUESTION_BY_TAG = {
    "董事长职责": "本制度如何规定董事长的职责、责任或权力边界？",
    "董事会职权": "哪些事项必须由董事会集体审议或承担最终责任？",
    "股权事务": "股权事项如何识别、办理、报告和追责？",
    "关联交易": "关联方和关联交易如何识别、审批、披露和问责？",
    "信息披露": "哪些事项需要披露，披露时限和责任人是什么？",
    "声誉风险": "声誉风险管理由谁负责，重大事件如何处置？",
    "操作风险": "操作风险治理、报告和整改要求是什么？",
    "合规管理": "合规管理职责、重大合规风险报告和整改机制是什么？",
    "内部审计": "内部审计体系、审计报告和整改责任如何安排？",
    "财会真实性": "财会工作、会计资料真实性和会计监督责任如何规定？",
    "消费者权益保护": "消费者权益保护应嵌入哪些治理和业务流程？",
    "投诉处理": "投诉、纠纷和重大消费者事件如何处理和报告？",
    "产品条款费率": "产品条款费率如何报批、报备、披露和管理？",
    "分支机构准入": "设立、变更或撤销分支机构需要哪些条件和材料？",
    "任职资格": "董监高任职资格、报告、审计和履职评价如何办理？",
    "行政处罚": "违反规定会触发哪些监管措施、行政处罚或责任追究？",
    "行政许可": "哪些事项需要事前审批、核准、备案或报告？",
}


TOPICS = [
    ("董事长职责监管规定汇总", ["董事长职责"], ["董事长"]),
    ("董事会职权与授权边界", ["董事会职权"], ["董事会职权", "集体行使", "一事一授", "授权"]),
    ("总经理和高级管理层职责", ["总经理职责", "高级管理层"], ["总经理", "高级管理层"]),
    ("董事会秘书职责与治理辅助机制", ["董事会秘书"], ["董事会秘书"]),
    ("独立董事履职与保障机制", ["独立董事"], ["独立董事"]),
    ("监事会监督职责", ["监事会职责"], ["监事会"]),
    ("首席合规官和合规管理职责", ["首席合规官", "合规管理"], ["首席合规官", "合规官"]),
    ("审计责任人与内部审计职责", ["审计责任人", "内部审计"], ["审计责任人", "内部审计"]),
    ("财会真实性和会计监督责任", ["财会真实性"], ["会计资料", "财会工作", "财务报告"]),
    ("股权事务与大股东行为管理", ["股权事务"], ["股权", "大股东", "控股股东"]),
    ("关联交易识别审批披露", ["关联交易"], ["关联交易", "关联方"]),
    ("重大事项和信息披露", ["信息披露"], ["重大事项", "信息披露", "临时信息披露"]),
    ("任职资格核准与履职评价", ["任职资格"], ["任职资格", "履职评价", "任命"]),
    ("公司章程治理和必载事项", ["章程治理"], ["章程", "必载"]),
    ("声誉风险管理责任", ["声誉风险"], ["声誉风险", "声誉事件"]),
    ("操作风险管理责任", ["操作风险"], ["操作风险"]),
    ("消费者权益保护治理", ["消费者权益保护"], ["消费者权益"]),
    ("投诉处理和纠纷化解", ["投诉处理"], ["投诉", "纠纷"]),
    ("反洗钱和客户尽职调查", ["反洗钱"], ["反洗钱", "客户尽职调查"]),
    ("监管检查和行政处罚应对", ["现场检查", "行政处罚"], ["现场检查", "行政处罚", "处罚"]),
    ("分支机构设立变更退出", ["分支机构准入"], ["分支机构", "设立", "撤销"]),
    ("产品条款费率报备与管理", ["产品条款费率"], ["条款", "费率"]),
    ("保险资金运用治理责任", ["资金运用"], ["资金运用", "投资"]),
    ("偿付能力和资本管理", ["偿付能力", "资本管理"], ["偿付能力", "资本"]),
    ("数据安全和监管统计", ["数据安全", "监管统计"], ["数据安全", "监管统计"]),
    ("恢复处置与突发事件应对", ["恢复处置", "突发事件"], ["恢复和处置", "突发事件"]),
    ("车险经营费用合规和报行合一", ["车险经营"], ["车险", "报行合一"]),
    ("互联网保险销售和可回溯", ["互联网保险", "销售行为"], ["互联网保险", "可回溯"]),
    ("农业保险和政策性业务", ["农业保险"], ["农业保险"]),
    ("再保险与准备金管理", ["再保险", "准备金"], ["再保险", "准备金"]),
    ("境外外资机构准入和管理", ["境外外资"], ["境外", "外资"]),
    ("许可证管理和行政许可流程", ["许可证管理", "行政许可"], ["许可证", "行政许可"]),
    ("业务范围和业务转让", ["业务范围"], ["业务范围", "业务转让"]),
    ("保险中介机构准入与治理", ["保险中介"], ["保险代理", "保险经纪", "保险公估"]),
    ("监管评级和分类监管", ["监管评级"], ["监管评级", "分类监管"]),
]


SCENARIOS = [
    ("董监高任免和履职管理流程", ["任职资格", "董事长职责", "董事会秘书"], ["选任", "申请", "核准", "任命", "报告", "履职评价", "审计"]),
    ("董事会会议和决议留痕流程", ["董事会职权", "董事会秘书"], ["提案", "通知", "审议", "表决", "会议记录", "归档"]),
    ("股权变更和股东资格审查流程", ["股权事务"], ["股东资质", "股权变更", "信息核实", "行政许可", "报告"]),
    ("关联交易审批披露流程", ["关联交易"], ["关联方识别", "审查", "回避", "董事会审议", "披露", "报告"]),
    ("重大事项临时信息披露流程", ["信息披露"], ["识别重大事项", "编制临时报告", "网站披露", "监管报告"]),
    ("分支机构设立变更退出流程", ["分支机构准入"], ["规划", "申请", "筹建", "开业", "变更", "退出"]),
    ("产品条款费率报批报备流程", ["产品条款费率"], ["开发", "审查", "报批", "备案", "使用", "披露"]),
    ("车险费用合规和报行合一检查流程", ["车险经营"], ["费用", "费率", "报行合一", "检查", "整改"]),
    ("消费者投诉处理和重大事件报告流程", ["消费者权益保护", "投诉处理"], ["受理", "处理", "统计分析", "整改", "重大事件报告"]),
    ("监管检查和行政处罚应对流程", ["现场检查", "行政处罚"], ["检查通知", "资料准备", "事实核对", "整改", "处罚应对"]),
    ("财务报告和会计监督流程", ["财会真实性"], ["会计资料", "财务报告", "内部会计监督", "审计"]),
    ("内部审计发现问题整改流程", ["内部审计", "审计责任人"], ["审计计划", "审计报告", "责任界定", "整改", "问责"]),
    ("声誉事件处置流程", ["声誉风险"], ["监测", "分级", "报告", "处置", "复盘"]),
    ("操作风险重大事件报告流程", ["操作风险"], ["识别", "评估", "报告", "整改", "审计"]),
    ("合规审查和重大合规风险报告流程", ["合规管理", "首席合规官"], ["合规审查", "重大风险报告", "董事会审定", "整改"]),
    ("反洗钱客户尽调和可疑交易流程", ["反洗钱"], ["客户尽职调查", "资料保存", "可疑交易", "报告"]),
    ("数据安全事件和监管统计报送流程", ["数据安全", "监管统计"], ["数据分类", "数据处理", "统计报送", "事件报告"]),
    ("保险资金重大投资决策流程", ["资金运用"], ["投资决策", "风险审查", "董事会", "投后管理"]),
    ("偿付能力管理和资本补充流程", ["偿付能力", "资本管理"], ["偿付能力监测", "资本补充", "报告", "整改"]),
    ("境外机构设立和外资机构管理流程", ["境外外资"], ["申请", "授权", "报告", "人员管理"]),
]


CHECKLISTS = [
    ("董事长不得事项清单", ["董事长职责"], ["不得", "禁止", "越权", "兼任", "代行", "多投"]),
    ("董事会必须审议事项清单", ["董事会职权"], ["董事会", "审议", "决定", "批准"]),
    ("需要监管报告事项清单", [], ["报告", "报送", "监管机构", "中国保监会", "银保监会", "金融监管总局"]),
    ("需要临时信息披露事项清单", ["信息披露"], ["临时信息披露", "重大事项", "披露"]),
    ("十个工作日及短时限事项清单", [], ["10 个工作日", "10日", "十日", "5 个工作日", "5日", "五日"]),
    ("董监高任职资格材料清单", ["任职资格"], ["任职资格", "申请材料", "提交"]),
    ("关联交易材料和审查清单", ["关联交易"], ["关联交易", "材料", "报告", "披露"]),
    ("股权变更材料和报告清单", ["股权事务"], ["股权", "申请材料", "报告", "披露"]),
    ("分支机构设立材料清单", ["分支机构准入"], ["分支机构", "申请材料", "设立"]),
    ("产品报批报备材料清单", ["产品条款费率"], ["条款", "费率", "报批", "备案", "材料"]),
    ("现场检查资料准备清单", ["现场检查"], ["现场检查", "资料", "检查"]),
    ("行政处罚高风险行为清单", ["行政处罚"], ["处罚", "罚款", "违法", "违规", "不得"]),
    ("消费者权益保护机制清单", ["消费者权益保护"], ["消费者权益", "机制", "审查", "披露", "投诉"]),
    ("合规审查事项清单", ["合规管理"], ["合规审查", "重大决策", "重大合规风险"]),
    ("内部审计整改清单", ["内部审计"], ["审计", "整改", "问责"]),
]


HUBS = [
    ("公司治理工作地图", ["董事长职责监管规定汇总", "董事会职权与授权边界", "总经理和高级管理层职责", "董事会秘书职责与治理辅助机制", "独立董事履职与保障机制", "监事会监督职责", "公司章程治理和必载事项"]),
    ("股权与关联交易工作地图", ["股权事务与大股东行为管理", "关联交易识别审批披露", "重大事项和信息披露"]),
    ("风险内控合规工作地图", ["首席合规官和合规管理职责", "审计责任人与内部审计职责", "财会真实性和会计监督责任", "声誉风险管理责任", "操作风险管理责任"]),
    ("信息披露与报送工作地图", ["重大事项和信息披露", "数据安全和监管统计", "监管检查和行政处罚应对"]),
    ("业务经营与产品监管工作地图", ["产品条款费率报备与管理", "车险经营费用合规和报行合一", "互联网保险销售和可回溯", "业务范围和业务转让"]),
    ("资金运用与资本管理工作地图", ["保险资金运用治理责任", "偿付能力和资本管理", "再保险与准备金管理"]),
    ("消费者保护与销售管理工作地图", ["消费者权益保护治理", "投诉处理和纠纷化解", "互联网保险销售和可回溯"]),
    ("监管检查处罚工作地图", ["监管检查和行政处罚应对", "监管评级和分类监管", "许可证管理和行政许可流程"]),
    ("机构准入和许可证工作地图", ["分支机构设立变更退出", "境外外资机构准入和管理", "保险中介机构准入与治理", "许可证管理和行政许可流程"]),
]


COMPARES = [
    ("公司法2018与2023修订对保险公司治理的影响", "中华人民共和国公司法(2018年修正)", "中华人民共和国公司法(2023修订)", ["董事长", "董事会", "法定代表人", "股东会", "监事会"]),
    ("反洗钱法新旧规则对照", "中华人民共和国反洗钱法", "中华人民共和国反洗钱法(2024修订)", ["反洗钱", "客户", "尽职调查", "报告", "处罚"]),
    ("农业保险条例新旧规则对照", "农业保险条例", "农业保险条例(2024修正)", ["农业保险", "经营", "补贴", "监督", "处罚"]),
    ("资本保证金新旧规则对照", "保险公司资本保证金管理办法(2015修订)", "保险公司资本保证金管理办法（新版）", ["资本保证金", "存款", "报告", "处罚"]),
]


@dataclass
class Evidence:
    eid: str
    source_title: str
    category: str
    source_rel: str
    source_page: str
    clause: str
    text: str
    summary: str
    subjects: list[str]
    actions: list[str]
    trigger: str
    time_limit: str
    consequence: str
    tags: list[str]


@dataclass
class SourceDoc:
    title: str
    category: str
    raw_path: Path
    raw_rel: str
    page_rel: str
    text: str
    evidence: list[Evidence] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def clean_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("javascript:void(0);", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact(text: str, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rstrip("，。；、 ")
    return cut + "……"


def first_sentence(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"[。；;]", text)
    if m and m.start() < limit:
        return text[: m.end()]
    return compact(text, limit)


ENUM_MARKER_RE = re.compile(r"([（(][一二三四五六七八九十百千万零〇0-9]+[）)])")
LIST_INTRO_WORDS = [
    "下列",
    "以下",
    "如下",
    "包括",
    "载明",
    "材料",
    "条件",
    "情形",
    "内容",
    "事项",
    "职权",
    "标准",
    "方式",
    "人员",
    "资料",
    "文件",
    "报告",
    "行为",
    "信息",
]


def looks_like_numbered_list(text: str, first_marker_start: int) -> bool:
    prefix = text[max(0, first_marker_start - 120) : first_marker_start]
    if re.search(r"第\s*$", prefix):
        return False
    return any(word in prefix for word in LIST_INTRO_WORDS)


def extract_numbered_items(text: str) -> list[tuple[str, str]]:
    normalized = re.sub(r"\s+", " ", text).strip()
    matches = list(ENUM_MARKER_RE.finditer(normalized))
    if len(matches) < 2:
        return []
    if not looks_like_numbered_list(normalized, matches[0].start()):
        return []
    items: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
        item = normalized[start:end].strip(" ；;。")
        if item:
            items.append((match.group(1), item))
    return items


def evidence_summary(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    items = extract_numbered_items(normalized)
    if len(items) >= 2:
        first_marker = ENUM_MARKER_RE.search(normalized)
        prefix = normalized[: first_marker.start()].strip() if first_marker else ""
        prefix = prefix if prefix else "列举事项"
        item_text = " ".join(f"{marker}{item}；" for marker, item in items)
        return f"{prefix} {item_text}".strip()
    return normalized


def slug_link(path: str, label: str | None = None) -> str:
    label = label or Path(path).stem
    return f"[[{path[:-3] if path.endswith('.md') else path}|{label}]]"


def page_stem(path: str) -> str:
    return path[:-3] if path.endswith(".md") else path


def clause_label(ev: Evidence) -> str:
    return f"《{ev.source_title}》{ev.clause}"


def evidence_link(ev: Evidence, label: str | None = None) -> str:
    return f"[[{page_stem(ev.source_page)}#{ev.clause}|{label or clause_label(ev)}]]"


def raw_link(doc: SourceDoc) -> str:
    return slug_link(doc.raw_rel, doc.raw_rel)


def paragraphize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def quote_lines(text: str) -> list[str]:
    lines = []
    for line in clean_text(text).splitlines():
        line = line.strip()
        lines.append(f"> {line}" if line else ">")
    return lines or [">"]


def source_reference_line(ev: Evidence) -> str:
    return f"- {evidence_link(ev)}"


def classify_evidence(ev: Evidence) -> str:
    joined = " ".join(ev.tags + ev.actions + [ev.text])
    if ev.consequence != "未明确" or any(word in ev.text for word in ["不得", "禁止", "严禁", "处罚", "公开批评", "责令", "撤销", "限制"]):
        return "禁止事项与责任后果"
    if ev.time_limit != "未明确" or any(word in joined for word in ["报告", "报送", "披露", "备案", "申请", "核准", "批准"]):
        return "程序、时限与报送"
    if any(tag in ev.tags for tag in ["任职资格", "章程治理", "公司治理", "高级管理层"]):
        return "任职定位与制度基础"
    return "职责、权限与治理要求"


def grouped_evidence(evs: list[Evidence]) -> dict[str, list[Evidence]]:
    groups: dict[str, list[Evidence]] = defaultdict(list)
    for ev in evs:
        groups[classify_evidence(ev)].append(ev)
    return groups


def detect_tags(text: str, title: str = "") -> list[str]:
    haystack = f"{title} {text}"
    tags = []
    for tag, patterns in TAG_RULES:
        if tag == "产品条款费率":
            if any(p in haystack for p in ["条款", "费率", "产品报批", "产品报备", "保险产品"]):
                tags.append(tag)
            continue
        if tag == "保险中介":
            if any(p in haystack for p in ["保险代理", "保险经纪", "保险公估", "保险中介"]):
                tags.append(tag)
            continue
        if any(p in haystack for p in patterns):
            tags.append(tag)
    return tags


def detect_subjects(text: str) -> list[str]:
    found = [s for s in SUBJECT_PATTERNS if s in text]
    return found[:6] if found else ["相关主体"]


def detect_actions(text: str) -> list[str]:
    found = [w for w in ACTION_WORDS if w in text]
    return found[:6] if found else ["见条款"]


def detect_time(text: str) -> str:
    patterns = [
        r"\d+\s*个工作日",
        r"\d+\s*工作日",
        r"\d+\s*日",
        r"[一二三四五六七八九十]+个工作日",
        r"[一二三四五六七八九十]+日",
        r"每年\s*\d+\s*月\s*\d+\s*日",
        r"每年[^，。；]{0,20}",
        r"自[^，。；]{0,30}起[^，。；]{0,30}",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0).replace(" ", "")
    return "未明确"


def detect_trigger(text: str) -> str:
    for key in ["发生", "出现", "申请", "变更", "更换", "任命", "聘任", "免职", "收到", "发现", "设立", "撤销", "报送", "披露"]:
        idx = text.find(key)
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(text), idx + 70)
            return compact(text[start:end], 90)
    return "适用本条事项时"


def detect_consequence(text: str) -> str:
    if not any(w in text for w in SANCTION_WORDS):
        return "未明确"
    for key in ["责令", "处罚", "罚款", "监管谈话", "警告", "通报批评", "公开批评", "撤销", "限制", "暂停", "追究", "移送", "不得", "禁止"]:
        idx = text.find(key)
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(text), idx + 100)
            return compact(text[start:end], 120)
    return "见禁止或责任后果表述"


WEAK_CLAUSE_PATTERNS = [
    r"^本(办法|规定|规范|细则|指引|通知|条例|法)自[^。；]{0,40}(起)?施行",
    r"^本(办法|规定|规范|细则|指引|通知|条例|法)由[^。；]{0,40}(负责)?解释",
    r"^本(办法|规定|规范|细则|指引|通知|条例|法)所称[^。；]{0,80}$",
    r"^附件[:：]",
    r"^目\s*录$",
    r"^主席[:：]",
    r"^的规定行使职权",
]


def is_weak_clause(clause: str, text: str) -> bool:
    if clause == "制度说明":
        return True
    summary = first_sentence(text, 140)
    if len(summary) < 10:
        return True
    return any(re.search(p, summary) for p in WEAK_CLAUSE_PATTERNS)


def split_articles(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"(?m)^\s*(第[一二三四五六七八九十百千万零〇0-9]+条)(?!第[一二三四五六七八九十百千万零〇0-9]+款)\s*")
    parts = pattern.split(text)
    articles: list[tuple[str, str]] = []
    if len(parts) >= 3:
        preface = clean_text(parts[0])
        if preface:
            articles.append(("制度说明", preface))
        for i in range(1, len(parts), 2):
            clause = parts[i]
            body = clean_text(parts[i + 1] if i + 1 < len(parts) else "")
            if body:
                articles.append((clause, body))
    else:
        chunks = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        for idx, chunk in enumerate(chunks, 1):
            articles.append((f"段落{idx:02d}", chunk))
    return articles


def is_operational(clause: str, text: str, title: str, article_count: int) -> bool:
    if is_weak_clause(clause, text):
        return False
    if len(extract_numbered_items(text)) >= 3:
        return True
    haystack = f"{title} {text}"
    has_action = any(w in haystack for w in ACTION_WORDS)
    has_tag = bool(detect_tags(haystack, title))
    if article_count <= 80:
        return has_action or has_tag
    return (has_action and has_tag) or any(w in haystack for w in SANCTION_WORDS)


def make_evidence(doc: SourceDoc) -> None:
    articles = split_articles(doc.text)
    selected = []
    for clause, body in articles:
        if is_operational(clause, body, doc.title, len(articles)):
            selected.append((clause, body))
    if not selected:
        selected = articles[:12]

    for idx, (clause, body) in enumerate(selected, 1):
        tags = detect_tags(body, doc.title)
        ev = Evidence(
            eid=f"E{idx:03d}",
            source_title=doc.title,
            category=doc.category,
            source_rel=doc.raw_rel,
            source_page=doc.page_rel,
            clause=clause,
            text=body,
            summary=evidence_summary(body),
            subjects=detect_subjects(body),
            actions=detect_actions(body),
            trigger=detect_trigger(body),
            time_limit=detect_time(body),
            consequence=detect_consequence(body),
            tags=tags,
        )
        doc.evidence.append(ev)
    doc.tags = sorted({tag for ev in doc.evidence for tag in ev.tags})


def frontmatter(page_type: str, title: str, extra: dict[str, str | int] | None = None) -> str:
    extra = extra or {}
    lines = ["---", f"type: {page_type}", f'title: "{title}"', f"rewritten: {TODAY}"]
    for key, value in extra.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def load_docs() -> list[SourceDoc]:
    docs: list[SourceDoc] = []
    for raw_file in sorted(RAW.rglob("*.md")):
        rel = raw_file.relative_to(ROOT).as_posix()
        category = raw_file.parent.name
        title = raw_file.stem
        page_rel = f"wiki/来源/{category}/{title}.md"
        text = clean_text(raw_file.read_text(encoding="utf-8", errors="ignore"))
        doc = SourceDoc(title=title, category=category, raw_path=raw_file, raw_rel=rel, page_rel=page_rel, text=text)
        make_evidence(doc)
        docs.append(doc)
    return docs


def source_page(doc: SourceDoc) -> str:
    questions = [QUESTION_BY_TAG[t] for t in doc.tags if t in QUESTION_BY_TAG]
    if not questions:
        questions = ["本制度中哪些条款会影响内部审批、报告、披露、留痕或责任追究？"]

    out = [
        frontmatter("来源证据页", doc.title, {"category": f'"{doc.category}"', "evidence_count": len(doc.evidence)}),
        f"# 来源：{doc.title}",
        "",
        "## 一、制度身份",
        f"- 原文位置：[[{doc.raw_rel[:-3]}|{doc.raw_rel}]]",
        f"- 所属分类：{doc.category}",
        f"- 证据定位：本页只抽取可被专题页、场景页和清单页引用的条款证据，不做跨制度综合结论。",
        f"- 证据数量：{len(doc.evidence)} 条",
        f"- 主要标签：{', '.join(doc.tags[:18]) if doc.tags else '待通过具体条款判断'}",
        "",
        "## 二、本制度能回答哪些工作问题",
    ]
    out.extend([f"- {q}" for q in questions[:10]])

    out += ["", "## 三、条款证据清单"]
    for ev in doc.evidence:
        out += [
            "",
            f"### {ev.eid}：{ev.clause}",
            f"- 原文要点：{ev.summary}",
            f"- 主体：{'、'.join(ev.subjects)}",
            f"- 动作/责任：{'、'.join(ev.actions)}",
            f"- 触发场景：{ev.trigger}",
            f"- 时限要求：{ev.time_limit}",
            f"- 禁止/后果：{ev.consequence}",
            f"- 可引用标签：{', '.join(ev.tags) if ev.tags else '综合监管证据'}",
        ]

    out += [
        "",
        "## 四、义务矩阵",
        "| 主体 | 事项 | 动作 | 时限 | 后果 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for ev in doc.evidence[:40]:
        out.append(
            f"| {'、'.join(ev.subjects[:3])} | {ev.clause}：{compact(ev.summary, 80)} | {'、'.join(ev.actions[:3])} | {ev.time_limit} | {compact(ev.consequence, 60)} |"
        )

    redlines = [ev for ev in doc.evidence if ev.consequence != "未明确" or any(w in ev.text for w in ["不得", "禁止", "严禁"])]
    out += ["", "## 五、禁止性规定和监管后果"]
    if redlines:
        for ev in redlines[:30]:
            out.append(f"- **{ev.clause}**：{compact(ev.summary, 120)}；后果/红线：{compact(ev.consequence, 100)}")
    else:
        out.append("- 本页未抽取到明确禁止性规定或监管后果，正式使用时仍应回看原文。")

    linked_topics = related_topics_for_tags(doc.tags)
    out += ["", "## 六、可被哪些专题引用"]
    if linked_topics:
        out.extend([f"- {slug_link(f'wiki/专题/{title}.md', title)}" for title in linked_topics[:12]])
    else:
        out.append("- 暂无明确专题归属，可从索引或分类页回看。")
    return "\n".join(out)


def related_topics_for_tags(tags: list[str]) -> list[str]:
    related = []
    tagset = set(tags)
    for title, topic_tags, _ in TOPICS:
        if tagset.intersection(topic_tags):
            related.append(title)
    return related


def is_weak_evidence(ev: Evidence) -> bool:
    return is_weak_clause(ev.clause, ev.text)


def has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def matches_chairman_duty(ev: Evidence) -> bool:
    haystack = f"{ev.source_title} {ev.text}"
    if "董事长" not in haystack or is_weak_evidence(ev):
        return False
    if ev.source_title in {"保险公估人监管规定", "保险中介行政许可及备案实施办法"}:
        return False
    if has_any(haystack, ["申请材料", "备案材料", "申请书应当载明", "拟任董事长", "签署的申请书", "首席代表授权书"]):
        return False

    patterns = [
        r"董事长[^。；\n]{0,100}(应当|不得|可以|负责|保证|提名|报告|支持|配合|召集|主持|签署|责令|追究|公开批评|兼任|代行)",
        r"(应当|不得|可以|负责|保证|提名|报告|支持|配合|授予|代行|兼任|公开批评|责令|追究)[^。；\n]{0,100}董事长",
        r"董事会[^。；\n]{0,120}(不得|原则上不得|谨慎)[^。；\n]{0,80}董事长",
        r"向董事会、董事长[^。；\n]{0,80}(报告|报送)",
    ]
    return any(re.search(p, haystack) for p in patterns)


def matches_board_authority(ev: Evidence) -> bool:
    haystack = f"{ev.source_title} {ev.text}"
    return "董事会" in haystack and has_any(haystack, ["职权", "授权", "审议", "决议", "集体", "不得授予", "议事规则"])


def matches_disclosure(ev: Evidence) -> bool:
    haystack = f"{ev.source_title} {ev.text}"
    return has_any(haystack, ["信息披露", "披露", "临时信息披露", "重大事项"]) and has_any(haystack, ["应当", "报告", "公告", "网站", "时限"])


def matches_board_secretary_duty(ev: Evidence) -> bool:
    haystack = f"{ev.source_title} {ev.text}"
    return "董事会秘书" in haystack or "董事会秘书" in ev.tags


def topic_specific_match(title: str, ev: Evidence) -> bool:
    if title == "董事长职责监管规定汇总":
        return matches_chairman_duty(ev)
    if title == "董事会职权与授权边界":
        return matches_board_authority(ev)
    if title == "董事会秘书职责与治理辅助机制":
        return matches_board_secretary_duty(ev)
    if title == "重大事项和信息披露":
        return matches_disclosure(ev)
    return True


def evidence_matches(ev: Evidence, tags: list[str], keywords: list[str]) -> bool:
    return bool(set(ev.tags).intersection(tags)) or any(k in ev.text or k in ev.source_title for k in keywords)


def collect_evidence(
    all_evidence: list[Evidence],
    tags: list[str],
    keywords: list[str],
    limit: int = 80,
    topic_title: str | None = None,
) -> list[Evidence]:
    scored = []
    for ev in all_evidence:
        if is_weak_evidence(ev):
            continue
        if topic_title and not topic_specific_match(topic_title, ev):
            continue
        if evidence_matches(ev, tags, keywords):
            score = 0
            score += 4 * len(set(ev.tags).intersection(tags))
            score += sum(1 for k in keywords if k in ev.text or k in ev.source_title)
            score += 4 if any(k in ev.summary for k in keywords) else 0
            if topic_title == "董事长职责监管规定汇总":
                score += 6 if has_any(ev.text, ["第一责任人", "牵头负责", "保证", "不得越权", "代行董事会", "无权多投一票"]) else 0
                score += 3 if has_any(ev.text, ["召集", "主持", "提名", "换届", "支持和配合", "不得兼任"]) else 0
            score += 2 if ev.consequence != "未明确" else 0
            scored.append((score, ev))
    scored.sort(key=lambda x: (-x[0], x[1].category, x[1].source_title, x[1].eid))
    return [ev for _, ev in scored[:limit]]


def evidence_table(evs: list[Evidence], limit: int = 30) -> list[str]:
    lines = ["| 来源 | 条款 | 证据要点 | 主体/动作/时限 |", "| --- | --- | --- | --- |"]
    for ev in evs[:limit]:
        lines.append(
            f"| {slug_link(ev.source_page, ev.source_title)} | {ev.clause} | {compact(ev.summary, 90)} | {'、'.join(ev.subjects[:2])}；{'、'.join(ev.actions[:3])}；{ev.time_limit} |"
        )
    return lines


def topic_page(title: str, tags: list[str], keywords: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, keywords, 90, title)
    redlines = [ev for ev in evs if ev.consequence != "未明确" or any(w in ev.text for w in ["不得", "禁止", "严禁"])]
    source_count = len({ev.source_title for ev in evs})
    out = [
        frontmatter("专题页", title, {"evidence_count": len(evs), "source_count": source_count}),
        f"# {title}",
        "",
        "## 一、工作问题",
        f"本页用于回答“{title}”相关事项在不同监管规定中的职责、流程、时限、禁止事项和责任后果。使用时先看本页形成判断，再回到来源证据页核对条款。",
        "",
        "## 二、监管结论",
    ]
    if "董事长职责" in tags:
        out += [
            "- 董事长首先是董事会运行和公司治理机制的组织者，不是替代董事会集体决策的个人决策中心。",
            "- 对股权事务、声誉风险、财会真实性、发展规划、合规报告、独立董事保障、内部审计等事项，监管会在专项制度中压实董事长责任。",
            "- 董事长权力边界同样清晰：不得代行董事会法定职权，不得取得额外表决权，不得越权干预经营管理，不得兼任特定职务。",
        ]
    elif "董事会职权" in tags:
        out += [
            "- 凡涉及战略、重大风险、重大交易、资本、财务报告、信息披露、重要人事和内控审计等事项，通常应回到董事会集体审议和留痕。",
            "- 董事会法定职权原则上不得笼统或永久授权给董事长、董事、管理层或其他个人机构。",
        ]
    elif "信息披露" in tags:
        out += [
            "- 信息披露的核心不是发布动作，而是识别重大事项、形成审核流程、按时披露并保留责任链条。",
            "- 董事长、总经理、董事会秘书、董事会等主体在不同制度中分别承担触发、组织、审议和最终责任。",
        ]
    else:
        out += [
            "- 监管要求应拆成主体、事项、动作、时限和后果，不能只停留在制度名称或抽象概念。",
            "- 同一工作问题通常散落在准入、治理、披露、风控、处罚等多个制度中，应以跨制度证据共同判断。",
        ]
    out += [
        "",
        "## 三、跨制度证据地图",
        *evidence_table(evs, 35),
        "",
        "## 四、主体—事项—动作清单",
        "| 主体 | 事项 | 监管动作 | 时限 | 依据 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for ev in evs[:35]:
        out.append(
            f"| {'、'.join(ev.subjects[:3])} | {compact(ev.summary, 70)} | {'、'.join(ev.actions[:4])} | {ev.time_limit} | {slug_link(ev.source_page, ev.source_title)} {ev.clause} |"
        )
    out += ["", "## 五、禁止事项和责任后果"]
    if redlines:
        for ev in redlines[:25]:
            out.append(f"- {slug_link(ev.source_page, ev.source_title)} **{ev.clause}**：{compact(ev.summary, 110)}；{compact(ev.consequence, 90)}")
    else:
        out.append("- 本专题未聚合到明确禁止或处罚条款，具体办理时仍需回看对应来源页。")
    out += [
        "",
        "## 六、内部落地建议",
        "- 把本专题中的主体、动作和时限落入公司制度、流程、会议议事规则、报告模板或检查表。",
        "- 对涉及报告、披露、审批、审议、整改、问责的事项，必须保留事实依据、过程记录、决策记录和后续跟踪记录。",
        "- 引用本页时，应至少回看一个来源证据页，确认条款编号、适用主体和触发条件。",
        "",
        "## 七、相关来源",
    ]
    for source in sorted({(ev.source_page, ev.source_title) for ev in evs})[:30]:
        out.append(f"- {slug_link(source[0], source[1])}")
    return "\n".join(out)


def topic_core_name(title: str) -> str:
    core = title
    for suffix in [
        "监管规定汇总",
        "职责与治理辅助机制",
        "职权与授权边界",
        "职责",
        "责任",
        "治理",
        "流程",
        "管理",
    ]:
        core = core.replace(suffix, "")
    return core.strip("与和、 ")


def topic_intro_paragraphs(title: str, tags: list[str], source_count: int, evs: list[Evidence]) -> list[str]:
    tag_text = "、".join(tags) if tags else topic_core_name(title)
    base = [
        f"本专题把散落在 {source_count} 个制度或文件中的相关规定合并阅读，目的不是复述单个条文，而是回答“{title}”在实际工作中应当如何理解、如何分工、如何留痕。监管规则通常不会只用一个条款完成这类问题的规定，而是通过主体定位、权限边界、程序要求、报告披露和责任后果共同构成约束体系。",
    ]

    if "董事长职责" in tags:
        base += [
            "从整体监管口径看，董事长首先是董事会运行和公司治理机制的组织者、召集者和责任压实对象，不应被理解为可以替代董事会集体决策的个人决策中心。凡涉及战略、资本、重大风险、重要交易、信息披露、内控审计和治理报告等事项，监管制度更强调董事长应当推动董事会依法履职、保证程序完整，而不是将董事会职权个人化。",
        ]
    elif "董事会秘书" in tags:
        base += [
            "董事会秘书的监管定位，应当理解为董事会治理运行的制度接口。一方面，其承接股东会、董事会会议筹备、文件保管、股东和董事资料管理等治理基础工作；另一方面，其承担信息披露、监管报送、治理协调和董事履职支持等连接外部监管与内部治理的职责。",
            "因此，董事会秘书并不是单纯的文书岗位。保险公司和银行保险机构相关规则通常将其纳入高级管理人员或重要治理岗位的管理逻辑，要求其具备公司治理、法律合规、信息披露和监管沟通能力，并通过任职资格、培训、工作保障和责任追究来维持履职质量。",
        ]
    elif "董事会职权" in tags:
        base += [
            "董事会职权的核心，是把公司重大经营管理事项放回集体审议、集体表决和集体留痕的治理框架内。监管并不只关心董事会“能不能决定”，更关心哪些事项必须由董事会审议、授权边界是否清楚、会议材料是否充分、表决过程是否可追溯。",
        ]
    elif "信息披露" in tags:
        base += [
            "信息披露不是单一发布动作，而是一套贯穿重大事项识别、内部审核、董事会责任、承办部门协同、对外披露和监管报告的流程。跨制度规定合并后可以看到，监管关注的是信息是否真实、准确、完整、及时，以及责任链条是否能够追溯到具体机构和人员。",
        ]
    elif "关联交易" in tags:
        base += [
            "关联交易治理的关键，不在于事后把交易归类，而在于事前识别关联方、明确审查层级、执行回避和表决程序，并在必要时完成报告或披露。跨制度规则共同指向一个要求：交易本身、决策过程和利益冲突控制都要能够被监管和内部审计复核。",
        ]
    elif "股权事务" in tags:
        base += [
            "股权事务的监管重点，是通过股东资质、资金来源、持股行为、重大变更、信息报告和责任约束，防止股东利用股权影响公司治理或风险控制。实务上应把股权变化、股东行为和公司治理后果放在同一条证据链中管理。",
        ]
    else:
        base += [
            f"围绕“{tag_text}”，专题页应当承担解释和组织功能：先把制度要求转换为统一的工作语言，再把具体条款作为依据放在相应段落之后。这样既能保留可追溯性，也能避免正文变成来源页或概念页的重复。",
        ]
    return base


def section_theme(section: str) -> str:
    if "任职定位" in section:
        return "制度定位"
    if "职责" in section or "权限" in section:
        return "职责和权限"
    if "程序" in section or "时限" in section:
        return "程序和时限"
    if "禁止" in section or "责任" in section:
        return "风险和责任"
    return section


def evidence_features(evs: list[Evidence]) -> tuple[str, str, str, str]:
    subjects = []
    actions = []
    times = []
    consequences = []
    for ev in evs:
        subjects.extend([s for s in ev.subjects if s and s != "未明确"])
        actions.extend([a for a in ev.actions if a])
        if ev.time_limit and ev.time_limit != "未明确":
            times.append(ev.time_limit)
        if ev.consequence and ev.consequence != "未明确":
            consequences.append(ev.consequence)

    def top(values: list[str], limit: int = 5) -> str:
        if not values:
            return "相关主体"
        counts = Counter(values)
        return "、".join([value for value, _ in counts.most_common(limit)])

    return top(subjects), top(actions), top(times, 4), top(consequences, 4)


def references_block(evs: list[Evidence], limit: int = 10) -> list[str]:
    if not evs:
        return ["依据：暂无可引用条款证据。"]
    refs = [source_reference_line(ev).removeprefix("- ") for ev in evs[:limit]]
    return ["依据：" + "；".join(refs)]


def section_narrative(title: str, tags: list[str], section: str, evs: list[Evidence]) -> list[str]:
    if not evs:
        return []
    subject_text, action_text, time_text, consequence_text = evidence_features(evs)
    theme = section_theme(section)
    core = topic_core_name(title)

    if theme == "制度定位":
        paragraph = (
            f"在制度定位层面，{core or title}首先要被放入公司治理和监管责任体系中理解。"
            f"相关条款共同说明，监管关注的不是抽象身份，而是{subject_text}等主体在特定治理事项中的角色边界。"
            f"因此，实务中应先判断本专题事项适用于哪些机构、人员和业务场景，再决定后续由谁发起、谁审议、谁报告以及谁承担最终责任。"
        )
    elif theme == "职责和权限":
        paragraph = (
            f"在职责和权限层面，监管要求通常表现为{action_text}等动作，但这些动作不能孤立理解。"
            f"它们共同构成一套履职链条：前端要识别事项和责任主体，中端要完成审议、批准、协助或管理动作，后端要保留能够证明履职过程的材料。"
            f"对于{core or title}，重点是把“谁有权决定”和“谁负责组织执行”区分清楚，避免把集体治理事项简化为单个岗位的事务性处理。"
        )
    elif theme == "程序和时限":
        time_sentence = f"相关证据中出现的时限或频率要求主要包括{time_text}。" if time_text != "相关主体" else "如果具体制度没有给出统一时限，仍应按照事项性质、会议规则、监管报送规则和内部制度确定可追溯的办理节点。"
        paragraph = (
            f"在程序和时限层面，本专题的监管要求应转换为可执行流程。"
            f"实务上需要把触发条件、材料准备、会议或审批路径、报告披露、归档留痕串成闭环，不能只记录最终结论。"
            f"{time_sentence}"
        )
    else:
        consequence_sentence = "相关风险通常体现为监管问责、责令整改、公开批评、处罚、任职限制或内部责任追究等；具体后果以段落后的条款依据为准。"
        paragraph = (
            f"在风险和责任层面，监管更关注职责是否被实质履行。"
            f"如果主体边界不清、授权不明、报告披露不及时或会议材料不足，即使事项本身已经推进，也可能形成治理程序风险。"
            f"{consequence_sentence}"
        )

    return [paragraph, *references_block(evs)]


def topic_practice_paragraphs(title: str, tags: list[str], evs: list[Evidence]) -> list[str]:
    core = topic_core_name(title) or title
    return [
        f"使用本专题时，可以把“{core}”拆成四个检查动作：先确认适用主体和触发场景，再确认审议、批准、报告或披露路径，随后检查时限和材料留痕，最后核对是否存在禁止性要求或责任后果。",
        "正式写入内部制度、会议材料、报告文本或检查底稿时，不宜直接复制本页的归纳结论作为唯一依据。应点击段落后的条款链接，回到来源证据页核对原文、条款号、适用对象和触发条件；必要时再回看 raw 原始资料。",
        "如果后续新增监管文件改变了主体、时限、审批层级、报送对象或责任后果，应优先更新来源证据页，再同步重写本专题的相关段落，而不是只在依据清单中追加一条链接。",
    ]


def topic_page(title: str, tags: list[str], keywords: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, keywords, 70, title)
    source_count = len({ev.source_title for ev in evs})
    groups = grouped_evidence(evs)
    out = [
        frontmatter("专题页", title, {"evidence_count": len(evs), "source_count": source_count, "style": '"article"'}),
        f"# {title}",
        "",
        "## 一、监管结论",
        *topic_intro_paragraphs(title, tags, source_count, evs),
        "",
        "## 二、适用边界",
        f"本页聚合的监管标签为：{'、'.join(tags) if tags else '综合监管事项'}。它适用于需要从多个制度中同时判断主体职责、权限边界、办理流程、报告披露、留痕材料和责任后果的工作场景。",
        "",
        "本页的正文是跨制度归纳，不替代监管原文。依据定位仍使用制度自身的条款号；点击条款链接，会跳转到来源证据页的对应条款标题，来源页再保留 raw 原始资料位置。",
        "",
        "## 三、监管要求的系统梳理",
    ]

    ordered_sections = ["任职定位与制度基础", "职责、权限与治理要求", "程序、时限与报送", "禁止事项与责任后果"]
    for section in ordered_sections:
        section_evs = groups.get(section, [])
        if not section_evs:
            continue
        out += ["", f"### {section}"]
        out.extend(section_narrative(title, tags, section, section_evs[:18]))

    out += [
        "",
        "## 四、实务落地口径",
        *topic_practice_paragraphs(title, tags, evs),
        "",
        "## 五、主要依据",
    ]
    for ev in evs:
        out.append(source_reference_line(ev))
    return "\n".join(out)


def scenario_page(title: str, tags: list[str], steps: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, steps, 60)
    out = [
        frontmatter("场景页", title, {"evidence_count": len(evs)}),
        f"# {title}",
        "",
        "## 一、适用场景",
        f"当实际工作进入“{title.replace('流程', '')}”时使用本页。本页按办理动作组织证据，帮助确认谁负责、走什么程序、何时报告披露、怎样留痕。",
        "",
        "## 二、办理路径",
    ]
    for idx, step in enumerate(steps, 1):
        out.append(f"{idx}. {step}：确认适用主体、触发条件、责任部门、审批层级和留痕材料。")
    out += [
        "",
        "## 三、关键证据",
        *evidence_table(evs, 25),
        "",
        "## 四、材料和留痕",
        "- 事实材料：业务背景、触发原因、涉及主体、金额或影响范围。",
        "- 程序材料：申请、报告、审批、会议通知、会议材料、表决记录、披露稿。",
        "- 风控材料：合规审查意见、法律意见、风险评估、审计意见、整改台账。",
        "- 报送材料：监管报告、系统填报记录、网站披露截图或公告留档。",
        "",
        "## 五、风险提示",
        "- 先确认是否触发监管报告或公开披露，再推进内部审批。",
        "- 涉及董事会、专门委员会、独立董事、合规、审计、财务等多个主体时，应分别留痕，不能只保留最终结论。",
        "- 如果来源证据页显示存在处罚、撤换、监管谈话或公开批评后果，应前置法务和合规复核。",
        "",
        "## 六、关联专题",
    ]
    related = related_topics_for_tags(tags)
    if related:
        out.extend([f"- {slug_link(f'wiki/专题/{t}.md', t)}" for t in related[:8]])
    else:
        out.append("- 暂无直接关联专题。")
    return "\n".join(out)


def checklist_page(title: str, tags: list[str], keywords: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, keywords, 70)
    out = [
        frontmatter("清单页", title, {"evidence_count": len(evs)}),
        f"# {title}",
        "",
        "## 一、使用场景",
        f"本清单用于快速核对“{title}”涉及的红线、材料、时限、报告、披露或责任后果。清单只做工作提示，正式判断应回看证据页和原文。",
        "",
        "## 二、检查清单",
    ]
    if evs:
        for ev in evs[:40]:
            text = compact(ev.summary, 120)
            out.append(f"- [ ] {text}（依据：{slug_link(ev.source_page, ev.source_title)} {ev.clause}；时限：{ev.time_limit}；后果：{compact(ev.consequence, 60)}）")
    else:
        out.append("- [ ] 暂未聚合到明确条款，需回看相关来源页。")
    out += [
        "",
        "## 三、证据依据",
        *evidence_table(evs, 25),
    ]
    return "\n".join(out)


def concept_page(tag: str, evs: list[Evidence]) -> str:
    related = related_topics_for_tags([tag])
    out = [
        frontmatter("概念页", tag, {"evidence_count": len(evs)}),
        f"# {tag}",
        "",
        "## 定位",
        f"“{tag}”在本库中是工作标签，不是结论页。使用时应优先进入相关专题或场景，再回到来源证据页核对条款。",
        "",
        "## 相关专题",
    ]
    if related:
        out.extend([f"- {slug_link(f'wiki/专题/{t}.md', t)}" for t in related])
    else:
        out.append("- 暂无专题页。")
    out += [
        "",
        "## 代表证据",
        *evidence_table(evs, 12),
    ]
    return "\n".join(out)


def hub_page(title: str, topics: list[str]) -> str:
    out = [
        frontmatter("枢纽页", title),
        f"# {title}",
        "",
        "## 使用方式",
        "本页是工作地图，不是制度摘要。先从问题进入专题页，再按专题页回看来源证据和原文。",
        "",
        "## 核心专题",
    ]
    out.extend([f"- {slug_link(f'wiki/专题/{t}.md', t)}" for t in topics])
    out += ["", "## 常用场景"]
    for scenario, tags, _ in SCENARIOS:
        related = related_topics_for_tags(tags)
        if set(related).intersection(topics):
            out.append(f"- {slug_link(f'wiki/场景/{scenario}.md', scenario)}")
    out += ["", "## 常用清单"]
    for checklist, tags, _ in CHECKLISTS:
        related = related_topics_for_tags(tags)
        if set(related).intersection(topics):
            out.append(f"- {slug_link(f'wiki/清单/{checklist}.md', checklist)}")
    return "\n".join(out)


def compare_page(title: str, old_title: str, new_title: str, keywords: list[str], by_title: dict[str, SourceDoc]) -> str:
    old_doc = by_title.get(old_title)
    new_doc = by_title.get(new_title)
    old_evs = [ev for ev in old_doc.evidence if any(k in ev.text for k in keywords)] if old_doc else []
    new_evs = [ev for ev in new_doc.evidence if any(k in ev.text for k in keywords)] if new_doc else []
    out = [
        frontmatter("对照页", title, {"old": f'"{old_title}"', "new": f'"{new_title}"'}),
        f"# {title}",
        "",
        "## 对照口径",
        "本页按工作关键词抽取新旧制度中的相关证据，用于提示变化方向；正式判断仍应回到来源页和原文逐条核对。",
        "",
        "## 旧规证据",
        *evidence_table(old_evs, 18),
        "",
        "## 新规证据",
        *evidence_table(new_evs, 18),
        "",
        "## 使用提示",
        "- 先看新规证据中是否新增主体、时限、报告、披露或处罚要求。",
        "- 如果新旧口径不一致，优先核对施行时间、修订说明和上位法效力。",
    ]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# v2 wiki rendering rules
#
# The earlier helpers keep the extraction logic intact. The definitions below
# intentionally override the first-pass page renderers so the wiki layer reads
# like a work memo: narrative first, actual article-number anchors as evidence,
# and tables only where they improve a checklist or index.


def evidence_table(evs: list[Evidence], limit: int = 30) -> list[str]:
    lines: list[str] = []
    if not evs:
        return ["- 暂无可引用条款证据。"]
    for ev in evs[:limit]:
        lines.append(f"- {evidence_link(ev)}：{topic_statement(ev)}")
    return lines


def topic_statement(ev: Evidence) -> str:
    lines = topic_statement_lines(ev)
    if len(lines) == 1:
        return lines[0]
    return lines[0] + " " + " ".join(line.strip("- ") for line in lines[1:])


def topic_statement_lines(ev: Evidence) -> list[str]:
    normalized = re.sub(r"\s+", " ", ev.text).strip()
    items = extract_numbered_items(normalized)
    first_marker = ENUM_MARKER_RE.search(normalized)
    prefix = normalized[: first_marker.start()].strip() if first_marker else ""
    if len(items) >= 2 and any(word in prefix for word in ["职责", "职权", "事项", "内容", "材料", "条件", "情形", "行为", "应当披露"]):
        lines = [prefix if prefix else "列举事项："]
        lines.extend([f"- {marker}{item}" for marker, item in items])
        return lines
    if len(items) >= 2:
        tagged_items = [
            (marker, item)
            for marker, item in items
            if any(tag in item for tag in ev.tags) or any(subject in item for subject in ev.subjects)
        ]
        if tagged_items:
            lines = [prefix if prefix else "相关列举事项："]
            lines.extend([f"- {marker}{item}" for marker, item in tagged_items])
            return lines

    m = re.search(r"[。；;]", normalized)
    if m:
        return [normalized[: m.end()].strip()]
    return [normalized]


def source_page(doc: SourceDoc) -> str:
    questions = [QUESTION_BY_TAG[t] for t in doc.tags if t in QUESTION_BY_TAG]
    if not questions:
        questions = ["本制度中哪些条款会影响内部审批、报告、披露、留痕或责任追究？"]

    out = [
        frontmatter("来源证据页", doc.title, {"category": f'"{doc.category}"', "evidence_count": len(doc.evidence)}),
        f"# 来源：{doc.title}",
        "",
        "## 一、制度身份",
        f"- 原始资料：{raw_link(doc)}",
        f"- 所属分类：{doc.category}",
        "- 证据定位：本页按实际条款号建立标题锚点；专题页、场景页、清单页引用时，应链接到本页的具体条款标题。",
        "- raw 原文保持原貌；本页负责提供可跳转、可阅读、可复用的条款依据。",
        f"- 证据数量：{len(doc.evidence)} 条",
        f"- 主要标签：{', '.join(doc.tags[:18]) if doc.tags else '待通过具体条款判断'}",
        "",
        "## 二、本制度能回答哪些工作问题",
    ]
    out.extend([f"- {q}" for q in questions[:10]])

    out += ["", "## 三、条款证据"]
    for ev in doc.evidence:
        related_topics = related_topics_for_tags(ev.tags)
        out += [
            "",
            f"### {ev.clause}",
            "",
            f"- 证据ID：{ev.eid}",
            f"- 可引用标签：{', '.join(ev.tags) if ev.tags else '综合监管证据'}",
            "",
            "原文依据：",
            *quote_lines(ev.text),
            "",
            "结构化要素：",
            f"- 主体：{'、'.join(ev.subjects)}",
            f"- 动作/责任：{'、'.join(ev.actions)}",
            f"- 触发场景：{ev.trigger}",
            f"- 时限要求：{ev.time_limit}",
            f"- 禁止/后果：{ev.consequence}",
            "",
            "关联专题：",
        ]
        if related_topics:
            out.extend([f"- {slug_link(f'wiki/专题/{topic}.md', topic)}" for topic in related_topics[:8]])
        else:
            out.append("- 暂无直接关联专题。")

    linked_topics = related_topics_for_tags(doc.tags)
    out += ["", "## 四、可被哪些专题引用"]
    if linked_topics:
        out.extend([f"- {slug_link(f'wiki/专题/{title}.md', title)}" for title in linked_topics[:12]])
    else:
        out.append("- 暂无明确专题归属，可从索引或分类页回看。")
    return "\n".join(out)


def topic_page(title: str, tags: list[str], keywords: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, keywords, 70, title)
    source_count = len({ev.source_title for ev in evs})
    groups = grouped_evidence(evs)
    out = [
        frontmatter("专题页", title, {"evidence_count": len(evs), "source_count": source_count}),
        f"# {title}",
        "",
        "## 一、监管结论",
    ]

    if "董事长职责" in tags:
        out += [
            "董事长首先是董事会运行和公司治理机制的组织者，不是替代董事会集体决策的个人决策中心。",
            "",
            "跨制度看，监管规则会在股权事务、公司治理报告、独立董事保障、声誉风险、财会真实性、发展规划、合规报告、内部审计等事项中压实董事长责任；同时也明确董事长不得代行董事会法定职权、不得取得额外表决权、不得越权干预经营管理。",
        ]
    elif "董事会秘书" in tags:
        out += [
            "董事会秘书不是单纯的会议记录或文书岗位，而是董事会治理运行、信息披露、股权事务、监管报送和治理协调的关键责任人。",
            "",
            "在保险公司、银行保险机构语境下，董事会秘书通常被纳入高级管理人员管理，并受任职资格、培训、履职支持和监管责任约束。",
        ]
    elif "董事会职权" in tags:
        out += [
            "凡涉及战略、重大风险、重大交易、资本、财务报告、信息披露、重要人事和内控审计等事项，通常应回到董事会集体审议和留痕。",
            "",
            "董事会法定职权原则上不得笼统或永久授权给董事长、董事、管理层或其他个人机构；确需授权的，应一事一授权并保留决策边界。",
        ]
    elif "信息披露" in tags:
        out += [
            "信息披露的核心不是发布动作，而是识别重大事项、形成审核流程、按时披露并保留责任链条。",
            "",
            "不同制度分别规定董事会、董事会秘书、经营管理层和具体承办部门的职责，应按事项性质确定触发、组织、审议、披露和报告责任。",
        ]
    else:
        out += [
            "本专题按真实工作问题汇总跨制度规定。使用时先看本页形成工作判断，再点击条款依据回到来源证据页核对原文。",
            "",
            "监管要求应拆成主体、事项、动作、程序、时限和后果；同一事项散落在多个制度中时，应以跨制度证据共同判断。",
        ]

    out += [
        "",
        "## 二、适用边界",
        f"- 本页聚合标签：{', '.join(tags) if tags else '综合监管事项'}",
        f"- 涉及来源：{source_count} 个制度或文件。",
        "- 本页依据定位使用实际条款号；点击条款号跳转至对应来源证据页的条款标题。",
        "- source 页展示原文依据并链接 raw 原始资料；raw 层保持原貌。",
        "",
        "## 三、跨制度监管要求",
    ]

    ordered_sections = ["任职定位与制度基础", "职责、权限与治理要求", "程序、时限与报送", "禁止事项与责任后果"]
    for section in ordered_sections:
        section_evs = groups.get(section, [])
        if not section_evs:
            continue
        out += ["", f"### {section}"]
        for idx, ev in enumerate(section_evs[:18], 1):
            statement_lines = topic_statement_lines(ev)
            out += ["", f"**{idx}. {statement_lines[0]}**"]
            if len(statement_lines) > 1:
                out.extend(statement_lines[1:])
            out += ["", "依据：", source_reference_line(ev)]

    out += [
        "",
        "## 四、实务落地口径",
        "- 将本专题中的主体、动作、时限和后果落入公司制度、流程、会议议事规则、报告模板或检查清单。",
        "- 涉及报告、披露、审批、审议、整改、问责的事项，应保留事实依据、过程记录、决策记录和后续跟踪记录。",
        "- 正式引用时，应点击条款依据进入来源证据页，核对条款号、适用主体和触发条件。",
        "",
        "## 五、主要依据",
    ]
    for ev in evs:
        out.append(source_reference_line(ev))
    return "\n".join(out)


def scenario_page(title: str, tags: list[str], steps: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, steps, 60)
    out = [
        frontmatter("场景页", title, {"evidence_count": len(evs)}),
        f"# {title}",
        "",
        "## 一、适用场景",
        f"当实际工作进入“{title.replace('流程', '')}”时使用本页。本页按办理动作组织证据，帮助确认谁负责、走什么程序、何时报送披露、怎样留痕。",
        "",
        "## 二、办理路径",
    ]
    for idx, step in enumerate(steps, 1):
        out.append(f"{idx}. {step}：确认适用主体、触发条件、责任部门、审批层级和留痕材料。")
    out += [
        "",
        "## 三、关键条款依据",
        *evidence_table(evs, 30),
        "",
        "## 四、材料和留痕",
        "- 事实材料：业务背景、触发原因、涉及主体、金额或影响范围。",
        "- 程序材料：申请、报告、审批、会议通知、会议材料、表决记录、披露稿。",
        "- 风控材料：合规审查意见、法律意见、风险评估、审计意见、整改台账。",
        "- 报送材料：监管报告、系统填报记录、网站披露截图或公告留档。",
        "",
        "## 五、风险提示",
        "- 先确认是否触发监管报告或公开披露，再推进内部审批。",
        "- 涉及董事会、专门委员会、独立董事、合规、审计、财务等多个主体时，应分别留痕，不能只保留最终结论。",
        "- 如来源证据页显示存在处罚、撤换、监管谈话或公开批评后果，应前置法务和合规复核。",
        "",
        "## 六、关联专题",
    ]
    related = related_topics_for_tags(tags)
    if related:
        out.extend([f"- {slug_link(f'wiki/专题/{t}.md', t)}" for t in related[:8]])
    else:
        out.append("- 暂无直接关联专题。")
    return "\n".join(out)


def checklist_page(title: str, tags: list[str], keywords: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, keywords, 70)
    out = [
        frontmatter("清单页", title, {"evidence_count": len(evs)}),
        f"# {title}",
        "",
        "## 一、使用场景",
        f"本清单用于快速核对“{title}”涉及的红线、材料、时限、报告、披露或责任后果。清单只做工作提示，正式判断应回看来源证据页和 raw 原文。",
        "",
        "## 二、检查清单",
    ]
    if evs:
        for ev in evs[:40]:
            out.append(f"- [ ] {topic_statement(ev)}（依据：{evidence_link(ev)}；时限：{ev.time_limit}；后果：{ev.consequence}）")
    else:
        out.append("- [ ] 暂未聚合到明确条款，需回看相关来源页。")
    out += [
        "",
        "## 三、条款依据",
        *evidence_table(evs, 25),
    ]
    return "\n".join(out)


def topic_page(title: str, tags: list[str], keywords: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, keywords, 70, title)
    source_count = len({ev.source_title for ev in evs})
    groups = grouped_evidence(evs)
    out = [
        frontmatter("专题页", title, {"evidence_count": len(evs), "source_count": source_count, "style": '"article"'}),
        f"# {title}",
        "",
        "## 一、监管结论",
        *topic_intro_paragraphs(title, tags, source_count, evs),
        "",
        "## 二、适用边界",
        f"本页聚合的监管标签为：{'、'.join(tags) if tags else '综合监管事项'}。它适用于需要从多个制度中同时判断主体职责、权限边界、办理流程、报告披露、留痕材料和责任后果的工作场景。",
        "",
        "本页的正文是跨制度归纳，不替代监管原文。依据定位仍使用制度自身的条款号；点击条款链接，会跳转到来源证据页的对应条款标题，来源页再保留 raw 原始资料位置。",
        "",
        "## 三、监管要求的系统梳理",
    ]

    ordered_sections = ["任职定位与制度基础", "职责、权限与治理要求", "程序、时限与报送", "禁止事项与责任后果"]
    for section in ordered_sections:
        section_evs = groups.get(section, [])
        if not section_evs:
            continue
        out += ["", f"### {section}"]
        out.extend(section_narrative(title, tags, section, section_evs[:18]))

    out += [
        "",
        "## 四、实务落地口径",
        *topic_practice_paragraphs(title, tags, evs),
        "",
        "## 五、主要依据",
    ]
    for ev in evs:
        out.append(source_reference_line(ev))
    return "\n".join(out)


def topic_ref(ev: Evidence) -> str:
    return source_reference_line(ev).removeprefix("- ")


def piece_is_relevant(piece: str, prefix: str, title: str, tags: list[str], ev: Evidence) -> bool:
    if any(tag and tag in piece for tag in tags):
        return True
    if any(subject and subject != "未明确" and subject in piece for subject in ev.subjects):
        return True
    if any(word in prefix for word in ["职责", "职权", "应当履行", "行使下列"]):
        return True
    core = topic_core_name(title)
    return bool(core and core in piece)


def should_expand_items(prefix: str) -> bool:
    if any(word in prefix for word in ["载明", "含义", "所称", "定义"]):
        return False
    return any(word in prefix for word in ["职责", "职权", "应当履行", "行使下列"])


def topic_bucket(title: str, tags: list[str], text: str, ev: Evidence) -> str:
    haystack = f"{text} {ev.source_title}"
    if any(word in haystack for word in ["不得", "禁止", "公开批评", "处罚", "责令", "撤销", "限制", "兼任", "责任后果"]):
        return "限制事项和责任后果"

    if "董事会秘书" in tags:
        if "协助" in haystack and any(word in haystack for word in ["股东", "董事", "监事", "权利", "履职"]):
            return "治理协调和履职支持职责"
        if (
            any(word in haystack for word in ["任职资格", "金融工作", "经济工作", "具备", "设董事会秘书", "设立董事会秘书", "培训"])
            or ("高级管理人员" in haystack and "名册" not in haystack and "相关资料" not in haystack)
        ):
            return "岗位设置、任职资格与能力要求"
        if any(word in haystack for word in ["信息披露", "投资者关系", "监管", "报告", "报送", "联系方式", "治理报告"]):
            return "信息披露和监管报送职责"
        if any(word in haystack for word in ["股东大会", "股东会", "董事会会议", "会议", "提案", "表决", "议程", "通知", "决议", "档案", "名册", "资料"]):
            return "董事会和股东会运作职责"
        if any(word in haystack for word in ["协助", "权利", "履行职责", "工作保障", "了解决策"]):
            return "治理协调和履职支持职责"
        return "其他治理辅助职责"

    if "董事长职责" in tags:
        if any(word in haystack for word in ["召集", "主持", "会议", "董事会", "提案", "议程"]):
            return "董事会运行组织职责"
        if any(word in haystack for word in ["股权", "股东", "发展规划", "治理报告", "声誉风险", "审计", "财务", "合规"]):
            return "重点治理事项牵头职责"
        return "职责边界和禁止事项"

    if "董事会职权" in tags:
        if any(word in haystack for word in ["审议", "决定", "批准", "职权", "授权"]):
            return "董事会必须审议或决定的事项"
        if any(word in haystack for word in ["会议", "表决", "提案", "决议"]):
            return "会议决策程序"
        return "授权边界和责任承担"

    if "信息披露" in tags:
        if any(word in haystack for word in ["临时", "重大", "披露"]):
            return "重大事项和临时披露"
        if any(word in haystack for word in ["报告", "报送", "监管"]):
            return "监管报告和报送"
        return "披露责任和内部分工"

    if "关联交易" in tags:
        if any(word in haystack for word in ["识别", "关联方", "关联关系"]):
            return "关联方识别"
        if any(word in haystack for word in ["审议", "批准", "回避", "表决"]):
            return "审议批准和回避"
        return "报告披露和责任后果"

    if "任职资格" in tags:
        if any(word in haystack for word in ["申请", "核准", "许可", "材料"]):
            return "申请核准和材料要求"
        if any(word in haystack for word in ["条件", "资格", "经历", "学历"]):
            return "任职条件"
        return "任职管理和履职评价"

    if any(word in haystack for word in ["报告", "报送", "披露", "备案", "通知"]):
        return "报告披露和监管报送"
    if any(word in haystack for word in ["审议", "批准", "决定", "会议", "表决", "授权"]):
        return "审议批准和决策程序"
    if any(word in haystack for word in ["任职", "资格", "设立", "条件", "人员"]):
        return "主体定位和适用条件"
    if any(word in haystack for word in ["时限", "日内", "工作日", "年度", "定期"]):
        return "办理时限和留痕要求"
    return "实务管理要求"


def paraphrase_topic_piece(title: str, tags: list[str], text: str, ev: Evidence) -> str:
    core = topic_core_name(title) or title
    s = re.sub(r"\s+", " ", text).strip(" ；;。")

    if "董事会秘书" in tags:
        if "设董事会秘书" in s and "股东" in s and "董事会" in s:
            return "公司治理架构中应设置董事会秘书，并由其承接股东会、董事会会议筹备、文件保管、股东资料管理和信息披露事务。"
        if "任期届满前 3 个月" in s or "任期届满前3个月" in s:
            return "董事会任期届满前，董事会秘书应提前书面提醒董事并推动董事长启动换届程序。"
        if "董事候选人" in s and "董事会秘书" in s:
            return "董事候选人提名材料应在截止时间前提交董事会秘书，由其作为提名材料流转和归集接口。"
        if "临时会议" in s and "提议" in s:
            return "董事会临时会议提议应通过董事会秘书送达董事长，并载明提议人、事由、召开方式等关键要素。"
        if "会议通知发出前" in s and "提案" in s:
            return "董事会定期会议通知发出前，可通过董事会秘书征集提案，提前确认需要列入审议的事项。"
        if "补充资料" in s or "进一步说明" in s:
            return "董事认为提案材料不充分或不清晰时，可以通过董事会秘书要求提案人补充资料或作进一步说明。"
        if "决策所需要的信息" in s:
            return "董事会秘书应作为会前信息沟通接口，协助董事获取作出决策所需的信息。"
        if "无法按时改选" in s:
            return "董事会换届可能无法按时完成时，董事会秘书应及时向监管机构报告原因和影响。"
        if "辞职报告" in s:
            return "董事提前辞职涉及应说明事项时，应形成书面报告并纳入董事会资料和后续治理安排。"
        if "筹备" in s and ("股东" in s or "董事会" in s):
            return "按规定程序和董事长要求组织股东会、董事会会议筹备，保证会议启动和材料准备有明确责任人。"
        if "制作" in s and "保管" in s:
            return "制作并保管股东会、董事会会议档案及股东、董事、监事、高管名册资料，确保治理文件可查询、可追溯。"
        if "会议通知" in s and "决议" in s:
            return "按监管要求报送股东会、董事会会议通知和决议等材料。"
        if "协助" in s and any(word in s for word in ["股东", "董事", "监事"]):
            return "协助股东、董事、监事依法行权和履职，发挥治理主体之间的协调接口作用。"
        if "信息披露" in s and "投资者关系" in s:
            return "负责对外信息披露和投资者关系管理，保证披露事务有专门组织和协调责任。"
        if "治理报告" in s:
            return "协助董事长起草公司治理报告，把治理运行情况转化为可报告、可核对的文本。"
        if "矛盾" in s or "问题" in s:
            return "按照监管要求报告公司治理结构中的矛盾和问题，避免治理缺陷停留在内部未处理状态。"
        if "培训" in s:
            return "组织董事等相关人员参加监管要求的培训，维护董事会成员持续履职能力。"
        if "高级管理人员" in s:
            return "将董事会秘书纳入高级管理人员或重要治理岗位管理，任职前应核对监管规则下的身份和资格要求。"
        if "设董事会秘书" in s or "设立董事会秘书" in s:
            return "公司治理架构中应设置董事会秘书岗位，并明确其由董事长提名、董事会聘任等任用路径。"
        if "金融工作" in s or "经济工作" in s:
            return "任命董事会秘书前应核对其金融、经济等从业经历是否满足监管资格条件。"
        if "具备" in s and ("公司治理" in s or "法律" in s):
            return "董事会秘书应具备公司治理、法律合规等履职所需专业能力，并保持良好职业操守。"
        if "工作保障" in s or "职权" in s:
            return "公司应向董事会秘书配置必要职权和工作条件，避免职责存在但缺少履职资源。"
        if "联系方式" in s:
            return "涉及信息披露事务的负责人、承办部门和联系方式，应按监管要求向监管机构报送并及时更新。"
        if "不得兼任" in s or "监事不得" in s:
            return "董事会秘书兼任安排应遵守监管限制，监事等不适合主体不得兼任该岗位。"

    if "董事长职责" in tags:
        if "董事会" in s and any(word in s for word in ["召集", "主持", "启动", "提议"]):
            return "董事长负责组织董事会运行，推动会议召集、议题安排和换届等程序按规则启动。"
        if "不得" in s or "禁止" in s:
            return "董事长不得越过董事会集体决策边界，不能以个人决定替代法定治理程序。"

    if any(word in s for word in ["报告", "报送"]):
        return f"涉及{s[:28]}等事项时，应明确报告路径、报送对象和留痕材料，避免监管沟通责任落空。"
    if any(word in s for word in ["披露", "信息披露"]):
        return f"涉及{s[:28]}等事项时，应纳入信息披露管理，确保披露内容、时点和责任主体清楚。"
    if any(word in s for word in ["审议", "批准", "决定", "表决"]):
        return f"涉及{s[:28]}等事项时，应回到相应治理机构履行审议、批准或表决程序，并保留决策记录。"
    if any(word in s for word in ["不得", "禁止", "处罚", "公开批评", "责令"]):
        return f"对{s[:28]}等风险事项，应作为禁止性要求或责任后果管理，提前设置合规复核和整改机制。"
    if any(word in s for word in ["任职", "资格", "条件", "设立", "具备"]):
        return f"围绕{s[:28]}等要求，应先核对适用主体、任职条件和审批或报告要求。"
    if ev.time_limit != "未明确":
        return f"围绕{s[:28]}等事项，应按“{ev.time_limit}”等时限要求推进，并保留过程记录。"
    return f"围绕{s[:36]}等事项，应明确责任主体、办理动作和留痕材料，纳入{core}的日常管理口径。"


def topic_points(title: str, tags: list[str], evs: list[Evidence]) -> dict[str, list[tuple[str, list[str]]]]:
    grouped: dict[str, dict[str, list[str]]] = {}
    for ev in evs:
        normalized = re.sub(r"\s+", " ", ev.text).strip()
        items = extract_numbered_items(normalized)
        first_marker = ENUM_MARKER_RE.search(normalized)
        prefix = normalized[: first_marker.start()].strip() if first_marker else ""
        pieces: list[str] = []
        if len(items) >= 2:
            if should_expand_items(prefix):
                for _, item in items:
                    if piece_is_relevant(item, prefix, title, tags, ev):
                        pieces.append(item)
            else:
                relevant_items = [item for _, item in items if piece_is_relevant(item, prefix, title, tags, ev)]
                if relevant_items:
                    pieces.append("；".join(relevant_items))
        if not pieces:
            pieces = [normalized]
        for piece in pieces:
            bucket = topic_bucket(title, tags, f"{prefix} {piece}", ev)
            point = paraphrase_topic_piece(title, tags, piece, ev)
            grouped.setdefault(bucket, {})
            grouped[bucket].setdefault(point, [])
            ref = topic_ref(ev)
            if ref not in grouped[bucket][point]:
                grouped[bucket][point].append(ref)
    return {bucket: list(points.items()) for bucket, points in grouped.items()}


def ordered_topic_buckets(title: str, tags: list[str], buckets: dict[str, list[tuple[str, list[str]]]]) -> list[str]:
    if "董事会秘书" in tags:
        preferred = [
            "岗位设置、任职资格与能力要求",
            "董事会和股东会运作职责",
            "信息披露和监管报送职责",
            "治理协调和履职支持职责",
            "限制事项和责任后果",
            "其他治理辅助职责",
        ]
    elif "董事长职责" in tags:
        preferred = ["董事会运行组织职责", "重点治理事项牵头职责", "职责边界和禁止事项", "限制事项和责任后果"]
    elif "董事会职权" in tags:
        preferred = ["董事会必须审议或决定的事项", "会议决策程序", "授权边界和责任承担", "限制事项和责任后果"]
    else:
        preferred = [
            "主体定位和适用条件",
            "审议批准和决策程序",
            "报告披露和监管报送",
            "办理时限和留痕要求",
            "限制事项和责任后果",
            "实务管理要求",
        ]
    return [bucket for bucket in preferred if bucket in buckets] + [bucket for bucket in buckets if bucket not in preferred]


def topic_page(title: str, tags: list[str], keywords: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, keywords, 70, title)
    source_count = len({ev.source_title for ev in evs})
    buckets = topic_points(title, tags, evs)
    core = topic_core_name(title) or title
    out = [
        frontmatter("专题页", title, {"evidence_count": len(evs), "source_count": source_count, "style": '"practical-article"'}),
        f"# {title}",
        "",
        "## 一、专题结论",
        f"本页围绕“{core}”把 {source_count} 个制度或文件中的规定重新组织为可执行的工作事项。正文不照抄监管原文，而是按实务职责和办理动作改写；每一点后保留条款依据，点击后可跳转至来源证据页的对应条款。",
        "",
        "## 二、职责和监管要求",
    ]

    for bucket in ordered_topic_buckets(title, tags, buckets):
        out += ["", f"### {bucket}"]
        for idx, (point, refs) in enumerate(buckets[bucket], 1):
            out.append(f"{idx}. {point}")
            out.append(f"   依据：{'；'.join(refs[:8])}")

    out += [
        "",
        "## 三、使用口径",
        f"使用本页时，应先按上面的分组判断事项属于哪一类职责，再点击依据回到具体条款核对适用主体、触发条件、时限和责任后果。涉及正式报告、制度修订、会议材料或检查底稿时，应以来源证据页和 raw 原文为最终核对对象。",
        "",
        "## 四、主要依据",
    ]
    for ev in evs:
        out.append(source_reference_line(ev))
    return "\n".join(out)


def build_index(docs: list[SourceDoc], all_evidence: list[Evidence]) -> str:
    tag_counts = Counter(tag for ev in all_evidence for tag in ev.tags)
    out = [
        "# 制度梳理知识库索引",
        f"> 重塑时间：{TODAY}",
        "> 当前 wiki 已重塑为“来源证据页 + 跨制度专题页 + 工作场景页 + 可执行清单页 + 工作地图”。查询时优先从专题、场景、清单进入，再回到来源页和 raw 原文核对条款。",
        "",
        "## 总览",
        f"- 原始制度：{len(docs)} 份",
        f"- 条款证据：{len(all_evidence)} 条",
        f"- 跨制度专题：{len(TOPICS)} 页",
        f"- 工作场景：{len(SCENARIOS)} 页",
        f"- 执行清单：{len(CHECKLISTS)} 页",
        "",
        "## 推荐入口",
        "- [[wiki/枢纽/公司治理工作地图|公司治理工作地图]]",
        "- [[wiki/枢纽/股权与关联交易工作地图|股权与关联交易工作地图]]",
        "- [[wiki/枢纽/风险内控合规工作地图|风险内控合规工作地图]]",
        "- [[wiki/枢纽/信息披露与报送工作地图|信息披露与报送工作地图]]",
        "- [[wiki/枢纽/业务经营与产品监管工作地图|业务经营与产品监管工作地图]]",
        "- [[wiki/枢纽/资金运用与资本管理工作地图|资金运用与资本管理工作地图]]",
        "- [[wiki/枢纽/消费者保护与销售管理工作地图|消费者保护与销售管理工作地图]]",
        "- [[wiki/枢纽/监管检查处罚工作地图|监管检查处罚工作地图]]",
        "- [[wiki/枢纽/机构准入和许可证工作地图|机构准入和许可证工作地图]]",
        "",
        "## 高频专题",
    ]
    for title, _, _ in TOPICS:
        out.append(f"- [[wiki/专题/{title}|{title}]]")
    out += ["", "## 工作场景"]
    for title, _, _ in SCENARIOS:
        out.append(f"- [[wiki/场景/{title}|{title}]]")
    out += ["", "## 执行清单"]
    for title, _, _ in CHECKLISTS:
        out.append(f"- [[wiki/清单/{title}|{title}]]")
    out += ["", "## 证据标签 Top 30"]
    for tag, count in tag_counts.most_common(30):
        out.append(f"- [[wiki/概念/{tag}|{tag}]]：{count}")
    out += ["", "## 来源分类"]
    by_cat = defaultdict(list)
    for doc in docs:
        by_cat[doc.category].append(doc)
    for cat in sorted(by_cat):
        out.append(f"### {cat}")
        for doc in sorted(by_cat[cat], key=lambda d: d.title):
            out.append(f"- [[{doc.page_rel[:-3]}|{doc.title}]]（证据 {len(doc.evidence)} 条）")
    return "\n".join(out)


def build_log(docs: list[SourceDoc], all_evidence: list[Evidence]) -> str:
    return "\n".join(
        [
            "# 制度梳理知识库整理日志",
            "",
            f"## {TODAY} 全库重塑",
            "- 按用户确认的方案 C，对 wiki 层进行彻底重写。",
            "- 来源页重塑为“条款证据页”：每份制度按条款抽取主体、动作、触发条件、时限、禁止/后果和可引用标签。",
            "- 新增跨制度专题层，以实际工作问题组织内容，避免只按制度标题或抽象概念检索。",
            "- 新增工作场景和执行清单，把审批、报告、披露、留痕、整改、问责转成可办理路径。",
            f"- 本次共处理原始制度 {len(docs)} 份，抽取条款证据 {len(all_evidence)} 条，生成专题 {len(TOPICS)} 页、场景 {len(SCENARIOS)} 页、清单 {len(CHECKLISTS)} 页。",
            "",
            "## 使用原则",
            "- 查询问题时，先从 index、枢纽、专题、场景或清单进入。",
            "- 写正式材料或制度时，必须从专题页回到来源证据页，再回到 raw 原文核对条款编号和原文表述。",
            "- 来源页不做跨制度结论，只提供可引用证据；跨制度结论由专题页承担。",
        ]
    )


def rebuild() -> None:
    if not RAW.exists():
        raise SystemExit("raw/ 不存在，无法重建 wiki。")
    if WIKI_NEW.exists():
        shutil.rmtree(WIKI_NEW)
    WIKI_NEW.mkdir(parents=True)

    docs = load_docs()
    all_evidence = [ev for doc in docs for ev in doc.evidence]
    by_title = {doc.title: doc for doc in docs}

    # Source evidence pages.
    for doc in docs:
        write(WIKI_NEW / "来源" / doc.category / f"{doc.title}.md", source_page(doc))

    # Topic pages.
    for title, tags, keywords in TOPICS:
        write(WIKI_NEW / "专题" / f"{title}.md", topic_page(title, tags, keywords, all_evidence))

    # Scenario pages.
    for title, tags, steps in SCENARIOS:
        write(WIKI_NEW / "场景" / f"{title}.md", scenario_page(title, tags, steps, all_evidence))

    # Checklist pages.
    for title, tags, keywords in CHECKLISTS:
        write(WIKI_NEW / "清单" / f"{title}.md", checklist_page(title, tags, keywords, all_evidence))

    # Concept pages from tags.
    for tag, _ in TAG_RULES:
        evs = [ev for ev in all_evidence if tag in ev.tags][:40]
        if evs:
            write(WIKI_NEW / "概念" / f"{tag}.md", concept_page(tag, evs))
    write(
        WIKI_NEW / "概念" / "README.md",
        frontmatter("概念索引", "概念索引")
        + "# 概念索引\n\n概念层用于提供工作定义、适用边界、判断方法和代表证据。需要形成跨制度结论时，请进入专题页、场景页或清单页，并回到来源页核对条款。\n\n"
        + "\n".join(f"- [[wiki/概念/{tag}|{tag}]]" for tag, _ in TAG_RULES),
    )

    # Hubs.
    for title, topics in HUBS:
        write(WIKI_NEW / "枢纽" / f"{title}.md", hub_page(title, topics))

    # Comparison pages.
    for title, old_title, new_title, keywords in COMPARES:
        write(WIKI_NEW / "对照" / f"{title}.md", compare_page(title, old_title, new_title, keywords, by_title))

    # Evidence index for machine-readable-ish manual lookup.
    evidence_index = [
        "# 证据总索引",
        "",
        "| 标签 | 来源 | 条款 | 证据要点 |",
        "| --- | --- | --- | --- |",
    ]
    for ev in all_evidence:
        label = ", ".join(ev.tags[:5]) if ev.tags else "综合监管证据"
        evidence_index.append(f"| {label} | {evidence_link(ev, ev.source_title)} | {ev.clause} | {compact(topic_statement(ev), 100)} |")
    write(WIKI_NEW / "证据总索引.md", "\n".join(evidence_index))

    write(ROOT / "index.md.new", build_index(docs, all_evidence))
    write(ROOT / "log.md.new", build_log(docs, all_evidence))

    # Replace wiki only after the new tree is complete.
    root_resolved = ROOT.resolve()
    wiki_resolved = WIKI.resolve()
    if wiki_resolved.parent != root_resolved or wiki_resolved.name != "wiki":
        raise SystemExit(f"拒绝删除异常路径：{wiki_resolved}")
    if WIKI.exists():
        shutil.rmtree(WIKI)
    WIKI_NEW.rename(WIKI)
    (ROOT / "index.md").write_text((ROOT / "index.md.new").read_text(encoding="utf-8"), encoding="utf-8")
    (ROOT / "log.md").write_text((ROOT / "log.md.new").read_text(encoding="utf-8"), encoding="utf-8")
    (ROOT / "index.md.new").unlink()
    (ROOT / "log.md.new").unlink()

    print(f"processed_sources={len(docs)}")
    print(f"evidence_count={len(all_evidence)}")
    print(f"topic_count={len(TOPICS)}")
    print(f"scenario_count={len(SCENARIOS)}")
    print(f"checklist_count={len(CHECKLISTS)}")


# ---------------------------------------------------------------------------
# 2026-05-25 practical wiki overrides.
#
# These definitions intentionally sit after the original renderer definitions.
# Python resolves global function names when rebuild() runs, so the overrides
# below keep the extraction logic but improve the generated wiki layer.


def frontmatter(page_type: str, title: str, extra: dict[str, str | int] | None = None) -> str:
    extra = extra or {}
    lines = [
        "---",
        f'type: "{page_type}"',
        f'title: "{title}"',
        f"rewritten: {TODAY}",
        'design: "IBM Carbon"',
        'cssclasses: ["ibm-carbon-regulatory"]',
    ]
    for key, value in extra.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def wikilink(path: str, label: str | None = None) -> str:
    return slug_link(path, label)


def top_values(values: list[str], limit: int = 5) -> list[str]:
    cleaned = [v for v in values if v and v != "未明确"]
    if not cleaned:
        return []
    return [value for value, _ in Counter(cleaned).most_common(limit)]


def scenario_focus(title: str, tags: list[str]) -> str:
    if "关联交易" in tags:
        return "识别关联方和交易类型，判断是否触发一般、重大或统一交易协议管理，再完成内部审查、回避、报告和披露。"
    if "任职资格" in tags:
        return "围绕拟任、改任、免任、辞任和履职评价，核对任职条件、核准路径、任命生效和后续评价留痕。"
    if "董事会职权" in tags:
        return "把会议触发、议案形成、材料送达、审议表决、决议执行和档案保管串成可复核的董事会闭环。"
    if "股权事务" in tags:
        return "从股东资格、资金来源、持股比例、股权质押或转让、监管许可和信息披露等维度建立穿透审查链条。"
    if "信息披露" in tags:
        return "先识别重大事项和披露触发点，再完成内部审核、披露文本、监管报告和披露留档。"
    if "分支机构准入" in tags:
        return "按规划、申请、筹建、开业、变更、退出顺序管理机构准入事项，重点控制材料真实性和监管许可节点。"
    if "产品条款费率" in tags:
        return "把产品开发、条款费率审查、报批报备、上线使用、披露和后评估纳入同一套材料链。"
    if "车险经营" in tags:
        return "围绕费用真实性、费率使用、报行合一、渠道管理和整改反馈建立检查流程。"
    if "投诉处理" in tags or "消费者权益保护" in tags:
        return "以受理、调查、处理、反馈、统计分析、整改和重大事件报告为主线，确保消费者事项可追踪。"
    if "现场检查" in tags or "行政处罚" in tags:
        return "把检查通知、资料准备、事实核对、申辩听证、整改和处罚应对分开留痕，避免只保留最终结论。"
    if "内部审计" in tags:
        return "从审计计划、实施、报告、问题认定、整改跟踪到责任追究建立闭环。"
    if "声誉风险" in tags:
        return "按监测、研判、分级、报告、处置、回应和复盘建立声誉事件处置链条。"
    if "操作风险" in tags:
        return "识别操作风险事件后，及时评估影响、报告、整改、追责并纳入风险数据库。"
    if "合规管理" in tags:
        return "把重大决策、新产品、新业务、重要制度和重大风险事件纳入合规审查和报告机制。"
    if "反洗钱" in tags:
        return "以客户尽调、风险评级、持续识别、资料保存、可疑交易监测和报告为主线。"
    if "数据安全" in tags or "监管统计" in tags:
        return "围绕数据分类分级、处理活动、统计报送、质量校验和事件报告建立责任链。"
    if "资金运用" in tags:
        return "把投资授权、尽调评审、决策审批、投后管理、信息披露和风险处置贯通。"
    if "偿付能力" in tags or "资本管理" in tags:
        return "以偿付能力监测、资本规划、压力测试、补充资本、报告和整改为主线。"
    if "境外外资" in tags:
        return "先判断境外设立、外资准入或代表机构管理事项，再核对审批、报告、人员和持续管理要求。"
    return "把触发条件、责任主体、办理动作、时限要求、材料留痕和责任后果串成可执行流程。"


def scenario_roles(tags: list[str]) -> list[str]:
    role_map = {
        "关联交易": ["业务发起部门", "关联交易管理牵头部门", "合规/风控部门", "独立董事或专门委员会", "董事会"],
        "任职资格": ["人力资源部门", "董事会办公室", "提名薪酬委员会", "董事会/股东会", "监管报送责任人"],
        "董事会职权": ["董事会办公室", "议案提交部门", "董事会秘书", "董事长", "董事会"],
        "股权事务": ["董事会办公室", "股东事务管理部门", "合规/法律部门", "财务部门", "董事会"],
        "信息披露": ["信息披露牵头部门", "事项发生部门", "董事会秘书", "合规/法律部门", "董事会"],
        "分支机构准入": ["战略/机构管理部门", "拟设机构筹建组", "合规部门", "财务/人力部门", "监管报送责任人"],
        "产品条款费率": ["产品部门", "精算/定价部门", "合规部门", "信息披露或报备人员", "经营管理层"],
        "车险经营": ["车险业务部门", "财务费用管理部门", "渠道管理部门", "合规/审计部门", "整改责任部门"],
        "消费者权益保护": ["消保部门", "投诉处理部门", "业务责任部门", "合规部门", "高级管理层"],
        "投诉处理": ["投诉处理部门", "业务责任部门", "消保部门", "合规部门", "整改责任部门"],
        "现场检查": ["检查对接部门", "资料提供部门", "法务/合规部门", "整改责任部门", "董事会或高级管理层"],
        "行政处罚": ["法务/合规部门", "业务责任部门", "检查对接部门", "整改责任部门", "董事会或高级管理层"],
        "内部审计": ["内部审计部门", "被审计部门", "审计责任人", "董事会审计委员会", "整改责任部门"],
        "合规管理": ["首席合规官/合规负责人", "业务责任部门", "法律合规部门", "高级管理层", "董事会"],
        "反洗钱": ["反洗钱牵头部门", "客户管理部门", "业务经办部门", "系统监测部门", "可疑交易报告人员"],
        "数据安全": ["数据管理部门", "信息科技部门", "业务数据责任部门", "合规部门", "高级管理层"],
        "监管统计": ["统计归口部门", "数据提供部门", "信息科技部门", "复核人员", "监管报送责任人"],
        "资金运用": ["投资管理部门", "风险管理部门", "合规部门", "投后管理部门", "董事会或投资决策机构"],
        "偿付能力": ["财务/精算部门", "风险管理部门", "资本管理部门", "高级管理层", "董事会"],
        "资本管理": ["财务部门", "风险管理部门", "资本管理部门", "高级管理层", "董事会"],
        "境外外资": ["战略发展部门", "境外机构管理部门", "合规/法律部门", "人力资源部门", "监管报送责任人"],
    }
    roles: list[str] = []
    for tag in tags:
        roles.extend(role_map.get(tag, []))
    return top_values(roles, 8) or ["业务发起部门", "合规/法律部门", "风险管理部门", "董事会办公室", "监管报送责任人"]


def step_evidence(evs: list[Evidence], step: str, limit: int = 5) -> list[Evidence]:
    keywords = [step]
    keywords.extend([word for word in re.split(r"[和、/与及 ]+", step) if len(word) >= 2])
    scored: list[tuple[int, Evidence]] = []
    for ev in evs:
        haystack = f"{ev.source_title} {ev.clause} {ev.text} {' '.join(ev.tags)}"
        score = sum(2 for keyword in keywords if keyword and keyword in haystack)
        if "报告" in step or "报送" in step or "备案" in step:
            score += 2 if any(word in haystack for word in ["报告", "报送", "备案", "监管"]) else 0
        if "披露" in step:
            score += 2 if "披露" in haystack else 0
        if "审" in step or "批" in step or "会议" in step or "决策" in step:
            score += 2 if any(word in haystack for word in ["审议", "批准", "决定", "会议", "表决", "回避"]) else 0
        if "整改" in step or "处置" in step or "应对" in step:
            score += 2 if any(word in haystack for word in ["整改", "处置", "责令", "处罚", "风险"]) else 0
        if score:
            scored.append((score, ev))
    scored.sort(key=lambda item: (-item[0], item[1].source_title, item[1].clause))
    return [ev for _, ev in scored[:limit]] or evs[: min(limit, len(evs))]


def step_actions(step: str) -> list[str]:
    if any(word in step for word in ["识别", "确认", "尽调", "监测", "评估", "核对"]):
        return [
            "确认事项是否落入本场景，记录触发事实、涉及主体、金额或影响范围。",
            "核对适用制度、内部授权和是否触发监管报告、信息披露或会议审议。",
            "形成初步判断，标明待核对事项和需要补充的证据材料。",
        ]
    if any(word in step for word in ["申请", "材料", "报批", "报备", "筹建", "开业"]):
        return [
            "按来源条款和内部制度列明材料目录，区分必备材料、补充说明和需签章文件。",
            "由业务发起部门提供事实材料，合规、财务、人力或精算等部门分别复核专业内容。",
            "在提交前完成一致性检查，确保申请文本、会议决议、附件和系统填报口径一致。",
        ]
    if any(word in step for word in ["审查", "审核", "合规", "法律", "风险", "评审"]):
        return [
            "由牵头部门组织合规、法律、风险、财务或审计意见，明确是否存在禁止性情形。",
            "对例外事项、关联关系、回避安排、利益冲突和重大风险形成书面意见。",
            "无法确认适用口径的，标注“待核对”并补充监管沟通或外部专业意见。"
        ]
    if any(word in step for word in ["会议", "董事会", "股东", "审议", "批准", "表决", "决策"]):
        return [
            "按公司章程和议事规则确认是否需要董事会、股东会、专门委员会或高级管理层审议。",
            "会议材料应写明事实、依据、审查意见、回避安排、表决事项和后续责任部门。",
            "表决和决议应完整留痕，涉及关联关系或利益冲突的，应记录回避情况。"
        ]
    if any(word in step for word in ["报告", "报送", "备案", "通知"]):
        return [
            "确认报送对象、报送渠道、时限、签发层级和附件清单。",
            "报送内容应与内部审批结论、会议决议、披露文本和事实材料保持一致。",
            "保留报送回执、系统截图、邮件记录、签收记录或其他可证明已报送的材料。"
        ]
    if any(word in step for word in ["披露", "公告", "网站"]):
        return [
            "确认是否触发临时披露、定期披露、网站披露或指定媒体披露。",
            "披露文本应完成事实核验、合规审核和必要审批，避免虚假记载、误导性陈述或重大遗漏。",
            "披露后留存发布页面、公告文件、审核记录和后续更正或补充披露记录。"
        ]
    if any(word in step for word in ["整改", "问责", "处置", "应急", "复盘", "退出"]):
        return [
            "建立整改或处置台账，明确问题、责任主体、完成时限、验收标准和报告路径。",
            "对涉及监管措施、处罚风险或重大影响的事项，及时提交管理层或董事会关注。",
            "完成后复核制度、流程、系统和人员责任是否同步修正，并保留闭环证据。"
        ]
    return [
        "明确该步骤的责任主体、输入材料、输出结论和下一步流转对象。",
        "把口头沟通转化为书面记录，确保后续审查、报告或检查时能够复盘。",
        "如发现主体、时限、审批层级或责任后果不明确，应回到来源证据页核对条款。"
    ]


def scenario_page(title: str, tags: list[str], steps: list[str], all_evidence: list[Evidence]) -> str:
    evs = collect_evidence(all_evidence, tags, steps, 75)
    roles = scenario_roles(tags)
    source_count = len({ev.source_title for ev in evs})
    out = [
        frontmatter("场景页", title, {"evidence_count": len(evs), "source_count": source_count, "style": '"workflow"'}),
        f"# {title}",
        "",
        "## 一、监管结论",
        scenario_focus(title, tags),
        "",
        f"本流程聚合 {source_count} 个制度或文件中的条款证据。它不是单一制度摘要，而是把触发、审查、决策、报送、披露、整改和留痕组织成可办理路径。",
        "",
        "## 二、触发场景",
        f"- 出现与“{title.replace('流程', '')}”相关的业务事项、治理事项、监管沟通或风险事件时，应启动本流程。",
        "- 如事项同时涉及审批、报告、披露、处罚风险或董事会责任，应按较严格路径办理，并同步保留依据。",
        "- raw 中未能直接确认的主体、时限或监管对象，应标注“待核对”，不得自行补造。",
        "",
        "## 三、责任分工",
    ]
    for role in roles:
        out.append(f"- {role}：负责提供事实、审核意见、决策记录或报送披露材料中与本岗位有关的部分。")

    out += ["", "## 四、办理流程"]
    for idx, step in enumerate(steps, 1):
        refs = step_evidence(evs, step, 4)
        out += ["", f"### {idx}. {step}"]
        out.extend([f"- {action}" for action in step_actions(step)])
        out.append("")
        out.append("依据：")
        out.extend([source_reference_line(ev) for ev in refs])

    time_evs = [ev for ev in evs if ev.time_limit != "未明确"][:10]
    risk_evs = [ev for ev in evs if ev.consequence != "未明确" or any(word in ev.text for word in SANCTION_WORDS)][:12]
    out += [
        "",
        "## 五、时限和报送控制",
    ]
    if time_evs:
        for ev in time_evs:
            out.append(f"- {ev.time_limit}：{evidence_link(ev)}")
    else:
        out.append("- 本流程未聚合到统一时限。实务办理时，应分别核对来源条款、监管通知、公司章程、议事规则和内部制度。")

    out += [
        "",
        "## 六、材料和留痕",
        "- 事实材料：业务背景、触发原因、涉及主体、金额、影响范围、客户或机构信息。",
        "- 审查材料：合规审查意见、法律意见、风险评估、财务或精算测算、关联关系或利益冲突核验。",
        "- 决策材料：会议通知、议案、会议材料、表决记录、回避记录、决议、授权文件。",
        "- 报送披露材料：监管报告、报送系统截图、回执、公告或网站披露截图、更正或补充披露记录。",
        "- 整改材料：整改台账、责任分解、完成证明、复核意见、问责记录和制度流程修订记录。",
        "",
        "## 七、风险后果",
    ]
    if risk_evs:
        for ev in risk_evs:
            out.append(f"- {evidence_link(ev)}：{compact(ev.consequence if ev.consequence != '未明确' else topic_statement(ev), 120)}")
    else:
        out.append("- 本流程未聚合到明确处罚或监管措施条款，但仍应按来源页核对禁止性要求和监管后果。")

    out += [
        "",
        "## 八、关联专题和清单",
    ]
    related = related_topics_for_tags(tags)
    if related:
        out.extend([f"- {wikilink(f'wiki/专题/{topic}.md', topic)}" for topic in related[:8]])
    else:
        out.append("- 暂无直接关联专题。")
    related_checklists = [name for name, checklist_tags, _ in CHECKLISTS if set(checklist_tags).intersection(tags)]
    for checklist in related_checklists[:6]:
        out.append(f"- {wikilink(f'wiki/清单/{checklist}.md', checklist)}")
    return "\n".join(out)


CONCEPT_GUIDANCE: dict[str, tuple[str, str, str]] = {
    "关联交易": (
        "关联交易是识别利益冲突、审批层级、回避表决、报告披露和责任后果的治理概念。",
        "判断时应同时看交易对手、实际控制关系、一致行动、资金来源、交易定价、担保或授信安排。",
        "不要只在合同签署后补做关联交易识别；实务上应在立项或交易方案阶段完成识别。"
    ),
    "信息披露": (
        "信息披露是把重大事项、经营管理信息和监管要求转化为公开或监管可见信息的责任链。",
        "边界包括披露内容、披露时点、披露渠道、审核责任、董事会或管理层责任和更正机制。",
        "不要把信息披露等同于发布公告；前置识别和内部审核同样属于披露管理。"
    ),
    "任职资格": (
        "任职资格是对董事、监事、高级管理人员和特定关键岗位任职前、任职中和离任后的准入与履职约束。",
        "判断时应核对资格条件、禁止任职情形、核准或报告路径、任命生效条件、培训和履职评价。",
        "未取得必要核准或未完成规定程序前，不应让相关人员实质履职或参与表决。"
    ),
    "董事会职权": (
        "董事会职权是公司重大事项集体决策、最终责任承担和治理留痕的核心入口。",
        "边界在于哪些事项必须董事会审议，哪些可以授权，以及授权是否一事一授权、边界清晰。",
        "不要把董事会事项简化为董事长、管理层或部门审批事项。"
    ),
    "董事会秘书": (
        "董事会秘书是董事会运作、信息披露、监管沟通和治理资料管理的接口岗位。",
        "工作边界包括会议筹备、提案流转、资料保管、股东和董事资料、披露组织和监管报送。",
        "不要把董事会秘书仅理解为会议记录人员，其岗位通常具有治理协调和监管责任。"
    ),
    "股权事务": (
        "股权事务是股东准入、持股变化、质押、转让、股东行为和公司治理影响的持续管理事项。",
        "判断时应穿透股东资质、资金来源、关联关系、实际控制、持股比例、许可或报告义务。",
        "不要只看工商或股权登记结果；监管更关注交易背后的控制关系和风险影响。"
    ),
    "合规管理": (
        "合规管理是把法律法规、监管规定和内部制度嵌入业务决策、流程执行和风险处置的管理机制。",
        "边界包括合规审查、重大合规风险报告、整改跟踪、问责建议、制度评估和合规文化建设。",
        "不要把合规审查放在业务决策之后补签；重大事项应前置合规意见。"
    ),
    "消费者权益保护": (
        "消费者权益保护是贯穿产品、销售、服务、投诉、信息披露和整改的全流程治理要求。",
        "判断时应关注适当性、销售可回溯、投诉处理、信息告知、公平交易和重大事件报告。",
        "不要把消保只等同于投诉处理，产品和销售前端也会触发消保要求。"
    ),
    "反洗钱": (
        "反洗钱是围绕客户身份识别、风险评级、交易监测、资料保存和可疑交易报告建立的持续义务。",
        "边界包括客户准入、业务关系存续期间、异常交易、受益所有人识别和高风险客户强化尽调。",
        "不要只在开户时做一次身份识别；持续尽调和可疑监测同样是核心义务。"
    ),
    "数据安全": (
        "数据安全是对数据分类分级、处理活动、权限控制、外部提供、事件处置和监管报告的治理要求。",
        "判断时应看数据类型、处理目的、处理主体、系统边界、外部共享和是否涉及个人信息或重要数据。",
        "不要只从信息科技角度处理，业务部门通常也是数据处理责任链的一环。"
    ),
    "资金运用": (
        "资金运用是保险资金投资授权、决策、风险控制、投后管理、信息披露和责任追究的组合概念。",
        "边界包括投资品种、比例限制、审批权限、关联交易、估值、压力测试、投后监测和退出安排。",
        "不要只核对投资收益和额度，还要核对授权、风控和投后证据是否完整。"
    ),
}


def concept_guidance(tag: str, evs: list[Evidence]) -> tuple[str, str, str]:
    if tag in CONCEPT_GUIDANCE:
        return CONCEPT_GUIDANCE[tag]
    subjects, actions, times, consequences = evidence_features(evs)
    definition = f"{tag}在本库中是把相关监管条款归集到同一工作入口的概念，用于帮助判断{subjects}等主体在{actions}等事项中的职责。"
    boundary = f"使用时应核对适用主体、触发条件、审批或报告路径、材料留痕和责任后果；出现{times}等时限要求时，应优先回看来源页。"
    warning = f"不要把“{tag}”当成单一制度定义；本概念页只做工作入口，正式结论应进入专题、场景或清单并回查条款。"
    return definition, boundary, warning


def concept_page(tag: str, evs: list[Evidence]) -> str:
    related = related_topics_for_tags([tag])
    definition, boundary, warning = concept_guidance(tag, evs)
    scenario_links = [name for name, scenario_tags, _ in SCENARIOS if tag in scenario_tags]
    checklist_links = [name for name, checklist_tags, _ in CHECKLISTS if tag in checklist_tags]
    key_subjects, key_actions, key_times, key_consequences = evidence_features(evs)
    out = [
        frontmatter("概念页", tag, {"evidence_count": len(evs), "style": '"concept-brief"'}),
        f"# {tag}",
        "",
        "## 一、工作定义",
        definition,
        "",
        "## 二、适用边界",
        boundary,
        "",
        f"- 高频主体：{key_subjects}",
        f"- 高频动作：{key_actions}",
        f"- 常见时限：{key_times}",
        f"- 常见后果：{key_consequences}",
        "",
        "## 三、实务判断方法",
        f"1. 先判断当前事项是否属于“{tag}”的触发范围，并记录触发事实。",
        "2. 再进入相关专题页形成跨制度口径，进入场景页确认办理流程，进入清单页核对材料和时限。",
        "3. 最后回到来源证据页核对条款号、适用主体、触发条件和责任后果；必要时回看 raw 原文。",
        "",
        "## 四、常见误区",
        warning,
        "",
        "## 五、相关专题、场景和清单",
    ]
    if related:
        out.extend([f"- {wikilink(f'wiki/专题/{topic}.md', topic)}" for topic in related])
    if scenario_links:
        out.extend([f"- {wikilink(f'wiki/场景/{scenario}.md', scenario)}" for scenario in scenario_links[:8]])
    if checklist_links:
        out.extend([f"- {wikilink(f'wiki/清单/{checklist}.md', checklist)}" for checklist in checklist_links[:8]])
    if not related and not scenario_links and not checklist_links:
        out.append("- 暂无直接关联页面，可从证据总索引继续检索。")
    out += [
        "",
        "## 六、代表证据",
    ]
    out.extend(evidence_table(evs, 15))
    return "\n".join(out)


def build_index(docs: list[SourceDoc], all_evidence: list[Evidence]) -> str:
    tag_counts = Counter(tag for ev in all_evidence for tag in ev.tags)
    out = [
        frontmatter("导航入口", "制度梳理知识库索引", {"source_count": len(docs), "evidence_count": len(all_evidence)}).rstrip(),
        "# 制度梳理知识库索引",
        "",
        "> 设计模板：IBM Carbon。当前 wiki 按“来源证据页 + 跨制度专题页 + 工作场景页 + 可执行清单页 + 概念入口 + 工作地图”重建。查询时先从专题、场景、清单进入，再回到来源页和 raw 原文核对条款。",
        "",
        "## 总览",
        f"- 原始制度：{len(docs)} 份",
        f"- 条款证据：{len(all_evidence)} 条",
        f"- 跨制度专题：{len(TOPICS)} 页",
        f"- 工作场景：{len(SCENARIOS)} 页",
        f"- 执行清单：{len(CHECKLISTS)} 页",
        f"- 概念入口：{sum(1 for tag, _ in TAG_RULES if any(tag in ev.tags for ev in all_evidence))} 页",
        "",
        "## 推荐入口",
        "- [[wiki/枢纽/公司治理工作地图|公司治理工作地图]]",
        "- [[wiki/枢纽/股权与关联交易工作地图|股权与关联交易工作地图]]",
        "- [[wiki/枢纽/风险内控合规工作地图|风险内控合规工作地图]]",
        "- [[wiki/枢纽/信息披露与报送工作地图|信息披露与报送工作地图]]",
        "- [[wiki/枢纽/业务经营与产品监管工作地图|业务经营与产品监管工作地图]]",
        "- [[wiki/枢纽/资金运用与资本管理工作地图|资金运用与资本管理工作地图]]",
        "- [[wiki/枢纽/消费者保护与销售管理工作地图|消费者保护与销售管理工作地图]]",
        "- [[wiki/枢纽/监管检查处罚工作地图|监管检查处罚工作地图]]",
        "- [[wiki/枢纽/机构准入和许可证工作地图|机构准入和许可证工作地图]]",
        "",
        "## 高频专题",
    ]
    for title, _, _ in TOPICS:
        out.append(f"- [[wiki/专题/{title}|{title}]]")
    out += ["", "## 工作场景"]
    for title, _, _ in SCENARIOS:
        out.append(f"- [[wiki/场景/{title}|{title}]]")
    out += ["", "## 执行清单"]
    for title, _, _ in CHECKLISTS:
        out.append(f"- [[wiki/清单/{title}|{title}]]")
    out += ["", "## 概念入口 Top 30"]
    for tag, count in tag_counts.most_common(30):
        out.append(f"- [[wiki/概念/{tag}|{tag}]]：{count}")
    out += ["", "## 来源分类"]
    by_cat = defaultdict(list)
    for doc in docs:
        by_cat[doc.category].append(doc)
    for cat in sorted(by_cat):
        out.append(f"### {cat}")
        for doc in sorted(by_cat[cat], key=lambda d: d.title):
            out.append(f"- [[{doc.page_rel[:-3]}|{doc.title}]]（证据 {len(doc.evidence)} 条）")
    return "\n".join(out)


def build_log(docs: list[SourceDoc], all_evidence: list[Evidence]) -> str:
    return "\n".join(
        [
            frontmatter("修订日志", "制度梳理知识库整理日志").rstrip(),
            "# 制度梳理知识库整理日志",
            "",
            f"## {TODAY} 全库重建与场景/概念增强",
            "- rebuild: 按 AGENTS.md 规则从 raw 原文重新生成 wiki 层，覆盖来源、专题、场景、清单、概念、枢纽、对照和证据总索引。",
            "- design: 选用 IBM Carbon 模板作为知识库排版基准，原因是其企业级、低装饰、高可读的风格适合监管制度库；新增统一 frontmatter 和 Obsidian CSS snippet。",
            "- source: 来源页继续按制度条款号建立标题锚点，保留原文依据、结构化要素和关联专题。",
            "- topic: 专题页继续按跨制度实务事项组织，避免退化为单篇制度摘要或概念页重复。",
            "- scenario: 场景页从“步骤名 + 证据列表”改为可执行流程，补充触发场景、责任分工、逐步办理动作、时限控制、材料留痕和风险后果。",
            "- concept: 概念页从证据索引扩展为工作定义、适用边界、判断方法、常见误区和代表证据，仍不替代专题页结论。",
            "- raw: raw 原始资料不改写；排版优化通过 Obsidian 全局样式和 wiki 层结构实现，避免破坏原始证据。",
            f"- result: 本次处理原始制度 {len(docs)} 份，抽取条款证据 {len(all_evidence)} 条，生成专题 {len(TOPICS)} 页、场景 {len(SCENARIOS)} 页、清单 {len(CHECKLISTS)} 页。",
            "",
            "## 使用原则",
            "- 查询问题时，先从 index、枢纽、专题、场景或清单进入。",
            "- 写正式材料或制度时，必须从专题页回到来源证据页，再回到 raw 原文核对条款编号和原文表述。",
            "- 来源页不做跨制度结论，只提供可引用证据；专题页、场景页和清单页承担实务组织功能。",
        ]
    )


def practical_fragment(text: str, limit: int = 34) -> str:
    s = re.sub(r"\s+", " ", text).strip(" ；;。")
    s = re.sub(r"^[（(]?[一二三四五六七八九十0-9]+[）).、]\s*", "", s)
    s = re.sub(r"^应当|^应|^须|^必须", "", s)
    s = s.strip(" ；;。")
    return compact(s, limit)


def paraphrase_topic_piece(title: str, tags: list[str], text: str, ev: Evidence) -> str:
    core = topic_core_name(title) or title
    s = re.sub(r"\s+", " ", text).strip(" ；;。")
    fragment = practical_fragment(s, 36)

    if "董事会秘书" in tags:
        if "设董事会秘书" in s and "股东" in s and "董事会" in s:
            return "公司治理架构中应设置董事会秘书，并由其承接股东会、董事会会议筹备、文件保管、股东资料管理和信息披露事务。"
        if "任期届满前 3 个月" in s or "任期届满前3个月" in s:
            return "董事会任期届满前，董事会秘书应提前书面提醒董事并推动董事长启动换届程序。"
        if "董事候选人" in s and "董事会秘书" in s:
            return "董事候选人提名材料应在截止时间前提交董事会秘书，由其作为提名材料流转和归集接口。"
        if "临时会议" in s and "提议" in s:
            return "董事会临时会议提议应通过董事会秘书送达董事长，并载明提议人、事由、召开方式等关键要素。"
        if "会议通知发出前" in s and "提案" in s:
            return "董事会定期会议通知发出前，可通过董事会秘书征集提案，提前确认需要列入审议的事项。"
        if "补充资料" in s or "进一步说明" in s:
            return "董事认为提案材料不充分或不清晰时，可以通过董事会秘书要求提案人补充资料或作进一步说明。"
        if "决策所需要的信息" in s:
            return "董事会秘书应作为会前信息沟通接口，协助董事获取作出决策所需的信息。"
        if "无法按时改选" in s:
            return "董事会换届可能无法按时完成时，董事会秘书应及时向监管机构报告原因和影响。"
        if "辞职报告" in s:
            return "董事提前辞职涉及应说明事项时，应形成书面报告并纳入董事会资料和后续治理安排。"
        if "筹备" in s and ("股东" in s or "董事会" in s):
            return "按规定程序和董事长要求组织股东会、董事会会议筹备，保证会议启动和材料准备有明确责任人。"
        if "制作" in s and "保管" in s:
            return "制作并保管股东会、董事会会议档案及股东、董事、监事、高管名册资料，确保治理文件可查询、可追溯。"
        if "会议通知" in s and "决议" in s:
            return "按监管要求报送股东会、董事会会议通知和决议等材料。"
        if "协助" in s and any(word in s for word in ["股东", "董事", "监事"]):
            return "协助股东、董事、监事依法行权和履职，发挥治理主体之间的协调接口作用。"
        if "信息披露" in s and "投资者关系" in s:
            return "负责对外信息披露和投资者关系管理，保证披露事务有专门组织和协调责任。"
        if "治理报告" in s:
            return "协助董事长起草公司治理报告，把治理运行情况转化为可报告、可核对的文本。"
        if "矛盾" in s or "问题" in s:
            return "按照监管要求报告公司治理结构中的矛盾和问题，避免治理缺陷停留在内部未处理状态。"
        if "培训" in s:
            return "组织董事等相关人员参加监管要求的培训，维护董事会成员持续履职能力。"
        if "高级管理人员" in s:
            return "将董事会秘书纳入高级管理人员或重要治理岗位管理，任职前应核对监管规则下的身份和资格要求。"
        if "设董事会秘书" in s or "设立董事会秘书" in s:
            return "公司治理架构中应设置董事会秘书岗位，并明确其由董事长提名、董事会聘任等任用路径。"
        if "金融工作" in s or "经济工作" in s:
            return "任命董事会秘书前应核对其金融、经济等从业经历是否满足监管资格条件。"
        if "具备" in s and ("公司治理" in s or "法律" in s):
            return "董事会秘书应具备公司治理、法律合规等履职所需专业能力，并保持良好职业操守。"
        if "工作保障" in s or "职权" in s:
            return "公司应向董事会秘书配置必要职权和工作条件，避免职责存在但缺少履职资源。"
        if "联系方式" in s:
            return "涉及信息披露事务的负责人、承办部门和联系方式，应按监管要求向监管机构报送并及时更新。"
        if "不得兼任" in s or "监事不得" in s:
            return "董事会秘书兼任安排应遵守监管限制，监事等不适合主体不得兼任该岗位。"

    if "董事长职责" in tags:
        if "董事会" in s and any(word in s for word in ["召集", "主持", "启动", "提议"]):
            return "董事长负责组织董事会运行，推动会议召集、议题安排和换届等程序按规则启动。"
        if "不得" in s or "禁止" in s:
            return "董事长不得越过董事会集体决策边界，不能以个人决定替代法定治理程序。"

    if any(word in s for word in ["余额不得超过", "比例不得超过", "不得超过", "资本净额", "注册资本", "持股比例"]):
        return f"应对“{fragment}”设置额度或比例复核，交易前核对计算口径、穿透范围、累计余额和超限处置路径。"
    if any(word in s for word in ["报告", "报送", "监管沟通", "备案", "通知"]):
        return f"应把“{fragment}”纳入监管报告台账，逐项明确触发条件、承办部门、报送对象、报送材料和回执留存。"
    if any(word in s for word in ["披露", "信息披露", "公告"]):
        return f"应把“{fragment}”纳入披露管理台账，逐项确认披露内容、披露时点、审核责任、发布渠道和更正机制。"
    if any(word in s for word in ["审计", "专项审计"]):
        return f"应把“{fragment}”纳入审计和复核计划，明确审计频率、审计范围、报告对象、问题整改和复核闭环。"
    if any(word in s for word in ["关联方信息档案", "信息档案", "名单", "关联方名单"]):
        return f"应维护“{fragment}”对应的信息档案，持续更新关联方名单、识别依据、变动记录和内部共享路径。"
    if any(word in s for word in ["回避", "表决"]):
        return f"出现“{fragment}”时，应先识别利益冲突主体，再落实回避、表决统计和会议记录留痕。"
    if any(word in s for word in ["审议", "批准", "决定", "会议", "授权", "决议"]):
        return f"应将“{fragment}”提交相应治理机构或授权层级处理，并保留议案、审查意见、表决结果和决议文件。"
    if any(word in s for word in ["遵守", "健全", "管理制度", "交易规则", "认定标准", "定价方法", "审查机制"]):
        return f"应把“{fragment}”转化为内部制度和控制要求，明确识别标准、定价原则、审查权限、监督检查和责任追究。"
    if any(word in s for word in ["不得", "禁止", "处罚", "公开批评", "责令", "限制", "撤销", "转让股权", "问责"]):
        return f"应将“{fragment}”作为红线或责任后果管理，前置复核禁止性情形，并把整改、问责和监管措施纳入台账。"
    if any(word in s for word in ["任职", "资格", "条件", "设立", "申请", "核准", "具备"]):
        return f"应把“{fragment}”转化为准入核对项，逐项确认适用主体、资格条件、禁止情形、申请材料和生效节点。"
    if any(word in s for word in ["关联方", "关联关系", "关联交易"]):
        return f"应在事项启动阶段识别“{fragment}”，同步核对关联关系、交易类型、金额口径、审批层级和后续披露义务。"
    if any(word in s for word in ["职责", "负责", "履行", "组织", "建立", "制定"]):
        return f"应把“{fragment}”拆分为岗位职责和流程节点，明确主责部门、协同部门、完成标准和留痕文件。"
    if ev.time_limit != "未明确":
        return f"应对“{fragment}”设置办理节点，按“{ev.time_limit}”推进，并保存通知、审批、报送或披露过程记录。"
    return f"应把“{fragment}”转化为{core}项下的可检查要求，明确适用主体、办理动作、依据条款和留痕材料。"


def step_actions(step: str) -> list[str]:
    if "触发" in step or "识别" in step:
        return [
            "登记触发事实，说明事项来源、发生时间、涉及主体、金额或影响范围。",
            "核对来源页中的适用对象和触发条件，判断是否进入审批、报告、披露或整改路径。",
            "无法确认适用范围时，标注待核对并回看 raw 原文或监管通知。"
        ]
    if "材料" in step or "准备" in step:
        return [
            "按清单收集事实材料、合同或议案文本、内部审查意见、风险评估和历史审批记录。",
            "把材料与条款要素逐项勾稽，确认主体、动作、对象、条件、时限和后果没有缺项。",
            "对扫描文本不完整、条款缺页或材料来源不明的部分单独列入待核对。"
        ]
    if "审查" in step or "核验" in step:
        return [
            "由合规、法律、风险或业务主责部门对适用条款、权限边界、禁止情形和责任后果形成审查意见。",
            "涉及关联关系、股权、任职资格、资金来源或客户权益的，应补做穿透核验。",
            "审查意见应写明依据条款、结论、例外或保留意见。"
        ]
    if "回避" in step:
        return [
            "先识别与事项存在利害关系的董事、股东、管理人员或其他表决主体。",
            "在会议材料和表决统计中单独记录回避主体、回避原因、有效表决人数和表决结果。",
            "如回避后无法达到审议或表决条件，应按章程、议事规则或监管要求启动替代程序。"
        ]
    if "审批" in step or "审议" in step or "表决" in step or "批准" in step:
        return [
            "确认应提交的治理机构或审批层级，避免以部门审批替代董事会、股东会或监管许可程序。",
            "会前发送议案和必要材料；需要回避或独立意见的，应在会议前完成提示。",
            "会议或审批结束后留存通知、议案、审查意见、表决结果、决议和授权文件。"
        ]
    if "报告" in step or "报送" in step or "披露" in step:
        return [
            "确认报送或披露对象、渠道、时限、格式和签发责任。",
            "报送披露内容应与内部审批结论、会议决议和事实材料一致。",
            "留存报送回执、披露截图、公告文本、监管反馈和后续更正记录。"
        ]
    if "整改" in step or "后续" in step or "跟踪" in step:
        return [
            "将监管反馈、内部审查问题或未完成事项纳入整改台账，明确责任人和完成时限。",
            "整改完成后由主责部门和合规部门复核证据，必要时向董事会、监管机构或信息披露渠道反馈。",
            "把问题根因同步回写到制度、流程、模板或培训材料中。"
        ]
    return [
        "明确该节点的主责部门、协同部门和输出文件。",
        "把办理动作拆成可核对事项，并逐项链接来源条款。",
        "节点完成后保存审批、沟通、报送或整改证据。"
    ]


def concise_feature(values: str, fallback: str) -> str:
    if not values or values == "相关主体":
        return fallback
    parts = [compact(part.strip(" ；;。"), 22) for part in values.split("、") if part.strip()]
    cleaned = [part for part in parts if part and part != "未明确"]
    return "、".join(cleaned[:5]) if cleaned else fallback


CONCEPT_FEATURES: dict[str, tuple[str, str, str, str]] = {
    "关联交易": (
        "保险公司、银行保险机构、控股股东、实际控制人、董事和高级管理人员",
        "关联方识别、交易审查、回避表决、董事会审议、报告披露、专项审计",
        "专项审计至少每年一次；具体报告、披露或损失处置时限按交易类型回查来源条款",
        "可能触发责令改正、限制股东权利、责令转让股权、监管措施或行政处罚"
    ),
    "信息披露": (
        "保险公司、董事会、信息披露负责人、承办部门",
        "重大事项识别、内容审核、公开披露、监管报告、更正补充",
        "临时披露、年度披露、定期报告等时点应分别核对来源条款",
        "可能触发责令改正、监管谈话、公开披露瑕疵责任或行政处罚"
    ),
    "任职资格": (
        "董事、监事、高级管理人员、关键岗位拟任人员",
        "资格核对、申请核准、任命生效、履职评价、离任审计",
        "任前核准、任期届满、离任和监管要求的补正时限分别核对来源条款",
        "可能影响任命生效、履职资格、监管评价、问责或行政处罚"
    ),
    "消费者权益保护": (
        "保险机构、销售人员、消保部门、投诉处理部门",
        "产品审查、销售适当性、信息告知、投诉处理、重大事项报告",
        "投诉办理、重大事件报告和整改反馈按来源条款分别控制",
        "可能触发监管评价扣分、责令整改、通报、处罚或内部问责"
    ),
    "反洗钱": (
        "金融机构、客户、受益所有人、反洗钱岗位",
        "客户身份识别、风险评级、交易监测、资料保存、可疑交易报告",
        "客户尽调、资料保存和可疑交易报告均有独立时限，应按具体条款核对",
        "可能触发责令整改、罚款、监管措施、岗位责任追究"
    ),
    "数据安全": (
        "银行保险机构、数据处理部门、信息科技部门、业务部门",
        "分类分级、权限控制、外部提供、事件处置、监管统计报送",
        "数据事件、监管统计和外部提供节点按具体条款设置办理时限",
        "可能触发整改、监管通报、行政处罚或信息科技风险问责"
    ),
}


def concept_features_for(tag: str, evs: list[Evidence]) -> tuple[str, str, str, str]:
    if tag in CONCEPT_FEATURES:
        return CONCEPT_FEATURES[tag]
    subjects, actions, times, consequences = evidence_features(evs)
    clean_times = []
    for item in times.split("、"):
        item = item.strip()
        if item and len(item) <= 18 and not any(word in item for word in ["报告", "披露", "申请材料"]):
            clean_times.append(item)
    clean_consequences = []
    for item in consequences.split("、"):
        item = item.strip()
        if item and any(word in item for word in ["责令", "处罚", "罚款", "限制", "撤销", "整改", "问责", "赔偿", "监管措施"]):
            clean_consequences.append(compact(item, 24))
    return (
        concise_feature(subjects, "需结合具体条款确认主体"),
        concise_feature(actions, "需结合专题页确认办理动作"),
        "、".join(clean_times[:4]) if clean_times else "本概念未聚合到稳定统一时限，按来源条款逐项核对",
        "、".join(clean_consequences[:4]) if clean_consequences else "可能涉及整改、监管措施、处罚或内部问责，按来源条款确认",
    )


def concept_page(tag: str, evs: list[Evidence]) -> str:
    related = related_topics_for_tags([tag])
    definition, boundary, warning = concept_guidance(tag, evs)
    scenario_links = [name for name, scenario_tags, _ in SCENARIOS if tag in scenario_tags]
    checklist_links = [name for name, checklist_tags, _ in CHECKLISTS if tag in checklist_tags]
    key_subjects, key_actions, key_times, key_consequences = concept_features_for(tag, evs)
    out = [
        frontmatter("概念页", tag, {"evidence_count": len(evs), "style": '"concept-brief"'}),
        f"# {tag}",
        "",
        "## 一、工作定义",
        definition,
        "",
        "## 二、适用边界",
        boundary,
        "",
        f"- 高频主体：{key_subjects}",
        f"- 高频动作：{key_actions}",
        f"- 时限控制：{key_times}",
        f"- 责任后果：{key_consequences}",
        "",
        "## 三、实务判断方法",
        f"1. 先判断当前事项是否属于“{tag}”的触发范围，并记录触发事实。",
        "2. 再进入相关专题页形成跨制度口径，进入场景页确认办理流程，进入清单页核对材料和时限。",
        "3. 最后回到来源证据页核对条款号、适用主体、触发条件和责任后果；必要时回看 raw 原文。",
        "",
        "## 四、常见误区",
        warning,
        "",
        "## 五、相关专题、场景和清单",
    ]
    if related:
        out.extend([f"- {wikilink(f'wiki/专题/{topic}.md', topic)}" for topic in related])
    if scenario_links:
        out.extend([f"- {wikilink(f'wiki/场景/{scenario}.md', scenario)}" for scenario in scenario_links[:8]])
    if checklist_links:
        out.extend([f"- {wikilink(f'wiki/清单/{checklist}.md', checklist)}" for checklist in checklist_links[:8]])
    if not related and not scenario_links and not checklist_links:
        out.append("- 暂无直接关联页面，可从证据总索引继续检索。")
    out += [
        "",
        "## 六、代表证据",
    ]
    out.extend(evidence_table(evs, 15))
    return "\n".join(out)


if __name__ == "__main__":
    rebuild()
