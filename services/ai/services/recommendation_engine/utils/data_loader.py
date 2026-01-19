"""
Data loading utilities for recommendation engine
Interfaces with Django backend and handles data preprocessing
"""
import httpx
import logging
from typing import List, Dict, Optional
from shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DjangoDataLoader:
    """Load data from Django DRF backend"""
    
    def __init__(self):
        self.base_url = settings.DJANGO_BACKEND_URL
        self.api_key = settings.DJANGO_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_user_orders(self, user_id: str) -> List[Dict]:
        """
        Get user's order history from Django
        
        Args:
            user_id: User UUID
            
        Returns:
            List of orders with products
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/orders/",
                    params={"user": user_id},
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json().get('results', [])
                else:
                    logger.error(f"Failed to fetch orders: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching user orders: {e}")
            return []
    
    async def get_product(self, product_id: str) -> Optional[Dict]:
        """
        Get product details from Django
        
        Args:
            product_id: Product UUID
            
        Returns:
            Product data dictionary
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/products/{product_id}/",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to fetch product: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching product: {e}")
            return None
    
    async def get_all_products(self, limit: int = 1000) -> List[Dict]:
        """
        Get all products for model training
        
        Args:
            limit: Maximum number of products
            
        Returns:
            List of products
        """
        try:
            products = []
            page = 1
            
            async with httpx.AsyncClient() as client:
                while len(products) < limit:
                    response = await client.get(
                        f"{self.base_url}/api/products/",
                        params={"page": page, "page_size": 100},
                        headers=self.headers,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get('results', [])
                        
                        if not results:
                            break
                        
                        products.extend(results)
                        page += 1
                        
                        # Check if there are more pages
                        if not data.get('next'):
                            break
                    else:
                        logger.error(f"Failed to fetch products: {response.status_code}")
                        break
            
            return products[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching all products: {e}")
            return []
    
    async def get_all_interactions(self) -> List[Dict]:
        """
        Get all user-product interactions for model training
        
        Returns:
            List of interactions with user_id, product_id, rating
        """
        try:
            interactions = []
            
            # Get orders (purchases are strong signals)
            async with httpx.AsyncClient() as client:
                page = 1
                while True:
                    response = await client.get(
                        f"{self.base_url}/api/orders/",
                        params={"page": page, "page_size": 100},
                        headers=self.headers,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        orders = data.get('results', [])
                        
                        if not orders:
                            break
                        
                        # Extract interactions from orders
                        for order in orders:
                            user_id = order.get('user')
                            
                            for item in order.get('items', []):
                                product_id = item.get('product')
                                
                                interactions.append({
                                    'user_id': user_id,
                                    'product_id': product_id,
                                    'rating': 5.0,  # Purchase = strong signal
                                    'timestamp': order.get('created_at')
                                })
                        
                        page += 1
                        
                        if not data.get('next'):
                            break
                    else:
                        break
            
            logger.info(f"Loaded {len(interactions)} interactions from Django")
            return interactions
            
        except Exception as e:
            logger.error(f"Error fetching interactions: {e}")
            return []


def preprocess_product_for_content(product: Dict) -> Dict:
    """
    Preprocess product data for content-based filtering
    
    Args:
        product: Raw product data from Django
        
    Returns:
        Preprocessed product dictionary
    """
    return {
        'product_id': product.get('id'),
        'name': product.get('name', ''),
        'description': product.get('description', ''),
        'category': product.get('category', {}).get('name', ''),
        'tags': [tag.get('name', '') for tag in product.get('tags', [])]
    }


def extract_user_product_history(orders: List[Dict]) -> List[str]:
    """
    Extract product IDs from user's order history
    
    Args:
        orders: List of user orders
        
    Returns:
        List of product IDs
    """
    product_ids = []
    
    for order in orders:
        for item in order.get('items', []):
            product_id = item.get('product')
            if product_id:
                product_ids.append(product_id)
    
    return list(set(product_ids))  # Remove duplicates


# Global data loader instance
data_loader = DjangoDataLoader()
