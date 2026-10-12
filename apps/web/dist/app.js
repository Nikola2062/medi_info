const API_BASE = window.MED_INFO_API_BASE || "http://127.0.0.1:8000";
const PUBLIC_REGISTRY_URL = window.MED_INFO_PUBLIC_REGISTRY_URL || null;
const MEDICINE_PROFILES_URL = window.MED_INFO_PROFILES_URL || "./data/medicine-profiles.json?v=7";
const CAPTURE_ENABLED = window.MED_INFO_CAPTURE_ENABLED !== false;

const form = document.querySelector("#lookup-form");
const input = document.querySelector("#registration-number");
const error = document.querySelector("#form-error");
const result = document.querySelector("#result");
const button = form.querySelector("button");
const privacyAcknowledgement = document.querySelector("#package-only");
const captureInputs = [...document.querySelectorAll(".capture-input")];
const captureMessage = document.querySelector("#capture-message");
const clearCaptureButton = document.querySelector("#clear-capture");
let scanSessionId = null;
let publicRegistryPromise = null;
let medicineProfilesPromise = null;

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = value ?? "";
  return node.innerHTML;
}

function formatDate(value) {
  if (!value) return "未提供";
  return new Intl.DateTimeFormat("zh-HK", { dateStyle: "medium" }).format(new Date(value));
}

function showEmpty() {
  result.dataset.state = "empty";
  result.innerHTML = `
    <p class="result-kicker">未能確認</p>
    <h2>找不到相符的官方記錄</h2>
    <p>沒有找到與這個編號相符的香港官方登記資料。</p>
    <p class="safety-copy">請檢查編號並再試一次。如仍有疑問，請帶同完整包裝向註冊藥劑師查詢。找不到記錄不代表藥物是假貨。</p>`;
  result.hidden = false;
  result.setAttribute("tabindex", "-1");
  result.focus();
}

function jurisdictionLabel(value) {
  const labels = {
    HK: "香港",
    US: "美國",
    UK: "英國",
    manufacturer_global: "廠商全球資料",
  };
  return labels[value] || value;
}

function renderSources(profile) {
  if (!profile?.sources?.length) return "";
  const sourceItems = profile.sources.map((item) => `
    <li>
      <a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.title)}</a>
      <span>${escapeHtml(item.authority)} · ${escapeHtml(jurisdictionLabel(item.jurisdiction))} · 查核 ${escapeHtml(item.checked_at)}</span>
    </li>`).join("");
  return `
    <details class="evidence-sources">
      <summary>查看資料來源及適用地區</summary>
      <p>不同地區的監管要求可能不同。外地資料只用作補充背景，不會取代香港處方標籤或醫護人員指示。</p>
      <ul>${sourceItems}</ul>
    </details>`;
}

function relationshipOverview(profile) {
  const relationship = profile?.relationship;
  if (!relationship) {
    return {
      badge: "未能確認",
      badgeClass: "status-pending",
      title: "研發血統未能確認",
      copy: "香港公開註冊資料沒有列出此產品是否原研、學名藥或獲原研公司授權；持證商名稱不能代替這項判定。",
    };
  }

  const referenceName = relationship.reference_product?.product_name
    || relationship.reference_product_name;
  const referenceCopy = referenceName ? `已記錄的原研／參考產品是 ${referenceName}。` : "";
  const confirmedRelationships = {
    confirmed_originator_or_reference: {
      title: "這是原研／參考藥",
      copy: "有明確證據確認它屬最初研發的品牌藥，或是監管機構指定作比較的參考產品。",
    },
    confirmed_generic: {
      title: "這是學名藥，不是原研藥",
      copy: `它與原研／參考藥的關係已有監管證據支持。學名藥不等於假藥；是否適合互換仍須按個別產品資料判斷。${referenceCopy}`,
    },
    confirmed_authorized_generic: {
      title: "這是授權學名藥",
      copy: `它是由原研公司或在原研公司授權下供應的學名版本，不是獨立冒充原研品牌的產品。${referenceCopy}`,
    },
    confirmed_biosimilar: {
      title: "這是生物相似藥，不是原研生物製劑",
      copy: `它以原研生物製劑作參考並證明高度相似；這種關係不同於一般化學藥的學名藥。${referenceCopy}`,
    },
    not_applicable: {
      title: "原研／學名藥分類不適用",
      copy: "這類產品不適合用原研藥與學名藥的關係來描述。",
    },
  };
  if (confirmedRelationships[relationship.status]) {
    return {
      badge: "有明確證據",
      badgeClass: "status-confirmed",
      ...confirmedRelationships[relationship.status],
    };
  }

  if (relationship.evidence_notes_zh_hant?.length) {
    return {
      badge: "部分證據",
      badgeClass: "status-context",
      title: "有原研品牌脈絡，但香港產品分類未確認",
      copy: "現有資料支持它與原研品牌的歷史關係，但未直接證明這個香港註冊產品屬原研、學名藥或授權版本。",
    };
  }

  return {
    badge: "未能確認",
    badgeClass: "status-pending",
    title: "研發血統未能確認",
    copy: "現有來源不足以判定原研、參考藥、學名藥或授權版本。這也不等於已證實產品是代理藥。",
  };
}

