/**
 * PostCSS pipeline.
 * ----------------------------------------------------------------------------
 * Tailwind compiles our utility classes; Autoprefixer adds vendor prefixes
 * (e.g. `-webkit-backdrop-filter` for the glassmorphism blur on Safari, which
 * is essential for our frosted-glass node cards to render on Apple devices).
 */
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};

export default config;
