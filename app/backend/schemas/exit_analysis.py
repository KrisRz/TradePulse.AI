"""
Exit Analysis Data Models - TradePulse.AI Enterprise
===================================================

Data models and schemas for intelligent exit analysis system.
Defines structured data for exit decisions, layer analysis, and audit trails.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class ExitReason(str, Enum):
    """Enumeration of exit reasons"""
    MANUAL = "manual"
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    CONSENSUS_EXIT = "consensus_exit"
    EMERGENCY_EXIT = "emergency_exit"
    TIME_LIMIT = "time_limit"
    REGIME_CHANGE = "regime_change"
    REVERSAL_DETECTED = "reversal_detected"
    LOW_CONFIDENCE = "low_confidence"
    TECHNICAL_SIGNAL = "technical_signal"
    HOLD_RECOMMENDED = "hold_recommended"
    INSUFFICIENT_DATA = "insufficient_data"
    ANALYSIS_FAILED = "analysis_failed"
    DECISION_ERROR = "decision_error"


class ConfidenceLevel(str, Enum):
    """Confidence levels for analysis"""
    VERY_LOW = "very_low"      # 0.0 - 0.2
    LOW = "low"                # 0.2 - 0.4
    MEDIUM = "medium"          # 0.4 - 0.6
    HIGH = "high"              # 0.6 - 0.8
    VERY_HIGH = "very_high"    # 0.8 - 1.0


class MarketRegime(str, Enum):
    """Market regime classifications"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS_MARKET = "sideways_market"
    VOLATILE_MARKET = "volatile_market"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    CONSOLIDATING = "consolidating"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    UNKNOWN = "unknown"


class LayerRecommendation(str, Enum):
    """Layer analysis recommendations"""
    EXIT = "exit"
    HOLD = "hold"
    UNCERTAIN = "uncertain"


class LayerAnalysis(BaseModel):
    """Individual layer analysis result"""
    layer_id: int = Field(..., ge=1, le=6, description="Layer number (1-6)")
    layer_name: str = Field(..., description="Human-readable layer name")
    recommendation: LayerRecommendation = Field(..., description="Layer recommendation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    reasoning: str = Field(..., description="Detailed reasoning for recommendation")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Layer-specific metrics")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    def get_confidence_level(self) -> ConfidenceLevel:
        """Convert numerical confidence to confidence level enum"""
        if self.confidence < 0.2:
            return ConfidenceLevel.VERY_LOW
        elif self.confidence < 0.4:
            return ConfidenceLevel.LOW
        elif self.confidence < 0.6:
            return ConfidenceLevel.MEDIUM
        elif self.confidence < 0.8:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH


class ExitDecision(BaseModel):
    """Final exit decision from the intelligent engine"""
    should_exit: bool = Field(..., description="Whether position should be closed")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall decision confidence")
    primary_reason: ExitReason = Field(..., description="Primary reason for decision")
    reasoning: str = Field(..., description="Detailed reasoning for decision")
    consensus_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Layer consensus score")
    layer_votes: Optional[Dict[str, int]] = Field(None, description="Layer voting breakdown")
    failed_layers: List[int] = Field(default_factory=list, description="Layers that failed analysis")
    emergency_conditions: Optional[Dict[str, Any]] = Field(None, description="Emergency condition details")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    def get_confidence_level(self) -> ConfidenceLevel:
        """Convert numerical confidence to confidence level enum"""
        if self.confidence < 0.2:
            return ConfidenceLevel.VERY_LOW
        elif self.confidence < 0.4:
            return ConfidenceLevel.LOW
        elif self.confidence < 0.6:
            return ConfidenceLevel.MEDIUM
        elif self.confidence < 0.8:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH


class ExitAnalysisResult(BaseModel):
    """Complete exit analysis result"""
    position_id: Optional[str] = Field(None, description="Position identifier")
    symbol: str = Field(..., description="Trading symbol")
    analysis_timestamp: datetime = Field(..., description="When analysis was performed")
    analysis_time_ms: float = Field(..., description="Time taken for analysis in milliseconds")
    exit_decision: ExitDecision = Field(..., description="Final exit decision")
    layer_analyses: List[LayerAnalysis] = Field(default_factory=list, description="Individual layer results")
    failed_layers: List[int] = Field(default_factory=list, description="Layers that failed")
    exit_reason: str = Field(..., description="Original exit request reason")
    engine_status: str = Field(..., description="Exit engine status during analysis")
    force_override: bool = Field(default=False, description="Whether analysis was force overridden")
    error_message: Optional[str] = Field(None, description="Error message if analysis failed")
    
    def was_blind_close_prevented(self) -> bool:
        """Check if this analysis prevented a blind close"""
        return not self.exit_decision.should_exit and self.exit_reason == "manual"
    
    def get_successful_layers(self) -> List[LayerAnalysis]:
        """Get only successful layer analyses"""
        return [analysis for analysis in self.layer_analyses if analysis.layer_id not in self.failed_layers]
    
    def get_average_confidence(self) -> float:
        """Calculate average confidence across successful layers"""
        successful_layers = self.get_successful_layers()
        if not successful_layers:
            return 0.0
        return sum(layer.confidence for layer in successful_layers) / len(successful_layers)


