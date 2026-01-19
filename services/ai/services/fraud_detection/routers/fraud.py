"""
Fraud Detection API Router - Endpoints for transaction analysis
Real-time fraud scoring and decision making
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from typing import List
import logging
from datetime import datetime
from collections import defaultdict
from ..schemas.fraud import (
    TransactionRequest,
    FraudAnalysisResponse,
    BatchTransactionRequest,
    BatchAnalysisResponse,
    ModelTrainingRequest,
    FraudStatsResponse,
    RiskLevel,
    FraudDecision
)
from ..models.fraud_engine import FraudDetectionEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fraud", tags=["fraud_detection"])

# Global fraud detection engine
fraud_engine = FraudDetectionEngine()


@router.post("/analyze", response_model=FraudAnalysisResponse)
async def analyze_transaction(request: TransactionRequest):
    """
    Analyze a single transaction for fraud
    
    Returns real-time risk assessment and decision
    """
    try:
        # Convert to dict for processing
        transaction_data = request.dict()
        
        # Analyze transaction
        result = fraud_engine.analyze_transaction(transaction_data)
        
        # Build response
        response = FraudAnalysisResponse(
            transaction_id=request.transaction_id,
            decision=result['decision'],
            risk_score=result['risk_score'],
            risk_factors=result['risk_factors'],
            velocity_check=result['velocity_check'],
            recommended_action=result['recommended_action'],
            review_reasons=result['review_reasons'],
            processing_time_ms=result['processing_time_ms']
        )
        
        logger.info(
            f"Transaction {request.transaction_id}: "
            f"Decision={result['decision']}, "
            f"Score={result['risk_score'].overall_score:.2f}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Fraud analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def analyze_batch(request: BatchTransactionRequest):
    """
    Analyze multiple transactions in batch
    
    More efficient for bulk processing
    """
    try:
        start_time = datetime.utcnow()
        
        results = []
        approved = 0
        declined = 0
        review_required = 0
        
        for transaction_req in request.transactions:
            transaction_data = transaction_req.dict()
            
            # Analyze each transaction
            result = fraud_engine.analyze_transaction(transaction_data)
            
            # Count decisions
            if result['decision'] == FraudDecision.APPROVE:
                approved += 1
            elif result['decision'] == FraudDecision.DECLINE:
                declined += 1
            else:
                review_required += 1
            
            # Add to results if details requested
            if request.return_details:
                results.append(FraudAnalysisResponse(
                    transaction_id=transaction_req.transaction_id,
                    decision=result['decision'],
                    risk_score=result['risk_score'],
                    risk_factors=result['risk_factors'],
                    velocity_check=result['velocity_check'],
                    recommended_action=result['recommended_action'],
                    review_reasons=result['review_reasons'],
                    processing_time_ms=result['processing_time_ms']
                ))
        
        # Calculate total processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.info(
            f"Batch analysis: {len(request.transactions)} transactions, "
            f"{approved} approved, {declined} declined, {review_required} review"
        )
        
        return BatchAnalysisResponse(
            total_transactions=len(request.transactions),
            approved=approved,
            declined=declined,
            review_required=review_required,
            results=results,
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Batch analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train", status_code=200)
async def train_model(request: ModelTrainingRequest):
    """
    Train/retrain the fraud detection model
    
    Uses historical transaction data with labels
    """
    try:
        logger.info(f"Training fraud model with {len(request.historical_data)} samples")
        
        # Extract transactions and labels
        transactions = []
        labels = []
        
        for data in request.historical_data:
            transactions.append(data.features)
            labels.append(data.is_fraud)
        
        # Train model
        training_stats = fraud_engine.train_model(transactions, labels)
        
        logger.info(f"Model training complete: {training_stats}")
        
        return {
            "status": "success",
            "message": f"Model trained on {len(transactions)} transactions",
            "training_stats": training_stats,
            "model_type": request.model_type
        }
        
    except Exception as e:
        logger.error(f"Model training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=FraudStatsResponse)
async def get_fraud_stats():
    """
    Get fraud detection statistics
    
    Returns performance metrics and detection rates
    """
    try:
        stats = fraud_engine.get_statistics()
        
        return FraudStatsResponse(
            total_transactions_analyzed=stats['total_analyzed'],
            fraud_detected=stats['fraud_detected'],
            fraud_rate=stats['fraud_rate'],
            avg_risk_score=0.0,  # Would calculate from stored data
            model_accuracy=0.95,  # Would calculate from validation
            is_model_trained=stats['is_model_trained'],
            last_trained=None  # Would track training timestamp
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-levels")
async def get_risk_levels():
    """
    Get information about risk level thresholds
    
    Useful for understanding scoring system
    """
    return {
        "risk_levels": {
            "low": {
                "score_range": "0-29",
                "description": "Low fraud risk - auto-approve",
                "action": "approve"
            },
            "medium": {
                "score_range": "30-49",
                "description": "Medium fraud risk - review recommended",
                "action": "review"
            },
            "high": {
                "score_range": "50-74",
                "description": "High fraud risk - manual review required",
                "action": "review"
            },
            "critical": {
                "score_range": "75-100",
                "description": "Critical fraud risk - auto-decline",
                "action": "decline"
            }
        },
        "decision_thresholds": {
            "auto_approve": "< 25",
            "review": "25-79",
            "auto_decline": ">= 80"
        }
    }


@router.get("/rules")
async def get_fraud_rules():
    """
    Get list of active fraud detection rules
    
    Shows all rules and their configurations
    """
    try:
        rules_info = []
        
        for rule in fraud_engine.rule_engine.rules:
            rules_info.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "severity": rule.severity,
                "weight": rule.weight,
                "description": rule.__class__.__doc__ or "No description"
            })
        
        return {
            "total_rules": len(rules_info),
            "rules": rules_info
        }
        
    except Exception as e:
        logger.error(f"Rules error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate")
async def simulate_fraud_check(
    amount: float,
    user_id: str = "test_user",
    is_vpn: bool = False,
    is_new_account: bool = False
):
    """
    Simulate a fraud check with custom parameters
    
    Useful for testing different scenarios
    """
    try:
        from datetime import datetime
        from ..schemas.fraud import DeviceInfo
        
        # Create test transaction
        transaction = TransactionRequest(
            transaction_id=f"sim_{datetime.utcnow().timestamp()}",
            user_id=user_id,
            amount=amount,
            currency="USD",
            payment_method="card",
            device_info=DeviceInfo(
                ip_address="192.168.1.1",
                is_vpn=is_vpn,
                is_proxy=False
            ),
            is_first_purchase=is_new_account,
            account_age_days=1 if is_new_account else 365
        )
        
        # Analyze
        result = fraud_engine.analyze_transaction(transaction.dict())
        
        return {
            "simulation": {
                "amount": amount,
                "is_vpn": is_vpn,
                "is_new_account": is_new_account
            },
            "decision": result['decision'],
            "risk_score": result['risk_score'].overall_score,
            "risk_level": result['risk_score'].risk_level,
            "explanation": result['recommended_action']
        }
        
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "fraud_detection",
        "model_trained": fraud_engine.anomaly_detector.is_trained,
        "rules_active": len(fraud_engine.rule_engine.rules)
    }

@router.post("/initialize")
async def initialize_fraud_engine(data: List[Dict]):
    """
    Load bulk historical transactions into FraudDetectionEngine.
    Accepts a JSON array: [ {txn}, {txn}, ... ]
    """

    engine = fraud_engine

    total = len(data)
    loaded = 0
    parsing_errors = 0
    duplicate_ids = 0

    # Reset history before loading
    engine.transaction_history = defaultdict(list)

    for idx, txn in enumerate(data):
        try:
            user_id = txn.get("user_id")
            if user_id is None:
                parsing_errors += 1
                continue

            # Add timestamp if missing
            if "timestamp" not in txn:
                txn["timestamp"] = datetime.utcnow()

            # Store inside defaultdict list for THIS user
            engine.transaction_history[user_id].append(txn)
            loaded += 1

        except Exception as e:
            parsing_errors += 1
            print(f"Load error at row {idx}: {e}")

    # Prepare response
    success_rate = (loaded / total * 100) if total > 0 else 0

    return {
        "status": "success" if loaded > 0 else "failed",
        "message": f"Loaded {loaded} of {total} transactions ({success_rate:.1f}% success rate)",
        "metrics": {
            "total_received": total,
            "successfully_loaded": loaded,
            "parsing_errors": parsing_errors,
            "duplicate_ids": duplicate_ids,
            "success_rate_percent": round(success_rate, 2),
        },
        "model_status": {
            "is_initialized": loaded > 0,
            "total_history_size": sum(len(v) for v in engine.transaction_history.values()),
            "ready_for_analysis": loaded > 0,
        }
    }