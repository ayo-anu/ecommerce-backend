"""
AI Service Clients for Django Backend

Provides easy-to-use clients for calling AI microservices with
built-in resilience (circuit breakers, retries, timeouts).

Usage:
    from core.ai_clients import recommendation_client, fraud_client

    # Get recommendations
    response = recommendation_client.get_user_recommendations(user_id=123)

    # Analyze fraud
    response = fraud_client.analyze_transaction(transaction_data)
"""

import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

from django.conf import settings

from .resilience import get_ai_service_client, CircuitBreakerError
from .ai_fallbacks import (
    recommendation_fallback,
    search_fallback,
    pricing_fallback,
    fraud_fallback,
    forecasting_fallback,
    chatbot_fallback,
    vision_fallback,
)

logger = logging.getLogger(__name__)


class AIServiceClient:
    """Base class for AI service clients"""

    def __init__(self, service_name: str, base_url: str):
        """
        Initialize AI service client.

        Args:
            service_name: Name of the service (for circuit breaker)
            base_url: Base URL of the service
        """
        self.service_name = service_name
        self.base_url = base_url.rstrip('/')
        self.client = get_ai_service_client(service_name)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request to AI service.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request arguments

        Returns:
            Response JSON data or None on failure
        """
        url = urljoin(self.base_url, endpoint)

        # Inject trace context into headers for distributed tracing
        headers = kwargs.get('headers', {})
        try:
            from opentelemetry.propagate import inject
            inject(headers)
            kwargs['headers'] = headers
        except ImportError:
            pass  # OpenTelemetry not installed

        try:
            if method.upper() == 'GET':
                response = self.client.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = self.client.post(url, **kwargs)
            elif method.upper() == 'PUT':
                response = self.client.put(url, **kwargs)
            elif method.upper() == 'DELETE':
                response = self.client.delete(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json() if response.text else {}

        except CircuitBreakerError as e:
            logger.warning(
                f"Circuit breaker open for {self.service_name}: {e}"
            )
            return None

        except Exception as e:
            logger.error(
                f"Error calling {self.service_name} ({endpoint}): {e}",
                exc_info=True
            )
            return None


class RecommendationClient(AIServiceClient):
    """Client for Recommendation Engine service"""

    def __init__(self):
        super().__init__(
            service_name="recommendation-service",
            base_url=getattr(settings, 'RECOMMENDATION_SERVICE_URL', 'http://recommendation-service:8001')
        )

    def get_user_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> Optional[List[Dict]]:
        """
        Get personalized product recommendations for a user.

        Args:
            user_id: User ID
            limit: Number of recommendations
            filters: Optional filters (category, price_range, etc.)

        Returns:
            List of recommended products (uses fallback if service fails)
        """
        params = {'limit': limit}
        if filters:
            params.update(filters)

        response = self._make_request(
            'GET',
            f'/recommendations/user/{user_id}',
            params=params
        )

        # Use fallback if service failed
        if response is None:
            return recommendation_fallback.get_user_recommendations(
                user_id, limit, filters
            )

        return response.get('recommendations')

    def get_similar_products(
        self,
        product_id: int,
        limit: int = 5
    ) -> Optional[List[Dict]]:
        """
        Get products similar to a given product.

        Args:
            product_id: Product ID
            limit: Number of similar products

        Returns:
            List of similar products (uses fallback if service fails)
        """
        response = self._make_request(
            'GET',
            f'/recommendations/product/{product_id}/similar',
            params={'limit': limit}
        )

        # Use fallback if service failed
        if response is None:
            return recommendation_fallback.get_similar_products(product_id, limit)

        return response.get('similar_products')

    def record_interaction(
        self,
        user_id: int,
        product_id: int,
        interaction_type: str
    ) -> bool:
        """
        Record user-product interaction.

        Args:
            user_id: User ID
            product_id: Product ID
            interaction_type: Type of interaction (view, click, purchase)

        Returns:
            True if successful, False otherwise
        """
        response = self._make_request(
            'POST',
            '/recommendations/interaction',
            json={
                'user_id': user_id,
                'product_id': product_id,
                'interaction_type': interaction_type
            }
        )

        return response is not None


class SearchClient(AIServiceClient):
    """Client for Search Engine service"""

    def __init__(self):
        super().__init__(
            service_name="search-service",
            base_url=getattr(settings, 'SEARCH_SERVICE_URL', 'http://search-service:8002')
        )

    def search_products(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> Optional[List[Dict]]:
        """
        Search for products using semantic search.

        Args:
            query: Search query
            filters: Optional filters
            limit: Number of results

        Returns:
            List of search results (uses fallback if service fails)
        """
        response = self._make_request(
            'POST',
            '/search/text',
            json={
                'query': query,
                'filters': filters or {},
                'limit': limit
            }
        )

        # Use fallback if service failed
        if response is None:
            return search_fallback.search_products(query, filters, limit)

        return response.get('results')

    def autocomplete(self, query: str, limit: int = 5) -> Optional[List[str]]:
        """
        Get autocomplete suggestions.

        Args:
            query: Partial search query
            limit: Number of suggestions

        Returns:
            List of suggestions or None
        """
        response = self._make_request(
            'POST',
            '/search/autocomplete',
            json={'query': query, 'limit': limit}
        )

        return response.get('suggestions') if response else None


class PricingClient(AIServiceClient):
    """Client for Pricing Engine service"""

    def __init__(self):
        super().__init__(
            service_name="pricing-service",
            base_url=getattr(settings, 'PRICING_SERVICE_URL', 'http://pricing-service:8003')
        )

    def recommend_price(
        self,
        product_id: int,
        cost: float,
        competitor_prices: Optional[List[float]] = None
    ) -> Optional[Dict]:
        """
        Get recommended price for a product.

        Args:
            product_id: Product ID
            cost: Product cost
            competitor_prices: List of competitor prices

        Returns:
            Pricing recommendation (uses fallback if service fails)
        """
        response = self._make_request(
            'POST',
            '/pricing/recommend',
            json={
                'product_id': product_id,
                'cost': cost,
                'competitor_prices': competitor_prices or []
            }
        )

        # Use fallback if service failed
        if response is None:
            return pricing_fallback.recommend_price(
                product_id, cost, competitor_prices
            )

        return response


class FraudClient(AIServiceClient):
    """Client for Fraud Detection service"""

    def __init__(self):
        super().__init__(
            service_name="fraud-service",
            base_url=getattr(settings, 'FRAUD_SERVICE_URL', 'http://fraud-service:8005')
        )

    def analyze_transaction(
        self,
        transaction_data: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        Analyze transaction for fraud risk.

        Args:
            transaction_data: Transaction details (amount, user_id, etc.)

        Returns:
            Fraud analysis result with risk_score (uses fallback if service fails)
        """
        response = self._make_request(
            'POST',
            '/fraud/analyze',
            json=transaction_data,
            timeout=(5.0, 10.0)  # Shorter timeout for fraud checks
        )

        # Use fallback if service failed - CRITICAL for fraud detection
        if response is None:
            return fraud_fallback.analyze_transaction(transaction_data)

        return response


