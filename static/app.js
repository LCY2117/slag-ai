async function postJSON(url, payload) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
}

function renderMarkdown(markdown) {
  const source = String(markdown ?? '');
  if (!window.markdownit) {
    return `<pre>${escapeHTML(source)}</pre>`;
  }
  const mathFragments = [];
  const sourceWithMathPlaceholders = source
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => stashMath(mathFragments, tex, true))
    .replace(/\$([^$\n]+?)\$/g, (_, tex) => stashMath(mathFragments, tex, false));
  const md = window.markdownit({
    html: false,
    linkify: true,
    typographer: true,
    breaks: false,
  });
  const html = md.render(sourceWithMathPlaceholders);
  const cleanHtml = window.DOMPurify?.sanitize ? DOMPurify.sanitize(html) : html;
  return restoreMath(cleanHtml, mathFragments);
}

function stashMath(store, tex, displayMode) {
  const index = store.length;
  store.push(renderFormulaHTML(tex, displayMode));
  return `@@KATEX_${index}@@`;
}

function restoreMath(html, store) {
  return store.reduce((output, fragment, index) => output.replaceAll(`@@KATEX_${index}@@`, fragment), html);
}

function renderFormulaHTML(tex, displayMode = true) {
  const source = String(tex ?? '').trim();
  if (!window.katex || !source) return escapeHTML(source);
  try {
    return katex.renderToString(source, {
      displayMode,
      throwOnError: false,
      strict: false,
    });
  } catch (err) {
    return escapeHTML(source);
  }
}

function renderLoading(kind = 'rule') {
  if (kind === 'ai') {
    return `
      <div class="ai-loading" role="status" aria-live="polite">
        <div class="ai-loader-panel">
          <div class="ai-core"></div>
          <div class="ai-loader-title">AI 正在生成</div>
          <p class="ai-loader-text">正在融合专家规则、性能评估和工程约束...</p>
          <div class="ai-steps">
            <div class="ai-step">枚举候选：${renderFormulaHTML('C_i=G\\times M', false)}</div>
            <div class="ai-step">校核约束：${renderFormulaHTML('F_c\\ge F_{c,target},\\ K\\ge K_{target}', false)}</div>
            <div class="ai-step">综合评分：${renderFormulaHTML('Score=\\sum w_iS_i-w_5C-w_6E', false)}</div>
          </div>
        </div>
      </div>
    `;
  }
  return `
    <div class="loading-skeleton" role="status" aria-live="polite">
      <div class="skeleton-line"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line"></div>
    </div>
  `;
}

function setMarkdown(id, markdown, notice = '') {
  const content = notice ? `${markdown}\n\n> [提示] ${notice}` : markdown;
  const target = document.getElementById(id);
  target.innerHTML = renderMarkdown(content);
  target.dataset.markdownRendered = window.markdownit ? 'true' : 'fallback';
}

function renderMathInElement(root = document) {
  if (!window.katex) return;
  for (const node of root.querySelectorAll('.formula[data-tex]')) {
    node.innerHTML = renderFormulaHTML(node.dataset.tex, true);
    node.dataset.mathRendered = 'true';
  }
}

function setSubmitBusy(form, busy) {
  const button = form.querySelector('button[type="submit"]');
  if (!button) return;
  button.disabled = busy;
  button.dataset.originalText ||= button.textContent;
  button.textContent = busy ? '生成中...' : button.dataset.originalText;
}

function formToObject(form) {
  const data = new FormData(form);
  const obj = {};
  for (const [key, value] of data.entries()) {
    if (key === 'goals') {
      obj[key] = value.split(/[,，]/).map(s => s.trim()).filter(Boolean);
    } else if (['area_m2','thickness_cm','porosity_pct','water_binder_ratio','aggregate_binder_ratio','age_day','steel_slag_consumption_kg_m3','raw_material_cost_saving_pct','construction_maintenance_saving_pct'].includes(key)) {
      obj[key] = Number(value);
    } else if (key === 'use_llm') {
      obj[key] = true;
    } else {
      obj[key] = value;
    }
  }
  if (form.id === 'qa-form' && !obj.use_llm) obj.use_llm = false;
  return obj;
}

