module.exports = {
  content: [
    "./themes/projects-theme/layouts/**/*.html",
    "./content/**/*.md",
    "./data/**/*.yaml",
  ],
  safelist: [
    "font-bold", "underline",
    "flex", "hidden",
    { pattern: /^(md|lg):w-(1\/2|1\/3)$/ },
    "col-span-full",
  ],
  theme: { extend: {} },
  plugins: [],
}
