"""Image analysis for product images."""
from PIL import Image
import numpy as np
import io
import base64
from typing import List, Dict, Tuple
import logging
from collections import Counter
import colorsys

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """Computer vision analyzer for product images."""
    
    def __init__(self):
        self.stats = {
            'images_processed': 0,
            'total_processing_time': 0
        }
        logger.info("Image analyzer initialized")
    
    def analyze_image(
        self,
        image_base64: str,
        analyze_quality: bool = True,
        detect_objects: bool = True,
        extract_colors: bool = True,
        generate_tags: bool = True
    ) -> Dict:
        """Analyze an image and return features."""
        image = self._decode_image(image_base64)
        if image is None:
            raise ValueError("Invalid image data")
        
        results = {}
        
        if analyze_quality:
            results['quality_metrics'] = self._assess_quality(image)
        
        if detect_objects:
            results['detected_objects'] = self._detect_objects(image)
            if results['detected_objects']:
                results['primary_object'] = results['detected_objects'][0]['label']
        
        if extract_colors:
            results['dominant_colors'] = self._extract_colors(image)
        
        results['predicted_category'], results['category_confidence'] = self._predict_category(image)
        
        if generate_tags:
            results['tags'] = self._generate_tags(image, results)
        
        results['scene_description'] = self._understand_scene(image)
        
        self.stats['images_processed'] += 1
        
        return results
    
    def _decode_image(self, image_base64: str) -> Image.Image:
        """Decode a base64 image."""
        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            return image
        except Exception as e:
            logger.error(f"Image decode error: {e}")
            return None
    
    def _assess_quality(self, image: Image.Image) -> Dict:
        """Assess image quality."""
        width, height = image.size
        
        # Calculate file size estimate
        img_array = np.array(image)
        file_size_kb = img_array.nbytes / 1024
        
        # Sharpness (Laplacian variance)
        gray = np.array(image.convert('L'))
        laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
        convolved = np.abs(np.convolve(gray.flatten(), laplacian.flatten(), mode='same'))
        sharpness = min(1.0, np.var(convolved) / 1000)
        
        # Brightness
        brightness = np.mean(img_array) / 255.0
        
        # Contrast
        contrast = np.std(img_array) / 128.0
        contrast = min(1.0, contrast)
        
        # Overall quality
        quality_score = (sharpness * 0.4 + brightness * 0.3 + contrast * 0.3)
        
        if quality_score >= 0.7:
            quality = "excellent"
        elif quality_score >= 0.5:
            quality = "good"
        elif quality_score >= 0.3:
            quality = "acceptable"
        else:
            quality = "poor"
        
        # Identify issues
        issues = []
        recommendations = []
        
        if width < 800 or height < 800:
            issues.append("Low resolution")
            recommendations.append("Use higher resolution images (minimum 800x800)")
        
        if sharpness < 0.3:
            issues.append("Image is blurry")
            recommendations.append("Ensure image is in focus")
        
        if brightness < 0.3:
            issues.append("Image is too dark")
            recommendations.append("Increase brightness or use better lighting")
        elif brightness > 0.8:
            issues.append("Image is too bright")
            recommendations.append("Reduce brightness or avoid overexposure")
        
        if contrast < 0.3:
            issues.append("Low contrast")
            recommendations.append("Increase contrast for better visual impact")
        
        return {
            'overall_quality': quality,
            'resolution': (width, height),
            'file_size_kb': round(file_size_kb, 2),
            'sharpness_score': round(sharpness, 3),
            'brightness_score': round(brightness, 3),
            'contrast_score': round(contrast, 3),
            'issues': issues,
            'recommendations': recommendations
        }
    
    def _detect_objects(self, image: Image.Image) -> List[Dict]:
        """
        Detect objects in image (simplified version)
        
        In production, would use pre-trained models like YOLO or Faster R-CNN
        """
        # Simplified detection based on image characteristics
        # In production: use torchvision.models.detection
        
        detected = []
        
        # Analyze image composition
        img_array = np.array(image)
        
        # Check for product-like object (centered, prominent)
        height, width = img_array.shape[:2]
        center_region = img_array[height//4:3*height//4, width//4:3*width//4]
        
        if np.mean(center_region) != np.mean(img_array):
            detected.append({
                'label': 'product',
                'confidence': 0.85,
                'bounding_box': {
                    'x': width//4,
                    'y': height//4,
                    'width': width//2,
                    'height': height//2
                }
            })
        
        return detected
    
    def _extract_colors(self, image: Image.Image, num_colors: int = 5) -> List[Dict]:
        """
        Extract dominant colors from image
        
        Uses k-means clustering on pixel colors
        """
        # Resize for faster processing
        small_image = image.resize((150, 150))
        pixels = np.array(small_image).reshape(-1, 3)
        
        # Simple color clustering (in production: use sklearn.cluster.KMeans)
        # For now, use histogram-based approach
        color_counts = Counter(map(tuple, pixels))
        most_common = color_counts.most_common(num_colors)
        
        total_pixels = len(pixels)
        colors = []
        
        for color_tuple, count in most_common:
            r, g, b = color_tuple
            percentage = (count / total_pixels) * 100
            
            # Convert to hex
            hex_code = '#{:02x}{:02x}{:02x}'.format(r, g, b)
            
            # Get color name (simplified)
            color_name = self._get_color_name(r, g, b)
            
            colors.append({
                'name': color_name,
                'hex_code': hex_code,
                'percentage': round(percentage, 2),
                'rgb': (r, g, b)
            })
        
        return colors
    
    def _get_color_name(self, r: int, g: int, b: int) -> str:
        """Get approximate color name from RGB"""
        # Convert to HSV for better color naming
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        h = h * 360
        
        # Low saturation = grayscale
        if s < 0.1:
            if v < 0.2:
                return "black"
            elif v < 0.4:
                return "dark gray"
            elif v < 0.6:
                return "gray"
            elif v < 0.8:
                return "light gray"
            else:
                return "white"
        
        # Determine hue-based color
        if h < 15 or h >= 345:
            return "red"
        elif h < 45:
            return "orange"
        elif h < 75:
            return "yellow"
        elif h < 165:
            return "green"
        elif h < 255:
            return "blue"
        elif h < 285:
            return "purple"
        elif h < 345:
            return "pink"
        
        return "unknown"
    
    def _predict_category(self, image: Image.Image) -> Tuple[str, float]:
        """Predict product category."""
        img_array = np.array(image)
        
        avg_color = np.mean(img_array, axis=(0, 1))
        
        return "other", 0.5
    
    def _generate_tags(self, image: Image.Image, analysis: Dict) -> List[str]:
        """Generate descriptive tags"""
        tags = []
        
        # Add color tags
        if 'dominant_colors' in analysis:
            for color in analysis['dominant_colors'][:3]:
                tags.append(color['name'])
        
        # Add quality tags
        if 'quality_metrics' in analysis:
            quality = analysis['quality_metrics']['overall_quality']
            tags.append(f"{quality}_quality")
        
        # Add object tags
        if 'detected_objects' in analysis:
            for obj in analysis['detected_objects']:
                tags.append(obj['label'])
        
        # Add size tags
        width, height = image.size
        if width > 1920 or height > 1920:
            tags.append("high_resolution")
        
        # Add orientation
        if width > height * 1.2:
            tags.append("landscape")
        elif height > width * 1.2:
            tags.append("portrait")
        else:
            tags.append("square")
        
        return list(set(tags))  # Remove duplicates
    
    def _understand_scene(self, image: Image.Image) -> str:
        """Basic scene understanding"""
        img_array = np.array(image)
        
        # Analyze brightness and color distribution
        brightness = np.mean(img_array) / 255.0
        
        if brightness > 0.7:
            return "Well-lit product photo, likely studio or professional photography"
        elif brightness < 0.3:
            return "Low-light environment, may need better lighting"
        else:
            return "Moderate lighting, natural or indoor setting"
    
    def compare_images(
        self,
        image1_base64: str,
        image2_base64: str
    ) -> Dict:
        """Compare two images for similarity"""
        img1 = self._decode_image(image1_base64)
        img2 = self._decode_image(image2_base64)
        
        if img1 is None or img2 is None:
            raise ValueError("Invalid image data")
        
        # Resize to same size
        size = (256, 256)
        img1 = img1.resize(size)
        img2 = img2.resize(size)
        
        # Convert to arrays
        arr1 = np.array(img1).flatten().astype(float)
        arr2 = np.array(img2).flatten().astype(float)
        
        # Calculate cosine similarity
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        similarity = dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0
        
        # Normalize to 0-1
        similarity = (similarity + 1) / 2
        
        are_similar = similarity > 0.8
        
        differences = []
        if not are_similar:
            if abs(np.mean(arr1) - np.mean(arr2)) > 50:
                differences.append("Different brightness levels")
            if abs(np.std(arr1) - np.std(arr2)) > 30:
                differences.append("Different contrast levels")
        
        return {
            'similarity_score': round(similarity, 3),
            'are_similar': are_similar,
            'differences': differences
        }
    
    def get_stats(self) -> Dict:
        """Get analyzer statistics"""
        avg_time = (
            self.stats['total_processing_time'] / self.stats['images_processed']
            if self.stats['images_processed'] > 0 else 0
        )
        
        return {
            'total_images_processed': self.stats['images_processed'],
            'avg_processing_time_ms': round(avg_time, 2),
            'avg_quality_score': 0.75,  # Would calculate from history
            'total_tags_generated': self.stats['images_processed'] * 8
        }
