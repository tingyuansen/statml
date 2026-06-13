/* ============================================================
   render.js — Markdown + Jupyter notebook renderer
   Handles: LaTeX (KaTeX), syntax highlighting (highlight.js),
   copy buttons, code/markdown cells, and all output types
   (stream, errors, images, HTML tables/dataframes, animations).
   ============================================================ */
(function () {
  'use strict';

  /* ---------- small utils ---------- */
  const joinSrc = (s) => Array.isArray(s) ? s.join('') : (s || '');
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function escapeAttr(str) {
    return escapeHtml(str).replace(/'/g, '&#39;');
  }
  // strip ANSI color escape codes from tracebacks
  function stripAnsi(str) {
    return String(str).replace(/\x1b\[[0-9;]*m/g, '').replace(/\x1b\[[0-9;]*[A-Za-z]/g, '');
  }
  function slugify(t) {
    return String(t).toLowerCase().trim()
      .replace(/[^\w\s-]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-').slice(0, 60);
  }

  /* ---------- code highlighting ---------- */
  function highlight(code, lang) {
    try {
      if (lang && window.hljs && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value;
      }
      if (window.hljs) return hljs.highlightAuto(code, ['python', 'bash', 'json', 'yaml']).value;
    } catch (e) {}
    return escapeHtml(code);
  }

  const COPY_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>';
  const CHECK_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';

  function codeCard(rawCode, lang, count) {
    const langLabel = lang ? lang.charAt(0).toUpperCase() + lang.slice(1) : 'Python';
    const promptHtml = (count != null && count !== '')
      ? `<span style="font-family:var(--font-mono);color:oklch(0.6 0.02 264)">[${count}]</span>` : '';
    return `<div class="nb-cell"><div class="code-card">
      <div class="code-top">
        <span class="code-label"><span class="lang-dot"></span>${promptHtml}${langLabel}</span>
        <button class="copy-btn" type="button" data-code="${escapeAttr(rawCode)}" aria-label="Copy code">
          <span class="ci">${COPY_SVG}</span><span class="ct">Copy</span></button>
      </div>
      <pre class="code-body"><code class="hljs language-${lang || 'python'}">${highlight(rawCode, lang || 'python')}</code></pre>
    </div></div>`;
  }

  /* ---------- markdown pipeline (code/math protected) ---------- */
  function renderMarkdown(md) {
    const store = { cb: [], ic: [], dm: [], im: [] };
    let s = md;

    // 1. fenced code blocks
    s = s.replace(/```([\w+\-]*)[^\S\n]*\n([\s\S]*?)```/g, (m, lang, body) => {
      store.cb.push({ lang: lang.trim(), body: body.replace(/\n$/, '') });
      return `\n\n@@CB${store.cb.length - 1}@@\n\n`;
    });
    // 2. inline code
    s = s.replace(/`([^`\n]+)`/g, (m, body) => {
      store.ic.push(body); return `@@IC${store.ic.length - 1}@@`;
    });
    // 3. display math  $$..$$  and  \[..\]
    s = s.replace(/\$\$([\s\S]+?)\$\$/g, (m, body) => {
      store.dm.push(body); return `@@DM${store.dm.length - 1}@@`;
    });
    s = s.replace(/\\\[([\s\S]+?)\\\]/g, (m, body) => {
      store.dm.push(body); return `@@DM${store.dm.length - 1}@@`;
    });
    // 4. inline math  $..$  and  \(..\)
    s = s.replace(/\$(?!\s)((?:[^$\n\\]|\\.)+?)(?<!\s)\$/g, (m, body) => {
      store.im.push(body); return `@@IM${store.im.length - 1}@@`;
    });
    s = s.replace(/\\\(([\s\S]+?)\\\)/g, (m, body) => {
      store.im.push(body); return `@@IM${store.im.length - 1}@@`;
    });

    let html = window.marked.parse(s, { gfm: true, breaks: false });

    const kd = (tex, display) => {
      try { return window.katex.renderToString(tex.trim(), { displayMode: display, throwOnError: false, strict: false }); }
      catch (e) { return `<code class="math-err">${escapeHtml(tex)}</code>`; }
    };
    // restore (handle paragraph-wrapped block tokens first)
    html = html.replace(/<p>\s*@@DM(\d+)@@\s*<\/p>/g, (m, i) => kd(store.dm[i], true));
    html = html.replace(/@@DM(\d+)@@/g, (m, i) => kd(store.dm[i], true));
    html = html.replace(/@@IM(\d+)@@/g, (m, i) => kd(store.im[i], false));
    html = html.replace(/<p>\s*@@CB(\d+)@@\s*<\/p>/g, (m, i) => codeCard(store.cb[i].body, store.cb[i].lang));
    html = html.replace(/@@CB(\d+)@@/g, (m, i) => codeCard(store.cb[i].body, store.cb[i].lang));
    html = html.replace(/@@IC(\d+)@@/g, (m, i) => `<code>${escapeHtml(store.ic[i])}</code>`);
    return html;
  }

  /* ---------- notebook outputs ---------- */
  function renderOutputs(outputs) {
    if (!outputs || !outputs.length) return '';
    let html = '';
    for (const out of outputs) {
      const t = out.output_type;
      if (t === 'stream') {
        const cls = out.name === 'stderr' ? 'out-stream stderr' : 'out-stream';
        html += `<div class="out-block"><pre class="${cls}">${escapeHtml(joinSrc(out.text))}</pre></div>`;
      } else if (t === 'error') {
        const tb = stripAnsi((out.traceback || []).join('\n')) ||
          `${out.ename || 'Error'}: ${out.evalue || ''}`;
        html += `<div class="out-block"><pre class="out-error">${escapeHtml(tb)}</pre></div>`;
      } else if (t === 'execute_result' || t === 'display_data') {
        const d = out.data || {};
        if (d['image/png']) {
          const b64 = joinSrc(d['image/png']).replace(/\s/g, '');
          html += `<div class="out-block"><div class="out-img"><img loading="lazy" src="data:image/png;base64,${b64}"></div></div>`;
        } else if (d['image/jpeg']) {
          const b64 = joinSrc(d['image/jpeg']).replace(/\s/g, '');
          html += `<div class="out-block"><div class="out-img"><img loading="lazy" src="data:image/jpeg;base64,${b64}"></div></div>`;
        } else if (d['image/svg+xml']) {
          html += `<div class="out-block"><div class="out-img">${joinSrc(d['image/svg+xml'])}</div></div>`;
        } else if (d['text/html']) {
          html += `<div class="out-block"><div class="out-html">${joinSrc(d['text/html'])}</div></div>`;
        } else if (d['text/plain']) {
          html += `<div class="out-block"><pre class="out-text">${escapeHtml(joinSrc(d['text/plain']))}</pre></div>`;
        }
      }
    }
    return html;
  }

  /* ---------- front-matter extraction (strip dup title, lift objectives) ---------- */
  function extractObjectives(md) {
    const lines = md.split('\n');
    const HDR = /^\s*\*\*Learning [Oo]bjectives[.:]?\*\*/;
    const start = lines.findIndex(line => HDR.test(line));
    if (start < 0) return { md, objectives: null };
    const lead = lines[start].replace(HDR, '').replace(/^\s*/, '').trim();

    let end = start + 1;
    let sawBullet = false;
    while (end < lines.length) {
      const line = lines[end];
      const trimmed = line.trim();
      const nextNonBlank = lines.slice(end + 1).find(x => x.trim() !== '');

      if (sawBullet && trimmed === '' && nextNonBlank && !/^[ \t]*[-*][ \t]/.test(nextNonBlank)) break;
      if (!sawBullet && /^#{1,6}\s+/.test(trimmed)) break;
      if (/^[ \t]*[-*][ \t]/.test(line)) sawBullet = true;
      end += 1;
    }

    const bullets = lines.slice(start + 1, end).join('\n').trim();
    const objectives = [lead, bullets].filter(Boolean).join('\n\n');
    const nextLines = lines.slice(end);
    if (nextLines[0] === '') nextLines.shift();
    return {
      md: lines.slice(0, start).concat(nextLines).join('\n'),
      objectives: objectives || null
    };
  }

  function extractIntro(md) {
    md = md.replace(/^\uFEFF?\s*#\s+[^\n]*\n+/, '');      // leading H1 title (the page header supplies it)
    md = md.replace(/^\s*\*[^\n]*\*\s*\n+/, '');           // series / edition italic meta line
    md = md.replace(/^\s*\*[^\n]*\*\s*\n+/, '');           // author italic meta line
    const ex = extractObjectives(md);
    md = ex.md;
    md = md.replace(/^\s*---\s*\n/, '');
    return { md: md.replace(/^\s+/, ''), objectives: ex.objectives };
  }

  /* ---------- assemble a chapter body ---------- */
  // returns HTML string for the prose/cells (header is built by the page)
  function renderChapter(meta, raw) {
    let body = '';
    let objectives = null;

    if (meta.type === 'md') {
      const ex = extractIntro(raw);
      objectives = ex.objectives;
      body = `<div class="prose">${renderMarkdown(ex.md)}</div>`;
    } else {
      const nb = (typeof raw === 'string') ? JSON.parse(raw) : raw;
      const cells = nb.cells || [];
      let first = true;
      let buf = '';      // buffer consecutive markdown into one .prose block
      const flush = () => { if (buf) { body += `<div class="prose">${renderMarkdown(buf)}</div>`; buf = ''; } };

      for (const cell of cells) {
        if (cell.cell_type === 'markdown_html') {
          // Pre-rendered markdown HTML (math kept raw; typeset by KaTeX auto-render).
          flush();
          body += `<div class="prose">${joinSrc(cell.html)}</div>`;
          first = false;
        } else if (cell.cell_type === 'markdown' || cell.cell_type === 'raw') {
          let src = joinSrc(cell.source);
          if (first) {
            const ex = extractIntro(src);
            objectives = ex.objectives;
            src = ex.md;
            first = false;
          }
          buf += '\n\n' + src + '\n\n';
        } else if (cell.cell_type === 'code') {
          flush();
          const code = joinSrc(cell.source);
          let cellHtml = '';
          if (code.trim() !== '') cellHtml += codeCard(code, 'python', cell.execution_count);
          const outs = renderOutputs(cell.outputs);
          if (outs) cellHtml += `<div class="nb-out">${outs}</div>`;
          // wrap code+output as one unit when there's a card
          body += cellHtml;
          first = false;
        }
      }
      flush();
    }

    let objHtml = '';
    if (objectives) {
      objHtml = `<div class="callout"><p class="callout-title">Learning Objectives</p>${renderMarkdown(objectives)}</div>`;
    }
    return { objHtml, body };
  }

  /* ---------- post-processing on mounted DOM ---------- */
  function enhance(root) {
    // copy buttons
    root.querySelectorAll('.copy-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const code = btn.getAttribute('data-code') || '';
        navigator.clipboard.writeText(code).then(() => {
          btn.classList.add('copied');
          btn.querySelector('.ci').innerHTML = CHECK_SVG;
          btn.querySelector('.ct').textContent = 'Copied';
          setTimeout(() => {
            btn.classList.remove('copied');
            btn.querySelector('.ci').innerHTML = COPY_SVG;
            btn.querySelector('.ct').textContent = 'Copy';
          }, 1600);
        });
      });
    });

    // wrap captioned prose images in <figure>
    root.querySelectorAll('.prose p > img').forEach(img => {
      const alt = img.getAttribute('alt') || '';
      const p = img.parentElement;
      if (p && p.children.length === 1 && p.textContent.trim() === '') {
        const fig = document.createElement('figure');
        p.replaceWith(fig);
        fig.appendChild(img);
        if (alt.trim()) {
          const cap = document.createElement('figcaption');
          cap.textContent = alt.trim();
          fig.appendChild(cap);
        }
      }
    });
    // broken external images: show a small placeholder note
    root.querySelectorAll('.prose img').forEach(img => {
      img.addEventListener('error', () => {
        const note = document.createElement('div');
        note.className = 'fig-cap';
        note.style.cssText = 'padding:1.4rem;border:1px dashed var(--rule);border-radius:8px;background:var(--paper-2)';
        note.textContent = 'figure — ' + (img.getAttribute('alt') || 'external image unavailable offline');
        img.replaceWith(note);
      });
    });

    // re-execute scripts inside HTML outputs (matplotlib animations, widgets)
    root.querySelectorAll('.out-html script').forEach(old => {
      const s = document.createElement('script');
      for (const a of old.attributes) s.setAttribute(a.name, a.value);
      s.textContent = old.textContent;
      old.replaceWith(s);
    });

    // assign heading ids for the on-this-page rail
    const heads = [];
    root.querySelectorAll('.prose h2, .prose h3').forEach(h => {
      if (!h.id) {
        let id = slugify(h.textContent);
        let base = id, k = 2;
        while (id && document.getElementById(id)) id = base + '-' + (k++);
        h.id = id || ('s-' + heads.length);
      }
      heads.push({ id: h.id, text: h.textContent, level: h.tagName.toLowerCase() });
    });
    return heads;
  }

  window.BookRender = { renderChapter, enhance, renderMarkdown, slugify };
})();
