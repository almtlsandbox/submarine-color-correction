from PIL import Image

def load_image(path):
    """
    Loads an image from the given path and returns a PIL Image object in RGB mode.
    """
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

def save_image(pil_img, path):
    """
    Saves a PIL Image object to the given path.
"""
    pil_img.save(path)