function metric(label, value, unit='') {
  return `<div class="metric"><span>${label}</span><strong>${value}${unit}</strong></div>`;
}

function formulaBlock(title, formulas, note = '') {
  return `
    <div class="formula-panel formula-result">
      <h3>${title}</h3>
      ${formulas.map(item => `<div class="formula" data-tex="${escapeHTML(item)}"></div>`).join('')}
      ${note ? `<p>${note}</p>` : ''}
    </div>
  `;
}

function renderRecommend(data) {
  const p = data.primary_recommendation;
  const params = data.recommended_parameters;
  const perf = p.estimated_performance;
  const scores = p.scores;
  const warnings = (p.warnings || []).map(w => `<div class="warning">${w}</div>`).join('');
  return `
    <p><span class="badge">${scores.recommendation_level}</span>${data.summary}</p>
    <h3>推荐参数</h3>
    <ul>
      <li>钢渣粒径：${params.aggregate_name}（${params.aggregate_range}）</li>
      <li>成型方式：${params.forming_name}</li>
      <li>孔隙率控制：${params.porosity_control_pct}%</li>
      <li>水胶比：${params.water_binder_ratio}</li>
      <li>骨料胶凝比：${params.aggregate_binder_ratio}</li>
    </ul>
    <div class="metric-grid">
      ${metric('抗压强度', perf.compressive_strength_mpa, ' MPa')}
      ${metric('抗折强度', perf.flexural_strength_mpa, ' MPa')}
      ${metric('透水系数', perf.permeability_mm_s, ' mm/s')}
      ${metric('综合评分', scores.composite_score, ' 分')}
    </div>
    ${formulaBlock('评分函数', [
      'Score=w_1S_c+w_2S_f+w_3S_k+w_4S_p-w_5C-w_6E',
      'K\\ge K_{target},\\quad 23.8\\%\\le P\\le 26.5\\%,\\quad P\\approx25\\%'
    ], '系统先筛掉不满足透水与孔隙率约束的方案，再计算综合得分。')}
    ${warnings}
    <h3>后续建议</h3>
    <ul>${data.next_steps.map(x => `<li>${x}</li>`).join('')}</ul>
  `;
}

function renderEvaluate(data) {
  const perf = data.estimated_performance;
  const scores = data.scores;
  const inp = data.input;
  const warnings = (data.warnings || []).map(w => `<div class="warning">${w}</div>`).join('');
  return `
    <p><span class="badge">${scores.recommendation_level}</span> ${inp.aggregate_name} + ${inp.forming_name}，应用场景：${inp.scenario}</p>
    <div class="metric-grid">
      ${metric('抗压强度', perf.compressive_strength_mpa, ' MPa')}
      ${metric('抗折强度', perf.flexural_strength_mpa, ' MPa')}
      ${metric('透水系数', perf.permeability_mm_s, ' mm/s')}
      ${metric('综合评分', scores.composite_score, ' 分')}
    </div>
    <h3>规则解释</h3>
    <ul>${data.explanation_points.map(x => `<li>${x}</li>`).join('')}</ul>
    ${formulaBlock('半经验预测公式', [
      'P=P_0+\\alpha d+\\beta_m',
      'K=aP+b_m',
      inp.forming_method === 'HM' ? 'F_c=B_0+B_d-\\mu P' : 'F_c=A_0+A_d+A_m-\\lambda(P-25)^2',
      inp.forming_method === 'VM' ? 'F_f=C_0+C_d+C_m-\\eta(P-25)^2' : 'F_f=D_0+D_d+D_m-\\theta P'
    ], 'P 为有效孔隙率，K 为透水系数，F_c/F_f 分别为抗压和抗折强度。')}
    ${warnings}
  `;
}

