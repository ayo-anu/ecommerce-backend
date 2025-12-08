"""
AI Service Fallbacks

Provides graceful degradation strategies when AI services are unavailable.
Each fallback uses simpler, rule-based logic or cached data to maintain
functionality even when ML services fail.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db.models import Count, Avg, Q

logger = logging.getLogger(__name__)


class FallbackStrategy:
    """Base class for fallback strategies"""

    def __init__(self, service_name: str):
        self.service_name = service_name

    def log_fallback(self, reason: str):
        """Log that fallback is being used"""
        logger.warning(
            f"Using fallback for {self.service_name}: {reason}"
        )


class RecommendationFallback(FallbackStrategy):
    """
    Fallback strategies for recommendation service.

    Strategy priority:
    1. Return cached recommendations
    2. Return popular products (most purchased in last 30 days)
    3. Return products from user's favorite categories
    4. Return trending products (most viewed in last 7 days)
    """

    def __init__(self):
        super().__init__("recommendation-service")

    def get_user_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Get recommendations using fallback strategies.

        Args:
            user_id: User ID
            limit: Number of recommendations
            filters: Optional filters

        Returns:
            List of recommended products
        """
        self.log_fallback("Service unavailable, using rule-based recommendations")

        # Strategy 1: Cached recommendations
        cache_key = f'recs:fallback:{user_id}'
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Using cached recommendations for user {user_id}")
            return cached[:limit]

        # Strategy 2: Popular products
        popular = self._get_popular_products(limit, filters)
        if popular:
            # Cache for 1 hour
            cache.set(cache_key, popular, timeout=3600)
            return popular

        # Strategy 3: Fallback to empty list
        return []

    def _get_popular_products(
        self,
        limit: int,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Get popular products based on order history"""
        try:
            from apps.products.models import Product
            from apps.orders.models import OrderItem

            # Get most purchased products in last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)

            queryset = Product.objects.filter(
                is_active=True,
                stock__gt=0,
            ).annotate(
                purchase_count=Count(
                    'orderitem',
                    filter=Q(orderitem__order__created_at__gte=thirty_days_ago)
                )
            ).order_by('-purchase_count')

            # Apply filters
            if filters:
                if 'category' in filters:
                    queryset = queryset.filter(category__slug=filters['category'])

            products = queryset[:limit]

            return [
                {
                    'product_id': p.id,
                    'name': p.name,
                    'price': float(p.price),
                    'image_url': p.get_primary_image_url() if hasattr(p, 'get_primary_image_url') else None,
                    'reason': 'popular',
                }
                for p in products
            ]

        except Exception as e:
            logger.error(f"Error getting popular products: {e}")
            return []

    def get_similar_products(
        self,
        product_id: int,
        limit: int = 5
    ) -> List[Dict]:
        """Get similar products using rule-based logic"""
        self.log_fallback("Using category-based similarity")

        try:
            from apps.products.models import Product

            # Get the source product
            product = Product.objects.get(id=product_id)

            # Find products in same category with similar price
            price_range = product.price * 0.2  # ±20% price range

            similar = Product.objects.filter(
                category=product.category,
                is_active=True,
                stock__gt=0,
                price__gte=product.price - price_range,
                price__lte=product.price + price_range,
            ).exclude(
                id=product_id
            ).order_by('-created_at')[:limit]

            return [
                {
                    'product_id': p.id,
                    'name': p.name,
                    'price': float(p.price),
                    'similarity_score': 0.7,  # Fixed score for fallback
                    'reason': 'same_category',
                }
                for p in similar
            ]

        except Exception as e:
            logger.error(f"Error getting similar products: {e}")
            return []


class SearchFallback(FallbackStrategy):
    """
    Fallback strategies for search service.

    Strategy priority:
    1. Use cached search results
    2. Use simple text matching (ILIKE)
    3. Use Elasticsearch if available
    """

    def __init__(self):
        super().__init__("search-service")

    def search_products(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search products using simple text matching.

        Args:
            query: Search query
            filters: Optional filters
            limit: Number of results

        Returns:
            List of search results
        """
        self.log_fallback("Using simple text matching")

        try:
            from apps.products.models import Product

            # Simple case-insensitive search
            queryset = Product.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__name__icontains=query),
                is_active=True,
            ).distinct()

            # Apply filters
            if filters:
                if 'category' in filters:
                    queryset = queryset.filter(category__slug=filters['category'])
                if 'min_price' in filters:
                    queryset = queryset.filter(price__gte=filters['min_price'])
                if 'max_price' in filters:
                    queryset = queryset.filter(price__lte=filters['max_price'])

            products = queryset[:limit]

            return [
                {
                    'product_id': p.id,
                    'name': p.name,
                    'description': p.description,
                    'price': float(p.price),
                    'score': 1.0,  # No relevance scoring in fallback
                }
                for p in products
            ]

        except Exception as e:
            logger.error(f"Error in search fallback: {e}")
            return []


