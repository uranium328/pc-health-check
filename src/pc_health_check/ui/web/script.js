/* 電腦硬體健康檢測儀表板 — 前端邏輯
 *
 * 職責邊界：本檔只負責「呈現」從 Python 端（js_api）拿到的現成資料，
 * 不重做任何健康判讀（正常/注意/警告的門檻邏輯全部在 health.py），
 * 這裡只做資料 -> DOM 的轉換與少量純展示性的文字切版（見 splitMetricText）。
 *
 * 唯讀健康檢測工具：本檔不包含任何會送出「寫入」指令的呼叫，只呼叫
 * window.pywebview.api.get_report() / refresh()，兩者在 Python 端都只是
 * 重新讀取健康報告，不做任何硬體/韌體/磁碟寫入操作。
 */

(function () {
  'use strict';

  // 單一 SVG 線性圖示風格（Lucide outline icon set，stroke 統一在 CSS 控制，
  // 這裡只放 24x24 viewBox 下的內部路徑資料）。
  var ICONS = {
    activity:
      '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    'refresh-cw':
      '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    cpu:
      '<path d="M12 20v2"/><path d="M12 2v2"/><path d="M17 20v2"/><path d="M17 2v2"/><path d="M2 12h2"/><path d="M2 17h2"/><path d="M2 7h2"/><path d="M20 12h2"/><path d="M20 17h2"/><path d="M20 7h2"/><path d="M7 20v2"/><path d="M7 2v2"/><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="8" y="8" width="8" height="8" rx="1"/>',
    zap:
      '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    'memory-stick':
      '<path d="M12 12v-2"/><path d="M12 18v-2"/><path d="M16 12v-2"/><path d="M16 18v-2"/><path d="M2 11h1.5"/><path d="M20 18v-2"/><path d="M20.5 11H22"/><path d="M4 18v-2"/><path d="M8 12v-2"/><path d="M8 18v-2"/><rect x="2" y="6" width="20" height="10" rx="2"/>',
    'hard-drive':
      '<path d="M10 16h.01"/><path d="M2.212 11.577a2 2 0 0 0-.212.896V18a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5.527a2 2 0 0 0-.212-.896L18.55 5.11A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><path d="M21.946 12.013H2.054"/><path d="M6 16h.01"/>',
    plug:
      '<path d="M12 22v-5"/><path d="M15 8V2"/><path d="M17 8a1 1 0 0 1 1 1v4a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1z"/><path d="M9 8V2"/>',
    monitor:
      '<rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/>',
    'circle-check': '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    'circle-alert':
      '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    'triangle-alert':
      '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    'circle-minus': '<circle cx="12" cy="12" r="10"/><path d="M8 12h8"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'
  };

  // 六大元件卡片各自的圖示語意（CPU→閃電/效能、主機板→晶片、記憶體→記憶體條、
  // 硬碟→硬碟、電源供應器→插頭、顯示卡→螢幕），依 docs/ui-design-spec.md
  // 建議挑選。CPU 刻意不沿用 'cpu' 這個 icon key（該 key 的晶片圖示已被
  // 主機板卡片沿用在先，不更動既有卡片圖示），改用 'zap' 代表處理效能/負載。
  var SECTION_ICON = {
    cpu: 'zap',
    motherboard: 'cpu',
    memory: 'memory-stick',
    disk: 'hard-drive',
    psu: 'plug',
    gpu: 'monitor'
  };

  // 4 級狀態徽章：一律「圖示 + 中文文字」，不單靠顏色。
  var BADGE_META = {
    normal: { icon: 'circle-check', label: '正常', cls: 'level-normal' },
    attention: { icon: 'circle-alert', label: '注意', cls: 'level-attention' },
    critical: { icon: 'triangle-alert', label: '警告', cls: 'level-critical' },
    unavailable: { icon: 'circle-minus', label: '不可用', cls: 'level-unavailable' }
  };

  // health.py 的判讀字串（NORMAL/ATTENTION/CRITICAL）對應到本檔的徽章 key。
  // 這只是「已知有限集合的字串 -> CSS class」對照，不是重新判讀健康門檻。
  var VERDICT_LEVEL = { 正常: 'normal', 注意: 'attention', 警告: 'critical' };

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function iconMarkup(name, extraClass) {
    var inner = ICONS[name] || '';
    var cls = 'icon' + (extraClass ? ' ' + extraClass : '');
    return (
      '<svg class="' +
      cls +
      '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true" focusable="false">' +
      inner +
      '</svg>'
    );
  }

  function badgeHtml(level, size) {
    var meta = BADGE_META[level] || BADGE_META.unavailable;
    var sizeCls = size ? ' badge-' + size : '';
    return (
      '<span class="badge ' +
      meta.cls +
      sizeCls +
      '">' +
      iconMarkup(meta.icon, 'badge-icon') +
      '<span class="badge-label">' +
      meta.label +
      '</span></span>'
    );
  }

  // health.py 產出的每一行文字通常是「標籤：數值（判讀）」的組合字串
  // （例如「溫度：45°C（正常）」）。這裡只做「純展示性」的字串切版，把它
  // 拆成左邊標籤／右邊數值兩欄，並在有判讀時把已經算好的判讀徽章獨立
  // 顯示出來——不重新計算任何門檻或判讀結果，判讀結果 100% 來自
  // item.verdict（health.py 算好的）。找不到全形冒號就整行原樣顯示。
  function splitMetricText(text, verdict) {
    var colonIndex = text.indexOf('：'); // "："
    var label = null;
    var value = text;
    if (colonIndex !== -1) {
      label = text.slice(0, colonIndex);
      value = text.slice(colonIndex + 1);
    }
    if (verdict) {
      var suffix = '（' + verdict + '）'; // "（判讀）"
      if (value.slice(-suffix.length) === suffix) {
        value = value.slice(0, -suffix.length);
      }
    }
    return { label: label, value: value };
  }

  function renderMetricRow(item) {
    var parts = splitMetricText(item.text, item.verdict);
    var level = item.verdict ? VERDICT_LEVEL[item.verdict] : null;
    var badge = level ? badgeHtml(level, 'sm') : '';

    if (parts.label === null) {
      return (
        '<div class="metric-line"><span class="metric-value metric-value-full">' +
        escapeHtml(parts.value) +
        '</span>' +
        badge +
        '</div>'
      );
    }

    return (
      '<div class="metric-row"><span class="metric-label">' +
      escapeHtml(parts.label) +
      '</span><span class="metric-value">' +
      escapeHtml(parts.value) +
      '</span>' +
      badge +
      '</div>'
    );
  }

  function renderDevice(device) {
    var html = '';
    if (device.name) {
      html += '<h3 class="device-name">' + escapeHtml(device.name) + '</h3>';
    }
    html += '<div class="metric-list">' + device.items.map(renderMetricRow).join('') + '</div>';
    return html;
  }

  function renderCard(section, index) {
    var iconName = SECTION_ICON[section.key] || 'cpu';
    var badge = badgeHtml(section.badge_level);
    var body;

    if (!section.available) {
      body =
        '<div class="card-unavailable">' +
        iconMarkup('circle-minus', 'card-unavailable-icon') +
        '<p class="card-unavailable-text">' +
        escapeHtml(section.unavailable_reason || '目前無法讀取此項目。') +
        '</p></div>';
    } else if (!section.devices || section.devices.length === 0) {
      body =
        '<div class="card-unavailable">' +
        iconMarkup('circle-minus', 'card-unavailable-icon') +
        '<p class="card-unavailable-text">未偵測到任何可用讀數。</p></div>';
    } else {
      body = section.devices.map(renderDevice).join('<hr class="device-divider">');
    }

    return (
      '<article class="card" style="--stagger-index:' +
      index +
      '"><header class="card-header"><div class="card-title">' +
      iconMarkup(iconName, 'card-icon') +
      '<h2>' +
      escapeHtml(section.title) +
      '</h2></div>' +
      badge +
      '</header><div class="card-body">' +
      body +
      '</div></article>'
    );
  }

  function renderSkeletonCards(container, count) {
    var html = '';
    for (var i = 0; i < count; i++) {
      html +=
        '<article class="card card-skeleton" aria-hidden="true">' +
        '<div class="skeleton-line skeleton-line-title"></div>' +
        '<div class="skeleton-line"></div>' +
        '<div class="skeleton-line"></div>' +
        '<div class="skeleton-line short"></div></article>';
    }
    container.innerHTML = html;
  }

  function renderOverallBanner(overall) {
    var el = document.getElementById('overall-banner');
    var meta = BADGE_META[overall.level] || BADGE_META.normal;
    el.className = 'banner overall-banner ' + meta.cls;
    el.innerHTML =
      iconMarkup(meta.icon, 'banner-icon') +
      '<span class="banner-text">' +
      escapeHtml(overall.text) +
      '</span>';
  }

  function renderInfoBanner(info) {
    var el = document.getElementById('info-banner');
    if (!info || !info.show) {
      el.hidden = true;
      el.innerHTML = '';
      return;
    }
    el.hidden = false;
    // 注意：這裡刻意不做成可點擊超連結。pywebview 內建的本地伺服器只會
    // 服務 index.html 所在目錄（ui/web/）之下的檔案，docs/setup.md 在專案
    // 更上層目錄，實測 bottle 的 static_file 會擋掉這種目錄穿越請求
    // （回 403），做成連結點下去只會壞掉、且視窗沒有返回鍵；因此改用
    // 純文字＋等寬樣式提及檔名，讓使用者自行到專案資料夾開啟。
    el.innerHTML =
      iconMarkup('info', 'banner-icon') +
      '<span class="banner-text">' +
      escapeHtml(info.text) +
      ' 詳細設定步驟請見專案內的 <code class="info-link">docs/setup.md</code>。' +
      '</span>';
  }

  function render(payload) {
    var grid = document.getElementById('cards-grid');

    if (!payload || payload.ok === false) {
      var errorText =
        payload && payload.error
          ? '讀取健康報告時發生問題：' + payload.error
          : '讀取健康報告時發生未知問題。';
      renderOverallBanner({ level: 'unavailable', text: '整體狀況：目前無法產生報告' });
      renderInfoBanner({
        show: true,
        text: errorText + '這通常代表尚未安裝相依套件、缺少 PawnIO 驅動，或未以系統管理員身分執行。'
      });
      grid.setAttribute('aria-busy', 'false');
      grid.innerHTML = '';
      if (payload && payload.generated_at_display) {
        document.getElementById('last-updated-time').textContent = payload.generated_at_display;
      }
      return;
    }

    renderOverallBanner(payload.overall);
    renderInfoBanner(payload.info_banner);
    grid.setAttribute('aria-busy', 'false');
    grid.innerHTML = payload.sections.map(renderCard).join('');
    document.getElementById('last-updated-time').textContent = payload.generated_at_display || '--:--:--';
  }

  var refreshBtn = document.getElementById('refresh-btn');
  var refreshLabel = refreshBtn.querySelector('.btn-refresh-label');

  function setLoading(loading) {
    refreshBtn.disabled = loading;
    refreshBtn.classList.toggle('is-loading', loading);
    refreshLabel.textContent = loading ? '更新中…' : '重新整理';
  }

  function apiUnavailableError() {
    return Promise.reject(new Error('pywebview API 尚未就緒，請稍後再試。'));
  }

  function loadReport(isRefresh) {
    var grid = document.getElementById('cards-grid');
    if (!isRefresh) {
      grid.setAttribute('aria-busy', 'true');
      renderSkeletonCards(grid, 6);
    }
    setLoading(true);

    var call;
    if (window.pywebview && window.pywebview.api) {
      call = isRefresh ? window.pywebview.api.refresh() : window.pywebview.api.get_report();
    } else {
      call = apiUnavailableError();
    }

    call
      .then(function (payload) {
        render(payload);
      })
      .catch(function (err) {
        render({ ok: false, error: err && err.message ? err.message : String(err) });
      })
      .then(function () {
        setLoading(false);
      });
  }

  refreshBtn.addEventListener('click', function () {
    loadReport(true);
  });

  function init() {
    loadReport(false);
  }

  if (window.pywebview) {
    init();
  } else {
    window.addEventListener('pywebviewready', init);
  }
})();