function renderCompanyRelationships(product, profile) {
  const relationship = profile?.company_relationships;
  const roles = relationship?.roles || [
    {
      label_zh_hant: "香港註冊及監管責任",
      value_from: "certificate_holder",
      status: "hk_verified",
      status_label_zh_hant: "香港官方資料",
      explanation_zh_hant: "這是香港註冊證明書持有人；單憑此欄不能判定它是研發者、製造商、代理或分銷商。",
    },
    {
      label_zh_hant: "現時香港版本製造商",
      value_zh_hant: "未有公開產品級資料確認",
      status: "not_publicly_confirmed",
      status_label_zh_hant: "未公開確認",
      explanation_zh_hant: "須以實物包裝、說明書或產品級官方文件核對，不能由持證商名稱推斷。",
    },
    {
      label_zh_hant: "香港進口／分銷角色",
      value_zh_hant: "未有公開產品級資料確認",
      status: "not_publicly_confirmed",
      status_label_zh_hant: "未公開確認",
      explanation_zh_hant: "公司可能同時擔任多種角色；公開註冊記錄沒有逐項說明。",
    },
  ];
  const roleItems = roles.map((role) => {
    const value = role.value_from === "certificate_holder"
      ? product.certificate_holder || "官方資料未提供"
      : role.value_zh_hant || "未有公開資料";
    const className = role.status === "hk_verified"
      ? "role-confirmed"
      : role.status === "context_only" ? "role-context" : "role-unconfirmed";
    return `
      <li class="${className}">
        <div class="role-heading">
          <span>${escapeHtml(role.label_zh_hant)}</span>
          <small>${escapeHtml(role.status_label_zh_hant)}</small>
        </div>
        <strong>${escapeHtml(value)}</strong>
        <p>${escapeHtml(role.explanation_zh_hant)}</p>
      </li>`;
  }).join("");
  const sourceIds = relationship?.source_ids || [];
  const sources = (profile?.sources || []).filter((source) => sourceIds.includes(source.id));
  const sourceLinks = sources.length
    ? `<p class="role-sources">判定依據：${sources.map((source) => `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.title)}</a>`).join("、")}</p>`
    : "";

  return `
    <section class="company-relationship-panel" aria-labelledby="company-relationship-title">
      <div class="section-heading">
        <div>
          <p class="section-kicker">研發血統與公司角色</p>
          <h3 id="company-relationship-title">${escapeHtml(relationship?.headline_zh_hant || "不能只用「自研／代理」二分")}</h3>
        </div>
        <span class="status-badge status-pending">逐項核對</span>
      </div>
      <p class="company-relationship-answer">${escapeHtml(relationship?.summary_zh_hant || "香港公開註冊資料可確認持證商，但通常不會公開產品的完整研發、製造、授權、進口及分銷鏈。")}</p>
      <ul class="company-role-list">${roleItems}</ul>
      <p class="company-boundary"><strong>怎樣理解：</strong>${escapeHtml(relationship?.boundary_zh_hant || "未有資料證明產品由香港持證商自行研發，不等於已證實它是學名藥或代理產品。")}</p>
      ${sourceLinks}
    </section>`;
}

