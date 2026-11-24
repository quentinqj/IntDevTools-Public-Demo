/* =====================================================================
   IntDevTools Public Demo v2 · 交互逻辑（真实 API 驱动）
   - 需求导入 → 设计审查 → 评价基准 → 知识沉淀，全部调用真实后端
   - API 失败 → 显示错误，不做假确认
   - 支持 #step=N 与 #export=1（截图/录屏用，自动跑完整链路）
   ===================================================================== */
(function () {
  "use strict";

  var API = window.IDT_API;
  var exportMode = /[?&#]export=1/.test(location.hash) || /[?&#]export=1/.test(location.search);
  var PROJECT_ID = 101;

  var state = {
    step: 1,
    api: null,
    project: null,
    requirements: [],
    assessment: null,
    designBlocks: [],
    findings: [],
    confirmations: {},
    evalResult: null,
    kbEntries: [],
    done: { 1: false, 2: false, 3: false, 4: false },
    error: null,
    loading: false,
  };

  // ---------- helpers ----------
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html !== undefined) e.innerHTML = html; return e; }
  function sevClass(s) { if (s === "必须") return "sev-must"; if (s === "推荐") return "sev-rec"; return "sev-ref"; }
  function sevTag(s) {
    if (s === "high") return '<span class="tag danger">高 · High</span>';
    if (s === "medium") return '<span class="tag warn">中 · Medium</span>';
    return '<span class="tag">低 · Low</span>';
  }

  var STEP_DEFS = [
    { zh: "需求导入", en: "Requirements Intake", tool: "01 需求管理" },
    { zh: "AI 设计审查", en: "AI Design Review", tool: "02 设计审查" },
    { zh: "AI 生成评价基准", en: "Evaluation Base", tool: "05 评价基准" },
    { zh: "知识沉淀", en: "Knowledge Loop-back", tool: "示例知识库" }
  ];

  function aiBanner(text) {
    return '<div class="ai-banner"><span class="ai-ico">&#9889;</span><div>' + text +
      '<div class="human-note">&#9998; 真实后端输出：' + modeLabel() + '。AI 结果需人工确认后生效（AI 辅助 / 编排，非全自动）。</div></div>';
  }
  function modeLabel() {
    if (!state.api) return "未连接";
    return state.api.mode === "llm" ? ("LLM 模式 · " + state.api.llm_model) : "确定性规则模式（离线可跑）";
  }

  function setError(msg) {
    state.error = msg;
    render();
  }

  async function call(fn) {
    state.loading = true;
    state.error = null;
    render();
    try {
      var data = await fn();
      return data;
    } catch (e) {
      state.error = e.message;
      return null;
    } finally {
      state.loading = false;
    }
  }

  // ---------- boot ----------
  async function boot() {
    var health = await call(function () { return API.get("/api/health"); });
    if (!health) { render(); return; }
    state.api = health;
    var cm = $("chip-mode");
    if (cm) cm.innerHTML = "模式：<b style=\\"color:var(--ai)\\">" + modeLabel() + "</b>";
    var proj = await call(function () { return API.get("/api/project/" + PROJECT_ID); });
    if (proj) state.project = proj.profile;
    var reqs = await call(function () { return API.get("/api/requirements"); });
    if (reqs) state.requirements = reqs.requirements;
    var kb = await call(function () { return API.get("/api/kb"); });
    if (kb) state.kbEntries = kb.entries;

    var m = location.hash.match(/[?&#]step=(\d)/);
    if (m && m[1] >= 1 && m[1] <= 4 && !exportMode) state.step = parseInt(m[1], 10);

    if (exportMode) { await runChain(); return; }
    render();
  }

  async function runChain() {
    // 导出模式：自动跑完整链路（真实 API）
    state.done = { 1: false, 2: false, 3: false, 4: false };
    await doAssessment(true);
    if (state.assessment) {
      state.done[1] = true;
      state.step = 2;
      await doReview();
      var conf = {};
      state.findings.forEach(function (f) { conf[f.id] = (f.severity === "high" || f.severity === "medium") && f.status !== "ok" && f.status !== "manual" ? "adopt" : "reject"; });
      await doConfirmReview(conf);
      state.done[2] = true;
      state.step = 3;
      await doConfirmEval();
      state.done[3] = true;
      state.step = 4;
    }
    render();
  }

  // ---------- stepper ----------
  function renderStepper() {
    var box = $("stepper");
    box.innerHTML = "";
    box.appendChild(el("div", "step-title-hint", "交付链路 · Delivery Chain"));
    STEP_DEFS.forEach(function (def, i) {
      var n = i + 1;
      var cls = "step" + (n === state.step ? " active" : "") + (state.done[n] ? " done" : "");
      var st = state.done[n] ? "已完成 · Done" : (n === state.step ? "进行中 · In progress" : "待办 · Pending");
      var row = el("div", cls);
      row.innerHTML = '<div class="num">' + (state.done[n] ? "&#10003;" : n) + "</div>" +
        '<div><div class="st-name">' + def.zh + '</div><div class="st-en">' + def.en + '</div>' +
        '<div class="st-state">' + st + "</div></div>";
      row.onclick = function () { if (!exportMode) gotoStep(n); };
      box.appendChild(row);
      if (n < 4) box.appendChild(el("div", "progress-line" + (state.done[n] ? " done" : "")));
    });
    var flow = el("div", "flow-mini");
    flow.innerHTML = "<h4>核心链路 · Core Chain</h4>" +
      '<div class="flow-node"><span>① 需求导入</span><span class="arrow">&#8595; 真实 API 评估</span>' +
      "<span>② 设计审查</span><span class=\"arrow\">&#8595; 真实审查引擎 · 人工确认</span>" +
      "<span>③ 评价基准</span><span class=\"arrow\">&#8595; 清单流转</span>" +
      "<span>④ 知识沉淀</span></div>";
    box.appendChild(flow);
  }

  function gotoStep(n) {
    if (n < 1 || n > 4) return;
    state.step = n;
    render();
    history.replaceState(null, "", "#step=" + n);
  }

  // ---------- render ----------
  function render() {
    renderStepper();
    renderSidebar();
    var v = $("view");
    v.innerHTML = "";

    if (state.error) {
      v.appendChild(errorPanel(state.error));
    }
    if (!state.api) {
      v.appendChild(connectionPanel());
      renderDisclaimer();
      return;
    }
    if (state.loading) {
      var ai = el("div", "ai-thinking", '<span>后端处理中</span><span class="bar"><i></i><i></i><i></i></span>');
      var holder = el("div", "ai-banner", ""); holder.appendChild(ai);
      v.appendChild(holder);
    }

    var fn = [renderStep1, renderStep2, renderStep3, renderStep4][state.step - 1];
    fn(v);
    renderDisclaimer();
  }

  function errorPanel(msg) {
    var p = el("div", "panel");
    p.style.borderColor = "rgba(248,113,113,0.5)";
    p.innerHTML = '<div class="panel-title-row"><h3 style="color:var(--danger)">⚠ 后端错误 · API Error</h3></div>' +
      '<div class="desc" style="color:#fca5a5">' + esc(msg) + "</div>" +
      '<div class="btn-row"><button class="btn" id="btn-retry">重试</button></div>';
    p.querySelector("#btn-retry").onclick = function () { location.reload(); };
    return p;
  }

  function connectionPanel() {
    var p = el("div", "panel");
    p.style.borderColor = "rgba(245,158,11,0.5)";
    p.innerHTML =
      '<div class="panel-title-row"><h3 style="color:var(--warn)">需要本地运行真实后端</h3><span class="tag warn">v2 · Real API</span></div>' +
      '<div class="desc">本演示 v2 的所有输出均来自真实后端（开发等级判定 / 审查引擎 / 评价基准 / 数据总线）。请先启动后端：</div>' +
      '<div class="cont-body" style="font-family:var(--mono);font-size:12.5px">' +
      "cd backend<br/>start.bat&nbsp;&nbsp;<span style=\"color:var(--muted)\"># Windows</span><br/>bash start.sh&nbsp;&nbsp;<span style=\"color:var(--muted)\"># macOS / Linux</span>" +
      "</div>" +
      '<div class="desc" style="margin-top:10px">启动后访问 <b>http://127.0.0.1:8000/</b>（后端同时提供页面与 API）。' +
      "也可用 <code>?api=http://127.0.0.1:8000</code> 指定后端地址。</div>" +
      '<div class="btn-row"><button class="btn primary" id="btn-reconnect">重新连接</button></div>';
    p.querySelector("#btn-reconnect").onclick = function () { location.reload(); };
    return p;
  }

  function renderDisclaimer() {
    $("disclaimer").innerHTML =
      "<b>诚实口径声明：</b>本演示为公开示例，所有项目、需求、设计、评价与知识库内容均为<b>虚构数据</b>。演示输出全部来自真实后端代码" +
      "（规则引擎 + 数据总线 + Schema 校验；配置 LLM_API_KEY 时复杂规则走真实 LLM）。AI 仅作为<b>辅助 / 编排</b>角色，结果必须人工确认后生效。";
  }

  // ---------- sidebar ----------
  function renderSidebar() {
    var box = $("kb-list");
    box.innerHTML = "";
    var entries = state.kbEntries || [];
    entries.forEach(function (e) {
      var card = el("div", "kb-card" + (e.id === state.contributedId ? " new" : ""));
      card.innerHTML = '<div class="t">' + esc(e.id) + " · " + esc(e.title) + "</div>" +
        '<div class="c">' + esc(e.category) + " · " + esc(e.added) + "</div>" +
        '<div class="tags">' + (e.tags || []).map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("") + "</div>";
      box.appendChild(card);
    });
    var fbox = $("flow-list");
    fbox.innerHTML = "";
    [
      ["需求管理", "设计审查", "SYRA / SYAD 设计文档", "07 数据总线"],
      ["设计审查", "评价基准", "审查发现（人工确认后）", "07 数据总线"],
      ["评价基准", "需求管理", "评价清单 → SYQT 补充", "07 数据总线"],
      ["设计审查", "知识库", "审查经验沉淀", "知识流"]
    ].forEach(function (f) {
      var node = el("div", "flow-node");
      node.innerHTML = "<span>" + f[0] + " &#8594; " + f[1] + "</span>" +
        '<span class="arrow">' + f[2] + " · <small>" + f[3] + "</small></span>";
      fbox.appendChild(node);
    });
  }

  // ---------- Step 1 ----------
  function renderStep1(v) {
    v.appendChild(el("div", "section-title", "① 需求导入与能力评估 <span class=\"en\">Requirements Intake &amp; Capability Assessment</span>"));
    var panel = el("div", "panel");
    panel.innerHTML = '<div class="panel-title-row"><h3>需求清单 REQM <span class="en">Requirements（真实读取 requirements.csv）</span></h3><span class="tag">工具：01 需求管理（示例）</span></div>';
    var table = el("table");
    table.innerHTML = "<thead><tr><th>要求ID</th><th>标题</th><th>大分类</th><th>重要度</th><th>状态</th><th>来源</th></tr></thead>";
    var tb = el("tbody");
    (state.requirements || []).forEach(function (r) {
      var tr = el("tr");
      if (r.req_id === "REQ-002") tr.className = "hl";
      tr.innerHTML = "<td><b>" + esc(r.req_id) + "</b></td><td>" + esc(r.title) + "</td><td>" + esc(r.category) + "</td>" +
        "<td>" + esc(r.priority) + "</td><td>" + esc(r.status) + "</td><td>" + esc(r.source) + "</td>";
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    panel.appendChild(table);
    v.appendChild(panel);

    var aPanel = el("div", "panel");
    aPanel.id = "assessment-panel";
    if (!state.assessment) {
      aPanel.innerHTML = '<div class="panel-title-row"><h3>AI 辅助评估 <span class="en">AI-assisted Assessment</span></h3><span class="tag ai">真实后端判定</span></div>' +
        '<div class="desc">选择需求并点击「开始评估」：后端执行 <b>开发等级判定</b>（真实逻辑）并匹配示例标准（真实读取 demo-data）。</div>' +
        aiBanner("评估 = <b>开发等级判定函数</b>（难度 → L1~L5）+ <b>标准关键词匹配</b>，非写死字符串。");
      var row = el("div", "btn-row");
      var go = el("button", "btn primary", "开始评估（REQ-002）");
      go.onclick = function () { doAssessment(false); };
      row.appendChild(go);
      aPanel.appendChild(row);
    } else {
      var A = state.assessment;
      aPanel.innerHTML =
        '<div class="panel-title-row"><h3>AI 辅助评估结果 <span class="en">Assessment Result</span></h3><span class="tag ok">已评估 · 待确认</span></div>' +
        aiBanner("后端判定开发等级 <b>" + esc(A.level) + "</b>，匹配 <b>" + A.standards.length + "</b> 项示例标准、建议 <b>" + A.verification_items.length + "</b> 条验证条目。") +
        '<div class="spec-grid">' +
        '<div class="spec-box"><div class="k">开发等级判定 · Development Level</div><div class="v level-badge">' + esc(A.level) + ' <small>· ' + esc(A.level_label) + "</small></div></div>" +
        '<div class="spec-box"><div class="k">判定理由 · Reason（真实判定输出）</div><div class="v" style="font-weight:400;font-size:12px;line-height:1.6">' + esc(A.reason) + "</div></div>" +
        "</div>" +
        '<div style="margin-top:12px"><div class="k" style="font-size:11px;color:var(--muted);margin-bottom:4px">匹配标准（数据驱动）</div>' +
        A.standards.map(function (s) { return '<span class="tag" style="margin-right:6px">' + esc(s.id) + " · " + esc(s.label) + "</span>"; }).join("") + "</div>" +
        '<div style="margin-top:10px"><div class="k" style="font-size:11px;color:var(--muted);margin-bottom:4px">建议验证条目</div>' +
        A.verification_items.map(function (s, i) { return '<div class="chk-row"><span class="box" style="border-color:var(--accent);color:var(--accent)">' + (i + 1) + "</span><span class=\"item\">" + esc(s) + "</span></div>"; }).join("") + "</div>" +
        '<div style="margin-top:10px;font-size:11.5px;color:var(--muted)">评估结果已写入数据总线（transit/development_level，Schema 校验通过）。</div>';
      if (!exportMode && !state.done[1]) {
        var row2 = el("div", "btn-row");
        var ok = el("button", "btn primary", "确认评估结果 &#8594; 进入设计审查");
        ok.onclick = function () { confirmAssessment(); };
        row2.appendChild(ok);
        aPanel.appendChild(row2);
      } else if (state.done[1]) {
        aPanel.appendChild(el("div", "btn-row", '<span class="tag ok">已确认 · 已进入下一环节</span>'));
      }
    }
    v.appendChild(aPanel);
  }

  async function doAssessment(auto) {
    var data = await call(function () {
      return API.post("/api/assessment", { project_id: PROJECT_ID, requirement_id: "REQ-002", difficulty: "medium" });
    });
    if (data) { state.assessment = data; if (auto) state.done[1] = true; }
    render();
  }

  function confirmAssessment() {
    state.done[1] = true;
    state.step = 2;
    render();
    doReview();
    history.replaceState(null, "", "#step=2");
  }

  // ---------- Step 2 ----------
  function renderStep2(v) {
    v.appendChild(el("div", "section-title", "② AI 设计审查 <span class=\"en\">AI-assisted Design Review</span>"));
    var panel = el("div", "panel");
    panel.innerHTML = '<div class="panel-title-row"><h3>设计文档（SYRA 摘要） <span class="en">真实解析 syra_design.md</span></h3><span class="tag">来源：需求管理（经 07 数据总线）</span></div>';
    (state.designBlocks || []).forEach(function (b) {
      panel.appendChild(el("div", "dd-sec",
        '<div class="dn">' + esc(b.location) + "</div>" +
        '<div class="dc">' + esc(b.text) + "</div>"));
    });
    v.appendChild(panel);

    var fPanel = el("div", "panel");
    if (state.findings.length === 0 && !state.loading) {
      fPanel.innerHTML = '<div class="panel-title-row"><h3>AI 预审发现 <span class="en">AI Findings</span></h3><span class="tag ai">真实审查引擎</span></div>' +
        '<div class="desc">点击「运行审查」：后端审查引擎读取 <b>review_rules.json</b> 规则，对文档块执行确定性检查（LLM 模式可选）。</div>' +
        aiBanner("审查 = <b>规则引擎</b>（可审查性闸门 + 确定性检查 + 可选 LLM），每条发现带命中规则与位置证据。");
      if (!exportMode) {
        var row = el("div", "btn-row");
        var go = el("button", "btn primary", "运行 AI 审查");
        go.onclick = function () { doReview(); };
        row.appendChild(go);
        fPanel.appendChild(row);
      }
    } else {
      fPanel.innerHTML = '<div class="panel-title-row"><h3>AI 预审发现 <span class="en">AI Findings</span></h3><span class="tag ai">真实引擎输出 · ' + esc(modeLabel()) + "</span></div>" +
        '<div class="desc">共 ' + state.findings.length + ' 条输出（含 OK / 需人工 / 问题项）。问题项请逐条确认。</div>';
      var needConfirm = false;
      state.findings.forEach(function (f) {
        var st = state.confirmations[f.id];
        var isOk = f.status === "ok";
        var isManual = f.status === "manual";
        var box = el("div", "finding");
        var stTag = isOk ? '<span class="tag ok">OK</span>' :
          (isManual ? '<span class="tag warn">需人工审查</span>' :
            (st === "adopt" ? '<span class="tag ok">已采纳</span>' : (st === "reject" ? '<span class="tag">已忽略</span>' : '<span class="tag warn">待确认</span>')));
        box.innerHTML =
          '<div class="fh"><span class="tag ai">' + esc(f.id) + "</span>" + sevTag(f.severity) + '<span class="ft">' + esc(f.rule_name || f.category) + "</span>" + stTag + "</div>" +
          '<div class="fd">' + esc(f.description || (isOk ? "符合要求" : "")) + "</div>" +
          '<div class="meta">' +
          (f.evidence ? "<span>命中位置 <b>" + esc(f.evidence) + "</b></span>" : "") +
          (f.suggestion ? "<span>建议 <b>" + esc(f.suggestion) + "</b></span>" : "") +
          "<span>置信度 <b>" + Math.round(f.confidence * 100) + "%</b></span>" +
          "</div>";
        if (!isOk && !isManual && !exportMode) {
          var act = el("div", "btn-row");
          act.style.marginTop = "8px";
          if (st !== "adopt") { var b1 = el("button", "btn small primary", "采纳"); b1.onclick = function () { state.confirmations[f.id] = "adopt"; render(); }; act.appendChild(b1); }
          if (st !== "reject") { var b2 = el("button", "btn small", "忽略"); b2.onclick = function () { state.confirmations[f.id] = "reject"; render(); }; act.appendChild(b2); }
          box.appendChild(act);
        }
        fPanel.appendChild(box);
        if (!isOk && !isManual && st !== "adopt") needConfirm = true;
      });
      if (!exportMode && state.findings.length > 0) {
        var row2 = el("div", "btn-row");
        var go2 = el("button", "btn primary" + (needConfirm ? "" : ""), needConfirm ? "确认审查结果 &#8594; 生成评价基准" : "全部已处理 &#8594; 生成评价基准");
        go2.onclick = function () {
          var conf = {};
          state.findings.forEach(function (f) { if (state.confirmations[f.id]) conf[f.id] = state.confirmations[f.id]; });
          doConfirmReview(conf);
        };
        row2.appendChild(go2);
        fPanel.appendChild(row2);
      }
    }
    v.appendChild(fPanel);
  }

  async function doReview() {
    var data = await call(function () { return API.post("/api/review", { project_id: PROJECT_ID }); });
    if (data) { state.findings = data.findings; state.designBlocks = await API.get("/api/design-doc/" + PROJECT_ID).then(function (d) { return d.blocks; }).catch(function () { return []; }); }
    render();
  }

  async function doConfirmReview(conf) {
    var data = await call(function () { return API.post("/api/review/confirm", { project_id: PROJECT_ID, confirmations: conf }); });
    if (data) {
      state.done[2] = true;
      state.step = 3;
      render();
      await doEvalBase();
      history.replaceState(null, "", "#step=3");
    } else { render(); }
  }

  // ---------- Step 3 ----------
  function renderStep3(v) {
    v.appendChild(el("div", "section-title", "③ AI 生成评价基准 <span class=\"en\">AI-generated Evaluation Base</span>"));
    var panel = el("div", "panel");
    panel.innerHTML = '<div class="panel-title-row"><h3>产品大类 <span class="en">Product Category</span></h3><span class="tag">工具：05 评价基准生成（示例）</span></div>' +
      '<div class="desc">后端按产品大类执行 <b>generate_evaluation_base</b>（真实逻辑），并把已采纳审查发现转换为产品特有评价项。</div>';
    if (state.evalResult) {
      panel.innerHTML += '<div class="spec-grid">' +
        '<div class="spec-box"><div class="k">产品大类</div><div class="v">' + esc(state.evalResult.product_name) + "</div></div>" +
        '<div class="spec-box"><div class="k">依据标准（示例）</div><div class="v" style="font-size:12px">' + (state.evalResult.standards || []).join(" · ") + "</div></div>" +
        "</div>";
    }
    v.appendChild(panel);

    var cPanel = el("div", "panel");
    if (!state.evalResult) {
      cPanel.innerHTML = '<div class="panel-title-row"><h3>评价清单 <span class="en">Evaluation Checklist</span></h3><span class="tag ai">真实生成逻辑</span></div>' +
        '<div class="desc">完成审查确认后自动生成。</div>' + aiBanner("评价 = <b>产品大类配置</b> + <b>审查发现转化</b>（仅采纳的 high/medium 进入产品特有项）。");
    } else {
      var E = state.evalResult;
      cPanel.innerHTML = '<div class="panel-title-row"><h3>评价清单 <span class="en">Evaluation Checklist</span></h3>' +
        (state.done[3] ? '<span class="tag ok">已确认 · 已流转</span>' : '<span class="tag ai">后端生成 · 待人工确认</span>') + "</div>" +
        '<div class="desc">共 ' + E.total_items + ' 项（通用大类 + 产品特有）。严重度：<b style="color:var(--danger)">必须</b> / <b style="color:var(--warn)">推荐</b> / 参考。</div>';
      (E.categories || []).forEach(function (cat) {
        cPanel.appendChild(el("div", "kb-panel-title", cat.id + " " + cat.name));
        cat.selected_items.forEach(function (it) {
          var row = el("div", "chk-row" + (state.done[3] ? " done" : ""));
          row.innerHTML = '<span class="box">&#10003;</span><span class="item">' + esc(it.name) + '</span>' +
            '<span class="sev ' + sevClass(it.severity) + '">' + esc(it.severity) + "</span>" +
            '<span class="std">通用大类</span>';
          cPanel.appendChild(row);
        });
      });
      if (E.special_items && E.special_items.length) {
        cPanel.appendChild(el("div", "kb-panel-title", "产品特有 · 来自审查发现（示例）"));
        E.special_items.forEach(function (it) {
          var row = el("div", "chk-row" + (state.done[3] ? " done" : ""));
          row.innerHTML = '<span class="box">&#10003;</span><span class="item">' + esc(it.name) + '</span>' +
            '<span class="sev ' + sevClass(it.severity) + '">' + esc(it.severity) + "</span>" +
            '<span class="std">' + esc(it.source) + "</span>";
          cPanel.appendChild(row);
        });
      }
      if (!exportMode && !state.done[3]) {
        var row = el("div", "btn-row");
        var go = el("button", "btn primary", "确认清单 &#8594; 进入知识沉淀");
        go.onclick = function () { doConfirmEval(); };
        row.appendChild(go);
        cPanel.appendChild(row);
      }
    }
    v.appendChild(cPanel);
  }

  async function doEvalBase() {
    var data = await call(function () { return API.post("/api/eval-base", { project_id: PROJECT_ID, product_type_id: "controller", severity: "推荐" }); });
    if (data) state.evalResult = data;
    render();
  }

  async function doConfirmEval() {
    var data = await call(function () { return API.post("/api/eval-base/confirm", { project_id: PROJECT_ID, product_type_id: "controller" }); });
    if (data) {
      state.done[3] = true;
      state.step = 4;
      render();
      await doContribute();
      history.replaceState(null, "", "#step=4");
    } else { render(); }
  }

  // ---------- Step 4 ----------
  function renderStep4(v) {
    v.appendChild(el("div", "section-title", "④ 知识沉淀 · 闭环复用 <span class=\"en\">Knowledge Loop-back</span>"));
    var panel = el("div", "panel");
    if (!state.contributed) {
      panel.innerHTML = '<div class="panel-title-row"><h3>沉淀条目 <span class="en">Contribution</span></h3><span class="tag ai">待沉淀 · 人工确认</span></div>' +
        '<div class="desc">后端将已采纳审查发现<b>提炼为可复用知识条目</b>并写入示例知识库（backend/data/kb_entries.json）。</div>' +
        aiBanner("沉淀 = <b>distill_contribution</b>（真实转换逻辑）：high/medium 已采纳发现 → 条目标题 / 要点 / 标签 / 来源。");
      if (!exportMode) {
        var row = el("div", "btn-row");
        var go = el("button", "btn primary", "确认沉淀 &#10003;");
        go.onclick = function () { doContribute(); };
        row.appendChild(go);
        panel.appendChild(row);
      }
    } else {
      var E = state.contributed;
      panel.innerHTML = '<div class="panel-title-row"><h3>沉淀条目 <span class="en">Contribution</span></h3><span class="tag ok">已写入示例知识库</span></div>';
      var card = el("div", "kb-card new");
      card.innerHTML = '<div class="t">' + esc(E.id) + " · " + esc(E.title) + "</div>" +
        '<div class="c">' + esc(E.category) + "</div>" +
        '<div class="tags">' + (E.tags || []).map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("") + "</div>";
      panel.appendChild(card);
      var body = el("div", "cont-body");
      body.innerHTML = "<ul>" + (E.body || []).map(function (b) { return "<li>" + esc(b) + "</li>"; }).join("") + "</ul>" +
        '<div class="cont-meta">来源：' + esc(E.source || "") + "</div>";
      panel.appendChild(body);
    }
    v.appendChild(panel);

    var loop = el("div", "panel");
    loop.innerHTML = '<div class="panel-title-row"><h3>闭环效果 <span class="en">Closed Loop</span></h3><span class="tag ok">链路完成</span></div>' +
      '<div class="spec-grid">' +
      '<div class="spec-box"><div class="k">沉淀 → 新项目</div><div class="v" style="font-size:12.5px">新项目需求导入时可直接复用该条目，减少重复设计审查。</div></div>' +
      '<div class="spec-box"><div class="k">审查经验 → 规则库</div><div class="v" style="font-size:12.5px">高频问题可升级为审查规则，下一次审查自动命中（示例）。</div></div>' +
      "</div>";
    v.appendChild(loop);

    if (state.done[4]) {
      v.appendChild(el("div", "btn-row", '<span class="tag ok">演示链路完成：需求导入 &#8594; AI 设计审查 &#8594; AI 生成评价基准 &#8594; 知识沉淀（全部来自真实 API）</span>'));
    }
  }

  async function doContribute() {
    var data = await call(function () { return API.post("/api/kb/contribute", { project_id: PROJECT_ID }); });
    if (data) {
      state.contributed = data.entry;
      state.contributedId = data.entry.id;
      state.done[4] = true;
      var kb = await API.get("/api/kb");
      if (kb) state.kbEntries = kb.entries;
    }
    render();
  }

  // ---------- boot ----------
  document.addEventListener("DOMContentLoaded", function () {
    boot();
  });
})();

