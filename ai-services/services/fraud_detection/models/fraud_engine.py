"""
Fraud Detection Engine - Main orchestrator
Combines ML anomaly detection with rule-based system
"""
import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from .anomaly_detector import AnomalyDetector
from .rule_engine import RuleEngine
from ..schemas.fraud import (
    RiskLevel, FraudDecision, RiskScore, RiskFactors, VelocityCheck
)

logger = logging.getLogger(__name__)


class FraudDetectionEngine:
    """
    Hybrid fraud detection system
    
    Combines:
    - ML-based anomaly detection (Isolation Forest)
    - Rule-based expert system
    - Velocity checks
    - Risk scoring
    """
    
    def __init__(self):
        self.anomaly_detector = AnomalyDetector(contamination=0.1)
        self.rule_engine = RuleEngine()
        
        # Transaction history (in production, use Redis/database)
        self.transaction_history = defaultdict(list)
        self.user_profiles = {}
        
        # Statistics
        self.stats = {
            'total_analyzed': 0,
            'fraud_detected': 0,
            'approved': 0,
            'declined': 0,
            'review_required': 0
        }
        
        logger.info("Fraud Detection Engine initialized")

    
    def analyze_transaction(
        self,
        transaction: Dict,
        user_history: Dict = None
    ) -> Dict:
        """
        Complete fraud analysis of a transaction
        
        Args:
            transaction: Transaction data
            user_history: Optional historical user data
            
        Returns:
            Comprehensive fraud analysis result
        """
        start_time = datetime.utcnow()
        
        # Extract transaction details
        user_id = transaction.get('user_id')
        amount = transaction.get('amount', 0)
        device_info = transaction.get('device_info', {})
        
        # Get or create user profile
        if user_history is None:
            user_history = self.user_profiles.get(user_id, {
                'usual_countries': ['US'],
                'known_devices': [],
                'avg_transaction': 100.0,
                'total_transactions': 0
            })
        
        # Calculate velocity metrics
        velocity_check = self._calculate_velocity(user_id, transaction)
        
        # Run anomaly detection
        is_anomaly, anomaly_score, ml_confidence = self.anomaly_detector.predict(transaction)
        
        # Run rule-based checks
        rule_score, triggered_rules, rule_reasons = self.rule_engine.evaluate_transaction(
            transaction,
            velocity_check.__dict__,
            user_history
        )
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(
            transaction,
            velocity_check,
            triggered_rules,
            is_anomaly
        )
        
        # Calculate component scores
        amount_risk = self._calculate_amount_risk(amount, user_history)
        velocity_risk = self._calculate_velocity_risk(velocity_check)
        device_risk = self._calculate_device_risk(device_info)
        behavior_risk = self._calculate_behavior_risk(transaction)
        location_risk = self._calculate_location_risk(transaction, user_history)
        
        # Combine scores (weighted average)
        weights = {
            'rule': 0.35,
            'anomaly': 0.25,
            'amount': 0.15,
            'velocity': 0.15,
            'device': 0.05,
            'behavior': 0.03,
            'location': 0.02
        }
        
        overall_score = (
            rule_score * weights['rule'] +
            anomaly_score * 100 * weights['anomaly'] +
            amount_risk * weights['amount'] +
            velocity_risk * weights['velocity'] +
            device_risk * weights['device'] +
            behavior_risk * weights['behavior'] +
            location_risk * weights['location']
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)
        
        # Make decision
        decision, recommended_action = self._make_decision(
            overall_score,
            risk_level,
            risk_factors
        )
        
        # Create risk score object
        risk_score = RiskScore(
            overall_score=round(overall_score, 2),
            risk_level=risk_level,
            confidence=round(ml_confidence, 3),
            amount_risk=round(amount_risk, 2),
            velocity_risk=round(velocity_risk, 2),
            device_risk=round(device_risk, 2),
            behavior_risk=round(behavior_risk, 2),
            location_risk=round(location_risk, 2),
            is_anomaly=is_anomaly,
            anomaly_score=round(anomaly_score, 3)
        )
        
        # Update statistics
        self.stats['total_analyzed'] += 1
        if decision == FraudDecision.DECLINE:
            self.stats['fraud_detected'] += 1
            self.stats['declined'] += 1
        elif decision == FraudDecision.APPROVE:
            self.stats['approved'] += 1
        else:
            self.stats['review_required'] += 1
        
        # Store transaction
        self._store_transaction(user_id, transaction, decision)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'decision': decision,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'velocity_check': velocity_check,
            'recommended_action': recommended_action,
            'review_reasons': rule_reasons if decision == FraudDecision.REVIEW else [],
            'processing_time_ms': round(processing_time, 2)
        }
    
    def _calculate_velocity(self, user_id: str, transaction: Dict) -> VelocityCheck:
        """Calculate transaction velocity metrics"""
        now = datetime.utcnow()
        history = self.transaction_history.get(user_id, [])
        
        # Helper function to parse timestamp
        def parse_timestamp(t):
            ts = t.get('timestamp')
            if ts is None:
                return now
            if isinstance(ts, str):
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if isinstance(ts, datetime):
                return ts
            return now
        
        # Count transactions in different time windows
        transactions_1h = sum(
            1 for t in history
            if now - parse_timestamp(t) < timedelta(hours=1)
        )
        transactions_24h = sum(
            1 for t in history
            if now - parse_timestamp(t) < timedelta(hours=24)
        )
        transactions_7d = sum(
            1 for t in history
            if now - parse_timestamp(t) < timedelta(days=7)
        )
        
        # Calculate amounts
        amount_1h = sum(
            t.get('amount', 0) for t in history
            if now - parse_timestamp(t) < timedelta(hours=1)
        )
        amount_24h = sum(
            t.get('amount', 0) for t in history
            if now - parse_timestamp(t) < timedelta(hours=24)
        )
        amount_7d = sum(
            t.get('amount', 0) for t in history
            if now - parse_timestamp(t) < timedelta(days=7)
        )
        
        # Count unique cards and IPs in 24h
        recent_24h = [t for t in history if now - parse_timestamp(t) < timedelta(hours=24)]
        unique_cards = len(set(t.get('card_last4', '') for t in recent_24h))
        unique_ips = len(set(t.get('device_info', {}).get('ip_address', '') for t in recent_24h))
        
        # Count failed attempts
        failed_1h = sum(
            1 for t in history
            if now - parse_timestamp(t) < timedelta(hours=1) and t.get('status') == 'failed'
        )
        
        return VelocityCheck(
            transactions_1h=transactions_1h,
            transactions_24h=transactions_24h,
            transactions_7d=transactions_7d,
            amount_1h=round(amount_1h, 2),
            amount_24h=round(amount_24h, 2),
            amount_7d=round(amount_7d, 2),
            unique_cards_24h=unique_cards,
            unique_ips_24h=unique_ips,
            failed_attempts_1h=failed_1h
        )
    
    def _identify_risk_factors(
        self,
        transaction: Dict,
        velocity: VelocityCheck,
        rules: List[Dict],
        is_anomaly: bool
    ) -> RiskFactors:
        """Identify specific risk factors"""
        amount = transaction.get('amount', 0)
        device = transaction.get('device_info', {})
        
        return RiskFactors(
            high_amount=amount > 2000,
            unusual_location='unusual country' in str(rules).lower(),
            vpn_or_proxy=device.get('is_vpn', False) or device.get('is_proxy', False),
            velocity_exceeded=velocity.transactions_1h > 5 or velocity.amount_1h > 10000,
            device_mismatch='device mismatch' in str(rules).lower(),
            suspicious_email=False,  # Would need email validation
            billing_shipping_mismatch=transaction.get('billing_country') != transaction.get('shipping_country'),
            new_account=(transaction.get('account_age_days') or 0) < 7,
            unusual_time=datetime.utcnow().hour < 6 or datetime.utcnow().hour > 23,
            blacklisted_entity=False  # Would need blacklist check
        )
    
    def _calculate_amount_risk(self, amount: float, user_history: Dict) -> float:
        """Calculate risk based on transaction amount"""
        avg_transaction = user_history.get('avg_transaction', 100.0)
        
        # Risk increases with deviation from average
        if avg_transaction > 0:
            ratio = amount / avg_transaction
            if ratio > 10:
                return 100.0
            elif ratio > 5:
                return 80.0
            elif ratio > 3:
                return 60.0
            elif ratio > 2:
                return 40.0
        
        # Absolute thresholds
        if amount > 5000:
            return 90.0
        elif amount > 2000:
            return 60.0
        elif amount > 1000:
            return 30.0
        
        return 10.0
    
    def _calculate_velocity_risk(self, velocity: VelocityCheck) -> float:
        """Calculate risk based on transaction velocity"""
        risk = 0.0
        
        if velocity.transactions_1h > 5:
            risk += 40.0
        elif velocity.transactions_1h > 3:
            risk += 20.0
        
        if velocity.amount_1h > 10000:
            risk += 30.0
        elif velocity.amount_1h > 5000:
            risk += 15.0
        
        if velocity.unique_cards_24h > 3:
            risk += 20.0
        
        if velocity.failed_attempts_1h > 2:
            risk += 30.0
        
        return min(100.0, risk)
    
    def _calculate_device_risk(self, device: Dict) -> float:
        """Calculate risk based on device characteristics"""
        risk = 0.0
        
        if device.get('is_vpn'):
            risk += 40.0
        if device.get('is_proxy'):
            risk += 40.0
        
        return min(100.0, risk)
    
    def _calculate_behavior_risk(self, transaction: Dict) -> float:
        """Calculate risk based on user behavior patterns"""
        risk_score = 0.0
        
        # Time on site analysis (with null safety)
        time_on_site = transaction.get('time_on_site')
        if time_on_site is not None:
            try:
                time_on_site = int(time_on_site)
                if time_on_site < 30:
                    risk_score += 5.0
                elif time_on_site < 60:
                    risk_score += 2.0
            except (ValueError, TypeError):
                logger.warning(f"Invalid time_on_site value: {time_on_site}")
        
        # First purchase analysis
        if transaction.get('is_first_purchase', False):
            risk_score += 15.0
        
        # Account age analysis
        account_age_days = transaction.get('account_age_days')
        if account_age_days is not None:
            try:
                account_age_days = int(account_age_days)
                if account_age_days < 7:
                    risk_score += 10.0
                elif account_age_days < 30:
                    risk_score += 5.0
            except (ValueError, TypeError):
                logger.warning(f"Invalid account_age_days value: {account_age_days}")
        else:
            # Unknown account age - moderate risk
            risk_score += 8.0
        
        # Number of items analysis
        num_items = transaction.get('num_items', 1)
        try:
            num_items = int(num_items)
            if num_items > 10:
                risk_score += 5.0
            elif num_items > 5:
                risk_score += 2.0
        except (ValueError, TypeError):
            logger.warning(f"Invalid num_items value: {num_items}")
        
        return min(100.0, risk_score)
    
    
    def _calculate_location_risk(self, transaction: Dict, user_history: Dict) -> float:
        """Calculate risk based on location"""
        risk = 0.0
        
        billing = transaction.get('billing_country', 'US')
        shipping = transaction.get('shipping_country', 'US')
        usual = user_history.get('usual_countries', ['US'])
        
        if billing not in usual:
            risk += 30.0
        
        if billing != shipping:
            risk += 20.0
        
        return min(100.0, risk)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level from score"""
        if score >= 75:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _make_decision(
        self,
        score: float,
        risk_level: RiskLevel,
        risk_factors: RiskFactors
    ) -> Tuple[FraudDecision, str]:
        """Make final fraud decision"""
        
        # Auto-decline critical risk
        if score >= 80:
            return FraudDecision.DECLINE, "Automatic decline - critical fraud risk"
        
        # Auto-approve low risk
        if score < 25:
            return FraudDecision.APPROVE, "Automatic approval - low fraud risk"
        
        # Review medium to high risk
        if score >= 50:
            return FraudDecision.REVIEW, "Manual review required - high fraud indicators"
        else:
            return FraudDecision.REVIEW, "Manual review recommended - moderate risk"
    
    def _store_transaction(self, user_id: str, transaction: Dict, decision: FraudDecision):
        """Store transaction in history"""
        record = {
            **transaction,
            'timestamp': datetime.utcnow(),
            'decision': decision,
            'status': 'completed' if decision == FraudDecision.APPROVE else 'flagged'
        }
        
        self.transaction_history[user_id].append(record)
        
        # Keep only recent history (last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        self.transaction_history[user_id] = [
            t for t in self.transaction_history[user_id]
            if t['timestamp'] > cutoff
        ]
    
    def train_model(self, transactions: List[Dict], labels: List[bool] = None):
        """Train the anomaly detection model"""
        return self.anomaly_detector.train(transactions, labels)
    
    def get_statistics(self) -> Dict:
        """Get fraud detection statistics"""
        total = self.stats['total_analyzed']
        fraud_rate = (self.stats['fraud_detected'] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            'fraud_rate': round(fraud_rate, 2),
            'is_model_trained': self.anomaly_detector.is_trained
        }