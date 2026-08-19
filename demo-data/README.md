# 虚构样例数据 · Sample Data（全部为公开示例）

本目录是 IntDevTools 公开演示的**虚构样例数据**，用于展示「需求导入 → AI 设计审查 → AI 生成评价基准 → 知识沉淀」链路中每个工具的输入/输出形态。

> ⚠️ 所有内容均为公开示例，**不包含**任何真实公司、产品型号或内部知识库信息。
> All content here is fictional sample data. No real company, product model, or internal KB content is included.

## 目录结构

```
demo-data/
├── kb/                     # 示例知识库（通用分类，非真实 KHDB）
│   ├── 10_standards.md     # 标准（示例引用）
│   ├── 20_products.md      # 产品知识/验证条目（通用）
│   └── 40_process.md       # 开发流程模板（示例）
└── project_sc2026/         # 虚构项目「某传感器控制器开发」样例
    ├── project.md          # 项目画像（产品大类 / 开发等级）
    ├── requirements.csv    # REQM 需求清单
    ├── syra_design.md      # 设计文档摘要（审查对象）
    ├── review_report.md    # AI 审查报告（人工确认后）
    └── eval_checklist.csv  # 评价/测试清单（生成结果）
```

## 与公开演示的关系

- `demo/index.html` 内的交互演示使用与本目录**同源**的样例数据（演示内嵌一份，本目录为可读文件版）。
- 交互演示是「能打开」的入口；本目录是给面试官/读者逐文件查看的静态样例。
