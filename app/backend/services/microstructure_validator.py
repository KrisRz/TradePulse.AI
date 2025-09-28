"""
Microstructure Validator - TradePulse.AI
======================================

Professional microstructure validation with edge checks for spread, imbalance, and slippage.
Implements advanced market microstructure analysis for entry timing validation.

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MicrostructureValidator:
    """Professional microstructure validation with edge checks"""
    
    def __init__(self):
        # Professional thresholds for day trading
        self.max_spread_bps = 1.5  # 1.5 basis points max spread
        self.min_imbalance_ratio = 0.55  # 55% minimum order book imbalance for BUY
        self.max_slippage_bps = 2.0  # 2.0 basis points max estimated slippage
        self.min_book_depth = 1000.0  # $1000 minimum depth on each side
        
        # Validation weights
        self.spread_weight = 0.35
        self.imbalance_weight = 0.25  
        self.slippage_weight = 0.25
        self.depth_weight = 0.15
        
        logger.info("🔬 Microstructure Validator initialized")
    
    async def validate_entry_microstructure(self, 
                                           market_data: Dict[str, Any], 
                                           signal_action: str,
                                           position_size_usd: float = 1000.0) -> Dict[str, Any]:
        """
        Validate entry conditions based on market microstructure
        
        Args:
            market_data: Market data including tick, orderbook, etc.
            signal_action: BUY or SELL
            position_size_usd: Position size for slippage estimation
            
        Returns:
            Dict with validation results and edge check scores
        """
        try:
            # Extract market microstructure data
            tick_data = market_data.get("tick", {})
            orderbook = market_data.get("orderbook", {})
            current_price = float(tick_data.get("price", 0.0))
            
            if current_price <= 0:
                return self._get_neutral_result("missing_price_data")
            
            # Calculate microstructure metrics
            spread_metrics = await self._calculate_spread_metrics(tick_data, orderbook, current_price)
            imbalance_metrics = await self._calculate_imbalance_metrics(orderbook, signal_action)
            slippage_metrics = await self._calculate_slippage_metrics(orderbook, signal_action, position_size_usd, current_price)
            depth_metrics = await self._calculate_depth_metrics(orderbook)
            
            # Edge checks
            spread_check = spread_metrics["spread_bps"] <= self.max_spread_bps
            imbalance_check = imbalance_metrics["imbalance_ratio"] >= self.min_imbalance_ratio if signal_action == "BUY" else \
                             imbalance_metrics["imbalance_ratio"] <= (1.0 - self.min_imbalance_ratio)
            slippage_check = slippage_metrics["slippage_bps"] <= self.max_slippage_bps
            depth_check = depth_metrics["total_depth_usd"] >= self.min_book_depth
            
            # Calculate weighted edge score
            edge_score = (
                (spread_check * self.spread_weight) +
                (imbalance_check * self.imbalance_weight) +
                (slippage_check * self.slippage_weight) +
                (depth_check * self.depth_weight)
            )
            
            # Detailed logging
            logger.info(f"🔬 MICROSTRUCTURE VALIDATION: {signal_action}")
            logger.info(f"   Spread: {spread_metrics['spread_bps']:.2f}bps ≤ {self.max_spread_bps:.2f} = {spread_check}")
            logger.info(f"   Imbalance: {imbalance_metrics['imbalance_ratio']:.2f} {'≥' if signal_action == 'BUY' else '≤'} {self.min_imbalance_ratio:.2f} = {imbalance_check}")
            logger.info(f"   Slippage: {slippage_metrics['slippage_bps']:.2f}bps ≤ {self.max_slippage_bps:.2f} = {slippage_check}")
            logger.info(f"   Depth: ${depth_metrics['total_depth_usd']:.0f} ≥ ${self.min_book_depth:.0f} = {depth_check}")
            logger.info(f"   Edge Score: {edge_score:.2f}")
            
            # Determine validation result
            is_valid = edge_score >= 0.75  # 75% of checks must pass
            
            return {
                "is_valid": is_valid,
                "edge_score": edge_score,
                "validation_reason": "microstructure_edge_checks",
                "spread_metrics": spread_metrics,
                "imbalance_metrics": imbalance_metrics,
                "slippage_metrics": slippage_metrics,
                "depth_metrics": depth_metrics,
                "checks": {
                    "spread_check": spread_check,
                    "imbalance_check": imbalance_check,
                    "slippage_check": slippage_check,
                    "depth_check": depth_check
                }
            }
            
        except Exception as e:
            logger.error(f"Microstructure validation failed: {e}")
            return self._get_neutral_result(f"validation_error: {e}")
    
    async def _calculate_spread_metrics(self, tick_data: Dict, orderbook: Dict, current_price: float) -> Dict[str, float]:
        """Calculate bid-ask spread metrics"""
        try:
            # Try to get spread from orderbook
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])
            
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                spread = best_ask - best_bid
                spread_bps = (spread / current_price) * 10000  # Convert to basis points
                
                return {
                    "spread": spread,
                    "spread_bps": spread_bps,
                    "best_bid": best_bid,
                    "best_ask": best_ask
                }
            else:
                # Fallback: estimate spread from volatility
                volatility = tick_data.get("volatility", 0.02)
                estimated_spread_bps = max(0.5, volatility * 10000 * 0.1)  # 10% of volatility
                
                return {
                    "spread": current_price * (estimated_spread_bps / 10000),
                    "spread_bps": estimated_spread_bps,
                    "best_bid": current_price * 0.9999,
                    "best_ask": current_price * 1.0001
                }
                
        except Exception as e:
            logger.warning(f"Spread calculation failed: {e}")
            return {
                "spread": current_price * 0.0001,
                "spread_bps": 1.0,
                "best_bid": current_price * 0.9999,
                "best_ask": current_price * 1.0001
            }
    
    async def _calculate_imbalance_metrics(self, orderbook: Dict, signal_action: str) -> Dict[str, float]:
        """Calculate order book imbalance metrics"""
        try:
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])
            
            if not bids or not asks:
                return {"imbalance_ratio": 0.5, "bid_depth": 0.0, "ask_depth": 0.0}
            
            # Calculate depth for top 10 levels (or available levels)
            bid_depth = sum(float(bid[0]) * float(bid[1]) for bid in bids[:10])  # Price * Quantity
            ask_depth = sum(float(ask[0]) * float(ask[1]) for ask in asks[:10])
            
            total_depth = bid_depth + ask_depth
            imbalance_ratio = bid_depth / total_depth if total_depth > 0 else 0.5
            
            return {
                "imbalance_ratio": imbalance_ratio,
                "bid_depth": bid_depth,
                "ask_depth": ask_depth,
                "total_depth": total_depth
            }
            
        except Exception as e:
            logger.warning(f"Imbalance calculation failed: {e}")
            return {"imbalance_ratio": 0.5, "bid_depth": 1000.0, "ask_depth": 1000.0}
    
    async def _calculate_slippage_metrics(self, orderbook: Dict, signal_action: str, 
                                        position_size_usd: float, current_price: float) -> Dict[str, float]:
        """Calculate estimated slippage for given position size"""
        try:
            # Determine which side of the book to consume
            levels = orderbook.get("asks" if signal_action == "BUY" else "bids", [])
            
            if not levels:
                # Fallback slippage estimate
                estimated_slippage_bps = min(5.0, (position_size_usd / 10000) * 10)  # Scale with size
                return {
                    "slippage_bps": estimated_slippage_bps,
                    "weighted_avg_price": current_price * (1.0001 if signal_action == "BUY" else 0.9999)
                }
            
            # Calculate volume-weighted average price for the order
            remaining_size_usd = position_size_usd
            total_cost = 0.0
            total_quantity = 0.0
            
            for level in levels:
                if remaining_size_usd <= 0:
                    break
                    
                price = float(level[0])
                quantity = float(level[1])
                level_value = price * quantity
                
                consumed_value = min(remaining_size_usd, level_value)
                consumed_quantity = consumed_value / price
                
                total_cost += consumed_value
                total_quantity += consumed_quantity
                remaining_size_usd -= consumed_value
            
            if total_quantity > 0:
                weighted_avg_price = total_cost / total_quantity
                slippage = abs(weighted_avg_price - current_price)
                slippage_bps = (slippage / current_price) * 10000
            else:
                slippage_bps = 10.0  # High slippage penalty if can't fill
                weighted_avg_price = current_price
            
            return {
                "slippage_bps": slippage_bps,
                "weighted_avg_price": weighted_avg_price,
                "fillable_percentage": min(100.0, ((position_size_usd - remaining_size_usd) / position_size_usd) * 100)
            }
            
        except Exception as e:
            logger.warning(f"Slippage calculation failed: {e}")
            return {"slippage_bps": 2.0, "weighted_avg_price": current_price}
    
    async def _calculate_depth_metrics(self, orderbook: Dict) -> Dict[str, float]:
        """Calculate order book depth metrics"""
        try:
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])
            
            # Calculate depth in USD for top 5 levels
            bid_depth_usd = sum(float(bid[0]) * float(bid[1]) for bid in bids[:5])
            ask_depth_usd = sum(float(ask[0]) * float(ask[1]) for ask in asks[:5])
            
            return {
                "bid_depth_usd": bid_depth_usd,
                "ask_depth_usd": ask_depth_usd,
                "total_depth_usd": bid_depth_usd + ask_depth_usd,
                "depth_ratio": bid_depth_usd / (ask_depth_usd + 1e-6)  # Avoid division by zero
            }
            
        except Exception as e:
            logger.warning(f"Depth calculation failed: {e}")
            return {
                "bid_depth_usd": 1000.0,
                "ask_depth_usd": 1000.0,
                "total_depth_usd": 2000.0,
                "depth_ratio": 1.0
            }
    
    def _get_neutral_result(self, reason: str) -> Dict[str, Any]:
        """Return neutral validation result when data is insufficient"""
        return {
            "is_valid": True,  # Neutral = don't block entry
            "edge_score": 0.5,
            "validation_reason": reason,
            "spread_metrics": {"spread_bps": 1.0},
            "imbalance_metrics": {"imbalance_ratio": 0.5},
            "slippage_metrics": {"slippage_bps": 1.0},
            "depth_metrics": {"total_depth_usd": 1000.0},
            "checks": {
                "spread_check": True,
                "imbalance_check": True, 
                "slippage_check": True,
                "depth_check": True
            }
        }


# Global validator instance
_microstructure_validator = None

def get_microstructure_validator() -> MicrostructureValidator:
    """Get global microstructure validator instance"""
    global _microstructure_validator
    if _microstructure_validator is None:
        _microstructure_validator = MicrostructureValidator()
    return _microstructure_validator
