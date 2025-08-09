"""
Green Water (Lake/Freshwater) Color Correction Module.
Specialized algorithms for correcting underwater images in lakes and green water conditions.
"""
import cv2
import numpy as np
import logging
from typing import Dict, Any, Tuple

from models.processing_params import ProcessingParameters
from services.logger_service import get_logger


class GreenWaterProcessor:
    """Specialized processor for green water (lake/freshwater) color correction."""
    
    def __init__(self):
        self.logger = get_logger('green_water_processor')
        
        # Lake-specific attenuation coefficients (different from ocean)
        self.lake_attenuation = {
            'red': 0.45,    # Higher red attenuation due to organic matter
            'green': 0.25,  # Lower green attenuation (dominant wavelength)
            'blue': 0.8     # High blue attenuation from particles
        }
        
        # Ocean attenuation coefficients for comparison
        self.ocean_attenuation = {
            'red': 0.6,
            'green': 0.1,
            'blue': 0.05
        }
    
    def detect_water_type(self, image_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Detect if the image is taken in green water (lake) or blue water (ocean).
        
        Args:
            image_bgr: Input image in BGR format
            
        Returns:
            Dictionary containing water type analysis
        """
        if image_bgr is None:
            return {'type': 'ocean', 'confidence': 0.0, 'green_dominance': 0.0}
        
        try:
            # Convert to float for analysis
            img_float = image_bgr.astype(np.float32)
            b, g, r = cv2.split(img_float)
            
            # Calculate channel statistics
            r_mean = np.mean(r)
            g_mean = np.mean(g)
            b_mean = np.mean(b)
            
            # Calculate green dominance ratio
            total_intensity = r_mean + g_mean + b_mean
            green_ratio = g_mean / max(total_intensity, 1.0) if total_intensity > 0 else 0
            
            # Calculate color cast indicators
            g_to_r_ratio = g_mean / max(r_mean, 1.0)
            g_to_b_ratio = g_mean / max(b_mean, 1.0)
            
            # Analyze color distribution in HSV
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            hue = hsv[:, :, 0]
            saturation = hsv[:, :, 1]
            
            # Count pixels in green hue range (40-80 in OpenCV HSV)
            green_mask = ((hue >= 40) & (hue <= 80) & (saturation > 30))
            green_pixel_ratio = np.sum(green_mask) / hue.size
            
            # Calculate turbidity indicator (variance in intensity)
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            turbidity_indicator = np.std(gray) / max(np.mean(gray), 1.0)
            
            # Decision logic for water type
            green_dominance = (green_ratio * 0.4 + 
                             (g_to_r_ratio - 1.0) * 0.3 + 
                             (g_to_b_ratio - 1.0) * 0.2 + 
                             green_pixel_ratio * 0.1)
            
            # Determine water type and confidence
            if green_dominance > 0.15:
                water_type = 'lake'
                confidence = min(1.0, green_dominance * 2.0)
            else:
                water_type = 'ocean'
                confidence = min(1.0, (0.15 - green_dominance) * 3.0)
            
            analysis = {
                'type': water_type,
                'confidence': confidence,
                'green_dominance': green_dominance,
                'green_ratio': green_ratio,
                'g_to_r_ratio': g_to_r_ratio,
                'g_to_b_ratio': g_to_b_ratio,
                'green_pixel_ratio': green_pixel_ratio,
                'turbidity_indicator': turbidity_indicator,
                'channel_means': {'r': r_mean, 'g': g_mean, 'b': b_mean}
            }
            
            self.logger.info(f"Water type detection: {water_type} (confidence: {confidence:.2f}, "
                           f"green_dominance: {green_dominance:.2f})")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Water type detection failed: {e}")
            return {'type': 'ocean', 'confidence': 0.0, 'green_dominance': 0.0}
    
    def apply_magenta_compensation(self, image_bgr: np.ndarray, 
                                 compensation_factor: float) -> np.ndarray:
        """
        Apply magenta compensation to reduce green cast.
        
        Args:
            image_bgr: Input image in BGR format
            compensation_factor: Strength of green channel dampening
            
        Returns:
            Image with magenta compensation applied
        """
        if image_bgr is None:
            return image_bgr
        
        try:
            img_float = image_bgr.astype(np.float32)
            
            # Split channels
            b, g, r = cv2.split(img_float)
            
            # Apply magenta compensation by dampening green and boosting red/blue
            green_dampen = 1.0 / compensation_factor
            red_boost = 1.0 + (compensation_factor - 1.0) * 0.3
            blue_boost = 1.0 + (compensation_factor - 1.0) * 0.2
            
            # Apply adjustments
            r_corrected = r * red_boost
            g_corrected = g * green_dampen
            b_corrected = b * blue_boost
            
            # Merge channels and convert back
            corrected = cv2.merge([b_corrected, g_corrected, r_corrected])
            corrected = np.clip(corrected, 0, 255).astype(np.uint8)
            
            self.logger.info(f"Magenta compensation applied: factor={compensation_factor:.2f}, "
                           f"red_boost={red_boost:.2f}, green_dampen={green_dampen:.2f}")
            
            return corrected
            
        except Exception as e:
            self.logger.error(f"Magenta compensation failed: {e}")
            return image_bgr
    
    def apply_lake_attenuation_correction(self, image_bgr: np.ndarray, 
                                        params: ProcessingParameters) -> np.ndarray:
        """
        Apply lake-specific attenuation correction using Beer-Lambert law.
        
        Args:
            image_bgr: Input image in BGR format
            params: Processing parameters with lake attenuation coefficients
            
        Returns:
            Image with lake attenuation correction applied
        """
        if image_bgr is None:
            return image_bgr
        
        try:
            img_float = image_bgr.astype(np.float32) / 255.0
            
            # Use lake-specific attenuation coefficients
            atten_r = params.lake_attenuation_red
            atten_g = params.lake_attenuation_green  
            atten_b = params.lake_attenuation_blue
            
            # Estimate depth proxy from image darkness
            gray = cv2.cvtColor((img_float * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
            depth_proxy = 1.0 - (np.mean(gray) / 255.0)  # Darker = deeper
            depth_factor = max(0.1, min(1.5, depth_proxy * 2.0))  # More moderate depth influence
            
            # Apply Beer-Lambert correction: I = I0 * exp(-c * d)
            # Inverse: I0 = I / exp(-c * d) = I * exp(c * d)
            b, g, r = cv2.split(img_float)
            
            r_corrected = r * np.exp(atten_r * depth_factor)
            g_corrected = g * np.exp(atten_g * depth_factor)
            b_corrected = b * np.exp(atten_b * depth_factor)
            
            # Merge and normalize
            corrected = cv2.merge([b_corrected, g_corrected, r_corrected])
            corrected = np.clip(corrected * 255, 0, 255).astype(np.uint8)
            
            self.logger.info(f"Lake attenuation correction applied: depth_factor={depth_factor:.2f}, "
                           f"coefficients=R:{atten_r:.2f}, G:{atten_g:.2f}, B:{atten_b:.2f}")
            
            return corrected
            
        except Exception as e:
            self.logger.error(f"Lake attenuation correction failed: {e}")
            return image_bgr
    
    def enhance_dehazing_for_turbidity(self, image_bgr: np.ndarray, 
                                     base_strength: float, 
                                     turbidity_factor: float) -> Tuple[np.ndarray, float]:
        """
        Enhance dehazing for turbid green water with increased backscattering.
        
        Args:
            image_bgr: Input image in BGR format
            base_strength: Base dehazing strength from parameters
            turbidity_factor: Additional turbidity compensation factor
            
        Returns:
            Tuple of (processed_image, adjusted_strength)
        """
        if image_bgr is None:
            return image_bgr, base_strength
        
        try:
            # Calculate enhanced dehazing strength for turbid water
            enhanced_strength = base_strength * turbidity_factor
            enhanced_strength = min(2.0, enhanced_strength)  # Cap at maximum
            
            # Apply stronger dark channel processing for turbid conditions
            # This is a simplified approach - the actual dehazing will be done
            # by the main processor with the adjusted strength
            
            self.logger.info(f"Enhanced dehazing for turbidity: "
                           f"base={base_strength:.2f}, enhanced={enhanced_strength:.2f}")
            
            return image_bgr, enhanced_strength
            
        except Exception as e:
            self.logger.error(f"Enhanced dehazing failed: {e}")
            return image_bgr, base_strength
    
    def process_green_water_image(self, image_bgr: np.ndarray, 
                                params: ProcessingParameters) -> np.ndarray:
        """
        Complete green water processing pipeline.
        
        Args:
            image_bgr: Input image in BGR format
            params: Processing parameters
            
        Returns:
            Processed image optimized for green water conditions
        """
        if image_bgr is None:
            return image_bgr
        
        try:
            result = image_bgr.copy()
            
            # Step 1: Detect water type if auto mode
            if params.water_type == "auto" and params.green_water_detection:
                water_analysis = self.detect_water_type(result)
                detected_type = water_analysis['type']
                self.logger.info(f"Auto-detected water type: {detected_type}")
            else:
                detected_type = params.water_type
            
            # Step 2: Apply green water corrections if needed
            if detected_type == "lake":
                self.logger.info("Applying green water corrections")
                
                # Apply magenta compensation to reduce green cast
                if params.magenta_compensation > 1.0:
                    result = self.apply_magenta_compensation(result, params.magenta_compensation)
                
                # Apply lake-specific attenuation correction
                result = self.apply_lake_attenuation_correction(result, params)
                
                self.logger.info("Green water corrections completed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Green water processing failed: {e}")
            return image_bgr
    
    def get_optimized_parameters_for_green_water(self, 
                                               base_params: ProcessingParameters) -> ProcessingParameters:
        """
        Get optimized parameters for green water processing.
        
        Args:
            base_params: Base processing parameters
            
        Returns:
            Optimized parameters for green water
        """
        # Create a copy to avoid modifying the original
        optimized = ProcessingParameters(
            # Copy all base parameters
            enable_white_balance=base_params.enable_white_balance,
            wb_method=base_params.wb_method,
            white_balance_strength=base_params.white_balance_strength * 1.2,  # Stronger WB
            robust_lower=base_params.robust_lower,
            robust_upper=base_params.robust_upper,
            retinex_percentile=base_params.retinex_percentile,
            
            enable_red_channel=base_params.enable_red_channel,
            red_scale=base_params.red_scale * 1.3,  # More red compensation
            enable_dehaze=base_params.enable_dehaze,
            dehaze_strength=base_params.dehaze_strength * 1.5,  # Stronger dehazing
            enable_saturation=base_params.enable_saturation,
            saturation=base_params.saturation * 1.1,  # Slight saturation boost
            
            enable_clahe=base_params.enable_clahe,
            clahe_clip=base_params.clahe_clip * 1.2,  # Enhanced contrast
            
            enable_fusion=base_params.enable_fusion,
            fusion_method=base_params.fusion_method,
            unsharp_amount=base_params.unsharp_amount,
            unsharp_radius=base_params.unsharp_radius,
            fusion_balance=base_params.fusion_balance,
            
            # Green water specific optimizations
            water_type="lake",
            green_water_detection=True,
            magenta_compensation=1.4,  # Moderate magenta compensation
            lake_attenuation_red=0.45,
            lake_attenuation_green=0.25,
            lake_attenuation_blue=0.8,
            enhanced_dehazing=True,
            turbidity_compensation=1.3
        )
        
        self.logger.info("Generated optimized parameters for green water")
        return optimized
