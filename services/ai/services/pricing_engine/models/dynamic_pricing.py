"""
Dynamic Pricing Algorithm - Adaptive pricing based on multiple factors
Adjusts prices in real-time based on demand, competition, and inventory
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

from ..schemas.pricing import PricingStrategy, PriceAdjustmentReason

logger = logging.getLogger(__name__)


class DynamicPricingEngine:
    """
    Dynamic pricing algorithm
    
    Adjusts prices based on:
    - Demand elasticity
    - Competitor prices
    - Inventory levels
    - Seasonality
    - Market conditions
    """
    
    def __init__(self):
        """Initialize pricing engine"""
        self.price_history = {}
        self.demand_cache = {}
        
        # Default parameters
        self.default_elasticity = -1.5  # Price elasticity
        self.inventory_pressure_threshold = 0.3  # 30% stock
        self.high_stock_threshold = 1.5  # 150% of target
        
        logger.info("Dynamic pricing engine initialized")
    
    def calculate_optimal_price(
        self,
        product_id: str,
        base_cost: float,
        current_price: Optional[float],
        market_data: Dict,
        inventory_data: Dict,
        sales_data: Dict,
        constraints: Dict,
        strategy: PricingStrategy
    ) -> Tuple[float, List[PriceAdjustmentReason], float]:
        """
        Calculate optimal price
        
        Returns:
            (recommended_price, reasons, confidence)
        """
        reasons = []
        adjustments = {}
        
        # Base price from cost plus minimum margin
        min_margin = constraints.get('min_margin_percent', 20.0)
        min_price = base_cost * (1 + min_margin / 100)
        
        # Start with current price or cost-plus
        if current_price and current_price > min_price:
            base_price = current_price
        else:
            base_price = base_cost * 1.5  # 50% markup default
        
        # Apply strategy-specific adjustments
        if strategy == PricingStrategy.DYNAMIC:
            adjustments = self._dynamic_adjustments(
                base_price, market_data, inventory_data, sales_data
            )
            reasons.extend(adjustments['reasons'])
        
        elif strategy == PricingStrategy.COMPETITIVE:
            adjustments = self._competitive_adjustments(
                base_price, market_data
            )
            reasons.append(PriceAdjustmentReason.COMPETITION)
        
        elif strategy == PricingStrategy.COST_PLUS:
            # Simple cost-plus with target margin
            target_margin = constraints.get('target_margin', 40.0)
            adjustments = {'price': base_cost * (1 + target_margin / 100)}
        
        elif strategy == PricingStrategy.PREMIUM:
            # Premium positioning
            market_avg = market_data.get('market_average', base_price)
            adjustments = {'price': market_avg * 1.15}  # 15% above market
        
        elif strategy == PricingStrategy.PENETRATION:
            # Aggressive pricing to gain market share
            market_avg = market_data.get('market_average', base_price)
            adjustments = {'price': market_avg * 0.85}  # 15% below market
            reasons.append(PriceAdjustmentReason.COMPETITION)
        
        # Apply adjustments
        recommended_price = adjustments.get('price', base_price)
        
        # Apply constraints
        max_discount = constraints.get('max_discount_percent', 50.0)
        max_price = current_price * (1 + max_discount / 100) if current_price else recommended_price * 2
        min_price = base_cost * (1 + min_margin / 100)
        
        recommended_price = np.clip(recommended_price, min_price, max_price)
        
        # Psychological pricing (round to .99)
        if constraints.get('round_to_99', True):
            recommended_price = np.floor(recommended_price) + 0.99
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(market_data, sales_data)
        
        logger.info(
            f"Price calculated for {product_id}: ${recommended_price:.2f} "
            f"(confidence: {confidence:.2f})"
        )
        
        return recommended_price, reasons, confidence
    
    def _dynamic_adjustments(
        self,
        base_price: float,
        market_data: Dict,
        inventory_data: Dict,
        sales_data: Dict
    ) -> Dict:
        """Calculate dynamic price adjustments"""
        reasons = []
        price = base_price
        
        # 1. Demand-based adjustment
        demand_factor = self._calculate_demand_factor(sales_data)
        if demand_factor > 1.1:
            price *= 1.05  # Increase 5% for high demand
            reasons.append(PriceAdjustmentReason.DEMAND)
        elif demand_factor < 0.9:
            price *= 0.95  # Decrease 5% for low demand
            reasons.append(PriceAdjustmentReason.DEMAND)
        
        # 2. Inventory-based adjustment
        inventory_factor = self._calculate_inventory_factor(inventory_data)
        if inventory_factor < self.inventory_pressure_threshold:
            price *= 0.90  # Discount to clear inventory
            reasons.append(PriceAdjustmentReason.INVENTORY)
        elif inventory_factor > self.high_stock_threshold:
            price *= 1.05  # Increase for scarce items
            reasons.append(PriceAdjustmentReason.INVENTORY)
        
        # 3. Competitive adjustment
        competitor_prices = market_data.get('competitor_prices', [])
        if competitor_prices:
            avg_competitor = np.mean(competitor_prices)
            if price > avg_competitor * 1.15:
                # We're significantly more expensive
                price = avg_competitor * 1.05  # Position slightly above
                reasons.append(PriceAdjustmentReason.COMPETITION)
        
        return {'price': price, 'reasons': reasons}
    
    def _competitive_adjustments(
        self,
        base_price: float,
        market_data: Dict
    ) -> Dict:
        """Competitive pricing adjustments"""
        competitor_prices = market_data.get('competitor_prices', [])
        
        if not competitor_prices:
            return {'price': base_price}
        
        # Position slightly below average competitor
        avg_competitor = np.mean(competitor_prices)
        min_competitor = np.min(competitor_prices)
        
        # Be competitive but not necessarily lowest
        target_price = min(avg_competitor * 0.98, min_competitor * 1.02)
        
        return {'price': target_price}
    
    def _calculate_demand_factor(self, sales_data: Dict) -> float:
        """
        Calculate demand factor (1.0 = normal)
        
        > 1.0 = High demand
        < 1.0 = Low demand
        """
        units_7d = sales_data.get('units_sold_7d', 0)
        units_30d = sales_data.get('units_sold_30d', 0)
        
        # Calculate weekly average
        avg_weekly = units_30d / 4.0 if units_30d > 0 else 1
        
        if avg_weekly == 0:
            return 1.0
        
        # Compare recent week to average
        demand_factor = units_7d / avg_weekly
        
        return demand_factor
    
    def _calculate_inventory_factor(self, inventory_data: Dict) -> float:
        """
        Calculate inventory pressure (1.0 = optimal)
        
        < 0.5 = Overstocked
        > 1.5 = Low stock
        """
        current_stock = inventory_data.get('current_stock', 100)
        target_stock = inventory_data.get('target_stock', current_stock)
        
        if target_stock == 0:
            return 1.0
        
        factor = current_stock / target_stock
        return factor
    
    def _calculate_confidence(
        self,
        market_data: Dict,
        sales_data: Dict
    ) -> float:
        """
        Calculate confidence in pricing recommendation
        
        Based on data quality and completeness
        """
        confidence = 0.5  # Base confidence
        
        # More competitor data = higher confidence
        competitor_prices = market_data.get('competitor_prices', [])
        if len(competitor_prices) >= 3:
            confidence += 0.2
        elif len(competitor_prices) >= 1:
            confidence += 0.1
        
        # More sales history = higher confidence
        units_30d = sales_data.get('units_sold_30d', 0)
        if units_30d >= 100:
            confidence += 0.2
        elif units_30d >= 10:
            confidence += 0.1
        
        # Conversion rate data = higher confidence
        if sales_data.get('conversion_rate') is not None:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def estimate_demand_change(
        self,
        current_price: float,
        new_price: float,
        elasticity: float = None
    ) -> float:
        """
        Estimate demand change from price change
        
        Uses price elasticity: % change in demand = elasticity * % change in price
        """
        if elasticity is None:
            elasticity = self.default_elasticity
        
        price_change_percent = ((new_price - current_price) / current_price) * 100
        demand_change_percent = elasticity * price_change_percent
        
        return demand_change_percent
    
    def calculate_revenue_impact(
        self,
        current_price: float,
        current_units: int,
        new_price: float,
        elasticity: float = None
    ) -> Tuple[float, float]:
        """
        Calculate revenue and profit impact
        
        Returns:
            (revenue_change, new_expected_units)
        """
        demand_change = self.estimate_demand_change(current_price, new_price, elasticity)
        new_units = current_units * (1 + demand_change / 100)
        
        current_revenue = current_price * current_units
        new_revenue = new_price * new_units
        
        revenue_change = ((new_revenue - current_revenue) / current_revenue) * 100
        
        return revenue_change, int(new_units)
    
    def optimize_for_revenue(
        self,
        base_cost: float,
        current_demand: int,
        min_price: float,
        max_price: float,
        elasticity: float = None
    ) -> float:
        """
        Find price that maximizes revenue
        
        Uses grid search over price range
        """
        if elasticity is None:
            elasticity = self.default_elasticity
        
        prices = np.linspace(min_price, max_price, 50)
        revenues = []
        
        for price in prices:
            demand_at_price = current_demand * ((price / min_price) ** elasticity)
            revenue = price * demand_at_price
            revenues.append(revenue)
        
        optimal_idx = np.argmax(revenues)
        optimal_price = prices[optimal_idx]
        
        return float(optimal_price)
    
    def optimize_for_profit(
        self,
        base_cost: float,
        current_demand: int,
        min_price: float,
        max_price: float,
        elasticity: float = None
    ) -> float:
        """
        Find price that maximizes profit
        
        Profit = (Price - Cost) * Demand
        """
        if elasticity is None:
            elasticity = self.default_elasticity
        
        prices = np.linspace(min_price, max_price, 50)
        profits = []
        
        for price in prices:
            demand_at_price = current_demand * ((price / min_price) ** elasticity)
            profit = (price - base_cost) * demand_at_price
            profits.append(profit)
        
        optimal_idx = np.argmax(profits)
        optimal_price = prices[optimal_idx]
        
        return float(optimal_price)
