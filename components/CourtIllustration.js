export default function CourtIllustration() {
  return (
    <div className="court-illustration" aria-hidden="true">
      <svg viewBox="0 0 400 265" fill="none">
        <defs>
          <linearGradient id="court-surface" x1="60" y1="40" x2="340" y2="220" gradientUnits="userSpaceOnUse"><stop stopColor="#28775d" /><stop offset="1" stopColor="#104b39" /></linearGradient>
          <pattern id="racket-strings" width="7" height="7" patternUnits="userSpaceOnUse"><path d="M7 0H0V7" stroke="#567b69" strokeWidth=".8" /></pattern>
          <filter id="court-shadow" x="-30%" y="-30%" width="170%" height="190%"><feDropShadow dx="0" dy="12" stdDeviation="10" floodColor="#123b2e" floodOpacity=".16" /></filter>
        </defs>
        <circle cx="219" cy="125" r="116" fill="#e3ede6" />
        <circle cx="355" cy="54" r="6" fill="#bed4c3" /><circle cx="58" cy="201" r="4" fill="#bed4c3" />
        <g transform="translate(36 49) rotate(-9 156 82)" filter="url(#court-shadow)">
          <rect width="314" height="179" rx="17" fill="#103e30" />
          <rect width="314" height="170" rx="17" fill="url(#court-surface)" />
          <g stroke="#d6e8dc" strokeWidth="1.4"><path d="M22 22H292V148H22Z" /><path d="M22 40H292M22 130H292M89 22V148M225 22V148M22 85H89M225 85H292" /></g>
          <path d="M157 17V153" stroke="#fff" strokeWidth="3" strokeDasharray="3 3" />
          <circle cx="157" cy="17" r="3" fill="#fff" /><circle cx="157" cy="153" r="3" fill="#fff" />
        </g>
        <g transform="translate(30 211)"><rect width="173" height="33" rx="16.5" fill="white" stroke="#d6e3da" /><circle cx="48" cy="16.5" r="3" fill="#17604a" /><text x="60" y="21" fill="#17604a" fontFamily="Arial, sans-serif" fontSize="11" fontWeight="600" letterSpacing="1.4">IIT GUWAHATI</text></g>
      </svg>
    </div>
  );
}