function renderRelationshipConnection(product, profile) {
  const relationship = profile?.relationship;
  if (!relationship) return "";
  const referenceName = relationship.reference_product?.product_name
    || relationship.reference_product_name
    || (relationship.status === "confirmed_biosimilar" ? "原研生物製劑" : "原研／參考藥");
  const connectionLabels = {
    confirmed_originator_or_reference: "本身屬於",
    confirmed_generic: "學名藥關係",
    confirmed_authorized_generic: "經原研公司授權",
    confirmed_biosimilar: "以其作比較及評估",
  };
  const connection = connectionLabels[relationship.status];
  if (!connection) return "";

  return `
    <div class="relationship-connection" aria-label="本產品與原研藥的關係">
      <span>${escapeHtml(product.product_name)}</span>
      <strong>${escapeHtml(connection)}</strong>
      <span>${escapeHtml(referenceName)}</span>
    </div>`;
}

function clinicalOverview(profile, ingredients) {
  const clinical = profile?.clinical_summary;
  if (clinical?.is_public) {
    const useSummary = clinical.general_use_zh_hant
      || clinical.uses_plain_zh_hant
      || clinical.summary_zh_hant;
    return {
      badge: "已審核",
      badgeClass: "status-confirmed",
      title: ingredients,
      copy: useSummary || "已建立經審核的用途與安全摘要，請展開查看。",
    };
  }
  return {
    badge: clinical ? "待藥劑師審核" : "未有摘要",
    badgeClass: clinical ? "status-review" : "status-pending",
    title: ingredients,
    copy: clinical
      ? "藥效、一般用途和重要警告尚未獲准公開；目前只確認活性成分。"
      : "目前只有官方登記的成分名稱，未有經審核的藥效與用途摘要。",
  };
}

function coverageOverview(profile) {
  const relationship = profile?.relationship;
  const composition = profile?.regulatory_and_composition?.composition;
  const clinical = profile?.clinical_summary;
  const relationshipConfirmed = relationship && relationship.status !== "insufficient_public_evidence";
  const compositionVerified = composition?.status === "hk_verified";

  return [
    { label: "官方身份", state: "已核實", className: "coverage-confirmed" },
    {
      label: "原研／學名藥關係",
      state: relationshipConfirmed ? "已核實" : relationship ? "部分資料" : "未有資料",
      className: relationshipConfirmed ? "coverage-confirmed" : relationship ? "coverage-partial" : "coverage-missing",
    },
    {
      label: "香港版本配方",
      state: compositionVerified ? "已核實" : composition ? "待本地核對" : "未有資料",
      className: compositionVerified ? "coverage-confirmed" : composition ? "coverage-partial" : "coverage-missing",
    },
    {
      label: "藥效與安全",
      state: clinical?.is_public ? "已審核" : clinical ? "待審核" : "未有摘要",
      className: clinical?.is_public ? "coverage-confirmed" : clinical ? "coverage-review" : "coverage-missing",
    },
  ];
}

