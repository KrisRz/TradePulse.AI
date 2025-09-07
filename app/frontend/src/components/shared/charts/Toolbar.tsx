import { useState } from 'preact/hooks';

export default function Toolbar({ onChange }: { onChange: (i: string) => void }) {
  const [active, setActive] = useState('1m');
  const items = ['1m', '5m', '15m', '1h', '4h', '1d'];
  
  return (
    <div style="display:flex; gap:8px; margin:8px 0;">
      {items.map(i => (
        <button
          key={i}
          onClick={() => { setActive(i); onChange(i); }}
          style={`padding:6px 10px;border-radius:10px;border:1px solid #263041;
                  background:${active === i ? '#1f2937' : '#0b1220'}; color:#e5e7eb;
                  cursor:pointer; transition: all 0.2s ease;`}
        >
          {i}
        </button>
      ))}
    </div>
  );
}
