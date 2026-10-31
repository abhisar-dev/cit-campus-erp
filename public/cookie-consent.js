/**
 * Chilika Institute of Technology (CIT) - Academic ERP
 * Cookie & Institutional Session Consent System
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'cit_cookie_consent';

  function getConsent() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      return null;
    }
  }

  function saveConsent(preferences) {
    try {
      const record = {
        essential: true,
        functional: !!preferences.functional,
        analytics: !!preferences.analytics,
        timestamp: new Date().toISOString(),
        version: '1.0'
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
      window.dispatchEvent(new CustomEvent('cit-cookie-consent-changed', { detail: record }));
    } catch (e) {
      console.warn('Unable to save cookie consent to localStorage', e);
    }
  }

  function injectStyles() {
    if (document.getElementById('cit-cookie-consent-styles')) return;

    const style = document.createElement('style');
    style.id = 'cit-cookie-consent-styles';
    style.textContent = `
      .cit-cookie-overlay {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 999999;
        max-width: 460px;
        width: calc(100vw - 48px);
        box-sizing: border-box;
        animation: citSlideInUp 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      }

      @keyframes citSlideInUp {
        from {
          opacity: 0;
          transform: translateY(24px) scale(0.98);
        }
        to {
          opacity: 1;
          transform: translateY(0) scale(1);
        }
      }

      @keyframes citSlideOutDown {
        from {
          opacity: 1;
          transform: translateY(0) scale(1);
        }
        to {
          opacity: 0;
          transform: translateY(24px) scale(0.98);
        }
      }

      .cit-cookie-card {
        background: #ffffff;
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid #e8e0d5;
        border-radius: 16px;
        box-shadow: 0 20px 45px -10px rgba(96, 15, 28, 0.16), 0 8px 24px -4px rgba(0, 0, 0, 0.08);
        padding: 22px 24px;
        color: #1c1917;
        box-sizing: border-box;
      }

      .cit-cookie-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
      }

      .cit-cookie-icon {
        width: 38px;
        height: 38px;
        border-radius: 10px;
        background: #fdf2f2;
        border: 1px solid #fad2d6;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
      }

      .cit-cookie-title-wrap {
        flex: 1;
      }

      .cit-cookie-title {
        font-size: 15px;
        font-weight: 700;
        color: #1c1917;
        margin: 0;
        line-height: 1.25;
      }

      .cit-cookie-badge {
        font-size: 11px;
        font-weight: 700;
        color: #600f1c;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        display: inline-block;
        margin-top: 2px;
      }

      .cit-cookie-body {
        font-size: 13px;
        line-height: 1.55;
        color: #57534e;
        margin-bottom: 16px;
      }

      .cit-cookie-body a {
        color: #600f1c;
        font-weight: 600;
        text-decoration: underline;
        text-underline-offset: 2px;
        transition: color 0.15s;
      }

      .cit-cookie-body a:hover {
        color: #8f1d2e;
      }

      .cit-cookie-details {
        display: none;
        background: #fbf6ee;
        border: 1px solid #e8e0d5;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 16px;
        font-size: 12px;
      }

      .cit-cookie-details.open {
        display: block;
        animation: citFadeIn 0.2s ease-in-out;
      }

      @keyframes citFadeIn {
        from { opacity: 0; transform: translateY(-4px); }
        to { opacity: 1; transform: translateY(0); }
      }

      .cit-cookie-option {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        padding: 8px 0;
        border-bottom: 1px solid #efe8dd;
      }

      .cit-cookie-option:last-child {
        border-bottom: none;
        padding-bottom: 2px;
      }

      .cit-cookie-option-title {
        font-weight: 700;
        color: #1c1917;
        margin-bottom: 2px;
      }

      .cit-cookie-option-desc {
        color: #44403c;
        font-size: 11px;
        line-height: 1.4;
      }

      .cit-cookie-switch-label {
        font-size: 11px;
        font-weight: 600;
        color: #600f1c;
        background: #fdf2f2;
        padding: 3px 8px;
        border-radius: 6px;
        white-space: nowrap;
        border: 1px solid #fad2d6;
      }

      .cit-cookie-actions {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
      }

      .cit-btn-accept {
        background: #600f1c;
        color: #ffffff;
        border: 1px solid #4a0b15;
        font-weight: 600;
        font-size: 13px;
        padding: 9px 16px;
        border-radius: 8px;
        cursor: pointer;
        flex: 1;
        min-width: 120px;
        text-align: center;
        transition: background 0.15s, transform 0.1s;
      }

      .cit-btn-accept:hover {
        background: #4a0b15;
      }

      .cit-btn-accept:active {
        transform: scale(0.98);
      }

      .cit-btn-essential {
        background: #fbf6ee;
        color: #292524;
        border: 1px solid #d5cbbe;
        font-weight: 600;
        font-size: 13px;
        padding: 9px 14px;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.15s, border-color 0.15s;
      }

      .cit-btn-essential:hover {
        background: #f3ece0;
        border-color: #baa997;
      }

      .cit-btn-customize {
        background: transparent;
        color: #44403c;
        border: none;
        font-weight: 600;
        font-size: 12px;
        padding: 6px 10px;
        cursor: pointer;
        text-decoration: underline;
        text-underline-offset: 3px;
        margin-left: auto;
        transition: color 0.15s;
      }

      .cit-btn-customize:hover {
        color: #1c1917;
      }

      /* Floating revisit trigger in corner */
      .cit-cookie-revisit-trigger {
        position: fixed;
        bottom: 16px;
        left: 16px;
        z-index: 99999;
        background: #ffffff;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid #e8e0d5;
        color: #44403c;
        font-size: 11px;
        font-weight: 600;
        padding: 6px 12px;
        border-radius: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
        opacity: 0.8;
      }

      .cit-cookie-revisit-trigger:hover {
        opacity: 1;
        color: #600f1c;
        border-color: #600f1c;
        transform: translateY(-2px);
      }

      @media (max-width: 600px) {
        .cit-cookie-overlay {
          bottom: 12px;
          right: 12px;
          left: 12px;
          width: auto;
          max-width: none;
        }
        .cit-cookie-card {
          padding: 18px 16px;
        }
        .cit-cookie-actions {
          flex-direction: column;
          align-items: stretch;
        }
        .cit-btn-customize {
          margin-left: 0;
          text-align: center;
          margin-top: 4px;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function renderBanner(forceOpen) {
    // If already consented and not forced open, don't show
    if (getConsent() && !forceOpen) {
      renderRevisitTrigger();
      return;
    }

    // Remove existing banner if present
    const existing = document.getElementById('cit-cookie-banner');
    if (existing) existing.remove();

    injectStyles();

    const overlay = document.createElement('div');
    overlay.id = 'cit-cookie-banner';
    overlay.className = 'cit-cookie-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-live', 'polite');
    overlay.setAttribute('aria-label', 'Cookie and Session Consent');

    overlay.innerHTML = `
      <div class="cit-cookie-card">
        <div class="cit-cookie-header">
          <div class="cit-cookie-icon" aria-hidden="true">🍪</div>
          <div class="cit-cookie-title-wrap">
            <h3 class="cit-cookie-title">Cookie & Session Privacy</h3>
            <span class="cit-cookie-badge">Chilika Institute of Technology</span>
          </div>
        </div>

        <div class="cit-cookie-body">
          CIT Campus ERP uses necessary session tokens and storage to secure your login clearance, preserve timetable view filters, and handle venue allocations. By accepting, you consent to our data handling in accordance with our 
          <a href="/privacy#section-cookies" target="_blank" rel="noopener noreferrer">Privacy Policy</a> and <a href="/terms" target="_blank" rel="noopener noreferrer">Terms & Conditions</a>.
        </div>

        <div class="cit-cookie-details" id="cit-cookie-details-panel">
          <div class="cit-cookie-option">
            <div>
              <div class="cit-cookie-option-title">Essential Authentication & Security</div>
              <div class="cit-cookie-option-desc">Strictly required for user sign-in, clearance tokens, and anti-tamper security. Cannot be disabled.</div>
            </div>
            <span class="cit-cookie-switch-label">Always Active</span>
          </div>

          <div class="cit-cookie-option">
            <div>
              <div class="cit-cookie-option-title">Timetable & View Preferences</div>
              <div class="cit-cookie-option-desc">Remembers your selected department, cohort view mode, and timetable filter states.</div>
            </div>
            <label style="display:flex; align-items:center; cursor:pointer;">
              <input type="checkbox" id="cit-pref-functional" checked style="accent-color: #600f1c; width:16px; height:16px; cursor:pointer;">
            </label>
          </div>

          <div class="cit-cookie-option">
            <div>
              <div class="cit-cookie-option-title">Performance Telemetry</div>
              <div class="cit-cookie-option-desc">Anonymous client-side metrics to assess timetable calculation latency and platform responsiveness.</div>
            </div>
            <label style="display:flex; align-items:center; cursor:pointer;">
              <input type="checkbox" id="cit-pref-analytics" checked style="accent-color: #600f1c; width:16px; height:16px; cursor:pointer;">
            </label>
          </div>
        </div>

        <div class="cit-cookie-actions">
          <button type="button" class="cit-btn-accept" id="cit-btn-accept-all">Accept All</button>
          <button type="button" class="cit-btn-essential" id="cit-btn-essential-only">Essential Only</button>
          <button type="button" class="cit-btn-customize" id="cit-btn-toggle-prefs">Customize</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    // Event listeners
    const btnAcceptAll = overlay.querySelector('#cit-btn-accept-all');
    const btnEssential = overlay.querySelector('#cit-btn-essential-only');
    const btnToggle = overlay.querySelector('#cit-btn-toggle-prefs');
    const detailsPanel = overlay.querySelector('#cit-cookie-details-panel');

    btnToggle.addEventListener('click', function () {
      const isOpen = detailsPanel.classList.toggle('open');
      btnToggle.textContent = isOpen ? 'Hide Options' : 'Customize';
      if (isOpen) {
        btnAcceptAll.textContent = 'Save All';
      }
    });

    btnAcceptAll.addEventListener('click', function () {
      const functional = document.getElementById('cit-pref-functional') ? document.getElementById('cit-pref-functional').checked : true;
      const analytics = document.getElementById('cit-pref-analytics') ? document.getElementById('cit-pref-analytics').checked : true;
      saveConsent({ functional, analytics });
      dismissBanner(overlay);
    });

    btnEssential.addEventListener('click', function () {
      saveConsent({ functional: false, analytics: false });
      dismissBanner(overlay);
    });
  }

  function dismissBanner(overlay) {
    if (!overlay) return;
    overlay.style.animation = 'citSlideOutDown 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards';
    setTimeout(() => {
      overlay.remove();
      renderRevisitTrigger();
    }, 300);
  }

  function renderRevisitTrigger() {
    if (document.getElementById('cit-cookie-revisit-btn')) return;

    injectStyles();

    const btn = document.createElement('button');
    btn.id = 'cit-cookie-revisit-btn';
    btn.className = 'cit-cookie-revisit-trigger';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Open cookie and privacy consent preferences');
    btn.innerHTML = `<span aria-hidden="true">🍪</span> Cookie Settings`;

    btn.addEventListener('click', function () {
      btn.remove();
      renderBanner(true);
    });

    document.body.appendChild(btn);
  }

  // Global API exposed for manual triggers (e.g. from footer links)
  window.CITCookies = {
    getConsent: getConsent,
    openPreferences: function () {
      renderBanner(true);
    }
  };

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => renderBanner(false));
  } else {
    renderBanner(false);
  }
})();
