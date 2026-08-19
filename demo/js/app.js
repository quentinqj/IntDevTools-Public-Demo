/* =====================================================================
   IntDevTools 公开演示 · 交互逻辑
   - 步骤状态机：需求导入 → 设计审查 → 评价基准 → 知识沉淀
   - AI 结果为确定性模拟（规则 + 示例知识库），人工确认后生效
   - 支持 #step=N 与 #export=1（用于截图/录屏的静态导出）
   ===================================================================== */
(function () {
  "use strict";

  var D = window.DEMO;
  var exportMode = /[?&#]export=1/.test(location.hash) || /[?&#]export=1/.test(location.search);

  var state = {
    step: 1,                       // 当前查看步骤
    done: {},                      // 步骤完成标记 {1:true,...}
    findings: {},                  // finding id -> "adopt" | "reject" | "pending"
    checklistConfirmed: false,
    contributionDone: false
  };

  // ---------- helpers ----------
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }
  function sevClass(s) {
    if (s === "必须") return "sev-must";
    if (s === "推荐") return "sev-rec";
    return "sev-ref";
  }

  // ---------- init state ----------
  (function initState() {
    D.reviewFindings.forEach(function (f) { state.findings[f.id] = "pending"; });
    if (exportMode) {
      // 导出模式：整条链路已完成，便于截图
      state.done = { 1: true, 2: true, 3: true, 4: true };
      D.reviewFindings.forEach(function (f) { state.findings[f.id] = "adopt"; });
      state.checklistConfirmed = true;
      state.contributionDone = true;
      document.body.classList.add("export");
    } else {
      state.done = { 1: true };
    }
    var m = location.hash.match(/[?&#]step=(\d)/);
    if (m && m[1] >= 1 && m[1] <= 4) state.step = parseInt(m[1], 10);
    if (state.done[state.step] !== true && exportMode) state.step = 1;
  })();

  // ---------- stepper ----------
  var STEP_DEFS = [
    { zh: "需求导入", en: "Requirements Intake", tool: "01 需求管理" },
    { zh: "AI 设计审查", en: "AI Design Review", tool: "02 设计审查" },
    { zh: "AI 生成评价基准", en: "Evaluation Base", tool: "05 评价基准" },
    { zh: "知识沉淀", en: "Knowledge Loop-back", tool: "知识库" }
  ];

  function renderStepper() {
    var box = $("stepper");
    box.innerHTML = "";
    var hint = el("div", "step-title-hint", "交付链路 · Delivery Chain");
    box.appendChild(hint);
    STEP_DEFS.forEach(function (def, i) {
      var n = i + 1;
      var cls = "step";
      if (n === state.step) cls += " active";
      if (state.done[n]) cls += " done";
      var st = state.done[n] ? "已完成 · Done" : (n === state.step ? "进行中 · In progress" : "待办 · Pending");
      var row = el("div", cls);
      row.innerHTML =
        '<div class="num">' + (state.done[n] ? "&#10003;" : n) + "</div>" +
        '<div><div class="st-name">' + def.zh + '</div>' +
        '<div class="st-en">' + def.en + '</div>' +
        '<div class="st-state">' + st + "</div></div>";
      row.onclick = function () { gotoStep(n); };
      box.appendChild(row);
      if (n < 4) box.appendChild(el("div", "progress-line" + (state.done[n] ? " done" : "")));
    });
    var flow = el("div", "flow-mini");
    flow.innerHTML = "<h4>核心链路 · Core Chain</h4>" +
      '<div class="flow-node">' +
      "<span>① 需求导入</span><span class=\"arrow\">&#8595; AI 辅助评估</span>" +
      "<span>② 设计审查</span><span class=\"arrow\">&#8595; AI 预审 · 人工确认</span>" +
      "<span>③ 评价基准</span><span class=\"arrow\">&#8595; 清单流转</span>" +
      "<span>④ 知识沉淀</span>" +
      "</div>";
    box.appendChild(flow);
  }

  function gotoStep(n) {
    if (exportMode) return;
    if (!state.done[n] && n !== state.step && n > firstUndone()) return; // 只能顺序前进
    state.step = n;
    render();
    if (!state.done[n]) runAi(n);
    history.replaceState(null, "", "#step=" + n + (exportMode ? "&export=1" : ""));
  }
  function firstUndone() {
    for (var i = 1; i <= 4; i++) if (!state.done[i]) return i;
    return 4;
  }

  // ---------- AI thinking simulation ----------
  function runAi(step) {
    var v = $("view");
    var ai = el("div", "ai-thinking", '<span>AI 正在处理</span><span class="bar"><i></i><i></i><i></i></span><span> ' + stepLabel(step) + " …</span>");
    var holder = el("div", "ai-banner", "");
    holder.appendChild(ai);
    v.appendChild(holder);
    setTimeout(function () { if (state.step === step && !state.done[step]) render(); }, 850);
  }
  function stepLabel(n) { return STEP_DEFS[n - 1].zh; }

  // ---------- main render ----------
  function render() {
    renderStepper();
    renderSidebar();
    var v = $("view");
    v.innerHTML = "";
    var fn = [renderStep1, renderStep2, renderStep3, renderStep4][state.step - 1];
    fn(v);
    renderDisclaimer();
  }

  function aiBanner(text) {
    return '<div class="ai-banner"><span class="ai-ico">&#9889;</span><div>' +
      text +
      '<div class="human-note">&#9998; 真实系统中由统一 LLM 网关生成，人工确认后写入（AI 辅助 / 编排，非全自动）。</div></div></div>';
  }

  // ---------- Step 1: Requirements ----------
  function renderStep1(v) {
    var P = D.project;
    var head = el("div", "section-title", "① 需求导入与能力评估 <span class=\"en\">Requirements Intake &amp; Capability Assessment</span>");
    v.appendChild(head);

    var panel = el("div", "panel");
    panel.appendChild(el("div", "panel-title-row", '<h3>需求清单 REQM <span class="en">Requirements</span></h3><span class="tag">工具：01 需求管理（示例）</span>'));
    panel.appendChild(el("div", "desc", "需求登录后，AI 辅助对照标准与产品基线，输出开发等级。以下为虚构项目 " + P.id + " 的示例需求。"));
    var table = el("table");
    table.innerHTML =
      "<thead><tr><th>要求ID</th><th>标题</th><th>大分类</th><th>重要度</th><th>状态</th><th>要求者</th></tr></thead>";
    var tb = el("tbody");
    D.requirements.forEach(function (r) {
      var tr = el("tr");
      if (r.id === D.aiAssessment.reqId) tr.className = "hl";
      var pri = r.priority === "高" ? "pri-high" : (r.priority === "中" ? "pri-mid" : "pri-low");
      tr.innerHTML =
        "<td><b>" + esc(r.id) + "</b></td>" +
        "<td>" + esc(r.title) + "</td>" +
        "<td>" + esc(r.category) + "</td>" +
        '<td class="' + pri + '">' + esc(r.priority) + "</td>" +
        "<td>" + esc(r.status) + "</td>" +
        "<td>" + esc(r.source) + "</td>";
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    panel.appendChild(table);
    v.appendChild(panel);

    var aiPanel = el("div", "panel");
    aiPanel.innerHTML =
      '<div class="panel-title-row"><h3>AI 辅助评估 <span class="en">AI-assisted Assessment</span></h3><span class="tag ai">AI 生成 · 待人工确认</span></div>' +
      '<div class="desc">针对 <b>' + esc(D.aiAssessment.reqId) + "</b> 的评估结果（基于示例规则库 + 示例产品基线）。</div>" +
      aiBanner("AI 已匹配 <b>2 项示例标准</b>、建议 <b>3 条验证条目</b>，并判定开发等级为 <b>L2</b>。") +
      '<div class="spec-grid">' +
      '<div class="spec-box"><div class="k">开发等级判定 · Development Level</div><div class="v level-badge">' + esc(D.aiAssessment.level) + ' <small>· ' + esc(D.aiAssessment.levelLabel) + "</small></div></div>" +
      '<div class="spec-box"><div class="k">判定理由 · Reasons</div><div class="v" style="font-weight:400;font-size:12px;line-height:1.6">' +
      D.aiAssessment.reasons.map(function (r) { return "· " + esc(r); }).join("<br/>") + "</div></div>" +
      "</div>" +
      '<div style="margin-top:12px"><div class="k" style="font-size:11px;color:var(--muted);margin-bottom:4px">匹配标准（示例引用）</div><div>' +
      D.aiAssessment.matchedStandards.map(function (s) { return '<span class="tag" style="margin-right:6px">' + esc(s.id) + " · " + esc(s.label) + "</span>"; }).join("") +
      "</div></div>" +
      '<div style="margin-top:10px"><div class="k" style="font-size:11px;color:var(--muted);margin-bottom:4px">建议验证条目 · Suggested Verification</div>' +
      D.aiAssessment.suggestedVerification.map(function (s, i) { return '<div class="chk-row"><span class="box" style="border-color:var(--accent);color:var(--accent)">' + (i + 1) + "</span><span class=\"item\">" + esc(s) + "</span></div>"; }).join("") +
      "</div>";
    v.appendChild(aiPanel);

    var row = el("div", "btn-row");
    var ok = el("button", "btn primary", "确认评估结果 &#8594; 进入设计审查");
    ok.onclick = function () {
      state.done[1] = true;
      state.step = 2;
      render();
      runAi(2);
      history.replaceState(null, "", "#step=2");
    };
    row.appendChild(ok);
    v.appendChild(row);
  }

  // ---------- Step 2: AI Design Review ----------
  function renderStep2(v) {
    var head = el("div", "section-title", "② AI 设计审查 <span class=\"en\">AI-assisted Design Review</span>");
    v.appendChild(head);

    var panel = el("div", "panel");
    panel.innerHTML = '<div class="panel-title-row"><h3>设计文档（SYRA 摘要） <span class="en">Design Document</span></h3><span class="tag">来源：需求管理（经 07 数据总线）</span></div>';
    D.designDoc.sections.forEach(function (s) {
      panel.appendChild(el("div", "dd-sec",
        '<div class="dn">' + esc(s.name) + "</div>" +
        '<div class="dc">' + esc(s.content) + "</div>" +
        '<div class="dt">' + s.tags.map(function (t) { return '<span class="tag" style="margin-right:4px">' + esc(t) + "</span>"; }).join("") + "</div>"));
    });
    v.appendChild(panel);

    var fPanel = el("div", "panel");
    fPanel.innerHTML = '<div class="panel-title-row"><h3>AI 预审发现 <span class="en">AI Findings</span></h3><span class="tag ai">AI 生成 · 人工确认</span></div>' +
      '<div class="desc">AI 依据审查规则库（示例）对设计文档预审，输出 ' + D.reviewFindings.length + " 项发现，请逐条确认。</div>" +
      aiBanner("AI 预审完成：<b>1 项高风险</b>、<b>1 项中风险</b>、<b>1 项低风险</b>。所有发现需人工确认后生效。");
    var all = true;
    D.reviewFindings.forEach(function (f) {
      var st = state.findings[f.id];
      if (st === "pending") all = false;
      var box = el("div", "finding");
      var stTag = st === "adopt" ? '<span class="tag ok">已采纳</span>' : (st === "reject" ? '<span class="tag">已忽略</span>' : '<span class="tag warn">待确认</span>');
      var sevTag = f.severity === "高" ? '<span class="tag danger">高 · High</span>' : (f.severity === "中" ? '<span class="tag warn">中 · Medium</span>' : '<span class="tag">低 · Low</span>');
      box.innerHTML =
        '<div class="fh"><span class="tag ai">' + esc(f.id) + "</span>" + sevTag + '<span class="ft">' + esc(f.title) + "</span>" + stTag + "</div>" +
        '<div class="fd">' + esc(f.detail) + "</div>" +
        '<div class="meta"><span>关联规则 <b>' + esc(f.rule) + "</b></span><span>置信度 <b>" + Math.round(f.confidence * 100) + "%</b></span><span>建议 <b>" + esc(f.suggestion) + "</b></span></div>" +
        '<div class="confbar"><i style="width:' + Math.round(f.confidence * 100) + '%"></i></div>';
      if (!exportMode) {
        var act = el("div", "btn-row");
        act.style.marginTop = "8px";
        if (st === "pending") {
          var b1 = el("button", "btn small primary", "采纳");
          b1.onclick = function () { state.findings[f.id] = "adopt"; render(); };
          var b2 = el("button", "btn small", "忽略");
          b2.onclick = function () { state.findings[f.id] = "reject"; render(); };
          act.appendChild(b1); act.appendChild(b2);
        } else if (st === "adopt") {
          var b3 = el("button", "btn small ghost", "撤销");
          b3.onclick = function () { state.findings[f.id] = "pending"; render(); };
          act.appendChild(b3);
        }
        box.appendChild(act);
      }
      fPanel.appendChild(box);
    });
    v.appendChild(fPanel);

    var row = el("div", "btn-row");
    if (all && !exportMode) {
      var go = el("button", "btn primary", "确认审查结果 &#8594; 生成评价基准");
      go.onclick = function () {
        state.done[2] = true;
        state.step = 3;
        render();
        runAi(3);
        history.replaceState(null, "", "#step=3");
      };
      row.appendChild(go);
    }
    if (exportMode) {
      var note = el("div", "tag ok", "审查结果已同步至追溯矩阵（示例）");
      row.appendChild(note);
    }
    v.appendChild(row);
  }

  // ---------- Step 3: Evaluation base ----------
  function renderStep3(v) {
    var head = el("div", "section-title", "③ AI 生成评价基准 <span class=\"en\">AI-generated Evaluation Base</span>");
    v.appendChild(head);

    var panel = el("div", "panel");
    panel.innerHTML =
      '<div class="panel-title-row"><h3>产品大类 <span class="en">Product Category</span></h3><span class="tag">工具：05 评价基准生成（示例）</span></div>' +
      '<div class="desc">按产品大类 + 需求特性，从评价分类（示例知识库）生成测试/评价清单。本演示覆盖 ' + D.evalChecklist.length + " 项。</div>" +
      '<div class="spec-grid">' +
      '<div class="spec-box"><div class="k">产品大类</div><div class="v">' + esc(D.project.productTypeLabel) + "</div></div>" +
      '<div class="spec-box"><div class="k">输出对象</div><div class="v">' + esc(D.project.productTypeLabel.split(" / ")[0]) + " · 测试文件清单（只出清单，文件由文件管理工具落地）</div></div>" +
      "</div>";
    v.appendChild(panel);

    var cPanel = el("div", "panel");
    cPanel.innerHTML = '<div class="panel-title-row"><h3>评价清单 <span class="en">Evaluation Checklist</span></h3>' +
      (state.checklistConfirmed ? '<span class="tag ok">已确认 · 已流转</span>' : '<span class="tag ai">AI 生成 · 待人工确认</span>') + "</div>" +
      '<div class="desc">严重度：<b style="color:var(--danger)">必须</b> / <b style="color:var(--warn)">推荐</b> / 参考。依据示例标准与产品基线。</div>';
    D.evalChecklist.forEach(function (c) {
      var row = el("div", "chk-row" + (state.checklistConfirmed ? " done" : ""));
      row.innerHTML =
        '<span class="box">&#10003;</span>' +
        '<span class="item">' + esc(c.item) + '</span>' +
        '<span class="sev ' + sevClass(c.severity) + '">' + esc(c.severity) + "</span>" +
        '<span class="std">' + esc(c.std) + "</span>";
      cPanel.appendChild(row);
    });
    v.appendChild(cPanel);

    var row = el("div", "btn-row");
    if (state.checklistConfirmed) {
      var tag = el("span", "tag ok", "清单已流转至：文件管理（落地文件）/ 需求管理 SYQT 补充（示例）");
      row.appendChild(tag);
    } else if (exportMode) {
      var tag2 = el("span", "tag ok", "清单已确认并流转（示例）");
      row.appendChild(tag2);
    } else {
      var go = el("button", "btn primary", "确认清单 &#8594; 进入知识沉淀");
      go.onclick = function () {
        state.checklistConfirmed = true;
        state.done[3] = true;
        state.step = 4;
        render();
        runAi(4);
        history.replaceState(null, "", "#step=4");
      };
      row.appendChild(go);
    }
    v.appendChild(row);
  }

  // ---------- Step 4: Knowledge loop-back ----------
  function renderStep4(v) {
    var head = el("div", "section-title", "④ 知识沉淀 · 闭环复用 <span class=\"en\">Knowledge Loop-back</span>");
    v.appendChild(head);

    var panel = el("div", "panel");
    panel.innerHTML = '<div class="panel-title-row"><h3>沉淀条目 <span class="en">Contribution</span></h3>' +
      (state.contributionDone ? '<span class="tag ok">已沉淀</span>' : '<span class="tag ai">待沉淀 · 人工确认</span>') + "</div>" +
      '<div class="desc">将人工确认后的审查发现提炼为可复用知识，沉淀回示例知识库，供新项目复用。</div>';
    var C = D.kbContribution;
    var card = el("div", "kb-card new");
    card.innerHTML =
      '<div class="t">' + esc(C.entryId) + " · " + esc(C.title) + "</div>" +
      '<div class="c">' + esc(C.category) + "</div>" +
      '<div class="tags">' + C.tags.map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("") + "</div>";
    panel.appendChild(card);
    var body = el("div", "cont-body");
    body.innerHTML = "<ul>" + C.body.map(function (b) { return "<li>" + esc(b) + "</li>"; }).join("") + "</ul>" +
      '<div class="cont-meta">来源：' + esc(C.source) + "<br/>复用场景：" + esc(C.reusableFor) + "</div>";
    panel.appendChild(body);
    v.appendChild(panel);

    var loop = el("div", "panel");
    loop.innerHTML = '<div class="panel-title-row"><h3>闭环效果 <span class="en">Closed Loop</span></h3><span class="tag ok">链路完成</span></div>' +
      '<div class="spec-grid">' +
      '<div class="spec-box"><div class="k">沉淀 → 新项目</div><div class="v" style="font-size:12.5px">新项目需求导入时，AI 可直接引用本条目，减少重复设计审查。</div></div>' +
      '<div class="spec-box"><div class="k">审查经验 → 规则库</div><div class="v" style="font-size:12.5px">高频问题可升级为审查规则，下一次审查自动命中（示例）。</div></div>' +
      "</div>";
    v.appendChild(loop);

    var row = el("div", "btn-row");
    if (state.contributionDone || exportMode) {
      var tag = el("span", "tag ok", "演示链路完成：需求导入 &#8594; AI 设计审查 &#8594; AI 生成评价基准 &#8594; 知识沉淀");
      row.appendChild(tag);
    } else {
      var go = el("button", "btn primary", "确认沉淀 &#10003;");
      go.onclick = function () {
        state.contributionDone = true;
        state.done[4] = true;
        render();
        history.replaceState(null, "", "#step=4");
      };
      row.appendChild(go);
    }
    v.appendChild(row);
  }

  // ---------- sidebar ----------
  function renderSidebar() {
    var box = $("kb-list");
    box.innerHTML = "";
    D.kbEntries.forEach(function (e) {
      var card = el("div", "kb-card");
      card.innerHTML =
        '<div class="t">' + esc(e.id) + " · " + esc(e.title) + "</div>" +
        '<div class="c">' + esc(e.category) + " · " + esc(e.added) + "</div>" +
        '<div class="tags">' + e.tags.map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("") + "</div>";
      box.appendChild(card);
    });
    if (state.contributionDone || exportMode) {
      var C = D.kbContribution;
      var ncard = el("div", "kb-card new");
      ncard.innerHTML =
        '<div class="t">' + esc(C.entryId) + " · " + esc(C.title) + "</div>" +
        '<div class="c">' + esc(C.category) + " · 刚刚</div>" +
        '<div class="tags">' + C.tags.map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("") + "</div>";
      box.insertBefore(ncard, box.firstChild);
    }

    var fbox = $("flow-list");
    fbox.innerHTML = "";
    D.flowSteps.forEach(function (f) {
      var node = el("div", "flow-node");
      node.innerHTML =
        "<span>" + esc(f.from) + " &#8594; " + esc(f.to) + "</span>" +
        '<span class="arrow">' + esc(f.artifact) + " · <small>" + esc(f.via) + "</small></span>";
      fbox.appendChild(node);
    });
  }

  function renderDisclaimer() {
    $("disclaimer").innerHTML =
      "<b>诚实口径声明：</b>本演示为公开示例，所有项目、需求、设计、评价与知识库内容均为<b>虚构数据</b>，不包含任何真实公司/产品/内部知识库信息。" +
      "真实系统中，AI 仅作为<b>辅助 / 编排</b>角色——AI 生成结果必须经工程师人工确认后才写入与流转。";
  }

  // ---------- boot ----------
  document.addEventListener("DOMContentLoaded", function () {
    $("chip-project").textContent = D.project.nameZh + " · " + D.project.id + "（虚构示例）";
    render();
    if (!exportMode && !state.done[state.step]) runAi(state.step);
  });
})();