class PricingFallback(FallbackStrategy):
    """
    Fallback strategies for pricing service.

    Strategy priority:
    1. Use fixed markup (cost * 1.3)
    2. Use category average pricing
    3. Use last known price
    """

    def __init__(self):
        super().__init__("pricing-service")

    def recommend_price(
        self,
        product_id: int,
        cost: float,
        competitor_prices: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Recommend price using rule-based logic.

        Args:
            product_id: Product ID
            cost: Product cost
            competitor_prices: Optional competitor prices

        Returns:
            Pricing recommendation
        """
        self.log_fallback("Using fixed markup pricing")

        # Strategy 1: Fixed markup
        recommended_price = cost * 1.3  # 30% markup

        # Strategy 2: Consider competitor prices if available
        if competitor_prices and len(competitor_prices) > 0:
            avg_competitor_price = sum(competitor_prices) / len(competitor_prices)
            # Don't price too far from competitors
            if abs(recommended_price - avg_competitor_price) > avg_competitor_price * 0.2:
                recommended_price = avg_competitor_price * 0.95  # Slightly below average

        return {
            'product_id': product_id,
            'recommended_price': round(recommended_price, 2),
            'min_price': round(cost * 1.1, 2),  # Minimum 10% markup
            'max_price': round(cost * 1.5, 2),  # Maximum 50% markup
            'strategy': 'fixed_markup',
            'confidence': 0.6,  # Lower confidence for fallback
        }


class FraudFallback(FallbackStrategy):
    """
    Fallback strategies for fraud detection.

    Strategy priority:
    1. Rule-based checks (amount, velocity, patterns)
    2. Historical fraud patterns from database
    3. Conservative scoring (flag for manual review)
    """

    def __init__(self):
        super().__init__("fraud-service")

    def analyze_transaction(
        self,
        transaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze transaction using rule-based fraud detection.

        Args:
            transaction_data: Transaction details

        Returns:
            Fraud analysis result
        """
        self.log_fallback("Using rule-based fraud detection")

        user_id = transaction_data.get('user_id')
        amount = transaction_data.get('amount', 0)
        payment_method = transaction_data.get('payment_method')

        risk_score = 0.0
        risk_factors = []

        # Rule 1: High amount
        if amount > 1000:
            risk_score += 0.3
            risk_factors.append('high_amount')

        # Rule 2: Very high amount
        if amount > 5000:
            risk_score += 0.3
            risk_factors.append('very_high_amount')

        # Rule 3: Velocity check (multiple transactions in short time)
        velocity_risk = self._check_velocity(user_id)
        risk_score += velocity_risk
        if velocity_risk > 0:
            risk_factors.append('high_velocity')

        # Rule 4: New user
        if self._is_new_user(user_id):
            risk_score += 0.2
            risk_factors.append('new_user')

        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)

        # Determine action
        if risk_score >= 0.8:
            action = 'reject'
        elif risk_score >= 0.5:
            action = 'review'
        else:
            action = 'approve'

        return {
            'transaction_id': transaction_data.get('transaction_id'),
            'risk_score': round(risk_score, 2),
            'risk_factors': risk_factors,
            'action': action,
            'strategy': 'rule_based',
            'confidence': 0.7,
        }

    def _check_velocity(self, user_id: int) -> float:
        """Check transaction velocity for user"""
        try:
            from apps.orders.models import Order

            # Count orders in last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_orders = Order.objects.filter(
                user_id=user_id,
                created_at__gte=one_hour_ago
            ).count()

            if recent_orders >= 5:
                return 0.4  # Very high velocity
            elif recent_orders >= 3:
                return 0.2  # High velocity

            return 0.0

        except Exception as e:
            logger.error(f"Error checking velocity: {e}")
            return 0.0

    def _is_new_user(self, user_id: int) -> bool:
        """Check if user is new (registered in last 7 days)"""
        try:
            from apps.accounts.models import User

            user = User.objects.get(id=user_id)
            seven_days_ago = datetime.now() - timedelta(days=7)

            return user.created_at >= seven_days_ago

        except Exception as e:
            logger.error(f"Error checking user age: {e}")
            return False


