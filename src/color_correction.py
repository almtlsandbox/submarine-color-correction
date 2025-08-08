import cv2
import numpy as np
import logging
import os
from datetime import datetime

# Setup logging
def setup_logging(log_file=None):
    """Setup logging for image processing operations."""
    if log_file is None:
        log_file = f"color_correction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also print to console
        ]
    )
    return logging.getLogger(__name__)

# Global logger instance
logger = setup_logging()

def white_patch_retinex(img, percentile=100):
    """White Patch Retinex white balancing. Scales each channel so its brightest value (or given percentile) is 255."""
    logger.info(f"Starting White Patch Retinex with percentile={percentile}")
    
    result = img.copy().astype(np.float32)
    gains = []
    
    for c in range(3):
        # Use the given percentile to avoid outliers (default 100 for max)
        max_val = np.percentile(result[:, :, c], percentile)
        gain = 255.0 / max_val if max_val > 0 else 1.0
        gains.append(gain)
        if max_val > 0:
            result[:, :, c] = result[:, :, c] * gain
    
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    logger.info(f"White Patch Retinex - Gains: B={gains[0]:.3f}, G={gains[1]:.3f}, R={gains[2]:.3f}")
    logger.info(f"White Patch Retinex - Max values before correction: B={np.percentile(img[:,:,0], percentile):.1f}, "
                f"G={np.percentile(img[:,:,1], percentile):.1f}, R={np.percentile(img[:,:,2], percentile):.1f}")
    
    return result

def robust_channel_mean(channel, lower=10, upper=90):
    """Compute the mean between the lower and upper percentiles (deciles) of a channel."""
    flat = channel.flatten()
    low = np.percentile(flat, lower)
    high = np.percentile(flat, upper)
    trimmed = flat[(flat >= low) & (flat <= high)]
    return np.mean(trimmed)

def white_balance(img, strength=1.0, lower=10, upper=90):
    logger.info(f"Starting Robust White Balance with strength={strength}, percentiles=[{lower}, {upper}]")
    
    result = img.copy().astype(np.float32)
    # Use robust mean for each channel
    avg_b = robust_channel_mean(result[:, :, 0], lower, upper)
    avg_g = robust_channel_mean(result[:, :, 1], lower, upper)
    avg_r = robust_channel_mean(result[:, :, 2], lower, upper)
    avg_gray = (avg_b + avg_g + avg_r) / 3

    # Calculate gains
    gain_b = avg_gray / avg_b if avg_b > 0 else 1.0
    gain_g = avg_gray / avg_g if avg_g > 0 else 1.0
    gain_r = avg_gray / avg_r if avg_r > 0 else 1.0

    result[:, :, 0] = result[:, :, 0] * gain_b
    result[:, :, 1] = result[:, :, 1] * gain_g
    result[:, :, 2] = result[:, :, 2] * gain_r
    result = np.clip(result, 0, 255)

    # Blend with original based on strength
    blended = img.astype(np.float32) * (1 - strength) + result * strength
    blended = np.clip(blended, 0, 255).astype(np.uint8)
    
    logger.info(f"Robust White Balance - Channel means: B={avg_b:.1f}, G={avg_g:.1f}, R={avg_r:.1f}")
    logger.info(f"Robust White Balance - Gains: B={gain_b:.3f}, G={gain_g:.3f}, R={gain_r:.3f}")
    logger.info(f"Robust White Balance - Gray average: {avg_gray:.1f}")
    
    return blended

def gray_world(img, strength=1.0, lower=10, upper=90):
    """Gray World white balancing. Scales each channel to match grayscale mean."""
    logger.info(f"Starting Gray World White Balance with strength={strength}, percentiles=[{lower}, {upper}]")
    
    result = img.copy().astype(np.float32)
    
    # Convert to grayscale for reference mean
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    gray_mean = robust_channel_mean(gray, lower, upper)
    
    # Get robust mean for each channel
    mean_b = robust_channel_mean(result[:, :, 0], lower, upper)
    mean_g = robust_channel_mean(result[:, :, 1], lower, upper)
    mean_r = robust_channel_mean(result[:, :, 2], lower, upper)
    
    # Calculate gains
    gain_b = gray_mean / mean_b if mean_b > 0 else 1.0
    gain_g = gray_mean / mean_g if mean_g > 0 else 1.0
    gain_r = gray_mean / mean_r if mean_r > 0 else 1.0
    
    # Scale each channel to match grayscale mean
    if mean_b > 0:
        result[:, :, 0] = result[:, :, 0] * gain_b
    if mean_g > 0:
        result[:, :, 1] = result[:, :, 1] * gain_g
    if mean_r > 0:
        result[:, :, 2] = result[:, :, 2] * gain_r
    
    result = np.clip(result, 0, 255)
    
    # Blend with original based on strength
    blended = img.astype(np.float32) * (1 - strength) + result * strength
    blended = np.clip(blended, 0, 255).astype(np.uint8)
    
    logger.info(f"Gray World - Channel means: B={mean_b:.1f}, G={mean_g:.1f}, R={mean_r:.1f}")
    logger.info(f"Gray World - Gains: B={gain_b:.3f}, G={gain_g:.3f}, R={gain_r:.3f}")
    logger.info(f"Gray World - Gray reference mean: {gray_mean:.1f}")
    
    return blended

