export default (ctx) => ({
  map: ctx.options.map,
  plugins: {
    // Ensure CSS nesting via Tailwind's official nesting plugin to avoid
    // third-party nesting plugins that may parse without a `from` option.
    'tailwindcss/nesting': {},
    'tailwindcss': {},
    'autoprefixer': {},
  },
})
