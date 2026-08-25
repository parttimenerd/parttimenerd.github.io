import Alpine from 'alpinejs';
import focus from '@alpinejs/focus';
import hljs from 'highlight.js/lib/core';
import java from 'highlight.js/lib/languages/java';
import xml from 'highlight.js/lib/languages/xml';
import groovy from 'highlight.js/lib/languages/groovy';
import bash from 'highlight.js/lib/languages/bash';

hljs.registerLanguage('java', java);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('groovy', groovy);
hljs.registerLanguage('bash', bash);

Alpine.plugin(focus);
window.Alpine = Alpine;
Alpine.start();

document.addEventListener('DOMContentLoaded', () => {
  hljs.highlightAll();

  // Measure sticky nav stack and set scroll-padding-top dynamically so hash
  // links always land below both the top nav and the tool nav.
  const topNav  = document.querySelector('header');
  const toolNav = document.getElementById('tool-nav');
  const updateScrollPadding = () => {
    const h = (topNav?.offsetHeight ?? 0) + (toolNav?.offsetHeight ?? 0);
    document.documentElement.style.scrollPaddingTop = h + 'px';
    // Keep scroll-margin-top in sync on all anchored sections
    document.querySelectorAll('section[id]').forEach(s => {
      s.style.scrollMarginTop = h + 'px';
    });
  };
  updateScrollPadding();
  window.addEventListener('resize', updateScrollPadding);

  if (!toolNav) return;

  const links = Array.from(toolNav.querySelectorAll('a[data-id]'));
  if (!links.length) return;

  const setActive = (id) => {
    links.forEach(a => {
      const active = a.dataset.id === id;
      a.classList.toggle('text-blue-700',   active);
      a.classList.toggle('font-semibold',   active);
      a.classList.toggle('border-b-2',      active);
      a.classList.toggle('border-blue-600', active);
      a.classList.toggle('text-gray-500',  !active);
    });
  };

  // Scroll the tool nav bar horizontally to keep the active link visible.
  // Use scrollLeft directly — scrollIntoView on nav items can scroll the page.
  const scrollNavToActive = (id) => {
    const a = toolNav.querySelector(`a[data-id="${id}"]`);
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

  const sections = links.map(a => document.getElementById(a.dataset.id)).filter(Boolean);
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