function renderAnswerSummary(product, profile, ingredients) {
  const relationship = relationshipOverview(profile);
  const relationshipConnection = renderRelationshipConnection(product, profile);
  const clinical = clinicalOverview(profile, ingredients);
  const coverage = coverageOverview(profile)
    .map((item) => `<li class="${item.className}"><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.state)}</strong></li>`)
    .join("");

  return `
    <section class="answer-summary" aria-labelledby="answer-summary-title">
      <div class="answer-summary-heading">
        <p class="section-kicker">一眼看懂</p>
        <h3 id="answer-summary-title">你最需要的四個答案</h3>
      </div>
      <div class="answer-grid">
        <article class="answer-card answer-confirmed">
          <div class="answer-label-row"><p>香港有正式登記嗎？</p><span class="status-badge status-confirmed">有記錄</span></div>
          <h4>${escapeHtml(product.registration_number)}</h4>
          <p>在香港官方資料集找到完全相同的註冊編號。</p>
        </article>
        <article class="answer-card">
          <div class="answer-label-row"><p>它的研發血統是甚麼？</p><span class="status-badge ${relationship.badgeClass}">${escapeHtml(relationship.badge)}</span></div>
          <h4>${escapeHtml(relationship.title)}</h4>
          <p>${escapeHtml(relationship.copy)}</p>
          ${relationshipConnection}
        </article>
        <article class="answer-card">
          <div class="answer-label-row"><p>成分有甚麼藥效？</p><span class="status-badge ${clinical.badgeClass}">${escapeHtml(clinical.badge)}</span></div>
          <h4>${escapeHtml(clinical.title)}</h4>
          <p>${escapeHtml(clinical.copy)}</p>
        </article>
        <article class="answer-card coverage-card">
          <div class="answer-label-row"><p>公開資料有多完整？</p><span class="status-badge status-context">逐項顯示</span></div>
          <h4>不以來源數量當作完整度</h4>
          <ul class="coverage-list">${coverage}</ul>
        </article>
      </div>
    </section>`;
}

function renderRelationship(profile) {
  const relationship = profile?.relationship;
  if (!relationship) {
    return `
      <section class="information-section relationship-panel" aria-labelledby="relationship-title">
        <div class="section-heading">
          <div><p class="section-kicker">品牌與研發關係</p><h3 id="relationship-title">未有已審核證據</h3></div>
          <span class="status-badge status-pending">證據不足</span>
        </div>
        <p>官方登記資料沒有說明這個產品是原研、參考製劑或學名藥。本工具不會根據品牌名稱或公司名稱作出推測。</p>
        <p class="generic-note">學名藥不等於假藥。這項分類描述藥物的研發和註冊關係，不代表相片可以證明產品真偽。</p>
      </section>`;
  }
  const overview = relationshipOverview(profile);
  const isUnconfirmed = relationship.status === "insufficient_public_evidence";
  const evidence = (relationship.evidence_notes_zh_hant || [])
    .map((note) => `<li>${escapeHtml(note)}</li>`)
    .join("");
  return `
    <section class="information-section relationship-panel" aria-labelledby="relationship-title">
      <div class="section-heading">
        <div><p class="section-kicker">本產品與原研藥的關係</p><h3 id="relationship-title">${escapeHtml(overview.title)}</h3></div>
        <span class="status-badge ${overview.badgeClass}">${escapeHtml(overview.badge)}</span>
      </div>
      <p class="relationship-plain-answer">${escapeHtml(overview.copy)}</p>
      ${relationship.interpretation_zh_hant ? `<p class="interpretation-note"><strong>先說結論：</strong>${escapeHtml(relationship.interpretation_zh_hant)}</p>` : ""}
      <p>${escapeHtml(relationship.explanation_zh_hant)}</p>
      <ul class="evidence-list">${evidence}</ul>
      ${isUnconfirmed ? `<p class="relationship-conclusion"><strong>資料邊界：</strong>現有證據不支持把這個產品稱為「非原研」或「複製版」；本工具只因香港公開資料沒有提供明確的參考製劑指定，而暫不作正式分類。</p>` : ""}
      <p class="generic-note">學名藥不等於假藥。這項分類描述藥物的研發和註冊關係，不代表相片可以證明產品真偽。</p>
    </section>`;
}

