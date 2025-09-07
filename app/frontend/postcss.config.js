export default (ctx) => ({
  map: ctx.options.map,
  plugins: {
    'tailwindcss': {},
    'autoprefixer': {},
  },
})
