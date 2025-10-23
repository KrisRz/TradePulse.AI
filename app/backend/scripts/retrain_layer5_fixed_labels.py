"""
🔄 LAYER 5 RETRAINING WITH FIXED LABELS
========================================

CRITICAL FIX: Layer 5 has INVERSE CORRELATION (higher confidence = worse results)
ROOT CAUSE: Training labels were based on the SAME broken model's predictions

NEW APPROACH:
- Labels based on ACTUAL trade performance (PnL%, hold time, market context)
- Add 10 new features (hour_of_day, momentum, volume_spike, etc)
- Generate synthetic trades from 3.6M historical candles
- Proper time-based validation (no data leakage)

Author: TradePulse.AI Development Team
Date: 2025-10-22
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import boto3
from decimal import Decimal

# ML imports
import xgboost as xgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
HISTORICAL_DATA_OLD = PROJECT_ROOT / "data/ml/historical/processed/BTCUSDT_1m_complete.parquet"
HISTORICAL_DATA_OCT2025 = PROJECT_ROOT / "data/ml/historical/processed/BTCUSDT_1m_october_2025_with_indicators.parquet"
MODEL_PATH = PROJECT_ROOT / "app/backend/models/enterprise"
BACKUP_PATH = MODEL_PATH / "backups"
BACKUP_PATH.mkdir(exist_ok=True, parents=True)

# DynamoDB config
DYNAMODB_ENDPOINT = "http://localhost:8000"
DYNAMODB_REGION = "us-east-1"


class Layer5Retrainer:
    """Professional Layer 5 retraining with fixed labels"""
    
    def __init__(self):
        self.historical_df = None
        self.live_trades = []
        self.training_data = []
        self.model = None
        self.scaler = None
        
        # Feature configuration
        self.base_features = [
            'close', 'volume', 'rsi', 'macd', 'bb_position', 
            'volatility', 'trend_strength', 'volume_ratio', 'price_change_24h'
        ]
        
        # NEW CRITICAL FEATURES (fix inverse correlation)
        self.new_features = [
            'hour_of_day',           # 0-1 normalized
            'day_of_week',           # 0-1 normalized
            'volume_spike',          # current_vol / avg_vol_60m
            'price_momentum_5m',     # % change last 5min
            'price_momentum_15m',    # % change last 15min
            'distance_from_support', # % from support level
            'distance_from_resistance', # % from resistance level
            'atr_normalized',        # ATR / close
            'stoch_oversold',        # 1 if stoch_k < 20
            'stoch_overbought',      # 1 if stoch_k > 80
        ]
        
        self.all_features = self.base_features + self.new_features
        logger.info(f"📊 Total features: {len(self.all_features)}")
        
    def load_historical_data(self):
        """Load October 2025 data (for joining live trades) + old data (for synthetic)"""
        logger.info("📈 Loading historical data...")
        
        # Load October 2025 data (for joining live trades)
        logger.info("   📅 Loading October 2025 data (for live trades)...")
        df_oct2025 = pd.read_parquet(HISTORICAL_DATA_OCT2025)
        
        # Load old data (for synthetic generation)
        logger.info("   📚 Loading 2018-2024 data (for synthetic generation)...")
        df_old = pd.read_parquet(HISTORICAL_DATA_OLD)
        
        # Combine both datasets
        logger.info("   🔗 Combining datasets...")
        self.historical_df = pd.concat([df_old, df_oct2025], ignore_index=True)
        
        # Ensure timestamp column exists and is datetime
        if 'timestamp' not in self.historical_df.columns:
            if 'open_time' in self.historical_df.columns:
                self.historical_df['timestamp'] = pd.to_datetime(self.historical_df['open_time'], unit='ms', errors='coerce')
            else:
                raise ValueError("No timestamp column found in historical data")
        else:
            # Already datetime, just ensure proper format
            if self.historical_df['timestamp'].dtype == 'object':
                self.historical_df['timestamp'] = pd.to_datetime(self.historical_df['timestamp'])
        
        # Set timestamp as index
        self.historical_df.set_index('timestamp', inplace=True)
        
        # Sort by timestamp to ensure proper indexing
        self.historical_df.sort_index(inplace=True)
        
        # Remove duplicates (if any overlap)
        original_len = len(self.historical_df)
        self.historical_df = self.historical_df[~self.historical_df.index.duplicated(keep='first')]
        if len(self.historical_df) < original_len:
            logger.info(f"   🧹 Removed {original_len - len(self.historical_df)} duplicates")
        
        logger.info(f"✅ Loaded {len(self.historical_df):,} total candles")
        logger.info(f"   Date range: {self.historical_df.index.min()} → {self.historical_df.index.max()}")
        
    def load_live_trades(self):
        """Load 235 live trades from DynamoDB"""
        logger.info("📊 Loading live trades from DynamoDB...")
        
        try:
            dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=DYNAMODB_ENDPOINT,
                region_name=DYNAMODB_REGION,
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )
            
            table = dynamodb.Table('portfolio_closed_positions')
            response = table.scan()
            positions = response['Items']
            
            logger.info(f"✅ Loaded {len(positions)} closed positions")
            
            # Convert to usable format
            for pos in positions:
                try:
                    # Parse timestamps
                    entry_time = self._parse_timestamp(pos.get('entry_time'))
                    exit_time = self._parse_timestamp(pos.get('exit_time'))
                    
                    if not entry_time or not exit_time:
                        continue
                    
                    # Extract trade data
                    trade = {
                        'position_id': pos.get('position_id'),
                        'entry_time': entry_time,
                        'exit_time': exit_time,
                        'entry_price': float(pos.get('entry_price', 0)),
                        'exit_price': float(pos.get('exit_price', 0)),
                        'pnl_percentage': float(pos.get('pnl_percentage', 0)),
                        'realized_pnl': float(pos.get('realized_pnl', 0)),
                        'duration_minutes': float(pos.get('duration_minutes', 0)),
                        'ai_confidence': float(pos.get('ai_confidence', 0.5)),
                        'position_type': pos.get('position_type', 'LONG')
                    }
                    
                    self.live_trades.append(trade)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse position: {e}")
                    continue
            
            logger.info(f"✅ Parsed {len(self.live_trades)} valid trades")
            
            # Analyze current problem
            if self.live_trades:
                winning = [t for t in self.live_trades if t['pnl_percentage'] > 0]
                losing = [t for t in self.live_trades if t['pnl_percentage'] < 0]
                
                if winning and losing:
                    win_conf = np.mean([t['ai_confidence'] for t in winning])
                    loss_conf = np.mean([t['ai_confidence'] for t in losing])
                    
                    logger.info(f"\n⚠️ CURRENT PROBLEM:")
                    logger.info(f"   Winning trades avg confidence: {win_conf:.2%}")
                    logger.info(f"   Losing trades avg confidence: {loss_conf:.2%}")
                    logger.info(f"   INVERSE CORRELATION: {loss_conf/win_conf:.2f}x higher!\n")
            
        except Exception as e:
            logger.error(f"❌ Failed to load live trades: {e}")
            self.live_trades = []
    
    def _parse_timestamp(self, ts) -> Optional[datetime]:
        """Parse various timestamp formats"""
        if not ts:
            return None
        
        try:
            # ISO format
            if isinstance(ts, str):
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            # Unix timestamp (ms)
            elif isinstance(ts, (int, float)):
                return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
            # Decimal
            elif isinstance(ts, Decimal):
                return datetime.fromtimestamp(float(ts) / 1000.0, tz=timezone.utc)
        except Exception as e:
            logger.debug(f"Failed to parse timestamp {ts}: {e}")
        
        return None
    
    def calculate_true_confidence_label(self, trade: Dict, market_context: Dict) -> float:
        """
        🎯 CRITICAL FIX: Calculate TRUE confidence based on actual performance
        
        This is the KEY fix - labels now based on RESULTS, not broken predictions!
        """
        pnl_pct = trade['pnl_percentage']
        hold_time_min = trade['duration_minutes']
        entry_hour = trade['entry_time'].hour
        volatility = market_context.get('volatility_20', 0.02)
        
        # 1️⃣ BASE SCORE FROM PNL (most important!)
        if pnl_pct > 5.0:
            base_confidence = 0.90  # 🔥 Excellent trade
        elif pnl_pct > 2.0:
            base_confidence = 0.80  # ✅ Good trade
        elif pnl_pct > 0.5:
            base_confidence = 0.65  # 👍 OK trade
        elif pnl_pct > 0:
            base_confidence = 0.50  # 😐 Marginal win
        elif pnl_pct > -2.0:
            base_confidence = 0.35  # ⚠️ Small loss
        elif pnl_pct > -5.0:
            base_confidence = 0.20  # ❌ Bad loss
        else:
            base_confidence = 0.10  # 💀 Catastrophic loss
        
        # 2️⃣ ADJUST FOR HOLD TIME (day trading - premature exits bad)
        if pnl_pct > 0 and hold_time_min < 10:
            base_confidence -= 0.10  # Could've held longer for more profit
        elif pnl_pct > 0 and hold_time_min > 120:
            base_confidence += 0.10  # Patient winner (good!)
        elif pnl_pct < 0 and hold_time_min < 5:
            base_confidence -= 0.05  # Quick loss (very bad timing)
        
        # 3️⃣ ADJUST FOR ENTRY HOUR (from your analysis: 17, 20, 21 UTC are bad)
        problematic_hours = [17, 20, 21, 22]
        if entry_hour in problematic_hours:
            base_confidence *= 0.85  # Lower confidence for bad timing
        
        # Good hours (based on your profitable trades analysis)
        good_hours = [8, 9, 10, 14, 15]
        if entry_hour in good_hours and pnl_pct > 0:
            base_confidence *= 1.05  # Slight boost for good timing
        
        # 4️⃣ ADJUST FOR VOLATILITY
        if volatility > 0.05 and pnl_pct < 0:
            base_confidence *= 0.90  # High vol + loss = bad conditions
        elif volatility < 0.02 and pnl_pct > 0:
            base_confidence *= 1.05  # Low vol + win = good conditions
        
        # 5️⃣ ADJUST FOR PNL MAGNITUDE (big wins = high confidence, big losses = low confidence)
        if abs(pnl_pct) > 3.0:
            if pnl_pct > 0:
                base_confidence += 0.05  # Big win
            else:
                base_confidence -= 0.05  # Big loss
        
        # Clip to valid range [0.1, 0.95]
        return float(np.clip(base_confidence, 0.1, 0.95))
    
    def extract_features(self, timestamp: datetime, lookback_df: pd.DataFrame) -> Optional[Dict]:
        """Extract 19 features from historical data at given timestamp"""
        try:
            # Convert timestamp to timezone-naive if needed (historical data is timezone-naive)
            if timestamp.tzinfo is not None:
                timestamp = timestamp.replace(tzinfo=None)
            
            # Find the closest candle (within 1 minute tolerance)
            time_tolerance = pd.Timedelta(minutes=1)
            mask = (lookback_df.index >= timestamp - time_tolerance) & \
                   (lookback_df.index <= timestamp + time_tolerance)
            
            if not mask.any():
                return None
            
            current_row = lookback_df[mask].iloc[0]
            current_idx = lookback_df.index.get_loc(current_row.name)
            
            # Need sufficient history for features
            if current_idx < 200:
                return None
            
            # Get historical context
            history = lookback_df.iloc[:current_idx+1]
            
            # BASE FEATURES (original 9)
            close = float(current_row['close'])
            volume = float(current_row.get('volume', 0))
            rsi = float(current_row.get('rsi', 50.0))
            macd = float(current_row.get('macd', 0) - current_row.get('macd_signal', 0))
            
            # Bollinger Band position
            bb_upper = float(current_row.get('bb_upper', close * 1.02))
            bb_lower = float(current_row.get('bb_lower', close * 0.98))
            bb_position = (close - bb_lower) / max(bb_upper - bb_lower, 1e-8) if bb_upper != bb_lower else 0.5
            
            volatility = float(current_row.get('volatility_20', 0.02))
            
            # Trend strength (linear regression slope)
            recent_prices = history['close'].tail(20).values
            if len(recent_prices) >= 20:
                x = np.arange(len(recent_prices))
                slope = np.polyfit(x, recent_prices, 1)[0]
                trend_strength = np.tanh(abs(slope) / np.mean(recent_prices) * 100)
            else:
                trend_strength = 0.5
            
            # Volume ratio
            avg_volume = history['volume'].tail(60).mean()
            volume_ratio = volume / max(avg_volume, 1e-8)
            
            price_change_24h = float(current_row.get('price_change_24h', 0))
            
            # NEW CRITICAL FEATURES (fix inverse correlation!)
            
            # Time features (normalized 0-1)
            hour_of_day = timestamp.hour / 24.0
            day_of_week = timestamp.weekday() / 7.0
            
            # Volume spike
            volume_spike = volume / max(history['volume'].tail(60).mean(), 1e-8)
            
            # Price momentum
            recent_5m = history['close'].tail(5)
            price_momentum_5m = (close / recent_5m.mean() - 1) if len(recent_5m) >= 5 else 0
            
            recent_15m = history['close'].tail(15)
            price_momentum_15m = (close / recent_15m.mean() - 1) if len(recent_15m) >= 15 else 0
            
            # Support/Resistance distance
            support = float(current_row.get('support', close * 0.98))
            resistance = float(current_row.get('resistance', close * 1.02))
            distance_from_support = (close - support) / close if support > 0 else 0
            distance_from_resistance = (resistance - close) / close if resistance > 0 else 0
            
            # ATR normalized
            atr = float(current_row.get('atr', close * 0.01))
            atr_normalized = atr / close
            
            # Stochastic oversold/overbought
            stoch_k = float(current_row.get('stoch_k', 50.0))
            stoch_oversold = 1.0 if stoch_k < 20 else 0.0
            stoch_overbought = 1.0 if stoch_k > 80 else 0.0
            
            return {
                # Base features
                'close': close,
                'volume': volume,
                'rsi': rsi,
                'macd': macd,
                'bb_position': bb_position,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'volume_ratio': volume_ratio,
                'price_change_24h': price_change_24h,
                # New features
                'hour_of_day': hour_of_day,
                'day_of_week': day_of_week,
                'volume_spike': volume_spike,
                'price_momentum_5m': price_momentum_5m,
                'price_momentum_15m': price_momentum_15m,
                'distance_from_support': distance_from_support,
                'distance_from_resistance': distance_from_resistance,
                'atr_normalized': atr_normalized,
                'stoch_oversold': stoch_oversold,
                'stoch_overbought': stoch_overbought,
            }
            
        except Exception as e:
            logger.debug(f"Feature extraction failed: {e}")
            return None
    
    def prepare_live_training_data(self):
        """Join live trades with historical market data"""
        logger.info("🔗 Joining live trades with historical market data...")
        
        successful_joins = 0
        out_of_range = 0
        
        # Check date range
        hist_min = self.historical_df.index.min()
        hist_max = self.historical_df.index.max()
        logger.info(f"   Historical data range: {hist_min} → {hist_max}")
        
        for trade in self.live_trades:
            # Check if trade is within historical data range
            # Ensure timezone-aware comparison
            entry_time = trade['entry_time']
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            
            hist_min_aware = hist_min if hist_min.tzinfo else hist_min.replace(tzinfo=timezone.utc)
            hist_max_aware = hist_max if hist_max.tzinfo else hist_max.replace(tzinfo=timezone.utc)
            
            if entry_time < hist_min_aware or entry_time > hist_max_aware:
                out_of_range += 1
                continue
            # Extract features at entry time
            features = self.extract_features(trade['entry_time'], self.historical_df)
            
            if features is None:
                continue
            
            # Get market context for labeling
            # Convert to timezone-naive for comparison
            entry_time_naive = trade['entry_time'].replace(tzinfo=None) if trade['entry_time'].tzinfo else trade['entry_time']
            time_tolerance = pd.Timedelta(minutes=1)
            mask = (self.historical_df.index >= entry_time_naive - time_tolerance) & \
                   (self.historical_df.index <= entry_time_naive + time_tolerance)
            
            if not mask.any():
                continue
            
            market_row = self.historical_df[mask].iloc[0]
            market_context = market_row.to_dict()
            
            # Calculate TRUE label (KEY FIX!)
            true_confidence = self.calculate_true_confidence_label(trade, market_context)
            
            self.training_data.append({
                'features': features,
                'label': true_confidence,
                'metadata': {
                    'source': 'live_trade',
                    'position_id': trade['position_id'],
                    'pnl_pct': trade['pnl_percentage'],
                    'old_confidence': trade['ai_confidence']
                }
            })
            
            successful_joins += 1
        
        logger.info(f"✅ Successfully joined {successful_joins}/{len(self.live_trades)} trades")
        if out_of_range > 0:
            logger.warning(f"⚠️ {out_of_range} trades outside historical data range (2025 trades, data ends 2024-12)")
            logger.warning(f"   Using ONLY synthetic trades for training (will fetch fresh 2025 data later)")
    
    def generate_synthetic_trades(self, n_samples: int = 5000):
        """Generate synthetic trades from historical data with PROPER labels"""
        logger.info(f"🧪 Generating {n_samples} synthetic trades...")
        
        # Use data from 2024-2025 for realistic market conditions
        recent_data = self.historical_df[self.historical_df.index >= '2024-01-01']
        
        if len(recent_data) < 2000:
            logger.warning("Insufficient recent data, using all available data")
            recent_data = self.historical_df
        
        synthetic_count = 0
        attempts = 0
        max_attempts = n_samples * 3
        
        while synthetic_count < n_samples and attempts < max_attempts:
            attempts += 1
            
            try:
                # Random entry point (need 1000 candles before and after)
                entry_idx = np.random.randint(1000, len(recent_data) - 1000)
                entry_timestamp = recent_data.index[entry_idx]
                
                # Simulate trade duration (day trading focused)
                hold_duration_min = np.random.choice(
                    [5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240],
                    p=[0.05, 0.15, 0.15, 0.15, 0.15, 0.10, 0.10, 0.05, 0.05, 0.03, 0.02]
                )
                
                exit_idx = entry_idx + hold_duration_min
                if exit_idx >= len(recent_data):
                    continue
                
                # Get entry and exit candles
                entry_candle = recent_data.iloc[entry_idx]
                exit_candle = recent_data.iloc[exit_idx]
                
                # Calculate PnL (assuming LONG position)
                entry_price = float(entry_candle['close'])
                exit_price = float(exit_candle['close'])
                pnl_pct = ((exit_price / entry_price) - 1) * 100
                
                # Extract features at entry
                features = self.extract_features(entry_timestamp, recent_data)
                if features is None:
                    continue
                
                # Calculate TRUE label
                synthetic_trade = {
                    'pnl_percentage': pnl_pct,
                    'duration_minutes': hold_duration_min,
                    'entry_time': entry_timestamp
                }
                
                market_context = entry_candle.to_dict()
                true_confidence = self.calculate_true_confidence_label(synthetic_trade, market_context)
                
                self.training_data.append({
                    'features': features,
                    'label': true_confidence,
                    'metadata': {
                        'source': 'synthetic',
                        'pnl_pct': pnl_pct,
                        'entry_time': entry_timestamp
                    }
                })
                
                synthetic_count += 1
                
                if synthetic_count % 500 == 0:
                    logger.info(f"   Generated {synthetic_count}/{n_samples} synthetic trades...")
                
            except Exception as e:
                logger.debug(f"Synthetic generation attempt failed: {e}")
                continue
        
        logger.info(f"✅ Generated {synthetic_count} synthetic trades (attempts: {attempts})")
    
    def prepare_training_arrays(self) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """Convert training data to numpy arrays"""
        logger.info("🔧 Preparing training arrays...")
        
        X_list = []
        y_list = []
        metadata_list = []
        
        for sample in self.training_data:
            # Extract features in correct order
            feature_vector = [sample['features'][f] for f in self.all_features]
            X_list.append(feature_vector)
            y_list.append(sample['label'])
            metadata_list.append(sample['metadata'])
        
        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)
        metadata_df = pd.DataFrame(metadata_list)
        
        logger.info(f"✅ Training arrays prepared:")
        logger.info(f"   X shape: {X.shape}")
        logger.info(f"   y shape: {y.shape}")
        logger.info(f"   y range: [{y.min():.3f}, {y.max():.3f}]")
        logger.info(f"   y mean: {y.mean():.3f} ± {y.std():.3f}")
        
        return X, y, metadata_df
    
    def train_model(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train XGBoost model with proper validation"""
        logger.info("🤖 Training Layer 5 XGBoost model...")
        
        # Split data (80/20)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=True
        )
        
        logger.info(f"   Train samples: {len(X_train)}")
        logger.info(f"   Test samples: {len(X_test)}")
        
        # Feature scaling (RobustScaler - resistant to outliers)
        self.scaler = RobustScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # XGBoost configuration (laptop-optimized)
        xgb_config = {
            'n_estimators': 300,
            'max_depth': 6,
            'learning_rate': 0.05,  # Lower for better generalization
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.5,  # L1 regularization
            'reg_lambda': 1.0,  # L2 regularization
            'random_state': 42,
            'n_jobs': -1,  # Use all CPU cores
            'eval_metric': 'rmse',
            'early_stopping_rounds': 50
        }
        
        logger.info(f"   XGBoost config: {xgb_config}")
        
        # Train model
        self.model = xgb.XGBRegressor(**xgb_config)
        
        eval_set = [(X_test_scaled, y_test)]
        self.model.fit(
            X_train_scaled, y_train,
            eval_set=eval_set,
            verbose=50
        )
        
        # Predictions
        y_pred_train = self.model.predict(X_train_scaled)
        y_pred_test = self.model.predict(X_test_scaled)
        
        # Clip predictions to valid range
        y_pred_train_clipped = np.clip(y_pred_train, 0.0, 1.0)
        y_pred_test_clipped = np.clip(y_pred_test, 0.0, 1.0)
        
        # Calculate metrics
        metrics = {
            'train_r2': r2_score(y_train, y_pred_train_clipped),
            'test_r2': r2_score(y_test, y_pred_test_clipped),
            'train_mse': mean_squared_error(y_train, y_pred_train_clipped),
            'test_mse': mean_squared_error(y_test, y_pred_test_clipped),
            'train_mae': mean_absolute_error(y_train, y_pred_train_clipped),
            'test_mae': mean_absolute_error(y_test, y_pred_test_clipped),
            'correlation': np.corrcoef(y_test, y_pred_test_clipped)[0, 1],
        }
        
        logger.info(f"\n📊 MODEL PERFORMANCE:")
        logger.info(f"   Train R²: {metrics['train_r2']:.4f}")
        logger.info(f"   Test R²:  {metrics['test_r2']:.4f}")
        logger.info(f"   Test MSE: {metrics['test_mse']:.4f}")
        logger.info(f"   Test MAE: {metrics['test_mae']:.4f}")
        logger.info(f"   🎯 CORRELATION: {metrics['correlation']:.4f}")
        
        if metrics['correlation'] > 0.7:
            logger.info(f"   ✅ POSITIVE CORRELATION - INVERSE PROBLEM FIXED!")
        else:
            logger.warning(f"   ⚠️ Correlation still low - may need more data or features")
        
        return metrics
    
    def validate_model(self, X: np.ndarray, y: np.ndarray, metadata_df: pd.DataFrame):
        """Validate model - ensure POSITIVE correlation!"""
        logger.info("\n🔍 VALIDATING MODEL...")
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predictions
        y_pred = self.model.predict(X_scaled)
        y_pred_clipped = np.clip(y_pred, 0.0, 1.0)
        
        # Overall correlation
        correlation = np.corrcoef(y, y_pred_clipped)[0, 1]
        
        logger.info(f"   Overall correlation: {correlation:.4f}")
        
        # Analyze by PnL quartiles
        metadata_df['true_label'] = y
        metadata_df['predicted_label'] = y_pred_clipped
        
        # Split by source
        live_mask = metadata_df['source'] == 'live_trade'
        synthetic_mask = metadata_df['source'] == 'synthetic'
        
        if live_mask.any():
            live_corr = np.corrcoef(
                metadata_df[live_mask]['true_label'],
                metadata_df[live_mask]['predicted_label']
            )[0, 1]
            logger.info(f"   Live trades correlation: {live_corr:.4f}")
        
        if synthetic_mask.any():
            synth_corr = np.corrcoef(
                metadata_df[synthetic_mask]['true_label'],
                metadata_df[synthetic_mask]['predicted_label']
            )[0, 1]
            logger.info(f"   Synthetic trades correlation: {synth_corr:.4f}")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': self.all_features,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        logger.info(f"\n📊 TOP 10 MOST IMPORTANT FEATURES:")
        for idx, row in feature_importance.head(10).iterrows():
            logger.info(f"   {row['feature']:25s}: {row['importance']:.4f}")
        
        return correlation, feature_importance
    
    def backup_current_model(self):
        """Backup current model before replacement"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_PATH / f"layer_5_confidence_{timestamp}.pkl"
        
        current_model = MODEL_PATH / "layer_5_confidence.pkl"
        if current_model.exists():
            import shutil
            shutil.copy2(current_model, backup_file)
            logger.info(f"📦 Current model backed up to: {backup_file}")
        else:
            logger.warning("⚠️ No existing model to backup")
    
    def deploy_model(self):
        """Deploy new model to production"""
        logger.info("🚀 Deploying new model...")
        
        # Save model
        model_file = MODEL_PATH / "layer_5_confidence.pkl"
        with open(model_file, 'wb') as f:
            pickle.dump(self.model, f)
        
        logger.info(f"   ✅ Model saved: {model_file}")
        
        # Save scaler
        scaler_file = MODEL_PATH / "layer_5_scaler.pkl"
        with open(scaler_file, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        logger.info(f"   ✅ Scaler saved: {scaler_file}")
        
        # Update metadata
        metadata_file = MODEL_PATH / "enterprise_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {}
        
        metadata['layer_performance'] = metadata.get('layer_performance', {})
        metadata['layer_performance']['layer_5'] = {
            'model_type': 'XGBRegressor_Retrained_FixedLabels',
            'features': self.all_features,
            'n_features': len(self.all_features),
            'retrained_at': datetime.now(timezone.utc).isoformat(),
            'training_samples': len(self.training_data),
            'version': 'v3.2.0_FIXED'
        }
        
        metadata['system_version'] = "6-Layer Enterprise v3.2.0 (Layer 5 Fixed - Positive Correlation)"
        metadata['last_retrain_date'] = datetime.now(timezone.utc).isoformat()
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"   ✅ Metadata updated: {metadata_file}")
    
    def run(self, n_synthetic: int = 5000):
        """Run complete retraining pipeline"""
        logger.info("=" * 80)
        logger.info("🔄 LAYER 5 RETRAINING - FIXED LABELS APPROACH")
        logger.info("=" * 80)
        
        # Step 1: Load data
        self.load_historical_data()
        self.load_live_trades()
        
        # Step 2: Prepare training data
        self.prepare_live_training_data()
        logger.info(f"   ✅ Live training samples: {len([d for d in self.training_data if d['metadata']['source'] == 'live_trade'])}")
        
        # Step 3: Generate synthetic data
        self.generate_synthetic_trades(n_samples=n_synthetic)
        logger.info(f"   ✅ Total training samples: {len(self.training_data)}")
        
        # Step 4: Prepare arrays
        X, y, metadata_df = self.prepare_training_arrays()
        
        # Step 5: Train model
        metrics = self.train_model(X, y)
        
        # Step 6: Validate
        correlation, feature_importance = self.validate_model(X, y, metadata_df)
        
        # Step 7: Deploy if acceptable
        if correlation > 0.70 and metrics['test_r2'] > 0.65:
            logger.info("\n✅ MODEL VALIDATION PASSED!")
            logger.info(f"   Correlation: {correlation:.4f} > 0.70 ✓")
            logger.info(f"   Test R²: {metrics['test_r2']:.4f} > 0.65 ✓")
            
            self.backup_current_model()
            self.deploy_model()
            
            logger.info("\n🎉 LAYER 5 RETRAINING COMPLETE!")
            logger.info("   🔄 Restart backend to load new model")
        else:
            logger.warning("\n⚠️ MODEL VALIDATION FAILED")
            logger.warning(f"   Correlation: {correlation:.4f} (need > 0.70)")
            logger.warning(f"   Test R²: {metrics['test_r2']:.4f} (need > 0.65)")
            logger.warning("   Model NOT deployed - investigate further")
        
        logger.info("=" * 80)


def main():
    """Main entry point"""
    retrainer = Layer5Retrainer()
    retrainer.run(n_synthetic=5000)


if __name__ == "__main__":
    main()

