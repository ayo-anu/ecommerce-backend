"""
Inventory Optimization
Calculate optimal stock levels and reorder points
"""
import numpy as np
from typing import Dict, List
from datetime import date, timedelta
import logging
from scipy import stats

logger = logging.getLogger(__name__)


class InventoryOptimizer:
    """
    Inventory optimization using forecasts
    
    Calculates optimal stock levels, reorder points, and order quantities
    """
    
    def __init__(self):
        self.stats = {'optimizations': 0}
        logger.info("Inventory optimizer initialized")
    
    def optimize(
        self,
        current_stock: int,
        lead_time_days: int,
        holding_cost: float,
        stockout_cost: float,
        order_cost: float,
        forecasted_demand: List[Dict],
        service_level: float = 0.95
    ) -> Dict:
        """
        Calculate optimal inventory policy
        
        Args:
            current_stock: Current inventory level
            lead_time_days: Days between order and delivery
            holding_cost: Cost to hold one unit per period
            stockout_cost: Cost of one stockout
            order_cost: Fixed cost per order
            forecasted_demand: List of forecast points
            service_level: Target service level
            
        Returns:
            Optimization recommendations
        """
        # Extract demand forecast
        demand_forecast = np.array([f['predicted_demand'] for f in forecasted_demand])
        
        # Calculate demand during lead time
        lead_time_demand = np.sum(demand_forecast[:lead_time_days])
        
        # Calculate demand standard deviation
        demand_std = np.std(demand_forecast[:30])  # Use first 30 days
        
        # Calculate safety stock
        z_score = stats.norm.ppf(service_level)
        safety_stock = int(np.ceil(z_score * demand_std * np.sqrt(lead_time_days)))
        
        # Calculate reorder point
        reorder_point = int(np.ceil(lead_time_demand + safety_stock))
        
        # Calculate Economic Order Quantity (EOQ)
        annual_demand = np.sum(demand_forecast) * (365 / len(demand_forecast))
        if annual_demand > 0 and holding_cost > 0:
            eoq = np.sqrt((2 * annual_demand * order_cost) / holding_cost)
            order_quantity = int(np.ceil(eoq))
        else:
            order_quantity = int(np.ceil(lead_time_demand * 2))
        
        # Calculate days until stockout
        days_until_stockout = None
        cumulative_demand = 0
        for i, demand in enumerate(demand_forecast):
            cumulative_demand += demand
            if cumulative_demand >= current_stock:
                days_until_stockout = i + 1
                break
        
        # Determine recommended order date
        if days_until_stockout and days_until_stockout <= lead_time_days:
            # Order now!
            order_date = date.today()
        elif days_until_stockout:
            # Order before stockout considering lead time
            order_date = date.today() + timedelta(days=max(0, days_until_stockout - lead_time_days - 2))
        else:
            # Plenty of stock
            order_date = date.today() + timedelta(days=lead_time_days)
        
        # Estimate costs
        avg_inventory = (order_quantity / 2) + safety_stock
        estimated_holding = holding_cost * avg_inventory * (365 / len(demand_forecast))
        
        # Stockout risk
        shortage = max(0, lead_time_demand - current_stock)
        stockout_prob = 1 - service_level
        estimated_stockout_risk = shortage * stockout_prob * stockout_cost
        
        total_cost = estimated_holding + estimated_stockout_risk
        
        self.stats['optimizations'] += 1
        
        return {
            'recommended_order_quantity': order_quantity,
            'reorder_point': reorder_point,
            'safety_stock': safety_stock,
            'days_until_stockout': days_until_stockout,
            'recommended_order_date': order_date,
            'estimated_holding_cost': round(estimated_holding, 2),
            'estimated_stockout_risk': round(estimated_stockout_risk, 2),
            'total_estimated_cost': round(total_cost, 2),
            'forecasted_demand': round(lead_time_demand, 2)
        }
    
    def analyze_promotional_impact(
        self,
        historical_data: List[Dict],
        promotion_dates: List[date]
    ) -> Dict:
        """
        Analyze impact of promotions on demand
        
        Args:
            historical_data: Historical demand data
            promotion_dates: Dates of promotions
            
        Returns:
            Promotional impact analysis
        """
        promotion_dates_set = set(promotion_dates)
        
        # Separate promotional and baseline periods
        baseline_demand = []
        promo_demand = []
        
        for data_point in historical_data:
            if data_point['date'] in promotion_dates_set:
                promo_demand.append(data_point['demand'])
            else:
                baseline_demand.append(data_point['demand'])
        
        if not baseline_demand or not promo_demand:
            return {
                'avg_baseline_demand': 0,
                'avg_promotional_demand': 0,
                'demand_lift_percent': 0,
                'promotion_effectiveness_score': 0,
                'pre_promotion_dip': False,
                'post_promotion_recovery_days': 0
            }
        
        avg_baseline = np.mean(baseline_demand)
        avg_promo = np.mean(promo_demand)
        
        lift_percent = ((avg_promo - avg_baseline) / avg_baseline * 100) if avg_baseline > 0 else 0
        
        # Effectiveness score (0-1)
        effectiveness = min(1.0, lift_percent / 100) if lift_percent > 0 else 0
        
        # Check for pre-promotion dip
        pre_promo_dip = False
        if len(historical_data) > 7:
            # Check if demand dipped before first promotion
            sorted_data = sorted(historical_data, key=lambda x: x['date'])
            first_promo = min(promotion_dates)
            
            week_before = [d['demand'] for d in sorted_data if d['date'] < first_promo][-7:]
            if week_before and len(week_before) >= 3:
                if np.mean(week_before) < avg_baseline * 0.9:
                    pre_promo_dip = True
        
        # Estimate recovery time
        recovery_days = int(abs(lift_percent) / 10) if lift_percent != 0 else 0
        
        return {
            'avg_baseline_demand': round(avg_baseline, 2),
            'avg_promotional_demand': round(avg_promo, 2),
            'demand_lift_percent': round(lift_percent, 2),
            'promotion_effectiveness_score': round(effectiveness, 3),
            'pre_promotion_dip': pre_promo_dip,
            'post_promotion_recovery_days': min(30, recovery_days)
        }
    
    def detect_anomalies(
        self,
        historical_data: List[Dict],
        sensitivity: float = 2.0
    ) -> Dict:
        """
        Detect demand anomalies
        
        Args:
            historical_data: Historical demand data
            sensitivity: Number of standard deviations for threshold
            
        Returns:
            Detected anomalies
        """
        demands = np.array([d['demand'] for d in historical_data])
        dates = [d['date'] for d in historical_data]
        
        # Calculate rolling statistics
        window = min(7, len(demands) // 3)
        if window < 2:
            window = 2
        
        rolling_mean = np.convolve(demands, np.ones(window)/window, mode='valid')
        rolling_std = np.array([np.std(demands[max(0, i-window):i+1]) for i in range(len(demands))])
        
        # Pad rolling stats to match original length
        pad_size = len(demands) - len(rolling_mean)
        rolling_mean = np.pad(rolling_mean, (pad_size, 0), mode='edge')
        
        # Detect anomalies
        anomalies = []
        threshold = sensitivity * rolling_std
        
        for i, (date_val, demand, mean, std) in enumerate(zip(dates, demands, rolling_mean, rolling_std)):
            deviation = abs(demand - mean)
            
            if deviation > threshold[i] and std > 0:
                deviation_percent = ((demand - mean) / mean * 100) if mean > 0 else 0
                anomaly_score = min(1.0, deviation / (threshold[i] * 2))
                
                # Guess potential cause
                potential_cause = None
                if demand > mean * 1.5:
                    potential_cause = "Unexpected spike - check for promotions or events"
                elif demand < mean * 0.5:
                    potential_cause = "Unexpected drop - check for stockouts or issues"
                
                anomalies.append({
                    'date': date_val,
                    'actual_demand': int(demand),
                    'expected_demand': round(mean, 2),
                    'deviation_percent': round(deviation_percent, 2),
                    'anomaly_score': round(anomaly_score, 3),
                    'potential_cause': potential_cause
                })
        
        anomaly_rate = len(anomalies) / len(historical_data) if historical_data else 0
        
        return {
            'anomalies_detected': anomalies,
            'total_anomalies': len(anomalies),
            'anomaly_rate': round(anomaly_rate, 3)
        }
    
    def calculate_forecast_accuracy(
        self,
        predictions: List[Dict],
        actuals: List[Dict]
    ) -> Dict:
        """
        Evaluate forecast accuracy
        
        Args:
            predictions: Forecast points
            actuals: Actual demand
            
        Returns:
            Accuracy metrics
        """
        # Align predictions and actuals by date
        pred_dict = {p['date']: p['predicted_demand'] for p in predictions}
        actual_dict = {a['date']: a['demand'] for a in actuals}
        
        common_dates = set(pred_dict.keys()) & set(actual_dict.keys())
        
        if not common_dates:
            return {
                'mae': 0, 'mape': 0, 'rmse': 0, 'mase': 0,
                'directional_accuracy': 0, 'forecast_bias': 0,
                'is_overforecasting': False
            }
        
        preds = np.array([pred_dict[d] for d in sorted(common_dates)])
        acts = np.array([actual_dict[d] for d in sorted(common_dates)])
        
        # Error metrics
        errors = preds - acts
        mae = np.mean(np.abs(errors))
        mape = np.mean(np.abs(errors / np.where(acts != 0, acts, 1))) * 100
        rmse = np.sqrt(np.mean(errors ** 2))
        
        # MASE (Mean Absolute Scaled Error)
        naive_errors = np.abs(np.diff(acts))
        mase = mae / np.mean(naive_errors) if len(naive_errors) > 0 and np.mean(naive_errors) > 0 else 0
        
        # Directional accuracy
        if len(acts) > 1:
            actual_direction = np.diff(acts) > 0
            pred_direction = np.diff(preds) > 0
            directional_accuracy = np.mean(actual_direction == pred_direction)
        else:
            directional_accuracy = 0.5
        
        # Forecast bias
        bias = np.mean(errors)
        is_overforecasting = bias > 0
        
        return {
            'mae': round(mae, 2),
            'mape': round(mape, 2),
            'rmse': round(rmse, 2),
            'mase': round(mase, 3),
            'directional_accuracy': round(directional_accuracy, 3),
            'forecast_bias': round(bias, 2),
            'is_overforecasting': is_overforecasting
        }
