

import logging

from typing import List, Dict, Any, Optional

from datetime import datetime, timedelta

from django.core.cache import cache

from django.db.models import Count, Avg, Q


logger = logging.getLogger(__name__)



class FallbackStrategy:


    def __init__(self, service_name: str):

        self.service_name = service_name


    def log_fallback(self, reason: str):

        logger.warning(

            f"Using fallback for {self.service_name}: {reason}"

        )



class RecommendationFallback(FallbackStrategy):


    def __init__(self):

        super().__init__("recommendation-service")


    def get_user_recommendations(

        self,

        user_id: int,

        limit: int = 10,

        filters: Optional[Dict] = None

    ) -> List[Dict]:

        self.log_fallback("Service unavailable, using rule-based recommendations")


        cache_key = f'recs:fallback:{user_id}'

        cached = cache.get(cache_key)

        if cached:

            logger.info(f"Using cached recommendations for user {user_id}")

            return cached[:limit]


        popular = self._get_popular_products(limit, filters)

        if popular:

            cache.set(cache_key, popular, timeout=3600)

            return popular


        return []


    def _get_popular_products(

        self,

        limit: int,

        filters: Optional[Dict] = None

    ) -> List[Dict]:

        try:

            from apps.products.models import Product

            from apps.orders.models import OrderItem


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

        self.log_fallback("Using category-based similarity")


        try:

            from apps.products.models import Product


            product = Product.objects.get(id=product_id)


            price_range = product.price * 0.2                    


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

                    'similarity_score': 0.7,

                    'reason': 'same_category',

                }

                for p in similar

            ]


        except Exception as e:

            logger.error(f"Error getting similar products: {e}")

            return []



class SearchFallback(FallbackStrategy):


    def __init__(self):

        super().__init__("search-service")


    def search_products(

        self,

        query: str,

        filters: Optional[Dict] = None,

        limit: int = 20

    ) -> List[Dict]:

        self.log_fallback("Using simple text matching")


        try:

            from apps.products.models import Product


            queryset = Product.objects.filter(

                Q(name__icontains=query) |

                Q(description__icontains=query) |

                Q(tags__name__icontains=query),

                is_active=True,

            ).distinct()


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

                    'score': 1.0,

                }

                for p in products

            ]


        except Exception as e:

            logger.error(f"Error in search fallback: {e}")

            return []



class PricingFallback(FallbackStrategy):


    def __init__(self):

        super().__init__("pricing-service")


    def recommend_price(

        self,

        product_id: int,

        cost: float,

        competitor_prices: Optional[List[float]] = None

    ) -> Dict[str, Any]:

        self.log_fallback("Using fixed markup pricing")


        recommended_price = cost * 1.3


        if competitor_prices and len(competitor_prices) > 0:

            avg_competitor_price = sum(competitor_prices) / len(competitor_prices)

            if abs(recommended_price - avg_competitor_price) > avg_competitor_price * 0.2:

                recommended_price = avg_competitor_price * 0.95


        return {

            'product_id': product_id,

            'recommended_price': round(recommended_price, 2),

            'min_price': round(cost * 1.1, 2),

            'max_price': round(cost * 1.5, 2),

            'strategy': 'fixed_markup',

            'confidence': 0.6,

        }



class FraudFallback(FallbackStrategy):


    def __init__(self):

        super().__init__("fraud-service")


    def analyze_transaction(

        self,

        transaction_data: Dict[str, Any]

    ) -> Dict[str, Any]:

        self.log_fallback("Using rule-based fraud detection")


        user_id = transaction_data.get('user_id')

        amount = transaction_data.get('amount', 0)

        payment_method = transaction_data.get('payment_method')


        risk_score = 0.0

        risk_factors = []


        if amount > 1000:

            risk_score += 0.3

            risk_factors.append('high_amount')


        if amount > 5000:

            risk_score += 0.3

            risk_factors.append('very_high_amount')


        velocity_risk = self._check_velocity(user_id)

        risk_score += velocity_risk

        if velocity_risk > 0:

            risk_factors.append('high_velocity')


        if self._is_new_user(user_id):

            risk_score += 0.2

            risk_factors.append('new_user')


        risk_score = min(risk_score, 1.0)


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

        try:

            from apps.orders.models import Order


            one_hour_ago = datetime.now() - timedelta(hours=1)

            recent_orders = Order.objects.filter(

                user_id=user_id,

                created_at__gte=one_hour_ago

            ).count()


            if recent_orders >= 5:

                return 0.4

            elif recent_orders >= 3:

                return 0.2


            return 0.0


        except Exception as e:

            logger.error(f"Error checking velocity: {e}")

            return 0.0


    def _is_new_user(self, user_id: int) -> bool:

        try:

            from apps.accounts.models import User


            user = User.objects.get(id=user_id)

            seven_days_ago = datetime.now() - timedelta(days=7)


            return user.created_at >= seven_days_ago


        except Exception as e:

            logger.error(f"Error checking user age: {e}")

            return False



class ForecastingFallback(FallbackStrategy):


    def __init__(self):

        super().__init__("forecasting-service")


    def forecast_demand(

        self,

        product_id: int,

        days_ahead: int = 30

    ) -> Dict[str, Any]:

        self.log_fallback("Using moving average forecast")


        try:

            from apps.orders.models import OrderItem

            from django.db.models import Sum


            thirty_days_ago = datetime.now() - timedelta(days=30)


            total_quantity = OrderItem.objects.filter(

                product_id=product_id,

                order__created_at__gte=thirty_days_ago,

                order__status='completed'

            ).aggregate(

                total=Sum('quantity')

            )['total'] or 0


            daily_average = total_quantity / 30


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


    def __init__(self):

        super().__init__("chatbot-service")


    def send_message(

        self,

        message: str,

        conversation_id: Optional[str] = None,

        user_id: Optional[int] = None

    ) -> Dict[str, Any]:

        self.log_fallback("Using FAQ-based responses")


        message_lower = message.lower()


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


    def __init__(self):

        super().__init__("vision-service")


    def analyze_image(

        self,

        image_url: Optional[str] = None,

        image_data: Optional[bytes] = None

    ) -> Dict[str, Any]:

        self.log_fallback("Skipping image analysis")


        return {

            'status': 'skipped',

            'message': 'Image analysis service unavailable',

            'tags': [],

            'quality_score': None,

            'strategy': 'skip',

        }



recommendation_fallback = RecommendationFallback()

search_fallback = SearchFallback()

pricing_fallback = PricingFallback()

fraud_fallback = FraudFallback()

forecasting_fallback = ForecastingFallback()

chatbot_fallback = ChatbotFallback()

vision_fallback = VisionFallback()

