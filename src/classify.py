"""
classify.py — 把 Chemist Warehouse 爬取的产品名清洗、去重，并按主成分 / 配方类型 / 形式 / 剂型 / 人群分类。
输入: chemistwarehouse.csv（原始数据，不修改）
输出: data/products_classified.json
"""
import csv
import json
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "chemistwarehouse.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/products_classified.json"

# ---------- 成分识别规则（用于标签，一个产品可有多个成分） ----------
ING = {
    "magnesium": r"magnes|\bmag\b|pharma mag|muscleze",
    "vitd": r"vitamin d|vit\.? ?d\b|\bd3\b|\bd 400\b|vitamin d3|\bc,? d\b|\bc \+ d\b",
    "omega3": r"fish oil|omega|krill|cod liver|\bdha\b|\bepa\b|algae oil|algal",
    "multi": r"multi(?!-?strain| strain| action)|ultivite|elevit|centrum(?! kids incremin)|pregnancy and breastfeeding|preconception|multivite",
    "probiotic": r"probiotic|inner health|floractiv|lactobac|acidophil|\bbiome\b|saccharomyces|bifido|cfu",
    "vitb": r"\bb12\b|b-?group|b complex|vitamin b|\bb6\b|methylcobalamin|berocca|energy b|stress\s?b",
    "vitc": r"\bc,? d\b|\bc \+ d\b|vitamin c|vit\.? ?c\b|\+ ?c\b|ester-?c|\bc 1000\b|\bc1000\b|redoxon|ferro plus c|garlic \+ c",
    "calcium": r"calcium|\bcal\b|caltrate",
    "iron": r"\biron\b|ferro|ferrous|floradix|spatone|maltofer",
    "glucosamine": r"glucosamine|chondroitin|joint|osteo eze|\bmsm\b|celadrin",
    "zinc": r"zinc",
    "k2": r"\bk2\b",
    "collagen": r"collagen",
    "turmeric": r"turmeric|curcum|theracurmin",
    "sleep": r"sleep|calm|relax|valerian|passionflower|theanine|ashwag|withania|zizyphus|chamomile|lavender|\bhops\b|5-htp|tryptophan|\bpm\b|night|rest & quiet|stress relief",
    "folate": r"folate|folic",
}

# 主分类的优先顺序（越靠前越优先作为「主成分」）
TOP10 = ["multi", "probiotic", "omega3", "glucosamine", "iron", "calcium",
         "vitd", "magnesium", "vitc", "vitb", "zinc", "collagen", "turmeric", "sleep"]

# 明显非补充品（食品、蜂蜜、奶粉、营养饮料等）
NON_SUPP = r"honey|goat milk|milk powder|ensure|sustagen|souvenaid|apple cider|no-doz|tea bags|\btea\b|xpel|worms|constipation|fibre|metamucil|shake|nail polish"

FORMATS = [
    ("软糖 Gummy", r"gumm|pastille|chew"),
    ("泡腾片 Effervescent", r"efferv|fizz"),
    ("粉 Powder", r"powder|\b\d+\s?g\b(?!.*caps)|sachet|stick"),
    ("液体 Liquid", r"liquid|\bml\b|syrup|shot|elixir|drops|spray|oral liquid"),
    ("胶囊 Capsule", r"caps|softgel|vege cap"),
    ("片 Tablet", r"tab"),
]

GROUPS = [
    ("儿童 Kids", r"kid|child|junior|toddler|baby(?! boomer)|pentavite"),
    ("孕期/备孕 Pregnancy", r"pregnan|prenatal|preconception|elevit|breastfeed|conceive"),
    ("50+ / 长者", r"50\+|65\+|60\+|over 50|over50|senior|baby boomer"),
    ("女性 Women", r"wom[ae]n|female|\bher\b|menopaus|perimenopaus"),
    ("男性 Men", r"\bmen\b|\bmens\b|men'?s|male|\bhim\b"),
]


def first_match(table, name):
    """返回第一个匹配的标签，否则返回 '其他'"""
    for label, pat in table:
        if re.search(pat, name, re.I):
            return label
    return "其他/未标注"


def parse_count(name):
    """从产品名解析粒数/包装量"""
    m = re.search(r"(\d+)\s?(?:x\s?\d+\s?)?(tablets?|capsules?|caps|softgels?|gummies|pastilles|pack|sachets|vege)",
                  name, re.I)
    return int(m.group(1)) if m else None