def enhance_red_channel(img, scale=1.5):
    logger.info(f"Enhancing red channel with scale={scale}")
    result = img.copy().astype(np.float32)
    
    # Log original red channel statistics
    original_red_mean = np.mean(result[:, :, 2])
    
    result[:, :, 2] = result[:, :, 2] * scale
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    enhanced_red_mean = np.mean(result[:, :, 2])
    logger.info(f"Red channel enhancement - Original mean: {original_red_mean:.1f}, Enhanced mean: {enhanced_red_mean:.1f}")
    
    return result

def apply_clahe(img):
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to Lab color space."""
    logger.info("Starting CLAHE application")
    
    # Convert to LAB color space
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l_clahe = clahe.apply(l)
    
    # Merge channels and convert back to BGR
    lab_clahe = cv2.merge([l_clahe, a, b])
    result = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
    
    logger.info("CLAHE application completed")
    return result

def apply_clahe_with_clip(img, clip_limit=2.0):
    """Apply CLAHE with custom clip limit."""
    logger.info(f"Starting CLAHE application with clip_limit={clip_limit}")
    
    # Convert to LAB color space
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8,8))
    l_clahe = clahe.apply(l)
    
    # Merge channels and convert back to BGR
    lab_clahe = cv2.merge([l_clahe, a, b])
    result = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
    
    logger.info("CLAHE application completed")
    return result

def enhance_saturation(img, factor=1.2):
    """Enhance saturation by given factor."""
    logger.info(f"Starting saturation enhancement with factor={factor}")
    
    # Convert to HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    
    # Scale saturation channel
    hsv[:, :, 1] = hsv[:, :, 1] * factor
    
    # Clip to valid range
    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
    
    # Convert back to BGR
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    
    logger.info("Saturation enhancement completed")
    return result

def dark_channel(img, size=15):
    min_img = cv2.min(cv2.min(img[:, :, 0], img[:, :, 1]), img[:, :, 2])
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (size, size))
    dark = cv2.erode(min_img, kernel)
    return dark

def estimate_atmospheric_light(img, dark):
    h, w = img.shape[:2]
    num_pixels = h * w
    num_brightest = int(max(num_pixels * 0.001, 1))
    dark_vec = dark.reshape(num_pixels)
    img_vec = img.reshape(num_pixels, 3)
    indices = dark_vec.argsort()[-num_brightest:]
    atmo = np.mean(img_vec[indices], axis=0)
    return atmo

def estimate_transmission(img, atmo, omega=0.95, size=15):
    normed = img / atmo
    transmission = 1 - omega * dark_channel(normed, size)
    return np.clip(transmission, 0.1, 1)

def recover(img, atmo, transmission):
    result = np.empty_like(img, dtype=np.float32)
    for c in range(3):
        result[:, :, c] = (img[:, :, c] - atmo[c]) / transmission + atmo[c]
    result = np.clip(result, 0, 255).astype(np.uint8)
    return result

def dehaze(img, omega=0.95):
    logger.info(f"Starting dehazing with omega={omega}")
    
    dark = dark_channel(img)
    atmo = estimate_atmospheric_light(img, dark)
    transmission = estimate_transmission(img.astype(np.float32), atmo, omega=omega)
    transmission = cv2.blur(transmission, (15, 15))
    result = recover(img, atmo, transmission)
    
    # Log dehazing statistics
    dark_mean = np.mean(dark)
    transmission_mean = np.mean(transmission)
    logger.info(f"Dehazing - Atmospheric light: B={atmo[0]:.1f}, G={atmo[1]:.1f}, R={atmo[2]:.1f}")
    logger.info(f"Dehazing - Dark channel mean: {dark_mean:.1f}")
    logger.info(f"Dehazing - Transmission mean: {transmission_mean:.3f}")
    
    return result

def unsharp_mask(img, amount=1.0, radius=1.0):
    """Apply unsharp masking for image sharpening."""
    # Create Gaussian blur
    blurred = cv2.GaussianBlur(img, (0, 0), radius)
    
    # Create sharpened image
    sharpened = cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)

def hsv_histogram_equalization(img):
    """Apply histogram equalization in HSV color space."""
    # Convert to HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # Apply histogram equalization to the V channel
    v_eq = cv2.equalizeHist(v)
    
    # Merge channels and convert back to BGR
    hsv_eq = cv2.merge([h, s, v_eq])
    result = cv2.cvtColor(hsv_eq, cv2.COLOR_HSV2BGR)
    return result

def average_fusion(img1, img2):
    """Average fusion of two images."""
    logger.info("Applying average fusion")
    result = cv2.addWeighted(img1.astype(np.float32), 0.5, img2.astype(np.float32), 0.5, 0)
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    # Log fusion statistics
    img1_mean = np.mean(img1)
    img2_mean = np.mean(img2)
    result_mean = np.mean(result)
    logger.info(f"Average fusion - Input1 mean: {img1_mean:.1f}, Input2 mean: {img2_mean:.1f}, Result mean: {result_mean:.1f}")
    
    return result

def pca_fusion(img1, img2):
    """PCA-based fusion of two images."""
    logger.info("Applying PCA fusion")
    
    # Convert images to float
    img1_f = img1.astype(np.float32)
    img2_f = img2.astype(np.float32)
    
    h, w, c = img1_f.shape
    result = np.zeros_like(img1_f)
    
    coefficients = []
    
    # Process each channel separately
    for channel in range(c):
        # Flatten channel data
        ch1 = img1_f[:, :, channel].flatten()
        ch2 = img2_f[:, :, channel].flatten()
        
        # Create data matrix (2 x N)
        data = np.array([ch1, ch2])
        
        # Center the data
        mean1, mean2 = np.mean(ch1), np.mean(ch2)
        data[0] -= mean1
        data[1] -= mean2
        
        # Compute covariance matrix
        cov_matrix = np.cov(data)
        
        # Compute eigenvalues and eigenvectors
        eigenvals, eigenvecs = np.linalg.eig(cov_matrix)
        
        # Get coefficients from the eigenvector corresponding to largest eigenvalue
        if eigenvals[0] >= eigenvals[1]:
            coeff = eigenvecs[:, 0]
        else:
            coeff = eigenvecs[:, 1]
        
        # Normalize coefficients
        coeff = coeff / np.sum(coeff)
        coefficients.append(coeff)
        
        # Apply fusion
        ch1_orig = img1_f[:, :, channel].flatten()
        ch2_orig = img2_f[:, :, channel].flatten()
        fused_ch = coeff[0] * ch1_orig + coeff[1] * ch2_orig
        
        # Reshape back to image dimensions
        result[:, :, channel] = fused_ch.reshape(h, w)
    
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    # Log PCA fusion statistics
    img1_mean = np.mean(img1)
    img2_mean = np.mean(img2)
    result_mean = np.mean(result)
    logger.info(f"PCA fusion - Input1 mean: {img1_mean:.1f}, Input2 mean: {img2_mean:.1f}, Result mean: {result_mean:.1f}")
    logger.info(f"PCA fusion - Coefficients: B=[{coefficients[0][0]:.3f}, {coefficients[0][1]:.3f}], "
                f"G=[{coefficients[1][0]:.3f}, {coefficients[1][1]:.3f}], "
                f"R=[{coefficients[2][0]:.3f}, {coefficients[2][1]:.3f}]")
    
    return result


def weighted_fusion(img1, img2, weight=0.5):
    """Weighted fusion of two images with adjustable balance.
    
    Args:
        img1: First image (typically dehazed path)
        img2: Second image (typically detail-enhanced path) 
        weight: Weight for img1 (0.0=pure img1, 1.0=pure img2)
    """
    logger.info(f"Applying weighted fusion with weight={weight:.3f} (0.0=dehaze emphasis, 1.0=detail emphasis)")
    
    result = cv2.addWeighted(img1.astype(np.float32), weight, img2.astype(np.float32), 1.0 - weight, 0)
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    # Log fusion statistics
    img1_mean = np.mean(img1)
    img2_mean = np.mean(img2)
    result_mean = np.mean(result)
    logger.info(f"Weighted fusion - Dehazed path mean: {img1_mean:.1f} (weight={weight:.3f}), "
                f"Detail path mean: {img2_mean:.1f} (weight={1.0-weight:.3f}), Result mean: {result_mean:.1f}")
    
    return result


def correct_underwater_image(image_path, output_path, wb_method="robust", wb_kwargs=None, use_fusion=False, fusion_method="average"):
    """
    wb_method: 'robust' (default), 'retinex', or 'grayworld'
    wb_kwargs: dict of extra arguments for the white balance function
    use_fusion: whether to apply dual-path fusion processing
    fusion_method: 'average' or 'pca' fusion method
    """
    logger.info("="*60)
    logger.info(f"STARTING IMAGE PROCESSING: {os.path.basename(image_path)}")
    logger.info("="*60)
    
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Failed to load image: {image_path}")
        raise ValueError("Image not found or invalid image path.")

    # Log original image statistics
    h, w, c = img.shape
    original_means = np.mean(img, axis=(0,1))
    original_stds = np.std(img, axis=(0,1))
    logger.info(f"Original image - Size: {w}x{h}x{c}")
    logger.info(f"Original image - Channel means: B={original_means[0]:.1f}, G={original_means[1]:.1f}, R={original_means[2]:.1f}")
    logger.info(f"Original image - Channel stds: B={original_stds[0]:.1f}, G={original_stds[1]:.1f}, R={original_stds[2]:.1f}")

    if wb_kwargs is None:
        wb_kwargs = {}

    # White balancing step
    logger.info(f"\nSTEP 1: White balancing using {wb_method.upper()} method")
    if wb_method == "retinex":
        img = white_patch_retinex(img, **wb_kwargs)
    elif wb_method == "grayworld":
        img = gray_world(img, **wb_kwargs)
    else:
        img = white_balance(img, **wb_kwargs)

    # Red channel enhancement step
    logger.info(f"\nSTEP 2: Red channel enhancement")
    img = enhance_red_channel(img, scale=1.8)
    
    # Dehazing step
    logger.info(f"\nSTEP 3: Dehazing")
    img = dehaze(img)
    
    # Fusion or CLAHE step
    if use_fusion:
        logger.info(f"\nSTEP 4: Fusion processing using {fusion_method.upper()} method")
        # Create two paths: sharpened and contrast enhanced
        logger.info("Creating sharpened path...")
        sharpened = unsharp_mask(img, amount=1.0, radius=1.0)
        logger.info("Creating contrast enhanced path...")
        contrast_enhanced = hsv_histogram_equalization(img)
        contrast_enhanced = apply_clahe(contrast_enhanced)
        
        # Apply fusion
        if fusion_method == "pca":
            img = pca_fusion(sharpened, contrast_enhanced)
        else:
            img = average_fusion(sharpened, contrast_enhanced)
    else:
        logger.info(f"\nSTEP 4: CLAHE contrast enhancement")
        img = apply_clahe(img)
    
    # Log final image statistics
    final_means = np.mean(img, axis=(0,1))
    final_stds = np.std(img, axis=(0,1))
    logger.info(f"\nFINAL RESULT:")
    logger.info(f"Final image - Channel means: B={final_means[0]:.1f}, G={final_means[1]:.1f}, R={final_means[2]:.1f}")
    logger.info(f"Final image - Channel stds: B={final_stds[0]:.1f}, G={final_stds[1]:.1f}, R={final_stds[2]:.1f}")
    logger.info(f"Mean brightness change: {np.mean(final_means) - np.mean(original_means):+.1f}")
    
    cv2.imwrite(output_path, img)
    logger.info(f"Image saved to: {output_path}")
    logger.info("="*60)

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="Underwater image color correction")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output image path")
    parser.add_argument("--wb", choices=["robust", "retinex", "grayworld"], default="robust", help="White balance method")
    parser.add_argument("--wb_percentile", type=float, default=100, help="Percentile for retinex (default 100)")
    parser.add_argument("--use_fusion", action="store_true", help="Enable dual-path fusion processing")
    parser.add_argument("--fusion_method", choices=["average", "pca"], default="average", help="Fusion method")
    parser.add_argument("--log_file", help="Custom log file path (default: auto-generated with timestamp)")
    args = parser.parse_args()

    # Setup logging with custom file if provided
    if args.log_file:
        setup_logging(args.log_file)
    
    wb_kwargs = {}
    if args.wb == "retinex":
        wb_kwargs["percentile"] = args.wb_percentile

    correct_underwater_image(args.input, args.output, wb_method=args.wb, wb_kwargs=wb_kwargs, 
                           use_fusion=args.use_fusion, fusion_method=args.fusion_method)