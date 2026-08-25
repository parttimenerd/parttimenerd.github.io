module.exports = {
  content: [
    "./themes/projects-theme/layouts/**/*.html",
    "./content/**/*.md",
    "./data/**/*.yaml",
  ],
  safelist: [
    "font-bold", "underline",
    "flex", "hidden",
  ],
  theme: { extend: {} },
  plugins: [],
}
