"""
Auto-tuning engine for intelligent parameter optimization.
Analyzes image characteristics and suggests optimal parameters.
Now includes green water (lake/freshwater) detection and specialized tuning.
"""
import cv2
import numpy as np
import logging
from typing import Dict, Any, Optional

from models.processing_params import ProcessingParameters, AutoTuneResult
from core.green_water_processor import GreenWaterProcessor
import color_correction as cc


class AutoTuner:
    """Intelligent parameter tuning based on image analysis."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.green_water_processor = GreenWaterProcessor()
    
    def auto_tune(self, image_bgr: np.ndarray, current_params: Optional[ProcessingParameters] = None) -> AutoTuneResult:
        """
        Analyze image and suggest optimal parameters.
        
        Args:
            image_bgr: Input image in BGR format
            current_params: Current processing parameters (optional, uses defaults if None)
            
        Returns:
            AutoTuneResult with optimized parameters and analysis
        """
        if image_bgr is None:
            raise ValueError("Input image is None")
        
        try:
            self.logger.info("Starting auto-tune analysis")
            
            # Start with current parameters or defaults
            if current_params is None:
                params = ProcessingParameters()
            else:
                # Preserve user selections like water type and auto detection settings
                params = current_params
            
            analysis_notes = {}
            
            # Perform image analysis
            analysis = self._analyze_image(image_bgr)
            
            # Determine water type based on user preference
            if current_params and not current_params.green_water_detection:
                # User has disabled auto detection - use their manual selection
                if current_params.water_type == 'lake':
                    self.logger.info("Using manual lake water selection (auto-detection disabled)")
                    # Create synthetic water analysis for lake mode
                    water_analysis = {
                        'type': 'lake',
                        'confidence': 1.0,  # High confidence since it's user-selected
                        'green_dominance': 0.5,  # Assume moderate green dominance
                        'green_ratio': 0.4,
                        'g_to_r_ratio': 1.5,
                        'turbidity_indicator': 0.3
                    }
                    analysis['water_type'] = water_analysis
                    return self._tune_for_green_water(analysis, current_params)
                else:
                    self.logger.info("Using manual ocean water selection (auto-detection disabled)")
                    # Create synthetic water analysis for ocean mode  
                    water_analysis = {
                        'type': 'ocean',
                        'confidence': 1.0,
                        'green_dominance': 0.1,
                        'green_ratio': 0.3,
                        'g_to_r_ratio': 1.0,
                        'turbidity_indicator': 0.1
                    }
                    analysis['water_type'] = water_analysis
                    return self._tune_for_ocean_water(analysis, current_params)
            else:
                # Auto detection is enabled or not specified - detect water type
                water_analysis = self.green_water_processor.detect_water_type(image_bgr)
                analysis['water_type'] = water_analysis
                
                # Determine if we need green water optimizations
                is_green_water = (water_analysis['type'] == 'lake' and 
                                water_analysis['confidence'] > 0.6)
                
                if is_green_water:
                    self.logger.info(f"Green water detected (confidence: {water_analysis['confidence']:.2f}), "
                                   "applying specialized tuning")
                    return self._tune_for_green_water(analysis, current_params)
                else:
                    self.logger.info("Ocean/blue water detected, applying standard tuning")
                    return self._tune_for_ocean_water(analysis, current_params)
        
        except Exception as e:
            self.logger.error(f"Auto-tune failed: {str(e)}")
            raise
    
    def _tune_for_green_water(self, analysis: Dict[str, Any], base_params: Optional[ProcessingParameters] = None) -> AutoTuneResult:
        """Specialized tuning for green water (lake/freshwater) conditions."""
        # Start with provided parameters or defaults
        if base_params is not None:
            params = base_params
            # Preserve user's water type and detection settings
            original_water_type = params.water_type
            original_detection_setting = params.green_water_detection
        else:
            params = ProcessingParameters()
            original_water_type = None
            original_detection_setting = None
            
        analysis_notes = {}
        
        # Set water type (preserve user selection if auto-detection is disabled)
        if original_water_type is not None and original_detection_setting is not None and not original_detection_setting:
            params.water_type = original_water_type
            params.green_water_detection = original_detection_setting
        else:
            params.water_type = "lake"
            # Only enable auto-detection if not explicitly disabled by user
            if original_detection_setting is None:
                params.green_water_detection = True
            else:
                params.green_water_detection = original_detection_setting
        
        # Get water analysis for adaptive tuning
        water_analysis = analysis['water_type']
        confidence = water_analysis.get('confidence', 0.0)
        green_dominance = water_analysis.get('green_dominance', 0.0)
        
        # Reduce aggressiveness for uncertain detections or mild green cast
        aggressiveness_factor = 1.0
        if confidence < 0.8:
            aggressiveness_factor *= 0.8
            analysis_notes['confidence_note'] = f"Reduced aggressiveness for uncertain detection (confidence: {confidence:.2f})"
        
        if green_dominance < 0.3:
            aggressiveness_factor *= 0.7
            analysis_notes['dominance_note'] = f"Reduced aggressiveness for mild green cast (dominance: {green_dominance:.2f})"
        
        # Enhanced white balance for green cast removal
        wb_params = self._tune_green_water_white_balance(analysis)
        params.white_balance_strength = wb_params['strength'] * aggressiveness_factor
        analysis_notes['white_balance'] = wb_params['note']
        
        # Enhanced red channel for green water
        red_params = self._tune_green_water_red_channel(analysis)
        params.red_scale = max(1.0, red_params['red_scale'] * aggressiveness_factor)
        analysis_notes['red_channel'] = red_params['note']
        
        # Magenta compensation
        magenta_params = self._tune_magenta_compensation(analysis)
        params.magenta_compensation = max(1.0, magenta_params['compensation'] * aggressiveness_factor)
        analysis_notes['magenta_compensation'] = magenta_params['note']
        
        # Smart adjustment: If strong magenta compensation is applied, reduce/disable red channel and dehaze
        # to prevent over-correction since magenta compensation already boosts red channels
        if params.magenta_compensation > 1.3:
            # Reduce red channel enhancement since magenta compensation already boosts red
            original_red_scale = params.red_scale
            params.red_scale = min(params.red_scale, 1.2)  # Cap at modest enhancement
            params.enable_red_channel = params.red_scale > 1.05  # Disable if very minimal
            
            analysis_notes['red_channel'] += f" → Reduced from {original_red_scale:.2f} to {params.red_scale:.2f} due to strong magenta compensation"
            if not params.enable_red_channel:
                analysis_notes['red_channel'] += " (disabled)"
        
        # Enhanced dehazing for turbidity
        dehaze_params = self._tune_turbid_water_dehazing(analysis)
        
        # Smart adjustment: Reduce dehaze strength if strong magenta compensation is applied
        # since magenta compensation addresses the green cast that's often mistaken for haze
        if params.magenta_compensation > 1.4:
            original_dehaze = dehaze_params['dehaze_strength']
            dehaze_params['dehaze_strength'] *= 0.7  # Reduce by 30%
            params.enable_dehaze = dehaze_params['dehaze_strength'] > 0.3  # Disable if very weak
            
            analysis_notes['dehazing'] = dehaze_params['note'] + f" → Reduced from {original_dehaze:.2f} to {dehaze_params['dehaze_strength']:.2f} due to strong magenta compensation"
            if not params.enable_dehaze:
                analysis_notes['dehazing'] += " (disabled)"
        else:
            analysis_notes['dehazing'] = dehaze_params['note']
        
        params.dehaze_strength = dehaze_params['dehaze_strength']
        params.enhanced_dehazing = True
        params.turbidity_compensation = dehaze_params['turbidity_compensation'] * aggressiveness_factor
        
        # Enhanced saturation and contrast
        sat_params = self._tune_green_water_saturation(analysis)
        params.saturation = max(1.0, sat_params['saturation'] * aggressiveness_factor)
        analysis_notes['saturation'] = sat_params['note']
        
        clahe_params = self._tune_green_water_clahe(analysis)
        params.clahe_clip = clahe_params['clahe_clip']
        analysis_notes['clahe'] = clahe_params['note']
        
        # Set lake attenuation coefficients
        params.lake_attenuation_red = 0.45
        params.lake_attenuation_green = 0.25
        params.lake_attenuation_blue = 0.8
        
        # Calculate confidence
        confidence = self._calculate_green_water_confidence(analysis)
        
        return AutoTuneResult(
            parameters=params,
            confidence=confidence,
            analysis_notes=analysis_notes
        )
    
    def _tune_for_ocean_water(self, analysis: Dict[str, Any], base_params: Optional[ProcessingParameters] = None) -> AutoTuneResult:
        """Standard tuning for ocean/blue water conditions."""
        # Start with provided parameters or defaults
        if base_params is not None:
            params = base_params
            # Preserve user's water type and detection settings
            original_water_type = params.water_type
            original_detection_setting = params.green_water_detection
        else:
            params = ProcessingParameters()
            original_water_type = None
            original_detection_setting = None
            
        analysis_notes = {}
        
        # Set water type (preserve user selection if auto-detection is disabled)
        if original_water_type is not None and original_detection_setting is not None and not original_detection_setting:
            params.water_type = original_water_type
            params.green_water_detection = original_detection_setting
        else:
            params.water_type = "ocean"
            # Only enable auto-detection if not explicitly disabled by user
            if original_detection_setting is None:
                params.green_water_detection = True
            else:
                params.green_water_detection = original_detection_setting
        
        # Standard tuning (existing logic)
        red_params = self._tune_red_channel(analysis)
        params.red_scale = red_params['red_scale']
        analysis_notes['red_channel'] = red_params['note']
        
        dehaze_params = self._tune_dehazing(analysis)
        params.dehaze_strength = dehaze_params['dehaze_strength']
        analysis_notes['dehazing'] = dehaze_params['note']
        
        sat_params = self._tune_saturation(analysis)
        params.saturation = sat_params['saturation']
        analysis_notes['saturation'] = sat_params['note']
        
        clahe_params = self._tune_clahe(analysis)
        params.clahe_clip = clahe_params['clahe_clip']
        analysis_notes['clahe'] = clahe_params['note']
        
        wb_params = self._tune_white_balance(analysis)
        params.white_balance_strength = wb_params['strength']
        analysis_notes['white_balance'] = wb_params['note']
        
        fusion_params = self._tune_fusion(analysis)
        params.fusion_balance = fusion_params['balance']
        params.unsharp_amount = fusion_params['unsharp_amount']
        params.unsharp_radius = fusion_params['unsharp_radius']
        analysis_notes['fusion'] = fusion_params['note']
        
        # Calculate confidence
        confidence = self._calculate_confidence(analysis)
        
        return AutoTuneResult(
            parameters=params,
            confidence=confidence,
            analysis_notes=analysis_notes
        )
        
    # Green water specific tuning methods
    def _tune_green_water_white_balance(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced white balance tuning for green water."""
        water_analysis = analysis['water_type']
        green_dominance = water_analysis.get('green_dominance', 0.0)
        
        # More moderate white balance adjustment for green water
        base_strength = 1.0
        green_boost = green_dominance * 0.4  # Reduced from 0.8
        strength = min(1.3, base_strength + green_boost)  # Reduced max from 1.8
        
        note = f"Enhanced WB for green water (dominance: {green_dominance:.2f}, strength: {strength:.2f})"
        return {'strength': strength, 'note': note}
    
    def _tune_green_water_red_channel(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced red channel tuning for green water."""
        water_analysis = analysis['water_type']
        g_to_r_ratio = water_analysis.get('g_to_r_ratio', 1.0)
        
        # More balanced red scaling for green-dominant images
        base_scale = 1.2  # Reduced from 1.4
        green_compensation = max(0, (g_to_r_ratio - 1.0) * 0.3)  # Reduced from 0.5
        red_scale = min(1.6, base_scale + green_compensation)  # Reduced max from 2.2
        
        note = f"Enhanced red for green water (G/R ratio: {g_to_r_ratio:.2f}, scale: {red_scale:.2f})"
        return {'red_scale': red_scale, 'note': note}
    
    def _tune_magenta_compensation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Tune magenta compensation to counteract green cast."""
        water_analysis = analysis['water_type']
        green_ratio = water_analysis.get('green_ratio', 0.33)
        green_dominance = water_analysis.get('green_dominance', 0.0)
        
        # More adaptive compensation based on both green content and dominance
        if green_dominance > 0.5 and green_ratio > 0.4:
            compensation = 1.4  # Reduced from 1.6
            note = f"Strong magenta compensation for high green dominance ({green_dominance:.2f})"
        elif green_dominance > 0.3 or green_ratio > 0.37:
            compensation = 1.2  # Reduced from 1.3
            note = f"Medium magenta compensation for moderate green content (dom:{green_dominance:.2f}, ratio:{green_ratio:.2f})"
        else:
            compensation = 1.0  # Reduced from 1.1
            note = f"Minimal magenta compensation for low green content (dom:{green_dominance:.2f}, ratio:{green_ratio:.2f})"
        
        return {'compensation': compensation, 'note': note}
    
    def _tune_turbid_water_dehazing(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced dehazing tuning for turbid green water."""
        water_analysis = analysis['water_type']
        turbidity = water_analysis.get('turbidity_indicator', 0.0)
        haze_level = analysis.get('haze_level', 0.0)
        
        # More moderate dehazing for turbid conditions
        base_strength = max(0.5, haze_level * 1.2)  # Reduced from 1.8
        turbidity_boost = turbidity * 0.3  # Reduced from 0.5
        dehaze_strength = min(1.0, base_strength + turbidity_boost)  # Reduced max from 1.8
        
        # More moderate turbidity compensation factor
        turbidity_compensation = min(1.5, 1.0 + turbidity * 0.4)  # Reduced from 2.0 and 0.8
        
        note = f"Enhanced dehazing for turbid water (turbidity: {turbidity:.2f}, strength: {dehaze_strength:.2f})"
        return {
            'dehaze_strength': dehaze_strength,
            'turbidity_compensation': turbidity_compensation,
            'note': note
        }
    
    def _tune_green_water_saturation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced saturation tuning for green water."""
        saturation_mean = analysis.get('saturation_mean', 100)
        
        # More moderate saturation boost for green water
        if saturation_mean < 60:
            saturation = 1.4  # Reduced from 1.6
            note = f"High saturation boost for very desaturated green water ({saturation_mean:.1f})"
        elif saturation_mean < 80:
            saturation = 1.3  # Reduced from 1.4  
            note = f"Medium-high saturation boost for desaturated green water ({saturation_mean:.1f})"
        elif saturation_mean < 100:
            saturation = 1.2  # Same as before
            note = f"Medium saturation boost for green water ({saturation_mean:.1f})"
        else:
            saturation = 1.1  # Reduced from 1.2
            note = f"Light saturation boost for green water ({saturation_mean:.1f})"
        
        return {'saturation': saturation, 'note': note}
    
    def _tune_green_water_clahe(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced CLAHE tuning for green water."""
        contrast = analysis.get('contrast', 300)
        water_analysis = analysis['water_type']
        turbidity = water_analysis.get('turbidity_indicator', 0.0)
        
        # More moderate CLAHE for green water
        base_clip = 2.5  # Reduced from 3.0
        turbidity_boost = turbidity * 0.5  # Reduced from 0.8
        contrast_adjustment = max(0, (400 - contrast) / 300)  # Reduced divisor from 200
        
        clahe_clip = min(3.5, base_clip + turbidity_boost + contrast_adjustment)  # Reduced max from 4.5
        
        note = f"Enhanced CLAHE for green water (turbidity: {turbidity:.2f}, clip: {clahe_clip:.2f})"
        return {'clahe_clip': clahe_clip, 'note': note}
    
    def _calculate_green_water_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence specifically for green water tuning."""
        confidence = 0.6  # Base confidence
        
        water_analysis = analysis['water_type']
        water_confidence = water_analysis.get('confidence', 0.0)
        green_dominance = water_analysis.get('green_dominance', 0.0)
        
        # Higher confidence for clearer green water detection
        if water_confidence > 0.8:
            confidence += 0.2
        elif water_confidence > 0.6:
            confidence += 0.1
        
        # Higher confidence for stronger green dominance
        if green_dominance > 0.2:
            confidence += 0.15
        elif green_dominance > 0.15:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _analyze_image(self, image_bgr: np.ndarray) -> Dict[str, Any]:
        """Perform comprehensive image analysis."""
        analysis = {}
        
        # Convert to float for analysis
        img_float = image_bgr.astype(np.float32)
        
        # Basic statistics
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        analysis['mean_intensity'] = np.mean(gray)
        analysis['std_intensity'] = np.std(gray)
        
        # Color channel analysis
        b, g, r = cv2.split(img_float)
        analysis['channel_means'] = {
            'blue': np.mean(b),
            'green': np.mean(g), 
            'red': np.mean(r)
        }
        analysis['channel_stds'] = {
            'blue': np.std(b),
            'green': np.std(g),
            'red': np.std(r)
        }
        
        # Haze analysis using dark channel
        dark_channel = cc.dark_channel(image_bgr)
        analysis['haze_level'] = np.mean(dark_channel) / 255.0
        analysis['haze_std'] = np.std(dark_channel) / 255.0
        
        # Saturation analysis
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        analysis['saturation_mean'] = np.mean(hsv[:, :, 1])
        analysis['saturation_std'] = np.std(hsv[:, :, 1])
        
        # Contrast analysis
        analysis['contrast'] = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Color cast analysis
        analysis['color_cast'] = np.std(list(analysis['channel_means'].values()))
        
        return analysis
    
    def _tune_red_channel(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Tune red channel enhancement based on color deficiency."""
        red_mean = analysis['channel_means']['red']
        blue_mean = analysis['channel_means']['blue']
        green_mean = analysis['channel_means']['green']
        
        # Calculate red deficiency (less aggressive than original)
        avg_other = (blue_mean + green_mean) / 2
        red_deficiency = max(1.0, (avg_other + 10) / max(red_mean, 1))
        
        # Scale with reduced aggressiveness
        red_scale = min(2.0, max(1.0, red_deficiency * 0.7))
        
        if red_scale > 1.5:
            note = f"Significant red deficiency detected (scale: {red_scale:.2f})"
        elif red_scale > 1.2:
            note = f"Moderate red enhancement applied (scale: {red_scale:.2f})"
        else:
            note = f"Minimal red adjustment needed (scale: {red_scale:.2f})"
        
        return {'red_scale': red_scale, 'note': note}
    
    def _tune_dehazing(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Tune dehazing strength based on haze analysis."""
        haze_level = analysis['haze_level']
        
        # Adjust dehazing strength based on detected haze
        dehaze_strength = min(2.0, max(0.1, haze_level * 2.0))
        
        if haze_level > 0.4:
            note = f"High haze detected (level: {haze_level:.2f}), strong dehazing applied"
        elif haze_level > 0.2:
            note = f"Moderate haze detected (level: {haze_level:.2f}), medium dehazing applied"
        else:
            note = f"Low haze detected (level: {haze_level:.2f}), light dehazing applied"
        
        return {'dehaze_strength': dehaze_strength, 'note': note}
    
    def _tune_saturation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Tune saturation based on color analysis."""
        saturation_mean = analysis['saturation_mean']
        
        # Adjust saturation based on current levels
        if saturation_mean < 80:
            saturation = 1.4  # High boost for very desaturated images
            note = f"Low saturation detected ({saturation_mean:.1f}), high boost applied"
        elif saturation_mean < 120:
            saturation = 1.2  # Medium boost
            note = f"Moderate saturation detected ({saturation_mean:.1f}), medium boost applied"
        else:
            saturation = 1.1  # Light boost
            note = f"Good saturation detected ({saturation_mean:.1f}), light boost applied"
        
        return {'saturation': saturation, 'note': note}
    
    def _tune_clahe(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Tune CLAHE based on contrast analysis."""
        contrast = analysis['contrast']
        std_intensity = analysis['std_intensity']
        
        # Adjust CLAHE based on image contrast
        if contrast < 100:  # Very low contrast
            clahe_clip = 3.5
            note = f"Very low contrast detected ({contrast:.1f}), strong CLAHE applied"
        elif contrast < 300:  # Low contrast
            clahe_clip = 3.0
            note = f"Low contrast detected ({contrast:.1f}), medium CLAHE applied"
        elif contrast < 600:  # Medium contrast
            clahe_clip = 2.5
            note = f"Medium contrast detected ({contrast:.1f}), standard CLAHE applied"
        else:  # High contrast
            clahe_clip = 2.0
            note = f"High contrast detected ({contrast:.1f}), light CLAHE applied"
        
        return {'clahe_clip': clahe_clip, 'note': note}
    
    def _tune_white_balance(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Tune white balance based on color cast analysis."""
        color_cast = analysis['color_cast']
        mean_intensity = analysis['mean_intensity']
        
        # Adjust white balance strength based on color cast and brightness
        if color_cast > 20:
            strength = 1.3
            note = f"Strong color cast detected ({color_cast:.1f}), strong white balance applied"
        elif color_cast > 10:
            strength = 1.1
            note = f"Moderate color cast detected ({color_cast:.1f}), medium white balance applied"
        else:
            strength = 0.9
            note = f"Minimal color cast detected ({color_cast:.1f}), light white balance applied"
        
        # Adjust for image brightness
        brightness_factor = max(0.7, min(1.3, 1.2 - mean_intensity / 255.0))
        strength *= brightness_factor
        
        return {'strength': max(0.5, min(1.5, strength)), 'note': note}
    
    def _tune_fusion(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Tune fusion parameters based on detail vs haze needs."""
        haze_level = analysis['haze_level']
        contrast = analysis['contrast']
        
        # Balance between haze removal and detail enhancement
        haze_indicator = haze_level
        detail_indicator = min(1.0, contrast / 1000.0)
        
        # Fusion balance (0 = more dehazing, 1 = more detail)
        balance = detail_indicator / (haze_indicator + detail_indicator + 0.1)
        
        # Tune unsharp mask parameters
        unsharp_amount = max(0.5, min(2.5, detail_indicator * 2.0))
        unsharp_radius = max(0.5, min(2.0, 1.0 + detail_indicator))
        
        if balance > 0.7:
            note = f"Detail-focused processing (balance: {balance:.2f})"
        elif balance > 0.3:
            note = f"Balanced processing (balance: {balance:.2f})"
        else:
            note = f"Haze-focused processing (balance: {balance:.2f})"
        
        return {
            'balance': balance,
            'unsharp_amount': unsharp_amount,
            'unsharp_radius': unsharp_radius,
            'note': note
        }
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence in auto-tune results based on analysis clarity."""
        # Factors that increase confidence
        confidence = 0.5  # Base confidence
        
        # Clear color cast increases confidence
        color_cast = analysis['color_cast']
        if color_cast > 15:
            confidence += 0.2
        elif color_cast > 8:
            confidence += 0.1
        
        # Clear haze detection increases confidence  
        haze_level = analysis['haze_level']
        if haze_level > 0.3:
            confidence += 0.2
        elif haze_level > 0.15:
            confidence += 0.1
        
        # Good contrast analysis increases confidence
        contrast = analysis['contrast']
        if 100 < contrast < 1000:
            confidence += 0.1
        
        return min(1.0, confidence)