function renderSameIngredientComparison(profile) {
  const comparison = profile?.same_ingredient_comparison;
  if (!comparison) return "";

  const fields = comparison.comparison_fields
    .map((field) => `
      <div>
        <dt>${escapeHtml(field.label_zh_hant)}</dt>
        <dd>${escapeHtml(field.value_zh_hant)}</dd>
      </div>`)
    .join("");
  const products = comparison.products
    .map((product) => `
      <li>
        <div>
          <strong>${escapeHtml(product.product_name)}</strong>
          <span>${escapeHtml(product.registration_number)}</span>
        </div>
        <p>${escapeHtml(product.certificate_holder)}</p>
      </li>`)
    .join("");

  return `
    <section class="information-section comparison-panel" aria-labelledby="comparison-title">
      <div class="section-heading">
        <div>
          <p class="section-kicker">同成分產品比較</p>
          <h3 id="comparison-title">香港另有相同活性成分及標示劑量的產品</h3>
        </div>
        <span class="status-badge status-context">只核對公開資料</span>
      </div>
      <p>${escapeHtml(comparison.intro_zh_hant)}</p>
      <dl class="comparison-grid">${fields}</dl>
      <details class="comparison-products">
        <summary>查看 ${comparison.products.length} 個同成分、同標示劑量的香港登記產品</summary>
        <p>以下是官方產品名稱及註冊證明書持有人；不是替代建議，也不是可互換清單。</p>
        <ul>${products}</ul>
      </details>
      <aside class="generic-explainer" aria-label="學名藥說明">
        <strong>學名藥是甚麼？</strong>
        <p>${escapeHtml(comparison.generic_explainer_zh_hant)}</p>
      </aside>
      <p class="action-copy"><strong>切勿自行轉藥：</strong>即使活性成分和劑量相同，非活性成分、膠囊外觀及適用資料仍可能不同。需要替換時，請讓處方醫生或藥劑師核對實際產品。</p>
    </section>`;
}

function renderRegulatoryAndComposition(profile) {
  const disclosure = profile?.regulatory_and_composition;
  if (!disclosure) return "";

  const compositionGroups = disclosure.composition.groups
    .map((group) => `
      <div class="composition-group">
        <dt>${escapeHtml(group.label_zh_hant)}</dt>
        <dd>${group.ingredients_zh_hant.map((ingredient) => `<span>${escapeHtml(ingredient)}</span>`).join("")}</dd>
      </div>`)
    .join("");

  return `
    <section class="information-section disclosure-panel" aria-labelledby="disclosure-title">
      <div class="section-heading">
        <div>
          <p class="section-kicker">註冊、專利與配方公開程度</p>
          <h3 id="disclosure-title">三種不同狀態，不應混為一談</h3>
        </div>
        <span class="status-badge status-context">按來源分級</span>
      </div>
      <div class="disclosure-status-grid">
        <article>
          <p class="disclosure-label">香港註冊證明書</p>
          <h4>${escapeHtml(disclosure.registration.label_zh_hant)}</h4>
          <p>${escapeHtml(disclosure.registration.summary_zh_hant)}</p>
        </article>
        <article>
          <p class="disclosure-label">專利</p>
          <h4>${escapeHtml(disclosure.patent.label_zh_hant)}</h4>
          <p>${escapeHtml(disclosure.patent.summary_zh_hant)}</p>
        </article>
        <article>
          <p class="disclosure-label">配方公開程度</p>
          <h4>${escapeHtml(disclosure.composition.label_zh_hant)}</h4>
          <p>${escapeHtml(disclosure.composition.jurisdiction_note_zh_hant)}</p>
        </article>
      </div>
      <details class="composition-details">
        <summary>查看廠商已公開的配方成分名稱</summary>
        <p class="composition-active"><strong>活性成分：</strong>${escapeHtml(disclosure.composition.active_ingredient_zh_hant)}</p>
        <dl>${compositionGroups}</dl>
        <p class="allergen-note"><strong>致敏提示：</strong>${escapeHtml(disclosure.composition.allergen_note_zh_hant)}</p>
      </details>
      <aside class="disclosure-boundary" aria-label="配方資料邊界">
        <strong>公開資料能告訴你的程度</strong>
        <p>${escapeHtml(disclosure.composition.completeness_zh_hant)}</p>
      </aside>
    </section>`;
}