def parse_strength(name):
    """解析产品名里的剂量字段（mg / IU / mcg / billion）"""
    vals = re.findall(r"(\d[\d,\.]*)\s?(mg|iu|mcg|µg|billion|b cfu)\b", name, re.I)
    return ", ".join(f"{v}{u.upper() if u.lower()=='iu' else u}" for v, u in vals) or ""


def sub_variant(cat, name, tags):
    """各品类内部的形式 / 变体细分，是比较时的关键维度"""
    n = name.lower()
    if cat == "magnesium":
        if "glycinate" in n or "bisglycinate" in n: return "甘氨酸镁 Glycinate"
        if "citrate" in n: return "柠檬酸镁 Citrate"
        if "orotate" in n: return "乳清酸镁 Orotate"
        if "threonate" in n: return "苏糖酸镁 L-Threonate"
        if re.search(r"cream|oil|spray|gel|flakes|bath", n): return "外用 Topical（乳霜/喷雾）"
        if re.search(r"\bgly\b|chelate|bisgly", n): return "甘氨酸镁 Glycinate"
        if "calcium" in tags: return "镁 + 钙 (+D) 复配"
        if re.search(r"powder|muscleze|\d+g\b", n): return "粉剂复配 Powder blend"
        if re.search(r"ashwag|theanine", n): return "助眠/放松复配"
        if re.search(r"turmeric", n): return "肌肉/抽筋复配"
        if re.search(r"gumm|pastille|efferv", n): return "软糖/泡腾（形式多不标明）"
        if re.search(r"sleep|night|pm|calm|stress", n): return "助眠/放松复配"
        if re.search(r"muscle|cramp|sport|recover", n): return "肌肉/抽筋复配"
        return "未标明形式（多为氧化镁/混合盐）"
    if cat == "vitd":
        if "k2" in tags: return "D3 + K2 (±镁)"
        if "calcium" in tags: return "D3 + 钙"
        if "vitc" in tags or "zinc" in tags: return "D3 + 免疫复配 (C/锌)"
        if re.search(r"gumm|chew|liquid|drops|spray", n): return "D3 单方（咀嚼/液体）"
        return "D3 单方"
    if cat == "omega3":
        if "krill" in n: return "磷虾油 Krill"
        if "cod liver" in n: return "鳕鱼肝油 Cod liver"
        if re.search(r"plant|algae|algal|vegan|flax", n): return "植物/藻油 Plant/Algae"
        if re.search(r"pregnan", n): return "孕期 DHA"
        if re.search(r"kid|child|junior", n): return "儿童 DHA/鱼油"
        if re.search(r"3-6-9|3-11", n): return "Omega 3-6-9 混合"
        if "glucosamine" in tags or re.search(r"joint|vision|brain|\+ ?d3|eye", n): return "鱼油 + 功能复配（关节/眼/脑/D）"
        if re.search(r"double|triple|super|high strength|concentrat|platinum|ultra|1500|2000|4x|4 x|epa/dha|\bdha\b", n): return "高浓度鱼油 Concentrated"
        return "标准鱼油 1000mg"
    if cat == "multi":
        g = first_match(GROUPS, name)
        return g if g != "其他/未标注" else "通用成人 Adult"
    if cat == "probiotic":
        if re.search(r"pregnan|breastfeed", n): return "孕期/哺乳"
        if re.search(r"wom[ae]n|vaginal|thrush|menopaus|perimenopaus|urogen|flora balance", n): return "女性/私处健康"
        if re.search(r"kid|child|baby|infant|junior", n): return "儿童/婴儿"
        if re.search(r"60\+|50\+|over 50|senior", n): return "长者 50+/60+"
        if re.search(r"ibs|bloat|gut relief|digest|travel|antibiotic|floractiv|saccharomyces|\bsb\b", n): return "特定用途（肠易激/腹泻/抗生素）"
        if re.search(r"immune|hayfever|eczema|pms|cholesterol", n): return "特定用途（免疫/过敏/经前）"
        if re.search(r"skin|mood|mind|sleep|weight|metabol|energy|slim|shape|collagen|hydration|milk thistle|iron", n): return "营销延伸（皮肤/情绪/体重等）"
        if re.search(r"gumm|prebiotic|fibre", n): return "软糖/益生元复配"
        return "通用广谱 Broad spectrum"
    if cat == "vitb":
        if "b12" in n: return "B12 单方"
        if "b6" in n and "group" not in n: return "B6 单方"
        if re.search(r"berocca|energy|efferv|stress", n): return "能量/压力 B 复配（泡腾等）"
        if re.search(r"\bb[1-3]\b", n): return "其他单一 B（B1/B2/B3）"
        return "B 族 B-group / B complex"
    if cat == "vitc":
        if "iron" in tags: return "铁 + C"
        if "zinc" in tags or "vitd" in tags: return "C + 锌 (+D) 免疫复配"
        if re.search(r"echinacea|garlic|horseradish|olive leaf|elder", n): return "C + 草本免疫复配"
        if re.search(r"quercetin|astaxanthin|bioflav", n): return "C + 抗氧化物复配"
        if re.search(r"liposom|ester-?c", n): return "C 特殊形式（脂质体/Ester-C）"
        if re.search(r"efferv|gumm|chew|powder|liquid", n): return "C 单方（咀嚼/泡腾/粉/液体）"
        return "C 单方 片剂"
    if cat == "calcium":
        if "magnesium" in tags and "vitd" in tags: return "钙 + 镁 + D3"
        if "vitd" in tags: return "钙 + D3"
        if "magnesium" in tags: return "钙 + 镁"
        if re.search(r"kid|child", n): return "儿童钙"
        if "caltrate" in n: return "名称未写复配（Caltrate，需看标签）"
        return "钙单方"
    if cat == "iron":
        if re.search(r"kid|child|incremin", n): return "儿童铁"
        if re.search(r"liquid|floradix|spatone|\bml\b|sachet|syrup", n): return "液体/天然铁 Liquid"
        if re.search(r"liver", n): return "天然来源（牛肝等）"
        if "vitc" in tags or "ferro plus c" in n: return "铁 + C"
        if re.search(r"maltofer|polymaltose|gentle|bisglycinate|glycinate|amino|chelat|ultiboost|bio iron|sustain", n): return "温和型（多糖铁/螯合/甘氨酸亚铁）"
        if re.search(r"gumm|melt|chew", n): return "软糖/口溶片"
        if re.search(r"\bb\b|b vitamin|b\+|energy|women|premium", n): return "铁 + B族/女性复配"
        return "未标明形式（片/胶囊）"
    if cat == "glucosamine":
        if "omega3" in tags: return "葡萄糖胺 + 鱼油"
        if "chondroitin" in n: return "葡萄糖胺 + 软骨素"
        if re.search(r"turmeric|curcum", n): return "其他关节方（姜黄/青口贝/MSM）"
        if "hcl" in n or "hydrochlor" in n: return "葡萄糖胺单方（盐酸盐 HCl）"
        if "glucosamine" in n: return "葡萄糖胺单方（硫酸盐 Sulfate）"
        if re.search(r"turmeric|curcum|boswell|krill|green[- ]lipped|celadrin|msm", n): return "其他关节方（姜黄/青口贝/MSM）"
        return "关节综合配方"
    if cat == "zinc":
        if re.search(r"kid|child|liquid", n): return "儿童/液体 Kids/Liquid"
        if "vitc" in tags or "vitd" in tags: return "锌 + C (+D) 免疫复配"
        if re.search(r"echinacea|garlic|immune|elder|olive", n): return "锌 + 草本免疫复配"
        if re.search(r"oyster", n): return "牡蛎锌 Oyster"
        if re.search(r"complete|bio zinc|zinc\+|forte|sustain", n): return "锌复合配方（含铜/B6 等）"
        if re.search(r"high strength|\d+mg", n): return "高剂量单方 High strength"
        return "锌单方（形式未标明）"
    if cat == "collagen":
        if re.search(r"hyaluron", n): return "胶原 + 透明质酸 Hyaluronic acid"
        if re.search(r"joint|uc-?ii|type ii", n): return "关节型胶原 Joint/UC-II"
        if re.search(r"powder|\d+g\b|shake|sachet", n): return "粉剂 Powder"
        if re.search(r"liquid|shot|elixir|ml\b|drink", n): return "饮品/口服液 Liquid"
        if re.search(r"gumm|pastille", n): return "软糖 Gummy"
        return "片/胶囊 Tablet/Capsule"
    if cat == "turmeric":
        if re.search(r"theracurmin|meriva|bcm|liposom|advanced|bioactive|curcumin", n): return "姜黄素提取物 / 高吸收形式 Curcumin"
        if re.search(r"joint|pain|glucosamine|boswell|arthr", n): return "关节/疼痛配方"
        if re.search(r"\d{4,}\+?|1-a-day|one-a-day", n): return "等效原料标示（如 30000+）"
        return "姜黄单方 Turmeric"
    if cat == "sleep":
        if re.search(r"kid|child", n): return "儿童助眠"
        if re.search(r"ashwag|withania", n): return "南非醉茄 Ashwagandha 配方"
        if re.search(r"theanine", n): return "L-茶氨酸 L-Theanine 配方"
        if re.search(r"valerian|passionflower|hops|zizyphus|chamomile|lavender", n): return "草本助眠（缬草/西番莲/酸枣仁）"
        if re.search(r"gumm|pastille", n): return "软糖 Gummy"
        if re.search(r"muscle|relax", n): return "肌肉放松/夜间配方"
        return "综合助眠/放松配方"
    return ""


