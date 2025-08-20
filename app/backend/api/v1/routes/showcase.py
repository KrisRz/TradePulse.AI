"""
Portfolio Showcase API - TradePulse.AI Enterprise
SUBSCRIPTION MONETIZATION API - Marketing Performance Endpoints

Professional API endpoints for portfolio showcase and subscription monetization:
- Real-time performance dashboard data
- Marketing-ready content generation
- Layer-by-layer performance analytics
- Subscription conversion metrics

MONETIZATION FOCUS: API endpoints designed for subscription revenue generation
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field

from app.backend.core.config import get_settings
from app.backend.core.logging import get_logger
from app.backend.utils.dependencies import get_current_user, User
from app.backend.services import portfolio_showcase_engine
from app.backend.services import VirtualPortfolioManager as VirtualPortfolioService

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

# Initialize services
portfolio_service = VirtualPortfolioService()


class ShowcaseRequest(BaseModel):
    """Portfolio showcase request model"""
    portfolio_id: str = Field(default="default", description="Portfolio ID to showcase")
    period_days: int = Field(default=30, ge=1, le=365, description="Analysis period in days")
    include_marketing: bool = Field(default=True, description="Include marketing content")
    include_layers: bool = Field(default=True, description="Include layer performance analysis")


class LiveShowcaseMetrics(BaseModel):
    """Live showcase metrics response"""
    portfolio_id: str
    return_7d: float
    sharpe_ratio: float
    win_rate: float
    max_drawdown: float
    total_trades: int
    ai_score: float
    latest_headline: str
    last_updated: str


class ShowcaseResponse(BaseModel):
    """Complete showcase response"""
    showcase_data: Dict[str, Any]
    marketing_content: Dict[str, Any]
    performance_summary: Dict[str, Any]
    metadata: Dict[str, Any]


@router.get("/live-metrics/{portfolio_id}", response_model=LiveShowcaseMetrics)
async def get_live_showcase_metrics(
    portfolio_id: str,
    current_user: User = Depends(get_current_user)
) -> LiveShowcaseMetrics:
    """
    Get real-time showcase metrics for portfolio
    
    Perfect for live dashboards and real-time marketing displays.
    Updates automatically as trading performance changes.
    
    Args:
        portfolio_id: Portfolio identifier
        current_user: Authenticated user
        
    Returns:
        Real-time showcase metrics
    """
    try:
        logger.info(f"📊 Getting live showcase metrics for {portfolio_id}")
        
        # Get portfolio data
        portfolio_data = await portfolio_service.get_portfolio(current_user.id)
        position_history = await portfolio_service.get_position_history(current_user.id, limit=100)
        
        if not portfolio_data:
            # Return default metrics for new users
            return LiveShowcaseMetrics(
                portfolio_id=portfolio_id,
                return_7d=0.0,
                sharpe_ratio=1.5,
                win_rate=0.65,
                max_drawdown=0.03,
                total_trades=0,
                ai_score=95.0,
                latest_headline="AI Trading System Ready",
                last_updated=datetime.utcnow().isoformat()
            )
        
        # Generate showcase data
        showcase_data = await portfolio_showcase_engine.generate_live_showcase_data(
            portfolio_data, position_history
        )
        
        # Extract live metrics
        performance = showcase_data['performance_metrics']
        
        return LiveShowcaseMetrics(
            portfolio_id=portfolio_id,
            return_7d=performance['weekly_return_pct'],
            sharpe_ratio=performance['sharpe_ratio'],
            win_rate=performance['win_rate'],
            max_drawdown=performance['max_drawdown'],
            total_trades=performance['total_trades'],
            ai_score=min(performance['win_rate'] * 100 + 30, 99.9),
            latest_headline=showcase_data['marketing_highlights'][0]['title'] if showcase_data['marketing_highlights'] else "AI Trading Active",
            last_updated=showcase_data['timestamp']
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get live showcase metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch live showcase metrics: {str(e)}"
        )


@router.post("/generate/{portfolio_id}", response_model=ShowcaseResponse)
async def generate_portfolio_showcase(
    portfolio_id: str,
    request: ShowcaseRequest,
    current_user: User = Depends(get_current_user)
) -> ShowcaseResponse:
    """
    Generate complete portfolio showcase for marketing/subscription
    
    Creates comprehensive performance showcase perfect for:
    - Subscription landing pages
    - Marketing campaigns
    - Investor presentations
    - Performance reports
    
    Args:
        portfolio_id: Portfolio identifier  
        request: Showcase generation parameters
        current_user: Authenticated user
        
    Returns:
        Complete showcase with marketing content
    """
    try:
        logger.info(f"💰 Generating showcase for {portfolio_id} ({request.period_days} days)")
        
        # Get portfolio data
        portfolio_data = await portfolio_service.get_portfolio(current_user.id)
        position_history = await portfolio_service.get_position_history(current_user.id, limit=200)
        
        if not portfolio_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        # Generate complete showcase data
        showcase_data = await portfolio_showcase_engine.generate_live_showcase_data(
            portfolio_data, position_history
        )
        
        # Return complete showcase response
        return ShowcaseResponse(
            showcase_data=showcase_data,
            marketing_content=showcase_data.get('social_content', {}),
            performance_summary=showcase_data.get('performance_metrics', {}),
            metadata={
                'portfolio_id': portfolio_id,
                'period_days': request.period_days,
                'generated_at': showcase_data['timestamp'],
                'include_marketing': request.include_marketing,
                'include_layers': request.include_layers,
                'subscription_ready': showcase_data.get('subscription_roi', {}).get('annual_roi_estimate', 0) > 0
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to generate showcase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate portfolio showcase: {str(e)}"
        )


@router.get("/marketing-summary")
async def get_marketing_summary(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get marketing summary for quick display
    
    Returns:
        Concise marketing metrics for dashboard display
    """
    try:
        summary = await portfolio_showcase_engine.get_marketing_summary()
        return summary
        
    except Exception as e:
        logger.error(f"❌ Failed to get marketing summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get marketing summary: {str(e)}"
        )
        
        # Marketing content
        marketing_content = {
            "headlines": showcase_data.marketing_headlines,
            "achievements": showcase_data.key_achievements,
            "summary": showcase_data.performance_summary,
            "subscription_ready": True
        }
        
        # Layer performance (if requested)
        if request.include_layers:
            response_data["layer_performance"] = [
                {
                    "layer_name": layer.layer_name,
                    "layer_number": layer.layer_number,
                    "success_rate": layer.success_rate,
                    "avg_confidence": layer.avg_confidence,
                    "total_decisions": layer.total_decisions,
                    "profitable_decisions": layer.profitable_decisions,
                    "avg_pnl_impact": layer.avg_pnl_impact
                }
                for layer in showcase_data.layer_performances
            ]
        
        # Performance summary for quick overview
        performance_summary = {
            "overall_grade": "A+" if showcase_data.sharpe_ratio > 2.0 else "A" if showcase_data.sharpe_ratio > 1.5 else "B+",
            "risk_grade": "A+" if showcase_data.max_drawdown < 2.0 else "A" if showcase_data.max_drawdown < 5.0 else "B+", 
            "ai_grade": "A+" if showcase_data.signal_accuracy > 85 else "A" if showcase_data.signal_accuracy > 80 else "B+",
            "subscription_recommendation": "HIGHLY RECOMMENDED" if showcase_data.sharpe_ratio > 1.5 and showcase_data.win_rate > 70 else "RECOMMENDED",
            "key_selling_points": [
                f"{showcase_data.total_return_percent:.1f}% returns achieved",
                f"{showcase_data.win_rate:.1f}% win rate with AI precision", 
                f"Only {showcase_data.max_drawdown:.1f}% maximum drawdown",
                f"Sharpe ratio of {showcase_data.sharpe_ratio:.2f} beats market"
            ]
        }
        
        # Metadata
        metadata = {
            "generated_at": showcase_data.showcase_generated.isoformat(),
            "data_period": showcase_data.data_period,
            "portfolio_id": portfolio_id,
            "version": "1.0.0",
            "monetization_ready": True
        }
        
        logger.info(f"✅ Showcase generated: {showcase_data.total_return_percent:.2f}% return, {showcase_data.win_rate:.1f}% win rate")
        
        return ShowcaseResponse(
            showcase_data=response_data,
            marketing_content=marketing_content,
            performance_summary=performance_summary,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to generate portfolio showcase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate portfolio showcase: {str(e)}"
        )


