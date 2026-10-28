# VitaminStudy · 补充品比较指南

**在线浏览 / Live page:** https://waiyan-so.github.io/VitaminStudy/

一个深色交互网页，按「成分」而不是「品牌」整理 Chemist Warehouse（澳洲）上 1,094 个保健补充品，挑出 14 类最常见的成分，说明怎么比较不同产品，以及谁可能需要、什么情况下考虑、谁要谨慎。

An interactive guide that groups 1,094 Australian supplement products (Chemist Warehouse) by ingredient rather than brand, and explains how to compare variants and who each ingredient may suit.

## 14 类成分 / Categories

镁 Magnesium · 维生素 D Vitamin D · 鱼油 Fish Oil / Omega-3 · 复合维生素 Multivitamin · 益生菌 Probiotic · 维生素 B12 / B 族 B-Group · 维生素 C Vitamin C · 钙 Calcium · 铁 Iron · 葡萄糖胺 Glucosamine · 锌 Zinc · 胶原蛋白 Collagen · 姜黄 Turmeric · 助眠/放松 Sleep & Calm

## 比较方法 / Method

1. **配方类型 Formula type**：单方、经典组合、多成分复方，只在同类之间比较
2. **成分形式 Form**：例如甘氨酸镁 vs 氧化镁、硫酸亚铁 vs 多糖铁
3. **有效量标注 Active amount**：元素量、EPA+DHA、姜黄素、菌株编号，而不是化合物总重
4. **重复与安全 Overlap & safety**：D、B6、铁、维生素 A、锌最容易在多个产品中叠加

## 文件结构 / Structure

```
index.html                         交互网页（自包含，无需服务器）
src/classify.py                    从产品名称清洗、去重并分类
src/guide_content.py               14 类成分的指南内容
src/build.py                       合并数据与内容，生成网页（含中英术语表）
src/template.html                  网页模板
src/build_xlsx.py                  生成 Excel（目前为 10 类旧版）
data/processed/products_classified.json   分类结果
Status_log.md                      项目进度
```

## 重新生成 / Rebuild

原始 CSV 没有放进仓库。把自己的 `chemistwarehouse.csv` 放在本地后：

```bash
python src/classify.py path/to/chemistwarehouse.csv data/processed/products_classified.json
python src/build.py data/processed/products_classified.json out/
cp out/VitaminAdviser_Top10.html index.html
```

## 限制 / Limitations

- 分类和剂量只从产品名称解析，具体成分请以实际标签为准
- 本阶段未引用 NHMRC 营养参考值（RDI/UL）与 RACGP 指引，也未比较价格
- 产品数据为 2026 年 10 月抓取的快照

## 免责声明 / Disclaimer

本项目只供研究与初步筛选，不能替代注册医生、药剂师或营养师的个别评估。
For research and general information only — not medical advice. Consult a GP, pharmacist or dietitian before starting supplements.