class PositionExitHistory(BaseModel):
    """Historical exit analysis for a position"""
    position_id: str = Field(..., description="Position identifier")
    symbol: str = Field(..., description="Trading symbol")
    exit_analyses: List[ExitAnalysisResult] = Field(default_factory=list, description="All exit analyses")
    final_exit: Optional[ExitAnalysisResult] = Field(None, description="Final successful exit analysis")
    blind_closes_prevented: int = Field(default=0, description="Number of blind closes prevented")
    
    def add_analysis(self, analysis: ExitAnalysisResult) -> None:
        """Add new exit analysis to history"""
        self.exit_analyses.append(analysis)
        
        if analysis.was_blind_close_prevented():
            self.blind_closes_prevented += 1
        
        if analysis.exit_decision.should_exit:
            self.final_exit = analysis
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary statistics for this position's exit analyses"""
        if not self.exit_analyses:
            return {
                'total_analyses': 0,
                'blind_closes_prevented': 0,
                'average_confidence': 0.0,
                'most_common_reason': None
            }
        
        total_analyses = len(self.exit_analyses)
        avg_confidence = sum(
            analysis.exit_decision.confidence for analysis in self.exit_analyses
        ) / total_analyses
        
        # Find most common exit reason
        reasons = [analysis.exit_decision.primary_reason for analysis in self.exit_analyses]
        most_common_reason = max(set(reasons), key=reasons.count) if reasons else None
        
        return {
            'total_analyses': total_analyses,
            'blind_closes_prevented': self.blind_closes_prevented,
            'average_confidence': avg_confidence,
            'most_common_reason': most_common_reason,
            'final_exit_successful': self.final_exit is not None,
            'analysis_time_avg_ms': sum(a.analysis_time_ms for a in self.exit_analyses) / total_analyses
        }


class ExitEngineMetrics(BaseModel):
    """Comprehensive exit engine performance metrics"""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")
    total_analyses: int = Field(default=0, description="Total exit analyses performed")
    blind_closes_prevented: int = Field(default=0, description="Total blind closes prevented")
    successful_exits: int = Field(default=0, description="Total successful exits")
    failed_analyses: int = Field(default=0, description="Total failed analyses")
    average_analysis_time_ms: float = Field(default=0.0, description="Average analysis time")
    average_confidence: float = Field(default=0.0, description="Average decision confidence")
    layer_health: Dict[str, str] = Field(default_factory=dict, description="Individual layer health status")
    prevention_rate: float = Field(default=0.0, description="Blind close prevention rate")
    
    def update_from_analysis(self, analysis: ExitAnalysisResult) -> None:
        """Update metrics from new analysis result"""
        self.total_analyses += 1
        
        if analysis.was_blind_close_prevented():
            self.blind_closes_prevented += 1
        
        if analysis.exit_decision.should_exit:
            self.successful_exits += 1
        
        if analysis.error_message:
            self.failed_analyses += 1
        
        # Update averages
        self.average_analysis_time_ms = (
            (self.average_analysis_time_ms * (self.total_analyses - 1) + analysis.analysis_time_ms)
            / self.total_analyses
        )
        
        self.average_confidence = (
            (self.average_confidence * (self.total_analyses - 1) + analysis.exit_decision.confidence)
            / self.total_analyses
        )
        
        self.prevention_rate = self.blind_closes_prevented / max(self.total_analyses, 1)


class LayerPerformanceMetrics(BaseModel):
    """Performance metrics for individual layers"""
    layer_id: int = Field(..., ge=1, le=6, description="Layer number")
    layer_name: str = Field(..., description="Layer name")
    total_analyses: int = Field(default=0, description="Total analyses performed")
    successful_analyses: int = Field(default=0, description="Successful analyses")
    failed_analyses: int = Field(default=0, description="Failed analyses")
    average_confidence: float = Field(default=0.0, description="Average confidence score")
    average_processing_time_ms: float = Field(default=0.0, description="Average processing time")
    success_rate: float = Field(default=0.0, description="Analysis success rate")
    
    def update_from_layer_analysis(self, analysis: LayerAnalysis) -> None:
        """Update metrics from layer analysis"""
        self.total_analyses += 1
        self.successful_analyses += 1
        
        # Update averages
        self.average_confidence = (
            (self.average_confidence * (self.total_analyses - 1) + analysis.confidence)
            / self.total_analyses
        )
        
        self.average_processing_time_ms = (
            (self.average_processing_time_ms * (self.total_analyses - 1) + analysis.processing_time_ms)
            / self.total_analyses
        )
        
        self.success_rate = self.successful_analyses / max(self.total_analyses, 1)
    
    def record_failure(self) -> None:
        """Record a failed analysis"""
        self.total_analyses += 1
        self.failed_analyses += 1
        self.success_rate = self.successful_analyses / max(self.total_analyses, 1)


# Request/Response models for API
class ExitAnalysisRequest(BaseModel):
    """Request model for exit analysis"""
    position_id: str = Field(..., description="Position to analyze")
    exit_reason: str = Field(default="manual", description="Reason for exit request")
    force_override: bool = Field(default=False, description="Force override analysis")


class ExitAnalysisResponse(BaseModel):
    """Response model for exit analysis"""
    success: bool = Field(..., description="Whether analysis was successful")
    result: Optional[ExitAnalysisResult] = Field(None, description="Analysis result")
    error: Optional[str] = Field(None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class EngineHealthResponse(BaseModel):
    """Response model for engine health check"""
    status: str = Field(..., description="Engine status")
    layer_health: Dict[str, str] = Field(..., description="Individual layer health")
    statistics: Dict[str, Any] = Field(..., description="Engine statistics")
    timestamp: datetime = Field(..., description="Health check timestamp")


class EngineMetricsResponse(BaseModel):
    """Response model for engine metrics"""
    metrics: ExitEngineMetrics = Field(..., description="Engine performance metrics")
    layer_metrics: List[LayerPerformanceMetrics] = Field(default_factory=list, description="Layer performance metrics")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp") 