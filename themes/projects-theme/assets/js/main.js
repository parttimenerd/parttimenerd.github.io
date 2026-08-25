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

  const nav = document.getElementById('tool-nav');
  if (!nav) return;

  const links = Array.from(nav.querySelectorAll('a[data-id]'));
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

  const sections = links.map(a => document.getElementById(a.dataset.id)).filter(Boolean);
  const visible = new Set();

  const pick = () => {
    if (!visible.size) { setActive(null); return; }
    // Highlight the topmost visible section
    let best = null;
    for (const s of visible) {
      if (!best || s.offsetTop < best.offsetTop) best = s;
    }
    setActive(best.id);
  };

  // Scroll into nav view when active changes (for long nav bars)
  const scrollNavToActive = (id) => {
    const a = nav.querySelector(`a[data-id="${id}"]`);
    if (a) a.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
  };

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) visible.add(entry.target);
      else visible.delete(entry.target);
    }
    const prev = nav.querySelector('a.text-blue-700')?.dataset.id;
    pick();
    const curr = nav.querySelector('a.text-blue-700')?.dataset.id;
    if (curr && curr !== prev) scrollNavToActive(curr);
  }, { rootMargin: '0px 0px -60% 0px', threshold: 0 });

  sections.forEach(s => observer.observe(s));
});
