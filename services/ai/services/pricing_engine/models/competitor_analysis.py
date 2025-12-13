"""
Competitor Analysis - Track and analyze competitor pricing
Monitor market positioning and recommend adjustments
"""
import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class CompetitorAnalyzer:
    """
    Analyze competitor pricing and market position
    
    Provides insights for competitive positioning
    """
    
    def __init__(self):
        """Initialize competitor analyzer"""
        self.competitor_history = defaultdict(list)
        logger.info("Competitor analyzer initialized")
    
    def analyze_position(
        self,
        our_price: float,
        competitor_prices: List[float]
    ) -> Dict:
        """
        Analyze our market position vs competitors
        
        Args:
            our_price: Our current price
            competitor_prices: List of competitor prices
            
        Returns:
            Analysis with position and recommendations
        """
        if not competitor_prices:
            return {
                'position': 'unknown',
                'recommendation': 'Need competitor data for analysis'
            }
        
        # Calculate statistics
        comp_min = np.min(competitor_prices)
        comp_max = np.max(competitor_prices)
        comp_avg = np.mean(competitor_prices)
        comp_median = np.median(competitor_prices)
        comp_std = np.std(competitor_prices)
        
        # Determine position
        position = self._determine_position(our_price, comp_min, comp_max, comp_avg)
        
        # Calculate price gap
        price_gap = our_price - comp_avg
        gap_percent = (price_gap / comp_avg) * 100
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            our_price, position, comp_avg, comp_min, gap_percent
        )
        
        # Suggest optimal price
        suggested_price = self._suggest_competitive_price(
            our_price, comp_avg, comp_min, position
        )
        
        analysis = {
            'position': position,
            'competitor_min': float(comp_min),
            'competitor_max': float(comp_max),
            'competitor_avg': float(comp_avg),
            'competitor_median': float(comp_median),
            'competitor_std': float(comp_std),
            'price_gap': float(price_gap),
            'gap_percent': float(gap_percent),
            'recommendation': recommendation,
            'suggested_price': float(suggested_price) if suggested_price else None,
            'vs_lowest': float(our_price - comp_min),
            'vs_average': float(our_price - comp_avg)
        }
        
        logger.info(
            f"Position analysis: {position}, "
            f"gap: {gap_percent:.1f}%, "
            f"recommendation: {recommendation}"
        )
        
        return analysis
    
    def _determine_position(
        self,
        our_price: float,
        comp_min: float,
        comp_max: float,
        comp_avg: float
    ) -> str:
        """Determine market position"""
        # Categorize position
        if our_price < comp_min:
            return "lowest"
        elif our_price <= comp_avg * 0.95:
            return "competitive_low"
        elif our_price <= comp_avg * 1.05:
            return "competitive"
        elif our_price <= comp_avg * 1.15:
            return "premium"
        else:
            return "very_premium"
    
    def _generate_recommendation(
        self,
        our_price: float,
        position: str,
        comp_avg: float,
        comp_min: float,
        gap_percent: float
    ) -> str:
        """Generate pricing recommendation based on position"""
        if position == "lowest":
            return "You have the lowest price. Consider small increase to improve margins."
        
        elif position == "competitive_low":
            return "Good competitive position. Monitor for opportunities to increase price."
        
        elif position == "competitive":
            return "Well positioned at market average. Current price is optimal."
        
        elif position == "premium":
            return f"Premium positioning (+{gap_percent:.1f}% vs market). Justify with quality/features."
        
        elif position == "very_premium":
            return f"Significantly above market (+{gap_percent:.1f}%). Risk of losing price-sensitive customers."
        
        else:
            return "Unable to determine position. Need more competitor data."
    
    def _suggest_competitive_price(
        self,
        our_price: float,
        comp_avg: float,
        comp_min: float,
        position: str
    ) -> float:
        """Suggest optimal competitive price"""
        if position in ["lowest", "competitive_low", "competitive"]:
            # Already well positioned
            return None
        
        elif position == "premium":
            # Slight reduction to be more competitive
            return comp_avg * 1.05
        
        elif position == "very_premium":
            # Significant reduction needed
            return comp_avg * 1.02
        
        return None
    
    def track_competitor(
        self,
        product_id: str,
        competitor_name: str,
        price: float
    ):
        """Track competitor price over time"""
        self.competitor_history[product_id].append({
            'competitor': competitor_name,
            'price': price,
            'timestamp': np.datetime64('now')
        })
    
    def get_price_trends(
        self,
        product_id: str,
        days: int = 30
    ) -> Dict:
        """Get competitor price trends"""
        history = self.competitor_history.get(product_id, [])
        
        if not history:
            return {'trend': 'unknown', 'data': []}
        
        # Extract prices
        prices = [h['price'] for h in history[-days:]]
        
        if len(prices) < 2:
            return {'trend': 'insufficient_data', 'data': prices}
        
        # Calculate trend
        if prices[-1] > prices[0] * 1.05:
            trend = 'increasing'
        elif prices[-1] < prices[0] * 0.95:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'start_price': prices[0],
            'end_price': prices[-1],
            'avg_price': np.mean(prices),
            'change_percent': ((prices[-1] - prices[0]) / prices[0]) * 100,
            'data': prices
        }
    
    def benchmark_against_market(
        self,
        our_prices: Dict[str, float],
        market_prices: Dict[str, List[float]]
    ) -> Dict:
        """
        Benchmark our entire catalog against market
        
        Args:
            our_prices: Dict of product_id: price
            market_prices: Dict of product_id: [competitor_prices]
            
        Returns:
            Aggregate market position analysis
        """
        positions = []
        gaps = []
        
        for product_id, our_price in our_prices.items():
            comp_prices = market_prices.get(product_id, [])
            
            if comp_prices:
                comp_avg = np.mean(comp_prices)
                gap_percent = ((our_price - comp_avg) / comp_avg) * 100
                gaps.append(gap_percent)
                
                position = self._determine_position(
                    our_price,
                    np.min(comp_prices),
                    np.max(comp_prices),
                    comp_avg
                )
                positions.append(position)
        
        # Aggregate results
        if not gaps:
            return {'overall_position': 'unknown'}
        
        avg_gap = np.mean(gaps)
        
        position_counts = {
            'lowest': positions.count('lowest'),
            'competitive_low': positions.count('competitive_low'),
            'competitive': positions.count('competitive'),
            'premium': positions.count('premium'),
            'very_premium': positions.count('very_premium')
        }
        
        # Determine overall strategy
        if avg_gap < -5:
            overall_position = 'discount_leader'
        elif -5 <= avg_gap <= 5:
            overall_position = 'competitive'
        elif 5 < avg_gap <= 15:
            overall_position = 'premium'
        else:
            overall_position = 'luxury'
        
        return {
            'overall_position': overall_position,
            'avg_price_gap_percent': float(avg_gap),
            'position_distribution': position_counts,
            'products_analyzed': len(gaps),
            'recommendation': self._overall_recommendation(overall_position, avg_gap)
        }
    
    def _overall_recommendation(self, position: str, gap: float) -> str:
        """Generate overall catalog recommendation"""
        if position == 'discount_leader':
            return "You're positioned as a discount leader. Ensure margins are sustainable."
        elif position == 'competitive':
            return "Well-balanced competitive positioning across catalog."
        elif position == 'premium':
            return "Premium positioning. Ensure value proposition justifies higher prices."
        elif position == 'luxury':
            return "Luxury positioning. May limit market size. Consider segment-specific pricing."
        else:
            return "Unable to determine overall position."