function renderCarbon(data) {
  const c = data.calculation;
  return `
    <p>${data.summary}</p>
    <div class="metric-grid">
      ${metric('混凝土体积', c.concrete_volume_m3, ' m³')}
      ${metric('钢渣消纳量', c.steel_slag_consumption_ton, ' 吨')}
      ${metric('天然骨料替代', c.estimated_natural_aggregate_replacement_ton, ' 吨')}
      ${metric('原材料降本参考', c.raw_material_cost_saving_pct_reference, '%')}
      ${metric('施工养护降本参考', c.construction_maintenance_saving_pct_reference, '%')}
    </div>
    ${formulaBlock('消纳量计算', [
      'V=A\\times h',
      'M_{slag}=V\\times steel\\_slag\\_consumption',
      'M_b=\\frac{M_a}{4.8},\\quad M_w=0.16M_b'
    ], '工程估算采用单位体积钢渣消纳量；实验室配比可按紧密堆积密度 ρ_c 修正。')}
  `;
}

function setLoading(id, kind = 'rule') { document.getElementById(id).innerHTML = renderLoading(kind); }
function setError(id, err) { document.getElementById(id).innerHTML = `<div class="warning">请求失败：${escapeHTML(err.message || err)}</div>`; }

for (const btn of document.querySelectorAll('.tab')) {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.target).classList.add('active');
  });
}

async function loadHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    document.getElementById('health-card').innerHTML = `
      <div class="status-row">
        <strong>服务状态</strong>
        <span class="status-pill">在线</span>
      </div>
      <div class="status-meta">
        模型：${escapeHTML(data.model)}<br>
        API Key：${data.has_api_key ? '已配置' : '未配置，使用离线规则模式'}
        <span>${escapeHTML(data.base_url)}</span>
      </div>
    `;
  } catch (e) {
    document.getElementById('health-card').textContent = '服务状态检测失败';
  }
}

loadHealth();

document.getElementById('recommend-form').addEventListener('submit', async (e) => {
  e.preventDefault(); setLoading('recommend-result'); setSubmitBusy(e.target, true);
  try { const res = await postJSON('/api/recommend', formToObject(e.target)); const target = document.getElementById('recommend-result'); target.innerHTML = renderRecommend(res.data); renderMathInElement(target); }
  catch (err) { setError('recommend-result', err); }
  finally { setSubmitBusy(e.target, false); }
});

document.getElementById('evaluate-form').addEventListener('submit', async (e) => {
  e.preventDefault(); setLoading('evaluate-result'); setSubmitBusy(e.target, true);
  try { const res = await postJSON('/api/evaluate', formToObject(e.target)); const target = document.getElementById('evaluate-result'); target.innerHTML = renderEvaluate(res.data); renderMathInElement(target); }
  catch (err) { setError('evaluate-result', err); }
  finally { setSubmitBusy(e.target, false); }
});

document.getElementById('project-form').addEventListener('submit', async (e) => {
  e.preventDefault(); setLoading('project-result', 'ai'); setSubmitBusy(e.target, true);
  try { const res = await postJSON('/api/project-plan', formToObject(e.target)); setMarkdown('project-result', res.data.plan_markdown, res.data.llm_error); }
  catch (err) { setError('project-result', err); }
  finally { setSubmitBusy(e.target, false); }
});

document.getElementById('carbon-form').addEventListener('submit', async (e) => {
  e.preventDefault(); setLoading('carbon-result'); setSubmitBusy(e.target, true);
  try { const res = await postJSON('/api/carbon-economy', formToObject(e.target)); const target = document.getElementById('carbon-result'); target.innerHTML = renderCarbon(res.data); renderMathInElement(target); }
  catch (err) { setError('carbon-result', err); }
  finally { setSubmitBusy(e.target, false); }
});

document.getElementById('qa-form').addEventListener('submit', async (e) => {
  e.preventDefault(); const payload = formToObject(e.target); setLoading('qa-result', payload.use_llm ? 'ai' : 'rule'); setSubmitBusy(e.target, true);
  try { const res = await postJSON('/api/qa', payload); setMarkdown('qa-result', res.data.answer, res.data.llm_error); }
  catch (err) { setError('qa-result', err); }
  finally { setSubmitBusy(e.target, false); }
});

// 页面打开时自动跑一个推荐示例
renderMathInElement();
setTimeout(() => document.getElementById('recommend-form').requestSubmit(), 300);
