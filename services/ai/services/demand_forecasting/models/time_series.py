"""
Time Series Forecasting Models
Multiple forecasting algorithms for demand prediction
"""
import numpy as np
from typing import List, Dict, Tuple
from datetime import date, timedelta
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class TimeSeriesForecaster:
    """
    Time series forecasting engine
    
    Implements multiple forecasting methods
    """
    
    def __init__(self):
        self.stats = defaultdict(int)
        logger.info("Time series forecaster initialized")
    
    def forecast(
        self,
        historical_data: List[Dict],
        periods: int,
        method: str = "exponential_smoothing",
        confidence_level: float = 0.95
    ) -> Dict:
        """
        Generate forecast using specified method
        
        Args:
            historical_data: List of {date, demand} dicts
            periods: Number of periods to forecast
            method: Forecasting method
            confidence_level: Confidence interval level
            
        Returns:
            Forecast results with predictions and bounds
        """
        # Extract time series
        dates = [d['date'] for d in historical_data]
        demands = np.array([d['demand'] for d in historical_data])
        
        # Select forecasting method
        if method == "moving_average":
            predictions = self._moving_average(demands, periods)
        elif method == "exponential_smoothing":
            predictions = self._exponential_smoothing(demands, periods)
        elif method == "linear_regression":
            predictions = self._linear_regression(demands, periods)
        elif method == "seasonal_naive":
            predictions = self._seasonal_naive(demands, periods)
        else:
            predictions = self._exponential_smoothing(demands, periods)
        
        # Calculate confidence intervals
        std_error = np.std(demands[-30:]) if len(demands) >= 30 else np.std(demands)
        z_score = 1.96 if confidence_level == 0.95 else 2.576  # 95% or 99%
        margin = z_score * std_error
        
        # Build forecast points
        last_date = dates[-1]
        forecast_points = []
        
        for i, pred in enumerate(predictions):
            forecast_date = last_date + timedelta(days=i+1)
            forecast_points.append({
                'date': forecast_date,
                'predicted_demand': max(0, pred),
                'lower_bound': max(0, pred - margin),
                'upper_bound': pred + margin,
                'confidence': confidence_level
            })
        
        # Calculate metrics (if we have recent actuals to compare)
        mae, mape, rmse = self._calculate_metrics(demands[-periods:], predictions[:len(demands[-periods:])])
        
        # Detect patterns
        seasonality = self._detect_seasonality(demands)
        trend = self._detect_trend(demands)
        
        # Summary statistics
        avg_pred = np.mean([p['predicted_demand'] for p in forecast_points])
        total_pred = np.sum([p['predicted_demand'] for p in forecast_points])
        peak_idx = np.argmax([p['predicted_demand'] for p in forecast_points])
        low_idx = np.argmin([p['predicted_demand'] for p in forecast_points])
        
        self.stats['total_forecasts'] += 1
        
        return {
            'forecast': forecast_points,
            'mae': mae,
            'mape': mape,
            'rmse': rmse,
            'detected_seasonality': seasonality,
            'detected_trend': trend,
            'avg_predicted_demand': round(avg_pred, 2),
            'total_predicted_demand': round(total_pred, 2),
            'peak_demand_date': forecast_points[peak_idx]['date'],
            'low_demand_date': forecast_points[low_idx]['date']
        }
    
    def _moving_average(self, data: np.ndarray, periods: int, window: int = 7) -> np.ndarray:
        """Simple moving average forecast"""
        predictions = []
        extended_data = data.copy()
        
        for _ in range(periods):
            avg = np.mean(extended_data[-window:])
            predictions.append(avg)
            extended_data = np.append(extended_data, avg)
        
        return np.array(predictions)
    
    def _exponential_smoothing(
        self,
        data: np.ndarray,
        periods: int,
        alpha: float = 0.3
    ) -> np.ndarray:
        """Exponential smoothing forecast"""
        # Initialize with first value
        smoothed = [data[0]]
        
        # Calculate smoothed values
        for i in range(1, len(data)):
            s = alpha * data[i] + (1 - alpha) * smoothed[-1]
            smoothed.append(s)
        
        # Forecast future periods
        predictions = [smoothed[-1]] * periods
        
        return np.array(predictions)
    
    def _linear_regression(self, data: np.ndarray, periods: int) -> np.ndarray:
        """Linear regression forecast"""
        n = len(data)
        x = np.arange(n)
        
        # Calculate slope and intercept
        x_mean = np.mean(x)
        y_mean = np.mean(data)
        
        numerator = np.sum((x - x_mean) * (data - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # Predict future values
        future_x = np.arange(n, n + periods)
        predictions = slope * future_x + intercept
        
        return predictions
    
    def _seasonal_naive(self, data: np.ndarray, periods: int, season_length: int = 7) -> np.ndarray:
        """Seasonal naive forecast (repeat last season)"""
        if len(data) < season_length:
            season_length = len(data)
        
        last_season = data[-season_length:]
        predictions = []
        
        for i in range(periods):
            predictions.append(last_season[i % season_length])
        
        return np.array(predictions)
    
    def _calculate_metrics(
        self,
        actuals: np.ndarray,
        predictions: np.ndarray
    ) -> Tuple[float, float, float]:
        """Calculate forecast accuracy metrics"""
        if len(actuals) == 0 or len(predictions) == 0:
            return None, None, None
        
        # Ensure same length
        min_len = min(len(actuals), len(predictions))
        actuals = actuals[:min_len]
        predictions = predictions[:min_len]
        
        # MAE
        mae = np.mean(np.abs(actuals - predictions))
        
        # MAPE (avoid division by zero)
        mape = np.mean(np.abs((actuals - predictions) / np.where(actuals != 0, actuals, 1))) * 100
        
        # RMSE
        rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
        
        return round(mae, 2), round(mape, 2), round(rmse, 2)
    
    def _detect_seasonality(self, data: np.ndarray) -> str:
        """Detect seasonality pattern"""
        if len(data) < 14:
            return "none"
        
        # Check weekly seasonality (7 days)
        if len(data) >= 21:
            weekly_pattern = self._test_seasonality(data, 7)
            if weekly_pattern > 0.3:
                return "weekly"
        
        # Check monthly seasonality
        if len(data) >= 60:
            monthly_pattern = self._test_seasonality(data, 30)
            if monthly_pattern > 0.3:
                return "monthly"
        
        return "none"
    
    def _test_seasonality(self, data: np.ndarray, period: int) -> float:
        """Test for seasonality at given period"""
        if len(data) < period * 2:
            return 0.0
        
        # Calculate autocorrelation at lag
        mean = np.mean(data)
        c0 = np.sum((data - mean) ** 2)
        
        if c0 == 0:
            return 0.0
        
        c_lag = np.sum((data[:-period] - mean) * (data[period:] - mean))
        autocorr = c_lag / c0
        
        return abs(autocorr)
    
    def _detect_trend(self, data: np.ndarray) -> str:
        """Detect trend direction"""
        if len(data) < 7:
            return "stable"
        
        # Calculate slope of recent data
        recent = data[-30:] if len(data) >= 30 else data
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]
        
        # Calculate volatility
        volatility = np.std(recent) / np.mean(recent) if np.mean(recent) > 0 else 0
        
        if volatility > 0.3:
            return "volatile"
        elif slope > 0.5:
            return "increasing"
        elif slope < -0.5:
            return "decreasing"
        else:
            return "stable"
    
    def analyze_seasonality(
        self,
        data: List[Dict],
        period_types: List[str]
    ) -> Dict:
        """Detailed seasonality analysis"""
        demands = np.array([d['demand'] for d in data])
        
        patterns = []
        max_strength = 0
        dominant = None
        
        for period_type in period_types:
            if period_type == "weekly":
                period = 7
            elif period_type == "monthly":
                period = 30
            elif period_type == "yearly":
                period = 365
            else:
                continue
            
            if len(demands) < period * 2:
                continue
            
            strength = self._test_seasonality(demands, period)
            
            if strength > 0.2:
                # Calculate pattern
                pattern = self._extract_pattern(demands, period)
                peak = np.argmax(pattern)
                low = np.argmin(pattern)
                
                patterns.append({
                    'period_type': period_type,
                    'strength': round(strength, 3),
                    'pattern': [round(p, 2) for p in pattern],
                    'peak_period': int(peak),
                    'low_period': int(low)
                })
                
                if strength > max_strength:
                    max_strength = strength
                    dominant = period_type
        
        return {
            'patterns_detected': patterns,
            'dominant_pattern': dominant,
            'overall_seasonality_strength': round(max_strength, 3)
        }
    
    def _extract_pattern(self, data: np.ndarray, period: int) -> np.ndarray:
        """Extract seasonal pattern"""
        num_periods = len(data) // period
        pattern = np.zeros(period)
        
        for i in range(num_periods):
            pattern += data[i*period:(i+1)*period]
        
        pattern /= num_periods
        return pattern
    
    def analyze_trend(self, data: List[Dict], window: int = 7) -> Dict:
        """Detailed trend analysis"""
        demands = np.array([d['demand'] for d in data])
        
        # Smooth data
        if len(demands) >= window:
            smoothed = np.convolve(demands, np.ones(window)/window, mode='valid')
        else:
            smoothed = demands
        
        # Calculate trend
        x = np.arange(len(smoothed))
        slope, intercept = np.polyfit(x, smoothed, 1)
        
        # Growth rate
        if len(smoothed) > 0 and smoothed[0] != 0:
            growth_rate = ((smoothed[-1] - smoothed[0]) / smoothed[0]) * 100
        else:
            growth_rate = 0.0
        
        # Check if accelerating
        first_half = smoothed[:len(smoothed)//2]
        second_half = smoothed[len(smoothed)//2:]
        
        slope1 = np.polyfit(np.arange(len(first_half)), first_half, 1)[0] if len(first_half) > 1 else 0
        slope2 = np.polyfit(np.arange(len(second_half)), second_half, 1)[0] if len(second_half) > 1 else 0
        
        is_accelerating = abs(slope2) > abs(slope1)
        
        # Trend type
        trend_type = self._detect_trend(demands)
        
        # Strength (R-squared)
        y_mean = np.mean(smoothed)
        ss_tot = np.sum((smoothed - y_mean) ** 2)
        ss_res = np.sum((smoothed - (slope * x + intercept)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Predictions
        pred_30d = slope * (len(smoothed) + 30) + intercept - smoothed[-1]
        pred_90d = slope * (len(smoothed) + 90) + intercept - smoothed[-1]
        
        return {
            'trend_type': trend_type,
            'trend_strength': round(max(0, min(1, r_squared)), 3),
            'growth_rate': round(growth_rate, 2),
            'is_accelerating': is_accelerating,
            'predicted_30d_change': round(pred_30d, 2),
            'predicted_90d_change': round(pred_90d, 2)
        }