def main():
    rows = list(csv.reader(open(SRC, encoding="utf-8")))[1:]
    seen, items = set(), []
    for r in rows:
        if len(r) < 4 or not r[1].strip():
            continue
        name = r[1].strip()
        if name in seen:
            continue
        seen.add(name)
        url = r[2]
        m = re.search(r"dest=([^&]+)", url)
        if m:  # 去掉广告追踪跳转
            from urllib.parse import unquote
            url = unquote(m.group(1))
        rating, reviews = None, None
        rm = re.match(r"([\d\.]+)\s*\((\d+)\)", r[3] or "")
        if rm:
            rating, reviews = float(rm.group(1)), int(rm.group(2))
        tags = [k for k, p in ING.items() if re.search(p, name, re.I)]
        non_supp = bool(re.search(NON_SUPP, name, re.I)) and not any(
            t in tags for t in ["probiotic", "magnesium", "collagen"])
        # 主分类：在 TOP10 中按优先级挑第一个
        # 规则：多种维生素/益生菌优先；其余取产品名中「最先出现」的成分（品牌通常把主成分放前面）
        cat = next((c for c in ["multi", "probiotic"] if c in tags), None)
        if re.search(r"berocca", name, re.I):
            cat = "vitb"
        if re.search(r"incremin", name, re.I):
            cat = "iron"
        if not cat:
            pos = []
            for c in TOP10:
                if c in tags:
                    mm = re.search(ING[c], name, re.I)
                    pos.append((mm.start(), c))
            cat = min(pos)[1] if pos else None
        # 例外：多种维生素以外的「钙+D」主分类归钙；「D+K2」归 D；「镁+D」等归镁以外按名称首词
        if cat == "multi" and re.search(r"probiotic", name, re.I) and "multi" not in name.lower():
            cat = "probiotic"
        brand = name.split(" ")[0]
        for b in ["Nature's Way", "Nature's Own", "Healthy Care", "Life-Space", "Inner Health", "GO Healthy",
                  "Go Healthy", "Henry Blooms", "Thompsons", "Nutra-Life", "BioCeuticals", "Bioceuticals",
                  "Ethical Nutrients", "The Beauty Chef", "Dr. LeWinn's", "BioHack Wanderlust", "Melrose",
                  "Nature's Sunshine", "Brauer", "Carusos", "Swisse", "Blackmores", "Ostelin", "Cenovis",
                  "Wagner", "Bioglan", "Elevit", "Centrum", "Caltrate", "Berocca", "JSHealth", "Microgenics",
                  "Unichi", "Teddi Lab", "Pentavite", "Floradix", "Spatone", "Kuci", "GEN", "Metagenics",
                  "Herbs of Gold", "Fusion", "Natures Way", "Vitable", "Musashi"]:
            if name.lower().startswith(b.lower()):
                brand = b
                break
        items.append({
            "name": name, "brand": brand, "url": url, "rating": rating, "reviews": reviews,
            "tags": tags, "cat": None if non_supp else cat, "non_supp": non_supp,
            "variant": sub_variant(cat, name, tags) if cat and not non_supp else "",
            "combo": ("单方" if len([t for t in tags if t not in ("sleep",)]) <= 1 else
                      "经典组合" if len(tags) <= 3 else "多成分复方"),
            "format": first_match(FORMATS, name),
            "group": first_match(GROUPS, name),
            "strength": parse_strength(name),
            "count": parse_count(name),
        })
    json.dump(items, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("unique", len(items), "non_supp", sum(i["non_supp"] for i in items))
    from collections import Counter
    print(Counter(i["cat"] for i in items))


if __name__ == "__main__":
    main()