function renderClinicalReview(profile) {
  const clinical = profile?.clinical_summary;
  if (!clinical) {
    return `
      <section class="information-section review-panel" aria-labelledby="clinical-title">
        <div class="section-heading">
          <div><p class="section-kicker">給使用者的藥物資料</p><h3 id="clinical-title">尚未建立已審核摘要</h3></div>
          <span class="status-badge status-pending">待整理</span>
        </div>
        <p>這個產品目前只有登記資料。請按藥袋及處方指示使用，並向醫生或藥劑師查詢用途、警告及副作用。</p>
      </section>`;
  }
  if (clinical.is_public) {
    return `
      <section class="information-section review-panel" aria-labelledby="clinical-title">
        <div class="section-heading">
          <div><p class="section-kicker">給使用者的藥物資料</p><h3 id="clinical-title">已通過臨床內容審核</h3></div>
          <span class="status-badge status-confirmed">已審核</span>
        </div>
        <p>${escapeHtml(clinical.general_use_zh_hant || clinical.uses_plain_zh_hant || clinical.summary_zh_hant || "已建立經審核的用途與安全摘要。")}</p>
      </section>`;
  }
  const sections = (clinical.sections_awaiting_review_zh_hant || [])
    .map((section) => `<li><span>${escapeHtml(section)}</span><strong>藥劑師審核中</strong></li>`)
    .join("");
  return `
    <section class="information-section review-panel" aria-labelledby="clinical-title">
      <div class="section-heading">
        <div><p class="section-kicker">給使用者的藥物資料</p><h3 id="clinical-title">內容已整理，尚未獲准公開</h3></div>
        <span class="status-badge status-review">臨床審核需要</span>
      </div>
      <p>${escapeHtml(clinical.reason_zh_hant)}</p>
      <ul class="review-list">${sections}</ul>
      <p class="action-copy"><strong>現在應怎樣做：</strong>只按藥袋和處方醫生指示使用。不要因本頁資料自行開始、停止、替換藥物或改變劑量。</p>
    </section>`;
}

function renderSupportingDetails(product, profile, ingredients) {
  const identity = profile?.identity;
  const registration = profile?.registration;
  return `
    <section class="supporting-details" aria-labelledby="supporting-title">
      <div class="supporting-heading">
        <p class="section-kicker">按需要再看</p>
        <h3 id="supporting-title">詳細資料與證據</h3>
        <p>以下內容預設收起，避免重要結論被技術資料淹沒。</p>
      </div>
      <details class="detail-disclosure">
        <summary><span>完整登記資料</span><small>持有人、劑型、首次登記及售賣規定</small></summary>
        <dl class="product-grid">
          <div><dt>香港註冊編號</dt><dd>${escapeHtml(product.registration_number)}</dd></div>
          <div><dt>登記狀態</dt><dd>官方資料集內有記錄</dd></div>
          <div><dt>活性成分</dt><dd>${escapeHtml(ingredients)}</dd></div>
          <div><dt>註冊證明書持有人</dt><dd>${escapeHtml(product.certificate_holder || "官方資料未提供")}</dd></div>
          ${identity ? `<div><dt>包裝標示劑量</dt><dd>${escapeHtml(identity.strength)}</dd></div>` : ""}
          ${identity ? `<div><dt>劑型及途徑</dt><dd>${escapeHtml(identity.dosage_form)} · ${escapeHtml(identity.route)}</dd></div>` : ""}
          ${registration ? `<div><dt>首次登記日期</dt><dd>${formatDate(registration.registration_date)}</dd></div>` : ""}
          ${registration ? `<div><dt>售賣規定</dt><dd>${escapeHtml(registration.sale_requirement)}</dd></div>` : ""}
        </dl>
      </details>
      <details class="detail-disclosure">
        <summary><span>與原研藥的關係及判定證據</span><small>原研、學名藥、授權關係與資料邊界</small></summary>
        ${renderRelationship(profile)}
      </details>
      ${profile?.regulatory_and_composition ? `<details class="detail-disclosure">
        <summary><span>配方與專利公開程度</span><small>香港版本核對狀態及廠商已公開資料</small></summary>
        ${renderRegulatoryAndComposition(profile)}
      </details>` : ""}
      ${profile?.same_ingredient_comparison ? `<details class="detail-disclosure">
        <summary><span>同成分產品比較</span><small>只比較公開登記，不代表可以互換</small></summary>
        ${renderSameIngredientComparison(profile)}
      </details>` : ""}
      <details class="detail-disclosure">
        <summary><span>藥效與安全內容狀態</span><small>顯示是否已通過臨床審核</small></summary>
        ${renderClinicalReview(profile)}
      </details>
      ${renderSources(profile)}
    </section>`;
}

