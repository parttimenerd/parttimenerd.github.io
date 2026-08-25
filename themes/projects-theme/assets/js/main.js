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

  // Highlight active anchor in the tool nav bar
  const nav = document.getElementById('tool-nav');
  if (!nav) return;

  const links = Array.from(nav.querySelectorAll('a[data-id]'));
  if (!links.length) return;

  const setActive = (id) => {
    links.forEach(a => {
      const active = a.dataset.id === id;
      a.classList.toggle('text-blue-700', active);
      a.classList.toggle('font-semibold', active);
      a.classList.toggle('border-b-2', active);
      a.classList.toggle('border-blue-600', active);
      a.classList.toggle('text-gray-500', !active);
    });
  };

  // Start with the first one active
  if (links[0]) setActive(links[0].dataset.id);

  const sections = links.map(a => document.getElementById(a.dataset.id)).filter(Boolean);

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) setActive(entry.target.id);
    });
  }, { rootMargin: '-20% 0px -70% 0px', threshold: 0 });

  sections.forEach(s => observer.observe(s));
});
