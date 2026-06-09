(function () {
  'use strict';

  // ── Config ──────────────────────────────────────────────────────────────────
  var scriptEl = document.currentScript ||
    (function () {
      var scripts = document.querySelectorAll('script[data-base-url]');
      return scripts[scripts.length - 1];
    })();

  var BASE_URL      = (scriptEl && scriptEl.getAttribute('data-base-url'))      || '';
  var APP           = (scriptEl && scriptEl.getAttribute('data-app'))           || '';
  var TOKEN         = (scriptEl && scriptEl.getAttribute('data-token'))         || '';
  var PRIMARY_COLOR = (scriptEl && scriptEl.getAttribute('data-primary-color')) || '#1d6fa4';
  var USER_NAME     = (scriptEl && scriptEl.getAttribute('data-name'))          || '';
  var USER_CONTACT  = (scriptEl && scriptEl.getAttribute('data-contact'))       || '';

  if (!BASE_URL) return; // nothing to do without a base URL

  // ── CSS ─────────────────────────────────────────────────────────────────────
  var CSS = [
    '*{box-sizing:border-box;margin:0;padding:0;}',

    // FAB
    '#fab{',
    '  position:fixed;bottom:24px;right:24px;',
    '  width:56px;height:56px;border-radius:50%;',
    '  background:var(--primary);color:#fff;',
    '  border:none;cursor:pointer;',
    '  box-shadow:0 4px 16px rgba(0,0,0,.28);',
    '  font-size:28px;line-height:56px;text-align:center;',
    '  z-index:999999;transition:transform .2s ease,box-shadow .2s ease;',
    '  display:flex;align-items:center;justify-content:center;',
    '  user-select:none;',
    '}',
    '#fab:hover{transform:scale(1.08);box-shadow:0 6px 22px rgba(0,0,0,.34);}',
    '#fab:active{transform:scale(.96);}',

    // Panel
    '#panel{',
    '  position:fixed;bottom:92px;right:24px;',
    '  width:380px;height:520px;',
    '  background:#fff;border-radius:16px;',
    '  box-shadow:0 8px 32px rgba(0,0,0,.18);',
    '  display:flex;flex-direction:column;',
    '  overflow:hidden;',
    '  z-index:999999;',
    '  transform:translateY(24px) scale(.96);opacity:0;',
    '  transition:transform .25s ease,opacity .25s ease;',
    '  pointer-events:none;',
    '  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;',
    '  font-size:14px;color:#1a1a1a;',
    '}',
    '#panel.open{transform:translateY(0) scale(1);opacity:1;pointer-events:all;}',

    // Mobile full-screen
    '@media(max-width:479px){',
    '  #panel{bottom:0;right:0;left:0;width:100vw;height:100vh;border-radius:0;}',
    '  #fab{bottom:20px;right:20px;}',
    '}',

    // Header
    '.w-header{',
    '  display:flex;align-items:center;justify-content:space-between;',
    '  padding:16px 16px 12px;',
    '  border-bottom:1px solid #f0f0f0;',
    '  background:var(--primary);color:#fff;',
    '  flex-shrink:0;',
    '}',
    '.w-header .logo{font-weight:700;font-size:15px;letter-spacing:.01em;}',
    '.w-header .logo span{font-weight:400;opacity:.85;}',
    '.w-btn-icon{',
    '  background:none;border:none;cursor:pointer;',
    '  color:#fff;font-size:20px;line-height:1;padding:4px;',
    '  border-radius:6px;display:flex;align-items:center;justify-content:center;',
    '  opacity:.85;transition:opacity .15s;',
    '}',
    '.w-btn-icon:hover{opacity:1;background:rgba(255,255,255,.15);}',

    // Body
    '.w-body{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;}',
    '.w-body::-webkit-scrollbar{width:4px;}',
    '.w-body::-webkit-scrollbar-thumb{background:#ddd;border-radius:4px;}',

    // Search
    '.w-search-wrap{position:relative;}',
    '.w-search-wrap svg{position:absolute;left:10px;top:50%;transform:translateY(-50%);opacity:.45;pointer-events:none;}',
    'input.w-input{',
    '  width:100%;padding:10px 12px 10px 36px;',
    '  border:1.5px solid #e0e0e0;border-radius:8px;',
    '  font-size:14px;outline:none;',
    '  transition:border-color .15s;',
    '  font-family:inherit;',
    '}',
    'input.w-input:focus{border-color:var(--primary);}',
    'textarea.w-input{padding:10px 12px;resize:vertical;min-height:88px;}',

    // Results
    '.w-results{list-style:none;display:flex;flex-direction:column;gap:4px;}',
    '.w-result-item{',
    '  padding:10px 12px;border-radius:8px;cursor:pointer;',
    '  border:1px solid #f0f0f0;transition:background .12s;',
    '}',
    '.w-result-item:hover{background:#f5f9ff;border-color:#c8dff5;}',
    '.w-result-title{font-weight:600;font-size:13px;margin-bottom:2px;color:#1a1a1a;}',
    '.w-result-desc{',
    '  font-size:12px;color:#666;',
    '  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;',
    '}',

    // Empty state
    '.w-empty{text-align:center;padding:16px 0 8px;color:#666;font-size:13px;}',

    // Primary button
    '.w-btn-primary{',
    '  width:100%;padding:11px 16px;',
    '  background:var(--primary);color:#fff;',
    '  border:none;border-radius:8px;',
    '  font-size:14px;font-weight:600;cursor:pointer;',
    '  font-family:inherit;letter-spacing:.01em;',
    '  transition:filter .15s;',
    '}',
    '.w-btn-primary:hover{filter:brightness(1.1);}',
    '.w-btn-primary:active{filter:brightness(.95);}',
    '.w-btn-primary:disabled{opacity:.6;cursor:default;filter:none;}',

    // Secondary / outline button
    '.w-btn-secondary{',
    '  width:100%;padding:10px 16px;',
    '  background:#fff;color:var(--primary);',
    '  border:1.5px solid var(--primary);border-radius:8px;',
    '  font-size:14px;font-weight:600;cursor:pointer;',
    '  font-family:inherit;',
    '  transition:background .15s;',
    '}',
    '.w-btn-secondary:hover{background:#f0f7ff;}',

    // Back button
    '.w-back{',
    '  display:inline-flex;align-items:center;gap:6px;',
    '  background:none;border:none;cursor:pointer;',
    '  color:var(--primary);font-size:13px;font-weight:600;',
    '  padding:0;font-family:inherit;',
    '}',
    '.w-back:hover{text-decoration:underline;}',

    // Form field
    '.w-field{display:flex;flex-direction:column;gap:5px;}',
    '.w-label{font-size:12px;font-weight:600;color:#444;letter-spacing:.02em;}',
    '.w-label .req{color:#e53e3e;}',

    // Error
    '.w-error{font-size:12px;color:#e53e3e;padding:8px 12px;background:#fff5f5;border-radius:6px;border:1px solid #fed7d7;}',

    // Divider
    '.w-divider{border:none;border-top:1px solid #f0f0f0;margin:4px 0;}',

    // Status view
    '.w-sl-no{text-align:center;padding:12px;background:#f8f8f8;border-radius:10px;margin-bottom:4px;}',
    '.w-sl-label{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#888;margin-bottom:4px;}',
    '.w-sl-value{font-size:20px;font-weight:700;color:#1a1a1a;letter-spacing:.03em;}',

    '.w-status-badge{',
    '  display:inline-block;padding:4px 12px;border-radius:20px;',
    '  font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;',
    '}',
    '.status-open{background:#fff0f0;color:#c0392b;}',
    '.status-inprogress{background:#fff7e6;color:#b7770d;}',
    '.status-resolved{background:#eafaf1;color:#1e8449;}',
    '.status-default{background:#f0f0f0;color:#555;}',

    // Stars
    '.w-stars{display:flex;gap:6px;justify-content:center;margin:8px 0;}',
    '.w-star{',
    '  font-size:28px;cursor:pointer;color:#e0e0e0;',
    '  transition:color .12s,transform .1s;',
    '  user-select:none;',
    '}',
    '.w-star.active,.w-star.hover{color:#f6c90e;}',
    '.w-star:hover{transform:scale(1.15);}',
    '.w-csat-label{text-align:center;font-size:13px;color:#555;font-weight:500;}',
    '.w-csat-thanks{text-align:center;font-size:13px;color:#1e8449;font-weight:600;padding:6px;}',

    // Spinner
    '.w-spinner{',
    '  display:inline-block;width:18px;height:18px;',
    '  border:2.5px solid rgba(255,255,255,.4);',
    '  border-top-color:#fff;border-radius:50%;',
    '  animation:spin .7s linear infinite;vertical-align:middle;margin-right:6px;',
    '}',
    '@keyframes spin{to{transform:rotate(360deg)}}',

    '.w-loading{display:flex;align-items:center;justify-content:center;gap:8px;color:#888;font-size:13px;padding:12px;}',
    '.w-loading-ring{width:20px;height:20px;border:2.5px solid #e0e0e0;border-top-color:var(--primary);border-radius:50%;animation:spin .7s linear infinite;}',
  ].join('\n');

  // ── Helpers ──────────────────────────────────────────────────────────────────
  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'className') el.className = attrs[k];
        else if (k === 'style') el.style.cssText = attrs[k];
        else if (k === 'textContent') el.textContent = attrs[k];
        else if (k === 'innerHTML') el.innerHTML = attrs[k];
        else el.setAttribute(k, attrs[k]);
      });
    }
    if (children) {
      children.forEach(function (c) {
        if (c) el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
      });
    }
    return el;
  }

  function debounce(fn, ms) {
    var t;
    return function () {
      var args = arguments;
      var ctx = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }

  function apiPost(path, body) {
    return fetch(BASE_URL + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) return Promise.reject(d);
        return d;
      });
    });
  }

  function apiGet(path) {
    return fetch(BASE_URL + path).then(function (r) { return r.json(); });
  }

  // ── Widget Factory ───────────────────────────────────────────────────────────
  function createWidget() {
    // Host container (outside shadow)
    var host = document.createElement('div');
    host.id = 'ml-support-widget';
    host.style.cssText = 'position:fixed;bottom:0;right:0;z-index:999999;pointer-events:none;';
    document.body.appendChild(host);

    var shadow = host.attachShadow({ mode: 'open' });

    // Inject styles
    var style = document.createElement('style');
    style.textContent = CSS;
    shadow.appendChild(style);

    // CSS custom property shim (shadow vars)
    var themeStyle = document.createElement('style');
    themeStyle.textContent = ':host{--primary:' + PRIMARY_COLOR + ';}';
    shadow.appendChild(themeStyle);

    // ── FAB ──────────────────────────────────────────────────────────────────
    var fab = h('button', { id: 'fab', 'aria-label': 'Support', 'aria-expanded': 'false' });
    fab.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
    shadow.appendChild(fab);

    // ── Panel ─────────────────────────────────────────────────────────────────
    var panel = h('div', { id: 'panel', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Support Widget' });
    shadow.appendChild(panel);

    var isOpen = false;

    function openPanel() {
      isOpen = true;
      panel.classList.add('open');
      fab.setAttribute('aria-expanded', 'true');
      fab.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    }

    function closePanel() {
      isOpen = false;
      panel.classList.remove('open');
      fab.setAttribute('aria-expanded', 'false');
      fab.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
    }

    fab.addEventListener('click', function () {
      if (isOpen) closePanel(); else openPanel();
    });

    // Allow pointer events on panel itself
    panel.style.pointerEvents = 'all';
    host.style.pointerEvents = 'none';
    fab.style.pointerEvents = 'all';

    // ── State ─────────────────────────────────────────────────────────────────
    var state = {
      view: 'SEARCH', // SEARCH | TICKET_FORM | TICKET_STATUS
      ticket: null,   // { sl_no, status, csat_token, rated }
      csatToken: TOKEN || null,
    };

    // ── Render Router ─────────────────────────────────────────────────────────
    function render() {
      // Clear panel
      while (panel.firstChild) panel.removeChild(panel.firstChild);
      if (state.view === 'SEARCH') renderSearch();
      else if (state.view === 'TICKET_FORM') renderTicketForm();
      else if (state.view === 'TICKET_STATUS') renderTicketStatus();
    }

    // ── SEARCH VIEW ───────────────────────────────────────────────────────────
    function renderSearch() {
      // Header
      var header = h('div', { className: 'w-header' }, [
        h('div', { className: 'logo' }, [
          'Medtronic ',
          h('span', { textContent: 'LABS Support' }),
        ]),
        h('button', { className: 'w-btn-icon', 'aria-label': 'Close support panel' }),
      ]);
      header.querySelector('button').innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
      header.querySelector('button').addEventListener('click', closePanel);
      panel.appendChild(header);

      // Body
      var body = h('div', { className: 'w-body' });
      panel.appendChild(body);

      // Search input
      var searchWrap = h('div', { className: 'w-search-wrap' });
      searchWrap.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>';
      var searchInput = h('input', {
        className: 'w-input',
        type: 'search',
        placeholder: 'Search for help...',
        'aria-label': 'Search knowledge base',
        autocomplete: 'off',
      });
      searchWrap.appendChild(searchInput);
      body.appendChild(searchWrap);

      // Results container
      var resultsWrap = h('div', {});
      body.appendChild(resultsWrap);

      // Divider
      body.appendChild(h('hr', { className: 'w-divider' }));

      // Always-visible submit button
      var submitBtn = h('button', { className: 'w-btn-secondary', textContent: 'Submit a Support Request' });
      submitBtn.addEventListener('click', function () { state.view = 'TICKET_FORM'; render(); });
      body.appendChild(submitBtn);

      // Debounced search
      function doSearch(q) {
        while (resultsWrap.firstChild) resultsWrap.removeChild(resultsWrap.firstChild);
        q = (q || '').trim();
        if (!q) return;

        var loading = h('div', { className: 'w-loading' }, [
          h('div', { className: 'w-loading-ring' }),
          document.createTextNode('Searching…'),
        ]);
        resultsWrap.appendChild(loading);

        apiGet('/widget/search?q=' + encodeURIComponent(q))
          .then(function (data) {
            while (resultsWrap.firstChild) resultsWrap.removeChild(resultsWrap.firstChild);
            var items = Array.isArray(data) ? data : (data.results || []);
            if (!items.length) {
              var empty = h('div', { className: 'w-empty' }, [
                h('p', { textContent: "Can't find what you need?" }),
                h('br'),
              ]);
              var suggestBtn = h('button', { className: 'w-btn-primary', textContent: 'Submit a Request', style: 'margin-top:8px;' });
              suggestBtn.addEventListener('click', function () { state.view = 'TICKET_FORM'; render(); });
              empty.appendChild(suggestBtn);
              resultsWrap.appendChild(empty);
              return;
            }
            var list = h('ul', { className: 'w-results' });
            items.forEach(function (item) {
              var li = h('li', { className: 'w-result-item' }, [
                h('div', { className: 'w-result-title', textContent: item.title || 'Article' }),
                h('div', { className: 'w-result-desc', textContent: item.meta_description || item.description || '' }),
              ]);
              li.addEventListener('click', function () {
                var url = item.url || item.link || (BASE_URL + '/kb/' + (item.id || item.slug));
                window.open(url, '_blank', 'noopener');
              });
              list.appendChild(li);
            });
            resultsWrap.appendChild(list);
          })
          .catch(function () {
            while (resultsWrap.firstChild) resultsWrap.removeChild(resultsWrap.firstChild);
            resultsWrap.appendChild(h('div', { className: 'w-error', textContent: 'Search failed. Please try again.' }));
          });
      }

      var debouncedSearch = debounce(doSearch, 400);
      searchInput.addEventListener('input', function () { debouncedSearch(searchInput.value); });
      searchInput.focus();
    }

    // ── TICKET_FORM VIEW ──────────────────────────────────────────────────────
    function renderTicketForm() {
      // Header
      var header = h('div', { className: 'w-header' }, [
        h('div', { className: 'logo', textContent: 'Submit a Request' }),
        h('button', { className: 'w-btn-icon', 'aria-label': 'Close' }),
      ]);
      header.querySelector('button').innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
      header.querySelector('button').addEventListener('click', closePanel);
      panel.appendChild(header);

      var body = h('div', { className: 'w-body' });
      panel.appendChild(body);

      // Back
      var backBtn = h('button', { className: 'w-back' });
      backBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg> Back to search';
      backBtn.addEventListener('click', function () { state.view = 'SEARCH'; render(); });
      body.appendChild(backBtn);

      // Name
      var nameField = h('div', { className: 'w-field' }, [
        h('label', { className: 'w-label', innerHTML: 'Name <span class="req">*</span>' }),
      ]);
      var nameInput = h('input', {
        className: 'w-input',
        type: 'text',
        placeholder: 'Your full name',
        value: USER_NAME,
        autocomplete: 'name',
      });
      nameField.appendChild(nameInput);
      body.appendChild(nameField);

      // Contact
      var contactField = h('div', { className: 'w-field' }, [
        h('label', { className: 'w-label', innerHTML: 'Phone or Email <span class="req">*</span>' }),
      ]);
      var contactInput = h('input', {
        className: 'w-input',
        type: 'text',
        placeholder: 'Phone number or email address',
        value: USER_CONTACT,
        autocomplete: 'email',
      });
      contactField.appendChild(contactInput);
      body.appendChild(contactField);

      // Issue
      var issueField = h('div', { className: 'w-field' }, [
        h('label', { className: 'w-label', innerHTML: 'Issue Description <span class="req">*</span>' }),
      ]);
      var issueInput = h('textarea', {
        className: 'w-input',
        rows: '4',
        placeholder: 'Describe your issue or question in detail…',
      });
      issueField.appendChild(issueInput);
      body.appendChild(issueField);

      // Error placeholder
      var errDiv = h('div', { style: 'display:none;' });
      body.appendChild(errDiv);

      // Submit
      var submitBtn = h('button', { className: 'w-btn-primary', textContent: 'Submit Request' });
      body.appendChild(submitBtn);

      submitBtn.addEventListener('click', function () {
        var name    = nameInput.value.trim();
        var contact = contactInput.value.trim();
        var issue   = issueInput.value.trim();

        // Validation
        if (!name || !contact || !issue) {
          errDiv.className = 'w-error';
          errDiv.textContent = 'Please fill in all required fields.';
          errDiv.style.display = '';
          return;
        }
        errDiv.style.display = 'none';

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="w-spinner"></span> Submitting…';

        apiPost('/widget/ticket', {
          name: name,
          contact: contact,
          issue: issue,
          app: APP,
          page: window.location.href,
        })
          .then(function (data) {
            state.ticket = {
              sl_no: data.sl_no || data.ticket_id || data.id || 'N/A',
              status: data.status || 'Open',
              csat_token: data.csat_token || data.token || null,
              rated: false,
            };
            if (state.ticket.csat_token) state.csatToken = state.ticket.csat_token;
            state.view = 'TICKET_STATUS';
            render();
          })
          .catch(function (err) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Request';
            var msg = (err && (err.detail || err.message || err.error)) || 'Submission failed. Please try again.';
            errDiv.className = 'w-error';
            errDiv.textContent = msg;
            errDiv.style.display = '';
          });
      });
    }

    // ── TICKET_STATUS VIEW ────────────────────────────────────────────────────
    function renderTicketStatus() {
      var ticket = state.ticket || { sl_no: 'N/A', status: 'Open' };

      // Header
      var header = h('div', { className: 'w-header' }, [
        h('div', { className: 'logo', textContent: 'Ticket Status' }),
        h('button', { className: 'w-btn-icon', 'aria-label': 'Close' }),
      ]);
      header.querySelector('button').innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
      header.querySelector('button').addEventListener('click', closePanel);
      panel.appendChild(header);

      var body = h('div', { className: 'w-body' });
      panel.appendChild(body);

      // Success notice
      body.appendChild(h('div', {
        style: 'background:#eafaf1;border:1px solid #b2dfdb;border-radius:8px;padding:10px 14px;font-size:13px;color:#1e8449;font-weight:500;',
        textContent: 'Your request has been submitted successfully.',
      }));

      // Sl No
      var slBox = h('div', { className: 'w-sl-no' }, [
        h('div', { className: 'w-sl-label', textContent: 'Ticket Reference' }),
        h('div', { className: 'w-sl-value', textContent: ticket.sl_no }),
      ]);
      body.appendChild(slBox);

      // Status badge
      var statusClass = 'status-default';
      var st = (ticket.status || '').toLowerCase().replace(/\s+/g, '');
      if (st === 'open') statusClass = 'status-open';
      else if (st === 'inprogress' || st === 'in_progress') statusClass = 'status-inprogress';
      else if (st === 'resolved' || st === 'closed') statusClass = 'status-resolved';

      var statusRow = h('div', { style: 'display:flex;align-items:center;justify-content:space-between;padding:4px 0;' }, [
        h('span', { style: 'font-size:13px;color:#555;font-weight:500;', textContent: 'Status' }),
        h('span', { className: 'w-status-badge ' + statusClass, textContent: ticket.status || 'Open' }),
      ]);
      body.appendChild(statusRow);

      body.appendChild(h('hr', { className: 'w-divider' }));

      // CSAT (only if resolved and not yet rated)
      var isResolved = (st === 'resolved' || st === 'closed');
      if (isResolved && !ticket.rated) {
        var csatSection = h('div', { style: 'display:flex;flex-direction:column;gap:6px;' });
        csatSection.appendChild(h('div', { className: 'w-csat-label', textContent: 'Rate your support experience' }));

        var starsRow = h('div', { className: 'w-stars' });
        var currentHover = 0;
        var rated = false;

        for (var i = 1; i <= 5; i++) {
          (function (val) {
            var star = h('span', { className: 'w-star', textContent: '★', 'data-val': val });
            star.addEventListener('mouseenter', function () {
              if (rated) return;
              currentHover = val;
              updateStars(starsRow, 0, currentHover);
            });
            star.addEventListener('mouseleave', function () {
              if (rated) return;
              currentHover = 0;
              updateStars(starsRow, 0, 0);
            });
            star.addEventListener('click', function () {
              if (rated) return;
              rated = true;
              updateStars(starsRow, val, 0);
              submitCsat(val, starsRow, csatSection);
            });
            starsRow.appendChild(star);
          })(i);
        }
        csatSection.appendChild(starsRow);
        body.appendChild(csatSection);
        body.appendChild(h('hr', { className: 'w-divider' }));
      }

      // Submit another
      var newBtn = h('button', { className: 'w-btn-secondary', textContent: 'Submit Another Request' });
      newBtn.addEventListener('click', function () {
        state.ticket = null;
        state.view = 'SEARCH';
        render();
      });
      body.appendChild(newBtn);

      // Back to search
      var backBtn = h('button', { className: 'w-back', style: 'justify-content:center;width:100%;margin-top:4px;' });
      backBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg> Back to Search';
      backBtn.addEventListener('click', function () { state.view = 'SEARCH'; render(); });
      body.appendChild(backBtn);
    }

    function updateStars(starsRow, active, hov) {
      var stars = starsRow.querySelectorAll('.w-star');
      var threshold = hov || active;
      stars.forEach(function (s, idx) {
        var v = idx + 1;
        if (v <= threshold) {
          s.classList.add('active');
          s.classList.remove('hover');
        } else {
          s.classList.remove('active');
          s.classList.remove('hover');
        }
      });
    }

    function submitCsat(rating, starsRow, csatSection) {
      if (!state.csatToken) {
        // No token — just show thanks
        showCsatThanks(csatSection);
        if (state.ticket) state.ticket.rated = true;
        return;
      }
      apiPost('/widget/csat/' + encodeURIComponent(state.csatToken), { rating: rating })
        .then(function () {
          if (state.ticket) state.ticket.rated = true;
          showCsatThanks(csatSection);
        })
        .catch(function () {
          if (state.ticket) state.ticket.rated = true;
          showCsatThanks(csatSection);
        });
    }

    function showCsatThanks(csatSection) {
      while (csatSection.firstChild) csatSection.removeChild(csatSection.firstChild);
      csatSection.appendChild(h('div', { className: 'w-csat-thanks', textContent: 'Thank you for your feedback!' }));
    }

    // Initial render
    render();
  }

  // ── Auto-init ─────────────────────────────────────────────────────────────
  function init() {
    if (document.getElementById('ml-support-widget')) return;
    createWidget();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