function showProduct(product, source, isStale, profile) {
  const ingredients = product.ingredients.length
    ? product.ingredients.map((item) => escapeHtml(item.name)).join("、")
    : "官方資料未提供";
  const identity = profile?.identity;
  const identityLine = identity
    ? `${escapeHtml(identity.active_ingredient)} · ${escapeHtml(identity.strength)} · ${escapeHtml(identity.dosage_form)} · ${escapeHtml(identity.route)}`
    : ingredients;
  result.dataset.state = "found";
  result.innerHTML = `
    <div class="result-heading-row">
      <p class="result-kicker">官方登記中找到完全相同的編號</p>
      <span class="status-badge status-confirmed">完整編號相符</span>
    </div>
    <h2>${escapeHtml(product.product_name)}</h2>
    <p class="identity-line">${identityLine}</p>
    ${renderAnswerSummary(product, profile, ingredients)}
    ${renderCompanyRelationships(product, profile)}
    <p class="safety-copy"><strong>關於真偽：</strong>這次只確認註冊編號在官方資料中有記錄。請再核對包裝上的產品名稱、成分和劑量；相符仍不能單獨證明手上產品是真貨。</p>
    ${renderSupportingDetails(product, profile, ingredients)}
    <p class="source-copy">
      來源：<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.authority)} — ${escapeHtml(source.title)}</a><br />
      擷取日期：${formatDate(source.retrieved_at)}${isStale ? " · 資料更新可能已逾期" : ""}<br />
      ${source.licence ? `使用條款：${escapeHtml(source.licence)}` : ""}
    </p>`;
  result.hidden = false;
  result.setAttribute("tabindex", "-1");
  result.focus();
}

async function loadMedicineProfile(registrationNumber) {
  if (!medicineProfilesPromise) {
    medicineProfilesPromise = fetch(MEDICINE_PROFILES_URL, {
      headers: { Accept: "application/json" },
    }).then(async (response) => {
      if (!response.ok) return { profiles: {} };
      return response.json();
    }).catch(() => ({ profiles: {} }));
  }
  const payload = await medicineProfilesPromise;
  return payload.profiles?.[registrationNumber] || null;
}

async function searchPublicRegistry(registrationNumber) {
  if (!publicRegistryPromise) {
    publicRegistryPromise = fetch(PUBLIC_REGISTRY_URL, {
      headers: { Accept: "application/json" },
    }).then(async (response) => {
      if (!response.ok) throw new Error("未能載入官方登記資料。請稍後再試。");
      return response.json();
    });
  }
  const payload = await publicRegistryPromise;
  const normalized = `HK-${registrationNumber.replace(/\D/g, "")}`;
  const row = payload.products.find((product) => product[0] === normalized);
  return {
    source: payload.source,
    source_is_stale: false,
    results: row
      ? [{
          registration_number: row[0],
          product_name: row[1],
          certificate_holder: row[2],
          ingredients: row[3].map((name) => ({ name })),
        }]
      : [],
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  error.hidden = true;
  result.hidden = true;
  const value = input.value.trim();
  if (!/^(?:HK\s*[-:]?\s*)?\d{5}$/i.test(value)) {
    error.textContent = "請輸入 HK-XXXXX 格式的五位數字註冊編號。";
    error.hidden = false;
    input.focus();
    return;
  }

  button.disabled = true;
  button.textContent = "查閱中…";
  try {
    let payload;
    if (PUBLIC_REGISTRY_URL) {
      payload = await searchPublicRegistry(value);
    } else {
      const response = await fetch(
        `${API_BASE}/v1/products/search?registration_number=${encodeURIComponent(value)}`,
        { headers: { Accept: "application/json" } },
      );
      payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "未能完成查閱。請稍後再試。");
    }
    if (!payload.results.length) {
      showEmpty();
    } else {
      const product = payload.results[0];
      const profile = await loadMedicineProfile(product.registration_number);
      showProduct(product, payload.source, payload.source_is_stale, profile);
    }
  } catch (requestError) {
    error.textContent = requestError.message || "未能連接資料服務。請稍後再試。";
    error.hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = "查閱";
  }
});