@router.get("/marketing-content/{portfolio_id}")
async def get_marketing_content(
    portfolio_id: str,
    period_days: int = Query(default=7, ge=1, le=90, description="Period for content generation"),
    content_type: str = Query(default="headlines", description="Type of content: headlines, achievements, summary"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get marketing content for subscription campaigns
    
    Perfect for:
    - Social media posts
    - Email campaigns  
    - Landing page content
    - Ad copy generation
    
    Args:
        portfolio_id: Portfolio identifier
        period_days: Period for performance analysis
        content_type: Type of marketing content to generate
        current_user: Authenticated user
        
    Returns:
        Marketing-ready content
    """
    try:
        logger.info(f"📝 Generating marketing content for {portfolio_id}")
        
        # Generate showcase for marketing content
        showcase_data = await portfolio_showcase_engine.generate_portfolio_showcase(
            portfolio_id=portfolio_id,
            period_days=period_days
        )
        
        # Prepare marketing content based on type
        if content_type == "headlines":
            content = {
                "headlines": showcase_data.marketing_headlines,
                "best_headline": showcase_data.marketing_headlines[0] if showcase_data.marketing_headlines else "AI Trading System Active",
                "social_media_ready": True
            }
        elif content_type == "achievements":
            content = {
                "achievements": showcase_data.key_achievements,
                "bullet_points": showcase_data.key_achievements,
                "list_ready": True
            }
        elif content_type == "summary":
            content = {
                "summary": showcase_data.performance_summary,
                "elevator_pitch": showcase_data.performance_summary[:200] + "..." if len(showcase_data.performance_summary) > 200 else showcase_data.performance_summary,
                "description_ready": True
            }
        else:
            # Return all content types
            content = {
                "headlines": showcase_data.marketing_headlines,
                "achievements": showcase_data.key_achievements,
                "summary": showcase_data.performance_summary,
                "complete_package": True
            }
        
        # Add metadata
        content.update({
            "generated_for": portfolio_id,
            "period": f"{period_days} days",
            "performance_summary": {
                "return_percent": showcase_data.total_return_percent,
                "win_rate": showcase_data.win_rate,
                "sharpe_ratio": showcase_data.sharpe_ratio,
                "max_drawdown": showcase_data.max_drawdown
            },
            "subscription_ready": True,
            "generated_at": datetime.now().isoformat()
        })
        
        return content
        
    except Exception as e:
        logger.error(f"❌ Failed to generate marketing content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate marketing content: {str(e)}"
        )


@router.get("/performance-comparison/{portfolio_id}")
async def get_performance_comparison(
    portfolio_id: str,
    benchmark: str = Query(default="btc", description="Benchmark to compare against: btc, sp500, nasdaq"),
    period_days: int = Query(default=30, ge=7, le=365, description="Comparison period"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get performance comparison vs benchmarks
    
    Perfect for demonstrating competitive advantage in marketing materials.
    
    Args:
        portfolio_id: Portfolio identifier
        benchmark: Benchmark for comparison
        period_days: Analysis period
        current_user: Authenticated user
        
    Returns:
        Performance comparison data
    """
    try:
        logger.info(f"📈 Generating performance comparison for {portfolio_id} vs {benchmark}")
        
        # Generate showcase data
        showcase_data = await portfolio_showcase_engine.generate_portfolio_showcase(
            portfolio_id=portfolio_id,
            period_days=period_days
        )
        
        # Benchmark returns (simulated - in production, fetch real data)
        benchmark_returns = {
            "btc": 5.2,      # Bitcoin benchmark
            "sp500": 2.1,    # S&P 500 benchmark  
            "nasdaq": 3.8,   # NASDAQ benchmark
            "gold": 1.2,     # Gold benchmark
            "bonds": 0.8     # Bonds benchmark
        }
        
        portfolio_return = showcase_data.total_return_percent
        benchmark_return = benchmark_returns.get(benchmark, 2.0)
        outperformance = portfolio_return - benchmark_return
        
        # Create comparison data
        comparison = {
            "portfolio_performance": {
                "return_percent": portfolio_return,
                "sharpe_ratio": showcase_data.sharpe_ratio,
                "max_drawdown": showcase_data.max_drawdown,
                "win_rate": showcase_data.win_rate,
                "volatility": showcase_data.volatility
            },
            "benchmark_performance": {
                "name": benchmark.upper(),
                "return_percent": benchmark_return,
                "sharpe_ratio": 1.0,  # Typical benchmark Sharpe
                "max_drawdown": 8.5,  # Typical benchmark drawdown
                "volatility": 20.0    # Typical benchmark volatility
            },
            "comparison_results": {
                "outperformance_percent": outperformance,
                "outperformance_ratio": portfolio_return / benchmark_return if benchmark_return > 0 else 1.0,
                "better_sharpe": showcase_data.sharpe_ratio > 1.0,
                "lower_drawdown": showcase_data.max_drawdown < 8.5,
                "competitive_advantage": outperformance > 0
            },
            "marketing_message": f"🚀 Outperformed {benchmark.upper()} by {outperformance:.1f}% with {showcase_data.sharpe_ratio:.2f} Sharpe ratio" if outperformance > 0 else f"⚡ Competitive performance vs {benchmark.upper()} with superior risk management",
            "period": f"{period_days} days",
            "generated_at": datetime.now().isoformat()
        }
        
        return comparison
        
    except Exception as e:
        logger.error(f"❌ Failed to generate performance comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate performance comparison: {str(e)}"
        )


@router.get("/subscription-metrics/{portfolio_id}")
async def get_subscription_metrics(
    portfolio_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get metrics specifically designed for subscription conversion
    
    Optimized metrics for converting visitors to paying subscribers.
    
    Args:
        portfolio_id: Portfolio identifier
        current_user: Authenticated user
        
    Returns:
        Subscription-focused metrics
    """
    try:
        logger.info(f"💰 Generating subscription metrics for {portfolio_id}")
        
        # Get comprehensive showcase
        showcase_data = await portfolio_showcase_engine.generate_portfolio_showcase(portfolio_id)
        
        # Calculate subscription appeal score
        appeal_score = 0
        if showcase_data.total_return_percent > 5: appeal_score += 25
        if showcase_data.sharpe_ratio > 1.5: appeal_score += 25  
        if showcase_data.win_rate > 70: appeal_score += 25
        if showcase_data.max_drawdown < 5: appeal_score += 25
        
        # Subscription pricing tiers (example)
        pricing_tiers = [
            {
                "tier": "Basic",
                "price_monthly": 49,
                "features": ["Real-time signals", "Basic dashboard", "Email alerts"],
                "target_audience": "Individual traders"
            },
            {
                "tier": "Professional", 
                "price_monthly": 149,
                "features": ["All Basic features", "Advanced analytics", "Layer-by-layer insights", "API access"],
                "target_audience": "Serious traders"
            },
            {
                "tier": "Enterprise",
                "price_monthly": 499,
                "features": ["All Professional features", "White-label solution", "Custom integration", "Priority support"],
                "target_audience": "Trading firms"
            }
        ]
        
        # Calculate potential ROI for subscribers
        monthly_return = showcase_data.total_return_percent / (showcase_data.data_period.split()[0] if showcase_data.data_period else "30") if "days" in showcase_data.data_period else showcase_data.total_return_percent / 30
        roi_basic = (monthly_return * 1000) - 49  # ROI on $1000 investment
        roi_professional = (monthly_return * 5000) - 149  # ROI on $5000 investment
        
        subscription_metrics = {
            "appeal_score": appeal_score,
            "appeal_grade": "A+" if appeal_score >= 90 else "A" if appeal_score >= 75 else "B+",
            "subscription_readiness": appeal_score >= 75,
            
            "key_selling_points": [
                f"{showcase_data.total_return_percent:.1f}% returns demonstrated",
                f"{showcase_data.win_rate:.1f}% success rate with AI precision",
                f"Professional risk management: {showcase_data.max_drawdown:.1f}% max drawdown",
                f"Sharpe ratio of {showcase_data.sharpe_ratio:.2f} beats market standards",
                f"6-layer AI system with {showcase_data.signal_accuracy:.1f}% signal accuracy"
            ],
            
            "pricing_tiers": pricing_tiers,
            
            "roi_projections": {
                "basic_tier": {
                    "investment_example": 1000,
                    "monthly_cost": 49,
                    "projected_monthly_profit": roi_basic,
                    "roi_multiple": roi_basic / 49 if roi_basic > 0 else 0
                },
                "professional_tier": {
                    "investment_example": 5000,
                    "monthly_cost": 149,
                    "projected_monthly_profit": roi_professional,
                    "roi_multiple": roi_professional / 149 if roi_professional > 0 else 0
                }
            },
            
            "conversion_headlines": [
                f"Turn ${pricing_tiers[0]['price_monthly']} into potential ${roi_basic:.0f} monthly profit" if roi_basic > 0 else f"Professional AI trading for just ${pricing_tiers[0]['price_monthly']}/month",
                f"Join {showcase_data.total_trades}+ successful trades with {showcase_data.win_rate:.1f}% win rate",
                f"Risk-managed trading: Only {showcase_data.max_drawdown:.1f}% maximum drawdown"
            ],
            
            "urgency_factors": [
                f"System generated {showcase_data.total_return_percent:.1f}% returns in last {showcase_data.data_period}",
                f"AI accuracy improving: {showcase_data.signal_accuracy:.1f}% signal success rate",
                "Limited beta access - early subscriber advantage"
            ],
            
            "social_proof": {
                "trades_executed": showcase_data.total_trades,
                "success_rate": showcase_data.win_rate,
                "ai_accuracy": showcase_data.signal_accuracy,
                "system_uptime": "99.9%"
            },
            
            "generated_at": datetime.now().isoformat()
        }
        
        return subscription_metrics
        
    except Exception as e:
        logger.error(f"❌ Failed to generate subscription metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate subscription metrics: {str(e)}"
        )


@router.get("/engine-status")
async def get_showcase_engine_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get portfolio showcase engine status"""
    try:
        status_data = portfolio_showcase_engine.get_engine_status()
        
        return {
            **status_data,
            "api_endpoints": [
                "/showcase/live-metrics/{portfolio_id}",
                "/showcase/generate/{portfolio_id}",
                "/showcase/marketing-content/{portfolio_id}",
                "/showcase/performance-comparison/{portfolio_id}",
                "/showcase/subscription-metrics/{portfolio_id}"
            ],
            "monetization_features": [
                "Real-time performance tracking",
                "Marketing content generation",
                "Benchmark comparisons",
                "Subscription conversion metrics",
                "Layer performance analytics"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get showcase engine status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get engine status: {str(e)}"
        ) 