import Alpine from 'alpinejs';
import focus from '@alpinejs/focus';
import { treeEditor } from './tree-editor.js';
import { go, back, goTo, reset, pfHide, pfShow, pfIsHidden, matchesTool } from './jvm-tools-core.js';
import hljs from 'highlight.js/lib/core';
import java from 'highlight.js/lib/languages/java';
import xml from 'highlight.js/lib/languages/xml';
import groovy from 'highlight.js/lib/languages/groovy';
import { highlightShell } from './shell-highlight.js';

hljs.registerLanguage('java', java);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('groovy', groovy);

Alpine.plugin(focus);
window.Alpine = Alpine;
window.treeEditor = treeEditor;
// Expose jvm-tools-core for use in Alpine x-data expressions on the jvm-tools page
window.jvmCore = { go, back, goTo, reset, pfHide, pfShow, pfIsHidden, matchesTool };
Alpine.start();

document.addEventListener('DOMContentLoaded', () => {
  hljs.highlightAll();

  // Shell highlighting via ohm.js tokenizer (replaces hljs bash)
  const SHELL_LANGS = new Set(['bash', 'shell', 'sh']);
  const TOKEN_STYLE = {
    command:     'color:#DCDCAA',
    flag:        'color:#C586C0',
    variable:    'color:#C586C0',
    placeholder: 'color:#569CD6',
    string:      'color:#CE9178',
    url:         'color:#8396A8',
    comment:     'color:#6A9955;font-style:italic',
    number:      'color:#B5CEA8',
    operator:    'color:#FFFFFF',
    path:        'color:#CE9178',
    plain:       'color:#D4D4D4',
  };
  document.querySelectorAll('pre code[class]').forEach(el => {
    const lang = [...el.classList].map(c => c.replace('language-', '')).find(l => SHELL_LANGS.has(l));
    if (!lang) return;
    const lines = highlightShell(el.textContent.trimEnd());
    if (!lines) return;
    const html = lines.map(line =>
      '<span>' + line.map(tok => {
        const style = TOKEN_STYLE[tok.types[0]] || TOKEN_STYLE.plain;
        const content = tok.content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return `<span style="${style}">${content}</span>`;
      }).join('') + '</span>'
    ).join('\n');
    el.innerHTML = html;
    el.classList.remove(...el.classList);
    el.classList.add('hljs');
  });

  // Copy-to-clipboard for code blocks
  document.querySelectorAll('.code-block-wrap').forEach(wrap => {
    const pre = wrap.querySelector('pre');
    const btn = wrap.querySelector('.copy-btn');
    if (!pre || !btn) return;
    btn.addEventListener('click', () => {
      const text = pre.innerText;
      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = 'Copied!';
        btn.classList.add('text-green-600');
        setTimeout(() => {
          btn.textContent = 'Copy';
          btn.classList.remove('text-green-600');
        }, 1500);
      });
    });
  });

  // Measure sticky nav stack and set scroll-padding-top dynamically
  const topNav  = document.querySelector('header');
  const toolNav = document.getElementById('tool-nav');
  const updateScrollPadding = () => {
    const h = (topNav?.offsetHeight ?? 0) + (toolNav?.offsetHeight ?? 0);
    document.documentElement.style.scrollPaddingTop = h + 'px';
    document.querySelectorAll('section[id]').forEach(s => {
      s.style.scrollMarginTop = h + 'px';
    });
  };
  updateScrollPadding();
  window.addEventListener('resize', updateScrollPadding);

  if (!toolNav) return;

  const links = Array.from(toolNav.querySelectorAll('a[data-id]'));
  if (!links.length) return;

  // Map every section ID to the nav link that represents its group
  const groupMap = JSON.parse(toolNav.dataset.groupMap || '{}');

  const setActive = (id) => {
    // id is any section id; resolve to the group's first-tool id
    const navId = groupMap[id] || id;
    links.forEach(a => {
      const active = a.dataset.id === navId;
      a.classList.toggle('text-blue-700',   active);
      a.classList.toggle('font-semibold',   active);
      a.classList.toggle('border-b-2',      active);
      a.classList.toggle('border-blue-600', active);
      a.classList.toggle('bg-blue-50',      active);
      a.classList.toggle('rounded',         active);
      a.classList.toggle('text-gray-500',  !active);
    });
  };

  const scrollNavToActive = (id) => {
    const navId = groupMap[id] || id;
    const a = toolNav.querySelector(`a[data-id="${navId}"]`);
    if (!a) return;
    const navRect  = toolNav.getBoundingClientRect();
    const linkRect = a.getBoundingClientRect();
    const leftEdge  = linkRect.left  - navRect.left  + toolNav.scrollLeft;
    const rightEdge = linkRect.right - navRect.left  + toolNav.scrollLeft;
    if (rightEdge > toolNav.scrollLeft + navRect.width) {
      toolNav.scrollLeft = rightEdge - navRect.width + 16;
    } else if (leftEdge < toolNav.scrollLeft) {
      toolNav.scrollLeft = leftEdge - 16;
    }
  };

  // Observe all detail sections (not just nav links — groups cover multiple tools)
  const sections = Array.from(document.querySelectorAll('section[id]'))
    .filter(s => groupMap[s.id] !== undefined || links.some(a => a.dataset.id === s.id));
  const visible = new Set();

  const pick = () => {
    if (!visible.size) { setActive(null); return; }
    let best = null;
    for (const s of visible) {
      if (!best || s.offsetTop < best.offsetTop) best = s;
    }
    setActive(best.id);
  };

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) visible.add(entry.target);
      else visible.delete(entry.target);
    }
    const prev = toolNav.querySelector('a.text-blue-700')?.dataset.id;
    pick();
    const curr = toolNav.querySelector('a.text-blue-700')?.dataset.id;
    if (curr && curr !== prev) scrollNavToActive(curr);
  }, { rootMargin: '0px 0px -60% 0px', threshold: 0 });

  sections.forEach(s => observer.observe(s));
});