function qualityMessage(warnings) {
  const labels = {
    insufficient_resolution: "解像度較低",
    possible_glare_or_overexposure: "可能有反光或過度曝光",
    image_too_dark: "相片可能太暗",
    possible_blur: "相片可能模糊",
  };
  return warnings.length
    ? `已安全儲存；${warnings.map((warning) => labels[warning] || warning).join("、")}，建議重拍。`
    : "已安全儲存。";
}

async function ensureScanSession() {
  if (scanSessionId) return scanSessionId;
  const response = await fetch(`${API_BASE}/v1/scan-sessions?jurisdiction=HK`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "未能建立拍攝工作階段。");
  scanSessionId = payload.id;
  clearCaptureButton.hidden = false;
  return scanSessionId;
}

function createIdempotencyKey(slot) {
  const randomPart = window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
  return `capture-${slot}-${randomPart}`;
}

async function uploadCapture(input) {
  const file = input.files?.[0];
  if (!file) return;
  const slot = input.id.replace("capture-", "");
  const card = input.closest(".capture-step");
  const statusText = card.querySelector(".capture-status");

  if (file.size > 10 * 1024 * 1024) {
    statusText.textContent = "檔案超過 10 MB，請選擇較小的相片。";
    input.value = "";
    return;
  }
  statusText.textContent = "安全處理中…";
  input.disabled = true;
  try {
    const sessionId = await ensureScanSession();
    const body = new FormData();
    body.append("slot", slot);
    body.append("image", file, file.name);
    const response = await fetch(`${API_BASE}/v1/scan-sessions/${sessionId}/uploads`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Idempotency-Key": createIdempotencyKey(slot),
      },
      body,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "未能處理相片。");
    card.dataset.state = "complete";
    statusText.textContent = qualityMessage(payload.quality_warnings || []);

    const completed = document.querySelectorAll('.capture-step[data-state="complete"]').length;
    captureMessage.textContent = completed === 3
      ? "三張相片已備妥。系統尚未進行文字辨識或藥物身份確認。"
      : `已完成 ${completed} / 3 張相片。`;
  } catch (captureError) {
    statusText.textContent = captureError.message || "未能處理相片，請稍後再試。";
  } finally {
    input.disabled = !privacyAcknowledgement.checked;
    input.value = "";
  }
}

privacyAcknowledgement.addEventListener("change", () => {
  if (!CAPTURE_ENABLED) return;
  captureInputs.forEach((captureInput) => {
    captureInput.disabled = !privacyAcknowledgement.checked;
  });
  captureMessage.textContent = privacyAcknowledgement.checked
    ? "請由包裝正面開始。"
    : "確認私隱提示後即可開始。";
});

captureInputs.forEach((captureInput) => {
  captureInput.addEventListener("change", () => uploadCapture(captureInput));
});

clearCaptureButton.addEventListener("click", async () => {
  if (!scanSessionId) return;
  clearCaptureButton.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/v1/scan-sessions/${scanSessionId}`, {
      method: "DELETE",
    });
    if (!response.ok && response.status !== 404) throw new Error("未能刪除相片。");
    scanSessionId = null;
    document.querySelectorAll(".capture-step").forEach((card) => {
      delete card.dataset.state;
      card.querySelector(".capture-status").textContent = "尚未加入";
    });
    captureMessage.textContent = "今次相片已刪除。你可以重新開始。";
    clearCaptureButton.hidden = true;
  } catch (captureError) {
    captureMessage.textContent = captureError.message || "未能刪除相片，請稍後再試。";
  } finally {
    clearCaptureButton.disabled = false;
  }
});

if (!CAPTURE_ENABLED) {
  privacyAcknowledgement.disabled = true;
  captureInputs.forEach((captureInput) => {
    captureInput.disabled = true;
  });
  captureMessage.textContent = "公開預覽暫不接收相片；請使用上方的香港註冊編號查閱。";
  document.querySelector("#capture-form").dataset.state = "unavailable";
} else {
  document.querySelector("#capture-intro").textContent =
    "依次拍攝三個位置。相片會先移除裝置資料，並在建立後最多 24 小時內刪除。";
}
