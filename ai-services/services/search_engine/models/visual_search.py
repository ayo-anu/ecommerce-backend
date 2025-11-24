"""
Visual Search Model - Search products by image
Uses ResNet50 for image embeddings
"""
from torchvision import models, transforms
from PIL import Image
import torch
import numpy as np
from typing import List, Tuple, Dict
import logging
import io
import base64
import requests

logger = logging.getLogger(__name__)


class VisualSearchModel:
    """Image-based product search using deep learning"""
    
    def __init__(self):
        self.model = None
        self.preprocess = None
        self.product_image_embeddings = None
        self.product_id_map = {}
        self.reverse_product_map = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_trained = False
        
    def load_model(self):
        """Load pre-trained ResNet50 model"""
        logger.info("Loading visual search model (ResNet50)")
        
        # Load pretrained ResNet50
        self.model = models.resnet50(pretrained=True)
        
        # Remove final classification layer (use as feature extractor)
        self.model = torch.nn.Sequential(*list(self.model.children())[:-1])
        self.model.eval()
        self.model.to(self.device)
        
        # Image preprocessing pipeline
        self.preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        logger.info("Visual model loaded successfully")
    
    def extract_image_features(self, image: Image.Image) -> np.ndarray:
        """Extract features from an image"""
        if self.model is None:
            self.load_model()
        
        # Preprocess image
        img_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        
        # Extract features
        with torch.no_grad():
            features = self.model(img_tensor)
        
        # Flatten and normalize
        features = features.cpu().numpy().flatten()
        features = features / np.linalg.norm(features)
        
        return features
    
    def index_product_images(self, products: List[Dict]):
        """
        Index product images
        
        Args:
            products: List with id and image_url
        """
        if self.model is None:
            self.load_model()
        
        logger.info(f"Indexing {len(products)} product images")
        
        embeddings = []
        valid_products = []
        
        for product in products:
            try:
                image_url = product.get('image_url') or product.get('primary_image')
                if not image_url:
                    continue
                
                # Load image (in production, this should be async/batched)
                image = self._load_image_from_url(image_url)
                if image is None:
                    continue
                
                # Extract features
                features = self.extract_image_features(image)
                embeddings.append(features)
                valid_products.append(product)
                
            except Exception as e:
                logger.warning(f"Failed to process image for product {product.get('id')}: {e}")
                continue
        
        if embeddings:
            self.product_image_embeddings = np.array(embeddings)
            self.product_id_map = {p['id']: idx for idx, p in enumerate(valid_products)}
            self.reverse_product_map = {idx: p['id'] for idx, p in enumerate(valid_products)}
            self.is_trained = True
            logger.info(f"Indexed {len(embeddings)} product images successfully")
        else:
            logger.warning("No product images were indexed")
    
    def search_by_image(
        self,
        image: Image.Image,
        top_k: int = 10,
        min_similarity: float = 0.6
    ) -> List[Tuple[str, float]]:
        """Search for similar products by image"""
        if not self.is_trained:
            return []
        
        # Extract query image features
        query_features = self.extract_image_features(image)
        
        # Calculate cosine similarity
        similarities = np.dot(self.product_image_embeddings, query_features)
        
        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= min_similarity:
                product_id = self.reverse_product_map[idx]
                results.append((product_id, score))
        
        return results
    
    def _load_image_from_url(self, url: str) -> Image.Image:
        """Load image from URL"""
        try:
            response = requests.get(url, timeout=5)
            image = Image.open(io.BytesIO(response.content)).convert('RGB')
            return image
        except:
            return None
    
    def load_image_from_base64(self, base64_str: str) -> Image.Image:
        """Load image from base64 string"""
        try:
            image_data = base64.b64decode(base64_str)
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            return image
        except:
            return None
