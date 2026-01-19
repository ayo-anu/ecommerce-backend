"""
Rule-Based Fraud Engine - Expert rules for fraud detection
Implements business logic and heuristic fraud patterns
"""
import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FraudRule:
    """Base class for fraud detection rules"""
    
    def __init__(self, rule_id: str, name: str, severity: str, weight: float):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity  # low, medium, high, critical
        self.weight = weight
        
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        """
        Evaluate rule against transaction
        
        Returns:
            (triggered, reason)
        """
        raise NotImplementedError


class RuleEngine:
    """
    Expert system for rule-based fraud detection
    
    Combines multiple rules with different severities and weights
    """
    
    def __init__(self):
        self.rules = []
        self._initialize_rules()
        
    def _initialize_rules(self):
        """Initialize all fraud detection rules"""
        
        # High amount rules
        self.rules.append(
            HighAmountRule("R001", "High Transaction Amount", "high", 25.0)
        )
        self.rules.append(
            VelocityExceededRule("R002", "Transaction Velocity Exceeded", "critical", 35.0)
        )
        
        # Location rules
        self.rules.append(
            UnusualLocationRule("R003", "Unusual Location", "medium", 15.0)
        )
        self.rules.append(
            LocationMismatchRule("R004", "Billing/Shipping Mismatch", "medium", 12.0)
        )
        
        # Device rules
        self.rules.append(
            VPNProxyRule("R005", "VPN/Proxy Detected", "high", 20.0)
        )
        self.rules.append(
            DeviceMismatchRule("R006", "Device Mismatch", "medium", 10.0)
        )
        
        # Behavioral rules
        self.rules.append(
            RushPurchaseRule("R007", "Rush Purchase (Low Time on Site)", "medium", 8.0)
        )
        self.rules.append(
            NewAccountHighValueRule("R008", "New Account High Value", "high", 18.0)
        )
        self.rules.append(
            UnusualTimeRule("R009", "Unusual Transaction Time", "low", 5.0)
        )
        
        # Card rules
        self.rules.append(
            MultipleFailedAttemptsRule("R010", "Multiple Failed Attempts", "critical", 30.0)
        )
        
        logger.info(f"Initialized {len(self.rules)} fraud detection rules")
    
    def evaluate_transaction(
        self,
        transaction: Dict,
        velocity_data: Dict,
        user_history: Dict
    ) -> Tuple[float, List[Dict], List[str]]:
        """
        Evaluate all rules against transaction
        
        Args:
            transaction: Transaction data
            velocity_data: Velocity metrics
            user_history: Historical user data
            
        Returns:
            (total_risk_score, triggered_rules, reasons)
        """
        context = {
            'velocity': velocity_data,
            'history': user_history
        }
        
        triggered_rules = []
        reasons = []
        total_score = 0.0
        
        for rule in self.rules:
            try:
                triggered, reason = rule.evaluate(transaction, context)
                
                if triggered:
                    triggered_rules.append({
                        'rule_id': rule.rule_id,
                        'rule_name': rule.name,
                        'severity': rule.severity,
                        'weight': rule.weight,
                        'details': reason
                    })
                    reasons.append(reason)
                    total_score += rule.weight
                    
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
        
        # Normalize score to 0-100
        max_possible_score = sum(r.weight for r in self.rules)
        normalized_score = min(100.0, (total_score / max_possible_score) * 100)
        
        return normalized_score, triggered_rules, reasons


# Individual Rule Implementations

