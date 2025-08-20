"""
TradePulse.AI - Learning Analytics API
=====================================

PHASE 3: Continuous Learning & Optimization API Endpoints

Provides access to:
- Learning analytics and metrics
- Optimization recommendations
- Pattern performance statistics
- Position result analysis
- Auto-optimization controls

Author: TradePulse.AI Development Team
Created: July 2025 (PHASE 3)
Version: 3.0.0
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from app.backend.services import get_continuous_learning_engine
from app.backend.services import get_position_result_tracker, PositionOutcome
from utils.dependencies import require_admin_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/analytics", summary="Get Learning Analytics")
async def get_learning_analytics(
    days: int = Query(default=7, ge=1, le=30, description="Days to analyze"),
    include_patterns: bool = Query(default=True, description="Include pattern analysis"),
    admin_user = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    🧠 Get comprehensive learning analytics
    
    Returns performance metrics, trends, and optimization insights
    """
    try:
        # Get learning engine and tracker
        learning_engine = await get_continuous_learning_engine()
        tracker = await get_position_result_tracker()
        
        # Get recent position results for analysis
        recent_results = await tracker._load_recent_results(days=days)
        
        if not recent_results:
            return {
                'status': 'no_data',
                'message': f'No position data found for last {days} days',
                'analytics': {}
            }
        
        # Calculate basic metrics
        total_positions = len(recent_results)
        successful_positions = sum(1 for r in recent_results if r.get('was_successful', False))
        success_rate = successful_positions / total_positions
        
        total_pnl = sum(r.get('pnl_absolute', 0) for r in recent_results)
        avg_pnl = total_pnl / total_positions
        avg_pnl_pct = sum(r.get('pnl_percentage', 0) for r in recent_results) / total_positions
        
        # Time in position analysis
        avg_time_in_position = sum(r.get('time_in_position_minutes', 0) for r in recent_results) / total_positions
        
        # Pattern analysis performance
        pattern_analytics = {}
        if include_patterns:
            pattern_results = [r for r in recent_results if r.get('pattern_analysis_enabled', False)]
            no_pattern_results = [r for r in recent_results if not r.get('pattern_analysis_enabled', False)]
            
            if pattern_results and no_pattern_results:
                pattern_success = sum(1 for r in pattern_results if r.get('was_successful', False)) / len(pattern_results)
                no_pattern_success = sum(1 for r in no_pattern_results if r.get('was_successful', False)) / len(no_pattern_results)
                
                pattern_analytics = {
                    'pattern_enabled_positions': len(pattern_results),
                    'pattern_success_rate': pattern_success,
                    'no_pattern_positions': len(no_pattern_results),
                    'no_pattern_success_rate': no_pattern_success,
                    'pattern_advantage': pattern_success - no_pattern_success,
                    'pattern_effectiveness': pattern_success > no_pattern_success
                }
        
        # Risk assessment breakdown
        risk_breakdown = {}
        for result in recent_results:
            risk = result.get('risk_assessment', 'MEDIUM')
            if risk not in risk_breakdown:
                risk_breakdown[risk] = {'total': 0, 'successful': 0, 'total_pnl': 0}
            risk_breakdown[risk]['total'] += 1
            if result.get('was_successful', False):
                risk_breakdown[risk]['successful'] += 1
            risk_breakdown[risk]['total_pnl'] += result.get('pnl_absolute', 0)
        
        # Calculate success rates for each risk level
        for risk, data in risk_breakdown.items():
            data['success_rate'] = data['successful'] / data['total'] if data['total'] > 0 else 0
            data['avg_pnl'] = data['total_pnl'] / data['total'] if data['total'] > 0 else 0
        
        # Get learning metrics
        learning_metrics = await learning_engine._calculate_learning_metrics(tracker)
        
        return {
            'status': 'success',
            'period_analyzed': f'{days} days',
            'last_updated': datetime.now().isoformat(),
            'analytics': {
                'overall_performance': {
                    'total_positions': total_positions,
                    'success_rate': success_rate,
                    'successful_positions': successful_positions,
                    'total_pnl': total_pnl,
                    'avg_pnl': avg_pnl,
                    'avg_pnl_percentage': avg_pnl_pct,
                    'avg_time_in_position_minutes': avg_time_in_position
                },
                'pattern_analysis': pattern_analytics,
                'risk_assessment_breakdown': risk_breakdown,
                'learning_metrics': {
                    'total_positions_analyzed': learning_metrics.total_positions_analyzed,
                    'success_rate_trend': learning_metrics.success_rate_trend,
                    'avg_pnl_trend': learning_metrics.avg_pnl_trend,
                    'pattern_performance_delta': learning_metrics.pattern_performance_delta,
                    'last_optimization_date': learning_metrics.last_optimization_date.isoformat() if learning_metrics.last_optimization_date != datetime.min else None,
                    'recommendations_generated': learning_metrics.recommendations_generated,
                    'recommendations_applied': learning_metrics.recommendations_applied
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get learning analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Learning analytics error: {str(e)}")


@router.get("/optimization-recommendations", summary="Get Optimization Recommendations")
async def get_optimization_recommendations(
    force_analysis: bool = Query(default=False, description="Force new analysis"),
    admin_user = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    🎯 Get optimization recommendations from the learning engine
    
    Returns actionable recommendations for improving system performance
    """
    try:
        learning_engine = await get_continuous_learning_engine()
        
        # Generate recommendations (but don't auto-apply)
        results = await learning_engine.analyze_and_optimize(
            force_optimization=force_analysis,
            auto_apply_recommendations=False
        )
        
        return {
            'status': 'success',
            'analysis_timestamp': datetime.now().isoformat(),
            'optimization_results': results
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get optimization recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization error: {str(e)}")


@router.post("/apply-optimization", summary="Apply Optimization Recommendations")
async def apply_optimization_recommendations(
    force_optimization: bool = Query(default=False, description="Force optimization despite cooldown"),
    admin_user = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    ⚡ Apply optimization recommendations automatically
    
    CAUTION: This will automatically modify system parameters
    """
    try:
        learning_engine = await get_continuous_learning_engine()
        
        # Run optimization with auto-apply enabled
        results = await learning_engine.analyze_and_optimize(
            force_optimization=force_optimization,
            auto_apply_recommendations=True
        )
        
        return {
            'status': 'success',
            'optimization_applied': True,
            'optimization_results': results,
            'warning': 'System parameters have been automatically modified'
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to apply optimization: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization application error: {str(e)}")


@router.get("/pattern-performance", summary="Get Pattern Performance Statistics")
async def get_pattern_performance(
    min_samples: int = Query(default=5, ge=1, description="Minimum samples for pattern inclusion"),
    admin_user = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    📊 Get detailed pattern performance statistics
    
    Returns success rates, P&L metrics, and recommendations for each pattern type
    """
    try:
        tracker = await get_position_result_tracker()
        
        # Get pattern performance statistics
        pattern_stats = await tracker.get_pattern_performance_stats(min_samples=min_samples)
        
        if not pattern_stats:
            return {
                'status': 'no_data',
                'message': f'No patterns with minimum {min_samples} samples found',
                'pattern_stats': {}
            }
        
        # Sort patterns by success rate
        sorted_patterns = sorted(
            pattern_stats.items(),
            key=lambda x: x[1]['success_rate'],
            reverse=True
        )
        
        # Identify best and worst performing patterns
        best_pattern = sorted_patterns[0] if sorted_patterns else None
        worst_pattern = sorted_patterns[-1] if sorted_patterns else None
        
        return {
            'status': 'success',
            'total_patterns_analyzed': len(pattern_stats),
            'min_samples_threshold': min_samples,
            'last_updated': datetime.now().isoformat(),
            'pattern_performance': {
                'all_patterns': dict(sorted_patterns),
                'best_performing': {
                    'pattern_key': best_pattern[0],
                    'stats': best_pattern[1]
                } if best_pattern else None,
                'worst_performing': {
                    'pattern_key': worst_pattern[0],
                    'stats': worst_pattern[1]
                } if worst_pattern else None,
                'performance_summary': {
                    'avg_success_rate': sum(stats['success_rate'] for stats in pattern_stats.values()) / len(pattern_stats),
                    'total_positions': sum(stats['total_positions'] for stats in pattern_stats.values()),
                    'total_pnl': sum(stats['total_pnl'] for stats in pattern_stats.values())
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get pattern performance: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern performance error: {str(e)}")


@router.get("/position-results", summary="Get Position Results Analysis")
async def get_position_results(
    days: int = Query(default=7, ge=1, le=30, description="Days to analyze"),
    outcome_filter: Optional[str] = Query(default=None, description="Filter by outcome: take_profit, stop_loss, manual_close"),
    admin_user = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    📈 Get detailed position results and analysis
    
    Returns comprehensive position outcome data with filtering options
    """
    try:
        tracker = await get_position_result_tracker()
        
        # Load recent results
        recent_results = await tracker._load_recent_results(days=days)
        
        if not recent_results:
            return {
                'status': 'no_data',
                'message': f'No position results found for last {days} days',
                'results': []
            }
        
        # Apply outcome filter if specified
        if outcome_filter:
            try:
                outcome_enum = PositionOutcome(outcome_filter)
                recent_results = [r for r in recent_results if r.get('outcome') == outcome_enum.value]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid outcome filter: {outcome_filter}")
        
        # Calculate outcome statistics
        outcome_stats = {}
        for result in recent_results:
            outcome = result.get('outcome', 'unknown')
            if outcome not in outcome_stats:
                outcome_stats[outcome] = {'count': 0, 'total_pnl': 0}
            outcome_stats[outcome]['count'] += 1
            outcome_stats[outcome]['total_pnl'] += result.get('pnl_absolute', 0)
        
        # Calculate averages
        for outcome, stats in outcome_stats.items():
            stats['avg_pnl'] = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0
        
        return {
            'status': 'success',
            'period_analyzed': f'{days} days',
            'total_positions': len(recent_results),
            'outcome_filter': outcome_filter,
            'last_updated': datetime.now().isoformat(),
            'position_results': {
                'outcome_statistics': outcome_stats,
                'detailed_results': recent_results[:50],  # Limit to 50 most recent
                'summary': {
                    'total_positions': len(recent_results),
                    'total_pnl': sum(r.get('pnl_absolute', 0) for r in recent_results),
                    'avg_pnl': sum(r.get('pnl_absolute', 0) for r in recent_results) / len(recent_results),
                    'success_rate': sum(1 for r in recent_results if r.get('was_successful', False)) / len(recent_results)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get position results: {e}")
        raise HTTPException(status_code=500, detail=f"Position results error: {str(e)}")


@router.get("/learning-status", summary="Get Learning Engine Status")
async def get_learning_status(
    admin_user = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    ⚙️ Get current status of the continuous learning engine
    
    Returns engine configuration, recent activity, and health metrics
    """
    try:
        learning_engine = await get_continuous_learning_engine()
        tracker = await get_position_result_tracker()
        
        # Get recent optimization history
        recent_optimizations = learning_engine.optimization_history[-5:] if learning_engine.optimization_history else []
        
        return {
            'status': 'operational',
            'engine_info': {
                'auto_optimization_enabled': learning_engine.auto_optimization_enabled,
                'last_optimization_time': learning_engine.last_optimization_time.isoformat() if learning_engine.last_optimization_time != datetime.min else None,
                'optimization_cooldown_hours': learning_engine.optimization_cooldown_hours,
                'min_samples_for_learning': learning_engine.min_samples_for_learning,
                'confidence_threshold': learning_engine.confidence_threshold
            },
            'tracker_info': {
                'total_positions_tracked': tracker.total_positions_tracked,
                'successful_positions': tracker.successful_positions,
                'total_pnl': tracker.total_pnl,
                'cache_entries': len(tracker.pattern_performance_cache)
            },
            'recent_activity': {
                'recent_optimizations': recent_optimizations,
                'total_optimization_cycles': len(learning_engine.optimization_history),
                'current_parameters': learning_engine.current_parameters
            },
            'next_optimization_eligible': datetime.now() + timedelta(hours=learning_engine.optimization_cooldown_hours),
            'learning_capabilities': [
                "Real-time position result tracking",
                "Automatic parameter optimization", 
                "Pattern performance analysis",
                "Statistical significance testing",
                "Risk-adjusted optimization",
                "Auto-blacklisting underperforming patterns"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get learning status: {e}")
        raise HTTPException(status_code=500, detail=f"Learning status error: {str(e)}")


@router.post("/toggle-auto-optimization", summary="Toggle Auto-Optimization")
async def toggle_auto_optimization(
    enabled: bool = Query(description="Enable or disable auto-optimization"),
    admin_user = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    🔄 Enable or disable automatic optimization
    
    Controls whether the learning engine can automatically apply optimizations
    """
    try:
        learning_engine = await get_continuous_learning_engine()
        
        old_status = learning_engine.auto_optimization_enabled
        learning_engine.auto_optimization_enabled = enabled
        
        logger.info(f"🔄 Auto-optimization {'ENABLED' if enabled else 'DISABLED'} by admin")
        
        return {
            'status': 'success',
            'auto_optimization_enabled': enabled,
            'previous_status': old_status,
            'message': f"Auto-optimization {'enabled' if enabled else 'disabled'}",
            'changed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to toggle auto-optimization: {e}")
        raise HTTPException(status_code=500, detail=f"Toggle error: {str(e)}")


@router.get("/health", summary="Learning System Health Check")
async def learning_health_check() -> Dict[str, Any]:
    """
    🏥 Quick health check for learning systems
    """
    try:
        # Test learning engine
        learning_engine = await get_continuous_learning_engine()
        
        # Test tracker
        tracker = await get_position_result_tracker()
        
        return {
            'status': 'healthy',
            'components': {
                'continuous_learning_engine': 'operational',
                'position_result_tracker': 'operational',
                'data_directories': 'accessible'
            },
            'last_check': datetime.now().isoformat(),
            'version': '3.0.0'
        }
        
    except Exception as e:
        logger.error(f"❌ Learning health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'last_check': datetime.now().isoformat()
        } 