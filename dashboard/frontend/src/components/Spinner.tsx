const BARS = Array.from({ length: 8 });

export function Spinner({ size = 44 }: { size?: number }) {
  return (
    <div className="spinner" style={{ width: size, height: size }} role="status" aria-label="불러오는 중">
      {BARS.map((_, i) => (
        <span
          key={i}
          style={{
            transform: `rotate(${i * 45}deg)`,
            transformOrigin: `50% ${size / 2}px`,
            animationDelay: `${-(BARS.length - 1 - i) * 0.125}s`,
          }}
        />
      ))}
    </div>
  );
}
