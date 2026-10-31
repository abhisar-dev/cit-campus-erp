/**
 * Chilika Institute of Technology (CIT) - Campus Operations ERP
 * Institutional Telemetry & Privacy-First Analytics Module
 * DPDP Act 2023 Compliant · Zero Third-Party Advertising Pixels
 */
(function (window, document) {
  'use strict';

  // Config & State
  const CONFIG = {
    endpoint: '/api/analytics/event',
    storageKey: 'cit_analytics_session',
    consentStorageKey: 'cit_cookie_consent',
    flushIntervalMs: 5000,
    gaMeasurementId: window.CIT_GA_ID || null // Optional Google Analytics ID
  };

  // Generate an ephemeral, anonymous session ID (rotates each session, no PII)
  function getSessionId() {
    let sid = sessionStorage.getItem(CONFIG.storageKey);
    if (!sid) {
      sid = 'cit_s_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
      sessionStorage.setItem(CONFIG.storageKey, sid);
    }
    return sid;
  }

  // Check consent from CIT Cookie Manager
  function hasAnalyticsConsent() {
    try {
      if (window.CITCookies && typeof window.CITCookies.getConsent === 'function') {
        const c = window.CITCookies.getConsent();
        return c ? !!c.analytics : false;
      }
      const raw = localStorage.getItem(CONFIG.consentStorageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        return !!parsed.analytics;
      }
    } catch (e) {}
    // Default to opt-in for internal anonymous telemetry if not explicitly refused
    return true;
  }

  // Telemetry buffer
  let eventQueue = [];
  let isFlushing = false;
  let sessionStartTime = Date.now();

  // Detect basic device category anonymously
  function getDeviceCategory() {
    const ua = navigator.userAgent.toLowerCase();
    if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) {
      return 'tablet';
    }
    if (/Mobile|iP(hone|od)|Android|BlackBerry|IEMobile|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(obi|ini)/i.test(ua)) {
      return 'mobile';
    }
    return 'desktop';
  }

  // Queue an event
  function enqueue(eventType, payload) {
    if (!hasAnalyticsConsent()) {
      return;
    }

    const eventObj = {
      type: eventType,
      path: window.location.pathname || '/',
      title: document.title || 'CIT Portal',
      referrer: document.referrer ? new URL(document.referrer, window.location.href).pathname : '',
      sessionId: getSessionId(),
      device: getDeviceCategory(),
      screen: `${window.innerWidth}x${window.innerHeight}`,
      timestamp: new Date().toISOString(),
      payload: payload || {}
    };

    eventQueue.push(eventObj);

    // Forward to GA4 if configured and consented
    if (CONFIG.gaMeasurementId && typeof window.gtag === 'function') {
      try {
        if (eventType === 'page_view') {
          window.gtag('event', 'page_view', {
            page_path: eventObj.path,
            page_title: eventObj.title
          });
        } else {
          window.gtag('event', payload.action || eventType, {
            event_category: payload.category || 'User Interaction',
            event_label: payload.label || '',
            value: payload.value || 0
          });
        }
      } catch (err) {}
    }

    // Auto-flush if queue grows
    if (eventQueue.length >= 5) {
      flush();
    }
  }

  // Dispatch events to backend
  function flush() {
    if (eventQueue.length === 0 || isFlushing) return;
    if (!hasAnalyticsConsent()) {
      eventQueue = [];
      return;
    }

    isFlushing = true;
    const batch = eventQueue.slice();
    eventQueue = [];

    const data = JSON.stringify({ events: batch });

    if (navigator.sendBeacon) {
      const ok = navigator.sendBeacon(CONFIG.endpoint, data);
      if (ok) {
        isFlushing = false;
        return;
      }
    }

    fetch(CONFIG.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: data,
      keepalive: true
    }).catch(function () {
      // Re-queue non-fatally
      eventQueue = batch.concat(eventQueue).slice(-50);
    }).finally(function () {
      isFlushing = false;
    });
  }

  // Performance & Web Vitals Telemetry
  function capturePerformanceMetrics() {
    if (!hasAnalyticsConsent() || !window.performance) return;

    window.addEventListener('load', function () {
      setTimeout(function () {
        try {
          const nav = performance.getEntriesByType('navigation')[0];
          if (nav) {
            enqueue('performance', {
              dns_ms: Math.round(nav.domainLookupEnd - nav.domainLookupStart),
              tcp_ms: Math.round(nav.connectEnd - nav.connectStart),
              ttfb_ms: Math.round(nav.responseStart - nav.requestStart),
              dom_ready_ms: Math.round(nav.domContentLoadedEventEnd - nav.startTime),
              load_ms: Math.round(nav.loadEventEnd - nav.startTime)
            });
          }
        } catch (e) {}
      }, 500);
    });
  }

  // Initialize optional Google Analytics 4 stub safely
  function initGA4(measurementId) {
    if (!measurementId || !hasAnalyticsConsent()) return;
    if (document.getElementById('cit-gtag-script')) return;

    const script = document.createElement('script');
    script.id = 'cit-gtag-script';
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag('js', new Date());
    gtag('config', measurementId, {
      anonymize_ip: true,
      send_page_view: false // Managed manually via trackPageView
    });
  }

  // Public API
  const CITAnalytics = {
    // Track page views
    pageView: function (customPath, customTitle) {
      enqueue('page_view', {
        custom_path: customPath || window.location.pathname,
        custom_title: customTitle || document.title
      });
    },

    // Track user interactions (clicks, tab switches, downloads)
    trackEvent: function (category, action, label, value) {
      enqueue('event', {
        category: category || 'General',
        action: action || 'Click',
        label: label || '',
        value: typeof value === 'number' ? value : 0
      });
    },

    // Track operation timings (e.g. CP-SAT timetable solver duration)
    trackTiming: function (name, durationMs, category) {
      enqueue('timing', {
        metric_name: name,
        duration_ms: Math.round(durationMs),
        category: category || 'Solver Latency'
      });
    },

    // Manually flush events
    flush: flush,

    // Configure GA4 ID dynamically
    setMeasurementId: function (id) {
      CONFIG.gaMeasurementId = id;
      initGA4(id);
    }
  };

  window.CITAnalytics = CITAnalytics;

  // React to Cookie Consent Changes
  window.addEventListener('cit-cookie-consent-changed', function (e) {
    if (e.detail && e.detail.analytics) {
      if (CONFIG.gaMeasurementId) initGA4(CONFIG.gaMeasurementId);
      CITAnalytics.pageView();
      flush();
    } else {
      eventQueue = [];
    }
  });

  // Automatic initial page view & performance capture
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      CITAnalytics.pageView();
      capturePerformanceMetrics();
    });
  } else {
    CITAnalytics.pageView();
    capturePerformanceMetrics();
  }

  // Periodic flush & flush on page exit
  setInterval(flush, CONFIG.flushIntervalMs);
  window.addEventListener('beforeunload', flush);
  window.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') flush();
  });

  // Track session duration on unload
  window.addEventListener('pagehide', function () {
    const durationSec = Math.round((Date.now() - sessionStartTime) / 1000);
    enqueue('session_end', { duration_sec: durationSec });
    flush();
  });

})(window, document);
