/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: { colors: { backdrop:'#090B10', side:'#10131B', panel:'#161B25', edge:'#252B38', violet:'#8B5CF6', blue:'#38BDF8', muted:'#94A3B8' }, fontFamily:{ sans:['Inter','Noto Sans Khmer','system-ui','sans-serif']}, boxShadow:{ glow:'0 0 50px rgba(139,92,246,.12)' } } },
  plugins: []
}
