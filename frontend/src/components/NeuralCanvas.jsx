const branches = Array.from({ length: 24 }, (_, index) => {
  const angle = index * Math.PI * 2 / 24;
  const radius = index % 2 ? 210 : 270;
  const x = 400 + Math.cos(angle) * radius;
  const y = 240 + Math.sin(angle) * radius * 0.65;
  const mx = 400 + Math.cos(angle + 0.14) * radius * 0.55;
  const my = 240 + Math.sin(angle + 0.14) * radius * 0.37;
  return { x, y, d: `M400 240 Q${mx} ${my} ${x} ${y}`, delay: `${index * -0.21}s` };
});
export default function NeuralCanvas({ active }) {
  return <div className={`cth-neural ${active ? "is-running" : ""}`}>
    <svg viewBox="0 0 800 480" role="img" aria-label={active ? "Pratinjau animasi saraf; bukan proses training" : "Visual saraf dalam keadaan diam"}>
      <defs><radialGradient id="cth-neural-glow"><stop stopColor="#087dc0" stopOpacity=".3" /><stop offset="1" stopColor="#031025" stopOpacity="0" /></radialGradient></defs>
      <rect width="800" height="480" fill="#020b18" />
      <ellipse cx="400" cy="240" rx="300" ry="230" fill="url(#cth-neural-glow)" />
      {branches.map((branch, index) => <g key={index}>
        <path d={branch.d} className="cth-nerve" />
        <path d={branch.d} className="cth-impulse" style={{ animationDelay: branch.delay }} />
        <rect x={branch.x - 3} y={branch.y - 3} width="6" height="6" rx="1" fill="#153f70" stroke="#277caf" />
      </g>)}
      <g className="cth-brain" transform="translate(356 196)" fill="#073254" stroke="#53d3ff" strokeWidth="2">
        <path d="M44 12C34 1 19 8 18 20 5 21 1 37 10 45 2 57 13 70 25 68 27 81 40 82 44 73V12ZM44 12C54 1 69 8 70 20 83 21 87 37 78 45 86 57 75 70 63 68 61 81 48 82 44 73V12Z" />
        <path d="M18 20q16-1 15 14M10 45q15-8 21 2M25 68q-4-17 9-17M70 20q-16-1-15 14M78 45q-15-8-21 2M63 68q4-17-9-17M44 34l-10 8m10 17 10-9" fill="none" />
      </g>
    </svg>
    <div className="cth-neural-caption"><span className={`cth-small-dot ${active ? "running" : ""}`} />{active ? "PRATINJAU VISUAL AKTIF" : "WORKSPACE SIAP · BELUM ADA TRAINING"}</div>
  </div>;
}
