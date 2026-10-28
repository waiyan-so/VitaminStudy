"""
build.py — 合并分类数据与指南内容，生成交互 HTML 与 Excel。
用法: python src/build.py data/products_classified.json output/
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from guide_content import GUIDE, OVERVIEW  # noqa: E402

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
ORDER = ["magnesium", "vitd", "omega3", "multi", "probiotic", "vitb", "vitc", "calcium", "iron", "glucosamine",
         "zinc", "collagen", "turmeric", "sleep"]

items = json.load(open(SRC, encoding="utf-8"))

# 医学名词与成分名中英对照：每个成分页只在第一次出现时标注英文，已带英文或括号的跳过
GLOSSARY = [
    ("2 型糖尿病", "Type 2 diabetes"), ("糖尿病", "Diabetes"), ("周围神经病变", "Peripheral neuropathy"),
    ("神经毒性", "Neurotoxicity"), ("甘油三酯", "Triglycerides"), ("类风湿关节炎", "Rheumatoid arthritis"),
    ("骨关节炎", "Osteoarthritis"), ("高钙血症", "Hypercalcaemia"), ("结节病", "Sarcoidosis"),
    ("甲状旁腺疾病", "Parathyroid disease"), ("血色病", "Haemochromatosis"), ("恶性贫血", "Pernicious anaemia"),
    ("缺铁性贫血", "Iron-deficiency anaemia"), ("乳糜泻", "Coeliac disease"), ("克罗恩病", "Crohn's disease"),
    ("炎症性肠病", "IBD"), ("心房颤动", "Atrial fibrillation"), ("偏头痛", "Migraine"),
    ("双膦酸盐", "Bisphosphonates"), ("骨质疏松", "Osteoporosis"), ("糖皮质激素", "Corticosteroids"),
    ("甲状腺素", "Levothyroxine"), ("四环素", "Tetracyclines"), ("喹诺酮类", "Quinolones"),
    ("抗凝/抗血小板药", "Anticoagulants/Antiplatelets"), ("抗凝药", "Anticoagulants"), ("菌血症", "Bacteraemia"),
    ("真菌血症", "Fungaemia"), ("肾结石", "Kidney stones"), ("草酸钙", "Calcium oxalate"),
    ("肾功能不全", "Kidney impairment"), ("抗生素相关腹泻", "Antibiotic-associated diarrhoea"),
    ("旅行者腹泻", "Traveller's diarrhoea"), ("肠绞痛", "Infant colic"), ("高血压", "Hypertension"),
    ("自身免疫病", "Autoimmune disease"), ("哮喘", "Asthma"), ("严重免疫低下", "Immunocompromised"),
    ("绝经后", "Postmenopausal"), ("减重手术", "Bariatric surgery"), ("胃切除", "Gastrectomy"),
    ("吸收不良", "Malabsorption"), ("致畸", "Teratogenic"), ("铜缺乏", "Copper deficiency"),
    ("叶酸", "Folate"), ("碘", "Iodine"), ("硒", "Selenium"), ("β-胡萝卜素", "Beta-carotene"),
    ("软骨素", "Chondroitin"), ("透明质酸", "Hyaluronic acid"), ("胡椒碱", "Piperine"), ("姜黄素", "Curcumin"),
    ("褪黑素", "Melatonin"), ("牛磺酸", "Taurine"), ("虾青素", "Astaxanthin"), ("槲皮素", "Quercetin"),
    ("紫锥菊", "Echinacea"), ("辣根", "Horseradish"), ("青口贝", "Green-lipped mussel"), ("乳香", "Boswellia"),
    ("菊粉", "Inulin"), ("益生元", "Prebiotic"), ("生物类黄酮", "Bioflavonoids"),
    ("缬草", "Valerian"), ("L-茶氨酸", "L-Theanine"), ("南非醉茄", "Ashwagandha"),
    ("铁蛋白", "Ferritin"), ("黄疸", "Jaundice"), ("睡眠呼吸暂停", "Sleep apnoea"), ("抑郁", "Depression"),
]


def annotate_text(t, done):
    """在字符串中为尚未标注过的术语加上英文，返回新字符串"""
    for zh, en in GLOSSARY:
        if zh in done:
            continue
        if en.lower() in t.lower():
            done.add(zh)
            continue
        for m in re.finditer(re.escape(zh), t):
            nxt = t[m.end():m.end() + 2]
            prev = t[max(0, m.start() - 1):m.start()]
            if zh == "糖尿病" and prev == "型":
                continue
            if zh == "骨质疏松" and nxt[:1] in "药风":
                continue
            if re.match(r"\s?[A-Za-z]|[（(][A-Za-z]", nxt):
                done.add(zh)
                break
            tail = " " if re.match(r"[\u4e00-\u9fff]", nxt[:1] or "") else ""
            t = t[:m.end()] + f" {en}" + tail + t[m.end():]
            done.add(zh)
            break
    return t


def annotate(g):
    """按页面渲染顺序逐字段标注"""
    done = set()
    g = json.loads(json.dumps(g, ensure_ascii=False))
    g["tagline"] = annotate_text(g["tagline"], done)
    g["test"] = annotate_text(g["test"], done)
    for key in ["who", "when", "caution"]:
        g[key] = [annotate_text(x, done) for x in g[key]]
    g["forms"] = [[f[0], annotate_text(f[1], done), f[2]] for f in g["forms"]]
    g["combos"] = [[annotate_text(c[0], done), c[1], annotate_text(c[2], done)] for c in g["combos"]]
    for key in ["compare", "food", "myths"]:
        g[key] = [annotate_text(x, done) for x in g[key]]
    return g


def stats_for(k):
    """计算每个成分的主成分数、附加成分数与变体分布"""
    prim = [i for i in items if i["cat"] == k]
    sec = [i for i in items if k in i["tags"] and i["cat"] != k and not i["non_supp"]]
    return {"primary": len(prim), "secondary": len(sec), "total": len(prim) + len(sec),
            "variants": Counter(i["variant"] for i in prim).most_common()}


stats = {k: stats_for(k) for k in ORDER}
# 只保留与前十相关的产品，字段缩写以减小页面体积
prods = [{"n": i["name"], "b": i["brand"], "u": i["url"], "r": i["rating"], "rv": i["reviews"],
          "c": i["cat"], "t": [t for t in i["tags"] if t in ORDER], "v": i["variant"], "f": i["format"],
          "g": i["group"], "s": i["strength"], "q": i["count"], "x": i["non_supp"]}
         for i in items if not i["non_supp"] and (i["cat"] in ORDER or any(t in ORDER for t in i["tags"]))]

OVERVIEW["overlap"] = [[r[0], r[1], annotate_text(r[2], set())] for r in OVERVIEW["overlap"]]
data = {"order": ORDER, "guide": {k: annotate(GUIDE[k]) for k in ORDER}, "overview": OVERVIEW, "stats": stats, "products": prods,
        "meta": {"unique": len(items), "nonSupp": sum(i["non_supp"] for i in items)}}
tpl = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
html = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
(OUT / "VitaminAdviser_Top10.html").write_text(html, encoding="utf-8")
print("html bytes", len(html.encode()), "products", len(prods))
for k in ORDER:
    print(k, stats[k]["primary"], stats[k]["secondary"])
