// =====================================================================
// IntDevTools 公开演示 · 虚构样例数据
// 本文件所有内容均为公开示例数据，不包含任何真实公司/产品/知识库信息。
// All data here is fictional sample data for the public demo only.
// =====================================================================

window.DEMO = (function () {

  // ---- 虚构项目信息 ----
  const project = {
    id: "SC-2026-001",
    nameZh: "某传感器控制器开发",
    nameEn: "Sensor Controller Development (Sample)",
    productType: "controller",
    productTypeLabel: "控制器 / 工业控制单元（示例）",
    owner: "demo@example.com",
    difficulty: "medium",
    level: "L2",
    levelLabel: "标准开发 — 常规功能 / 模块级变更"
  };

  // ---- 需求列表（REQM）----
  const requirements = [
    {
      id: "REQ-001",
      title: "支持 0.3~0.5 m 检测距离（透过型），带灵敏度调节",
      category: "额定性能",
      priority: "高",
      status: "已评审",
      source: "市场部（示例）",
      syraCount: 2
    },
    {
      id: "REQ-002",
      title: "环境光抗扰 ≥ 10,000 lx（含阳光直射场景）",
      category: "电气环境",
      priority: "高",
      status: "评审中",
      source: "客户（示例）",
      syraCount: 1
    },
    {
      id: "REQ-003",
      title: "输出接口 NPN / PNP 可选，响应时间 ≤ 1 ms",
      category: "额定性能",
      priority: "中",
      status: "草稿",
      source: "内部规范（示例）",
      syraCount: 1
    }
  ];

  // ---- AI 辅助评估结果（需求导入步骤）----
  const aiAssessment = {
    reqId: "REQ-002",
    matchedStandards: [
      { id: "STD-01", label: "IEC 60947-5-2（示例引用）", note: "接近/光电开关通用要求" },
      { id: "STD-02", label: "IEC 61000-4-3（示例引用）", note: "辐射电磁场抗扰度" }
    ],
    suggestedVerification: [
      "环境光抗扰试验（白炽灯 / 荧光灯 / 太阳光三种光源）",
      "检测距离随环境光强度变化的稳定性测试",
      "强光误触发测试（瞬时光斑照射）"
    ],
    level: "L2",
    levelLabel: "标准开发 — 常规功能 / 模块级变更",
    reasons: [
      "常规功能增强，无新平台 / 无安全关键等级提升",
      "涉及光学 + 电气跨模块设计，需模块级测试",
      "已有同类产品设计基线可复用（示例）"
    ]
  };

  // ---- 设计文档摘要（SYRA）----
  const designDoc = {
    title: "系统要件定义（SYRA）摘要 · 传感器控制器",
    sections: [
      { name: "检测电路", content: "光电二极管 + 前置放大 + 比较器，输出数字电平。", tags: ["光学", "模拟电路"] },
      { name: "环境光抑制", content: "载波调制（10 kHz）+ 带通滤波，抑制直流/低频环境光。", tags: ["抗扰", "信号处理"] },
      { name: "输出接口", content: "NPN / PNP 可选，推挽输出 + 短路保护。", tags: ["输出", "保护"] },
      { name: "供电", content: "DC 10~30 V，反接保护。", tags: ["电源"] }
    ]
  };

  // ---- 审查规则（示例规则库）----
  const reviewRules = [
    { id: "R-202", name: "电磁兼容设计检查", desc: "载波/开关频率应与常见干扰源频段错开" },
    { id: "R-118", name: "参数容差检查", desc: "关键性能参数应定义范围与容差" },
    { id: "R-007", name: "术语一致性", desc: "同一概念在全文档中使用统一术语" }
  ];

  // ---- AI 审查发现（设计审查步骤）----
  const reviewFindings = [
    {
      id: "F-01",
      severity: "高",
      rule: "R-202 电磁兼容设计检查",
      title: "载波调制频率与光源频闪谐波存在重叠风险",
      detail: "日光灯/LED 灯频闪（100~120 Hz 及其谐波）可能与 10 kHz 载波边带重叠，需补充频谱分析与实测验证。",
      suggestion: "建议在 SYRA 中补充频段错开分析，并在 SYQT 增加强光频闪场景测试。",
      confidence: 0.92,
      status: "待确认"
    },
    {
      id: "F-02",
      severity: "中",
      rule: "R-118 参数容差检查",
      title: "灵敏度调节范围未定义下限",
      detail: "未定义灵敏度调节的增益裕量下限，量产批次间检测距离可能缩水至规格外。",
      suggestion: "建议定义调节范围下限（如 ≥ 标称增益的 80%），并加入出厂校准项。",
      confidence: 0.85,
      status: "待确认"
    },
    {
      id: "F-03",
      severity: "低",
      rule: "R-007 术语一致性",
      title: "术语不一致：\"感测距离\" 与 \"检测距离\" 混用",
      detail: "SYRA 第 2.1 节使用\"感测距离\"，第 4 节使用\"检测距离\"，同一参数两种写法。",
      suggestion: "统一为\"检测距离\"，并同步 REQM/SYQT 引用。",
      confidence: 0.98,
      status: "待确认"
    }
  ];

  // ---- 评价基准分类（9 大分类，通用）----
  const evalCategories = [
    { id: "01", name: "额定性能", items: ["消耗电流 / 功率", "工作电压范围", "检测距离 / 精度", "响应时间", "输出特性"] },
    { id: "02", name: "电气环境", items: ["ESD 静电放电", "浪涌抗扰", "电快速瞬变脉冲群", "辐射电磁场抗扰"] },
    { id: "03", name: "环境适应性", items: ["高温试验", "低温试验", "温湿度循环"] },
    { id: "05", name: "安全性", items: ["介电强度", "接地连续性"] },
    { id: "07", name: "可用性", items: ["设置便利性", "指示灯辨识度"] }
  ];

  // ---- AI 生成的评价清单（评价基准步骤）----
  const evalChecklist = [
    { cat: "01 额定性能", item: "消耗电流 / 功率", severity: "必须", std: "STD-01" },
    { cat: "01 额定性能", item: "工作电压范围（DC 10~30 V）", severity: "必须", std: "STD-01" },
    { cat: "01 额定性能", item: "检测距离 / 精度（0.3~0.5 m）", severity: "必须", std: "STD-01" },
    { cat: "01 额定性能", item: "响应时间 ≤ 1 ms", severity: "必须", std: "STD-01" },
    { cat: "01 额定性能", item: "灵敏度调节范围下限", severity: "推荐", std: "产品基线（示例）" },
    { cat: "02 电气环境", item: "ESD 静电放电（接触 ±4 kV / 空气 ±8 kV）", severity: "必须", std: "STD-02" },
    { cat: "02 电气环境", item: "浪涌抗扰（电源线 ±1 kV）", severity: "必须", std: "STD-02" },
    { cat: "02 电气环境", item: "电快速瞬变脉冲群（电源线 ±2 kV）", severity: "必须", std: "STD-02" },
    { cat: "02 电气环境", item: "辐射电磁场抗扰（10 V/m，含光源频闪场景）", severity: "推荐", std: "审查发现 F-01（示例）" },
    { cat: "03 环境适应性", item: "高温试验（+70 ℃）", severity: "推荐", std: "STD-03" },
    { cat: "03 环境适应性", item: "低温试验（-25 ℃）", severity: "推荐", std: "STD-03" },
    { cat: "05 安全性", item: "介电强度（AC 1500 V / 1 min）", severity: "必须", std: "STD-01" },
    { cat: "05 安全性", item: "接地连续性（保护接地端子）", severity: "必须", std: "STD-01" },
    { cat: "07 可用性", item: "指示灯颜色 / 状态辨识", severity: "参考", std: "产品基线（示例）" }
  ];

  // ---- 知识沉淀（步骤四）----
  const kbContribution = {
    entryId: "KB-2026-031",
    title: "光电传感器控制器 · 环境光抗扰设计要点",
    category: "20_Products / 60_Evaluation_Criteria（示例分类）",
    tags: ["环境光", "抗扰", "载波调制", "灵敏度"],
    body: [
      "载波调制频率应避开常见光源频闪（100~120 Hz）谐波频段，必要时提高载波频率并补充频谱分析。",
      "灵敏度调节需定义增益裕量下限（示例：≥ 标称增益 80%），防止批次间检测距离缩水。",
      "环境光抗扰验证建议覆盖白炽灯 / 荧光灯 / 太阳光三种光源。"
    ],
    source: "审查发现 F-01 / F-02（人工确认后沉淀）",
    reusableFor: "某传感器控制器改版、同类光电类产品新项目"
  };

  const kbEntries = [
    { id: "KB-2026-030", title: "接近传感器 · 输出接口短路保护选型要点", category: "20_Products（示例）", tags: ["输出", "保护"], added: "2 周前" },
    { id: "KB-2026-029", title: "压力传感器 · EMC 滤波布局基线", category: "20_Products（示例）", tags: ["EMC", "布局"], added: "1 个月前" },
    { id: "KB-2025-118", title: "通用开发流程模板 · L2 标准开发", category: "40_Process（示例）", tags: ["流程", "L2"], added: "3 个月前" }
  ];

  // ---- 数据流说明（右栏）----
  const flowSteps = [
    { from: "需求管理", to: "设计审查", artifact: "SYRA / SYAD 设计文档", via: "07 数据总线" },
    { from: "设计审查", to: "评价基准", artifact: "审查发现（采纳后）", via: "07 数据总线" },
    { from: "评价基准", to: "需求管理", artifact: "评价清单 → SYQT 补充", via: "07 数据总线" },
    { from: "设计审查", to: "知识库", artifact: "审查经验沉淀（人工确认）", via: "知识流" }
  ];

  return { project, requirements, aiAssessment, designDoc, reviewRules, reviewFindings, evalCategories, evalChecklist, kbContribution, kbEntries, flowSteps };
})();
