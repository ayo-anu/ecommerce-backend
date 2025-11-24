"""
Fraud Detection Schemas - Request/Response models
Comprehensive transaction and risk assessment models
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """Risk classification levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FraudDecision(str, Enum):
    """Fraud decision types"""
    APPROVE = "approve"
    REVIEW = "review"
    DECLINE = "decline"


class DeviceInfo(BaseModel):
    """Device fingerprint information"""
    device_id: Optional[str] = None
    ip_address: str
    user_agent: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    device_type: Optional[str] = None  # mobile, desktop, tablet
    is_vpn: bool = False
    is_proxy: bool = False


class TransactionRequest(BaseModel):
    """Transaction data for fraud analysis"""
    transaction_id: str
    user_id: str
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD", max_length=3)
    merchant_id: Optional[str] = None
    merchant_category: Optional[str] = None
    
    # Payment details
    payment_method: str  # card, paypal, bank_transfer, etc.
    card_last4: Optional[str] = Field(None, max_length=4)
    card_type: Optional[str] = None  # visa, mastercard, amex, etc.
    billing_country: Optional[str] = None
    shipping_country: Optional[str] = None
    
    # Device and location
    device_info: DeviceInfo
    
    # Behavioral data
    time_on_site: Optional[int] = Field(None, description="Seconds on site")
    num_items: int = Field(default=1, ge=1)
    is_first_purchase: bool = False
    account_age_days: Optional[int] = Field(None, ge=0)
    
    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v > 1000000:  # 1 million limit
            raise ValueError('Transaction amount exceeds maximum limit')
        return v


class VelocityCheck(BaseModel):
    """Velocity metrics for fraud detection"""
    transactions_1h: int = 0
    transactions_24h: int = 0
    transactions_7d: int = 0
    amount_1h: float = 0.0
    amount_24h: float = 0.0
    amount_7d: float = 0.0
    unique_cards_24h: int = 0
    unique_ips_24h: int = 0
    failed_attempts_1h: int = 0


class RiskFactors(BaseModel):
    """Individual risk factors identified"""
    high_amount: bool = False
    unusual_location: bool = False
    vpn_or_proxy: bool = False
    velocity_exceeded: bool = False
    device_mismatch: bool = False
    suspicious_email: bool = False
    billing_shipping_mismatch: bool = False
    new_account: bool = False
    unusual_time: bool = False
    blacklisted_entity: bool = False


class RiskScore(BaseModel):
    """Detailed risk scoring breakdown"""
    overall_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    confidence: float = Field(..., ge=0, le=1)
    
    # Component scores
    amount_risk: float = Field(0.0, ge=0, le=100)
    velocity_risk: float = Field(0.0, ge=0, le=100)
    device_risk: float = Field(0.0, ge=0, le=100)
    behavior_risk: float = Field(0.0, ge=0, le=100)
    location_risk: float = Field(0.0, ge=0, le=100)
    
    # Anomaly detection
    is_anomaly: bool = False
    anomaly_score: float = Field(0.0, ge=-1, le=1)


class FraudAnalysisResponse(BaseModel):
    """Complete fraud analysis result"""
    transaction_id: str
    decision: FraudDecision
    risk_score: RiskScore
    risk_factors: RiskFactors
    velocity_check: VelocityCheck
    
    # Recommendations
    recommended_action: str
    review_reasons: List[str] = []
    
    # Processing metadata
    processing_time_ms: float
    model_version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BatchTransactionRequest(BaseModel):
    """Batch fraud check request"""
    transactions: List[TransactionRequest]
    return_details: bool = Field(default=True)


class BatchAnalysisResponse(BaseModel):
    """Batch fraud check response"""
    total_transactions: int
    approved: int
    declined: int
    review_required: int
    results: List[FraudAnalysisResponse]
    processing_time_ms: float


class HistoricalData(BaseModel):
    """Historical transaction data for model training"""
    transaction_id: str
    features: Dict[str, float]
    is_fraud: bool
    fraud_type: Optional[str] = None


class ModelTrainingRequest(BaseModel):
    """Request to train/retrain fraud detection model"""
    historical_data: List[HistoricalData]
    model_type: str = Field(default="isolation_forest")
    contamination: float = Field(default=0.1, ge=0, le=0.5)


class ModelMetrics(BaseModel):
    """Model performance metrics"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    false_positive_rate: float
    false_negative_rate: float


class FraudStatsResponse(BaseModel):
    """Fraud detection statistics"""
    total_transactions_analyzed: int
    fraud_detected: int
    fraud_rate: float
    avg_risk_score: float
    model_accuracy: float
    is_model_trained: bool
    last_trained: Optional[datetime] = None


class RuleTrigger(BaseModel):
    """Rule-based fraud trigger"""
    rule_id: str
    rule_name: str
    severity: RiskLevel
    triggered: bool
    details: Optional[str] = None