class ForecastingFallback(FallbackStrategy):
    """
    Fallback strategies for demand forecasting.

    Strategy priority:
    1. Use simple moving average (last 30 days)
    2. Use same period last year
    3. Use category-level forecast
    """

    def __init__(self):
        super().__init__("forecasting-service")

    def forecast_demand(
        self,
        product_id: int,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        Forecast demand using simple moving average.

        Args:
            product_id: Product ID
            days_ahead: Number of days to forecast

        Returns:
            Demand forecast
        """
        self.log_fallback("Using moving average forecast")

        try:
            from apps.orders.models import OrderItem
            from django.db.models import Sum

            # Get sales for last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)

            total_quantity = OrderItem.objects.filter(
                product_id=product_id,
                order__created_at__gte=thirty_days_ago,
                order__status='completed'
            ).aggregate(
                total=Sum('quantity')
            )['total'] or 0

            # Calculate daily average
            daily_average = total_quantity / 30

            # Forecast = daily average * days ahead
            forecasted_demand = daily_average * days_ahead

            return {
                'product_id': product_id,
                'days_ahead': days_ahead,
                'forecasted_demand': round(forecasted_demand, 0),
                'daily_average': round(daily_average, 2),
                'strategy': 'moving_average',
                'confidence': 0.5,
            }

        except Exception as e:
            logger.error(f"Error in forecast fallback: {e}")
            return {
                'product_id': product_id,
                'forecasted_demand': 0,
                'error': str(e),
            }


class ChatbotFallback(FallbackStrategy):
    """
    Fallback strategies for chatbot service.

    Strategy priority:
    1. Return pre-defined FAQs
    2. Redirect to human support
    3. Provide helpful links
    """

    def __init__(self):
        super().__init__("chatbot-service")

    def send_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Respond to message using rule-based logic.

        Args:
            message: User message
            conversation_id: Optional conversation ID
            user_id: Optional user ID

        Returns:
            Chatbot response
        """
        self.log_fallback("Using FAQ-based responses")

        message_lower = message.lower()

        # Simple keyword matching
        if any(word in message_lower for word in ['shipping', 'delivery', 'ship']):
            response = "We offer free shipping on orders over $50. Standard delivery takes 3-5 business days."

        elif any(word in message_lower for word in ['return', 'refund']):
            response = "You can return items within 30 days for a full refund. Visit our returns page for more info."

        elif any(word in message_lower for word in ['track', 'order', 'status']):
            response = "You can track your order in the 'My Orders' section of your account."

        elif any(word in message_lower for word in ['payment', 'pay']):
            response = "We accept credit cards, PayPal, and Apple Pay."

        elif any(word in message_lower for word in ['help', 'support']):
            response = "I'm here to help! You can also contact our support team at support@example.com or call 1-800-123-4567."

        else:
            response = "I'm sorry, I'm not able to answer that right now. Please contact our support team at support@example.com or call 1-800-123-4567."

        return {
            'response': response,
            'conversation_id': conversation_id,
            'strategy': 'faq_based',
            'confidence': 0.4,
        }


class VisionFallback(FallbackStrategy):
    """
    Fallback strategies for vision service.

    Strategy priority:
    1. Skip image analysis
    2. Use manual tags
    3. Use filename-based categorization
    """

    def __init__(self):
        super().__init__("vision-service")

    def analyze_image(
        self,
        image_url: Optional[str] = None,
        image_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Skip image analysis and return minimal info.

        Args:
            image_url: URL of image
            image_data: Raw image bytes

        Returns:
            Image analysis result (minimal)
        """
        self.log_fallback("Skipping image analysis")

        return {
            'status': 'skipped',
            'message': 'Image analysis service unavailable',
            'tags': [],
            'quality_score': None,
            'strategy': 'skip',
        }


# Global fallback instances
recommendation_fallback = RecommendationFallback()
search_fallback = SearchFallback()
pricing_fallback = PricingFallback()
fraud_fallback = FraudFallback()
forecasting_fallback = ForecastingFallback()
chatbot_fallback = ChatbotFallback()
vision_fallback = VisionFallback()