class HighAmountRule(FraudRule):
    """Flag high-value transactions"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        amount = transaction.get('amount', 0)
        
        # Thresholds by user tier
        account_age_days = transaction.get('account_age_days', 0)
        
        if account_age_days < 7:
            threshold = 500
        elif account_age_days < 30:
            threshold = 1500
        else:
            threshold = 5000
        
        if amount > threshold:
            return True, f"Transaction amount ${amount:.2f} exceeds threshold ${threshold}"
        
        return False, ""


class VelocityExceededRule(FraudRule):
    """Check transaction velocity limits"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        velocity = context.get('velocity', {})
        
        # Check multiple velocity metrics
        triggers = []
        
        if velocity.get('transactions_1h', 0) > 5:
            triggers.append("5+ transactions in 1 hour")
        
        if velocity.get('transactions_24h', 0) > 20:
            triggers.append("20+ transactions in 24 hours")
        
        if velocity.get('amount_1h', 0) > 10000:
            triggers.append("$10k+ in 1 hour")
        
        if velocity.get('unique_cards_24h', 0) > 3:
            triggers.append("3+ different cards in 24h")
        
        if velocity.get('unique_ips_24h', 0) > 5:
            triggers.append("5+ different IPs in 24h")
        
        if triggers:
            return True, "; ".join(triggers)
        
        return False, ""


class UnusualLocationRule(FraudRule):
    """Detect transactions from unusual locations"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        billing_country = transaction.get('billing_country', '')
        history = context.get('history', {})
        
        # Check if country is in user's typical locations
        usual_countries = history.get('usual_countries', ['US'])
        
        if billing_country and billing_country not in usual_countries:
            return True, f"Transaction from unusual country: {billing_country}"
        
        return False, ""


class LocationMismatchRule(FraudRule):
    """Check billing and shipping address mismatch"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        billing = transaction.get('billing_country', '')
        shipping = transaction.get('shipping_country', '')
        
        if billing and shipping and billing != shipping:
            return True, f"Billing ({billing}) and shipping ({shipping}) countries differ"
        
        return False, ""


class VPNProxyRule(FraudRule):
    """Detect VPN or proxy usage"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        device = transaction.get('device_info', {})
        
        if device.get('is_vpn') or device.get('is_proxy'):
            return True, "VPN or proxy detected"
        
        return False, ""


class DeviceMismatchRule(FraudRule):
    """Check for device fingerprint changes"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        device = transaction.get('device_info', {})
        history = context.get('history', {})
        
        current_device_id = device.get('device_id')
        known_devices = history.get('known_devices', [])
        
        if current_device_id and known_devices and current_device_id not in known_devices:
            return True, "Transaction from unrecognized device"
        
        return False, ""


class RushPurchaseRule(FraudRule):
    """Detect suspiciously quick purchases"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        time_on_site = transaction.get('time_on_site', 300)
        amount = transaction.get('amount', 0)
        
        # Suspicious if high-value purchase with little time on site
        if amount > 500 and time_on_site < 60:
            return True, f"High-value purchase (${amount:.2f}) with only {time_on_site}s on site"
        
        return False, ""


class NewAccountHighValueRule(FraudRule):
    """Flag high-value transactions from new accounts"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        account_age_days = transaction.get('account_age_days', 0)
        amount = transaction.get('amount', 0)
        is_first_purchase = transaction.get('is_first_purchase', False)
        
        if account_age_days < 7 and amount > 1000:
            return True, f"New account ({account_age_days} days old) with high-value transaction (${amount:.2f})"
        
        if is_first_purchase and amount > 2000:
            return True, f"First purchase with unusually high amount: ${amount:.2f}"
        
        return False, ""


class UnusualTimeRule(FraudRule):
    """Detect transactions at unusual hours"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        timestamp = transaction.get('timestamp')
        
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif not isinstance(timestamp, datetime):
            return False, ""
        
        hour = timestamp.hour
        
        # Flag transactions between 2 AM and 6 AM
        if 2 <= hour < 6:
            return True, f"Transaction at unusual hour: {hour}:00"
        
        return False, ""


class MultipleFailedAttemptsRule(FraudRule):
    """Detect multiple failed transaction attempts"""
    
    def evaluate(self, transaction: Dict, context: Dict) -> Tuple[bool, str]:
        velocity = context.get('velocity', {})
        failed_attempts = velocity.get('failed_attempts_1h', 0)
        
        if failed_attempts >= 3:
            return True, f"{failed_attempts} failed attempts in past hour"
        
        return False, ""
