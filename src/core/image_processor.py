"""
Core image processor - handles the actual image processing pipeline.
Clean, focused, and testable. Now includes green water processing capabilities.
"""
import cv2
import numpy as np
import logging
from typing import Optional

from models.processing_params import ProcessingParameters
from core.green_water_processor import GreenWaterProcessor
import color_correction as cc


class ImageProcessor:
    """Core image processing engine with clean separation of concerns."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.green_water_processor = GreenWaterProcessor()
    
    def process_image(self, image_bgr: np.ndarray, params: ProcessingParameters) -> np.ndarray:
        """
        Process an image with the given parameters.
        
        Args:
            image_bgr: Input image in BGR format
            params: Processing parameters
            
        Returns:
            Processed image in BGR format
        """
        if image_bgr is None:
            raise ValueError("Input image is None")
        
        try:
            self.logger.info(f"Processing image with parameters: {params}")
            result = image_bgr.copy()
            
            # Step 1: Apply green water specific preprocessing if needed
            if params.water_type in ["lake", "auto"]:
                result = self.green_water_processor.process_green_water_image(result, params)
            
            # Step 2: White balance
            if params.enable_white_balance:
                result = self._apply_white_balance(result, params)
            
            # Step 3: Red channel enhancement (may be adjusted for green water)
            if params.enable_red_channel:
                result = self._apply_red_enhancement(result, params)
            
            # Step 4: Fusion or separate processing
            if params.enable_fusion:
                result = self._apply_fusion_processing(result, params)
            else:
                # Apply dehazing separately if fusion is disabled
                if params.enable_dehaze:
                    result = self._apply_dehazing(result, params)
            
            # Step 5: CLAHE
            if params.enable_clahe:
                result = self._apply_clahe(result, params)
            
            # Saturation enhancement
            if params.enable_saturation:
                result = self._apply_saturation(result, params)
            
            self.logger.info("Image processing completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing image: {str(e)}")
            raise
    
    def _apply_white_balance(self, image: np.ndarray, params: ProcessingParameters) -> np.ndarray:
        """Apply white balance correction."""
        method = params.wb_method
        strength = params.white_balance_strength
        
        if method == 'robust':
            lower = int(params.robust_lower)
            upper = int(params.robust_upper)
            return cc.white_balance(image, strength=strength, lower=lower, upper=upper)
        elif method == 'white_patch':
            percentile = int(params.retinex_percentile)
            return cc.white_patch_retinex(image, percentile=percentile)
        elif method == 'gray_world':
            lower = int(params.robust_lower)
            upper = int(params.robust_upper)
            return cc.gray_world(image, strength=strength, lower=lower, upper=upper)
        else:
            self.logger.warning(f"Unknown white balance method: {method}")
            return image
    
    def _apply_red_enhancement(self, image: np.ndarray, params: ProcessingParameters) -> np.ndarray:
        """Apply red channel enhancement."""
        return cc.enhance_red_channel(image, scale=params.red_scale)
    
    def _apply_fusion_processing(self, image: np.ndarray, params: ProcessingParameters) -> np.ndarray:
        """Apply fusion processing with two paths."""
        method = params.fusion_method
        
        # Create two paths for fusion
        if params.fusion_balance < 0.5:
            # Path A: More dehazing (atmospheric correction)
            path_a = image.copy()
            if params.enable_dehaze:
                path_a = cc.dehaze(path_a, omega=params.dehaze_strength)
            
            # Path B: Detail enhancement
            path_b = image.copy()
            path_b = cc.unsharp_mask(path_b, amount=params.unsharp_amount, radius=params.unsharp_radius)
        else:
            # Path A: Detail enhancement (primary)
            path_a = image.copy()
            path_a = cc.unsharp_mask(path_a, amount=params.unsharp_amount, radius=params.unsharp_radius)
            
            # Path B: Dehazing
            path_b = image.copy()
            if params.enable_dehaze:
                path_b = cc.dehaze(path_b, omega=params.dehaze_strength)
        
        # Fuse the two paths
        if method == 'average':
            return cc.average_fusion(path_a, path_b)
        elif method == 'pca':
            return cc.pca_fusion(path_a, path_b)
        elif method == 'weighted':
            weight = params.fusion_balance
            return cc.weighted_fusion(path_a, path_b, weight=weight)
        else:
            self.logger.warning(f"Unknown fusion method: {method}")
            return path_a
    
    def _apply_dehazing(self, image: np.ndarray, params: ProcessingParameters) -> np.ndarray:
        """Apply dehazing."""
        return cc.dehaze(image, omega=params.dehaze_strength)
    
    def _apply_clahe(self, image: np.ndarray, params: ProcessingParameters) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        return cc.apply_clahe_with_clip(image, clip_limit=params.clahe_clip)
    
    def _apply_saturation(self, image: np.ndarray, params: ProcessingParameters) -> np.ndarray:
        """Apply saturation enhancement."""
        return cc.enhance_saturation(image, params.saturation)
