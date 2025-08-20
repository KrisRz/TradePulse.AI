// app/frontend/src/components/shared/charts/BtcCandleLive.tsx
// TODO: Fix lightweight-charts Time export issue tomorrow
import type { FunctionalComponent } from 'preact';

const BtcCandleLive: FunctionalComponent = () => {
  return (
    <div style={{ 
      width: '100%', 
      height: '420px', 
      background: '#0f0f0f', 
      borderRadius: '8px', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center', 
      color: '#c8c8c8' 
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '18px', marginBottom: '10px' }}>📈 Bitcoin Chart</div>
        <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '10px' }}>
          Temporarily disabled - lightweight-charts export issue
        </div>
        <div style={{ fontSize: '10px', color: '#6b7280' }}>
          Will implement proper chart tomorrow
        </div>
      </div>
    </div>
  );
};

export default BtcCandleLive;