class ForecastingClient(AIServiceClient):
    """Client for Demand Forecasting service"""

    def __init__(self):
        super().__init__(
            service_name="forecasting-service",
            base_url=getattr(settings, 'FORECAST_SERVICE_URL', 'http://forecasting-service:8006')
        )

    def forecast_demand(
        self,
        product_id: int,
        days_ahead: int = 30
    ) -> Optional[Dict]:
        """
        Forecast product demand.

        Args:
            product_id: Product ID
            days_ahead: Number of days to forecast

        Returns:
            Demand forecast (uses fallback if service fails)
        """
        response = self._make_request(
            'POST',
            '/forecast/demand',
            json={
                'product_id': product_id,
                'days_ahead': days_ahead
            }
        )

        # Use fallback if service failed
        if response is None:
            return forecasting_fallback.forecast_demand(product_id, days_ahead)

        return response


class ChatbotClient(AIServiceClient):
    """Client for Chatbot RAG service"""

    def __init__(self):
        super().__init__(
            service_name="chatbot-service",
            base_url=getattr(settings, 'CHATBOT_SERVICE_URL', 'http://chatbot-service:8004')
        )

    def send_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Send message to chatbot.

        Args:
            message: User message
            conversation_id: Optional conversation ID
            user_id: Optional user ID for context

        Returns:
            Chatbot response (uses fallback if service fails)
        """
        response = self._make_request(
            'POST',
            '/chat/message',
            json={
                'message': message,
                'conversation_id': conversation_id,
                'user_id': user_id
            }
        )

        # Use fallback if service failed
        if response is None:
            return chatbot_fallback.send_message(message, conversation_id, user_id)

        return response


class VisionClient(AIServiceClient):
    """Client for Visual Recognition service"""

    def __init__(self):
        super().__init__(
            service_name="vision-service",
            base_url=getattr(settings, 'VISION_SERVICE_URL', 'http://vision-service:8007')
        )

    def analyze_image(
        self,
        image_url: Optional[str] = None,
        image_data: Optional[bytes] = None
    ) -> Optional[Dict]:
        """
        Analyze product image.

        Args:
            image_url: URL of image
            image_data: Raw image bytes

        Returns:
            Image analysis result (uses fallback if service fails)
        """
        if image_url:
            response = self._make_request(
                'POST',
                '/vision/analyze',
                json={'image_url': image_url}
            )
        elif image_data:
            response = self._make_request(
                'POST',
                '/vision/analyze',
                files={'image': image_data}
            )
        else:
            raise ValueError("Either image_url or image_data must be provided")

        # Use fallback if service failed
        if response is None:
            return vision_fallback.analyze_image(image_url, image_data)

        return response


# Global client instances (lazy initialization)
_recommendation_client = None
_search_client = None
_pricing_client = None
_fraud_client = None
_forecasting_client = None
_chatbot_client = None
_vision_client = None


def get_recommendation_client() -> RecommendationClient:
    """Get global recommendation client instance"""
    global _recommendation_client
    if _recommendation_client is None:
        _recommendation_client = RecommendationClient()
    return _recommendation_client


def get_search_client() -> SearchClient:
    """Get global search client instance"""
    global _search_client
    if _search_client is None:
        _search_client = SearchClient()
    return _search_client


def get_pricing_client() -> PricingClient:
    """Get global pricing client instance"""
    global _pricing_client
    if _pricing_client is None:
        _pricing_client = PricingClient()
    return _pricing_client


def get_fraud_client() -> FraudClient:
    """Get global fraud client instance"""
    global _fraud_client
    if _fraud_client is None:
        _fraud_client = FraudClient()
    return _fraud_client


def get_forecasting_client() -> ForecastingClient:
    """Get global forecasting client instance"""
    global _forecasting_client
    if _forecasting_client is None:
        _forecasting_client = ForecastingClient()
    return _forecasting_client


def get_chatbot_client() -> ChatbotClient:
    """Get global chatbot client instance"""
    global _chatbot_client
    if _chatbot_client is None:
        _chatbot_client = ChatbotClient()
    return _chatbot_client


def get_vision_client() -> VisionClient:
    """Get global vision client instance"""
    global _vision_client
    if _vision_client is None:
        _vision_client = VisionClient()
    return _vision_client


# Convenience aliases
recommendation_client = get_recommendation_client()
search_client = get_search_client()
pricing_client = get_pricing_client()
fraud_client = get_fraud_client()
forecasting_client = get_forecasting_client()
chatbot_client = get_chatbot_client()
vision_client = get_vision_client()
