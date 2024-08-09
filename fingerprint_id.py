import argparse
from typing import List, Tuple
import numpy as np
import math
from loader import Loader
from board import Board
from type_classifier import TypeClassifier
from minutiae_extractor import MinutiaeExtractor

# Constants for image enhancement
ALPHA = 150
Y = 95

def enhance(image: np.ndarray) -> np.ndarray:
    """
    Enhance the fingerprint image by applying contrast adjustment.
    
    Args:
        image (np.ndarray): Input fingerprint image.
    
    Returns:
        np.ndarray: Enhanced fingerprint image.
    """
    mean = np.mean(image)
    variance = np.var(image)
    s = np.sqrt(variance)
    
    enhanced_image = np.where(image < 2, 255, 
                              np.where(Y < s, 
                                       ALPHA + Y * ((image - mean) / s),
                                       ALPHA + Y * ((image - mean) / Y)))
    
    return enhanced_image.astype(np.uint8)

def detect_roi(image: np.ndarray, block_size: int) -> List[List[int]]:
    """
    Detect the Region of Interest (ROI) in the fingerprint image.
    
    Args:
        image (np.ndarray): Input fingerprint image.
        block_size (int): Size of blocks for processing.
    
    Returns:
        List[List[int]]: Binary mask of valid blocks in the ROI.
    """
    width, height = image.shape
    blocks_x, blocks_y = width // block_size, height // block_size
    
    mean = np.zeros((blocks_x, blocks_y))
    std_dev = np.zeros((blocks_x, blocks_y))
    
    for i in range(blocks_x):
        for j in range(blocks_y):
            block = image[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size]
            mean[i, j] = np.mean(block)
            std_dev[i, j] = np.std(block)
    
    max_mean = np.max(mean)
    max_std_dev = np.max(std_dev)
    
    image_center = np.array([width/2, height/2])
    image_center_distance = image.shape[0] * np.sqrt(2) / 2
    
    valid_blocks = np.zeros((blocks_x, blocks_y), dtype=int)
    
    for i in range(blocks_x):
        for j in range(blocks_y):
            block_center = np.array([(i+0.5)*block_size, (j+0.5)*block_size])
            block_ratio_distance = get_ratio(image_center, block_center, image_center_distance)
            
            if is_valid(block_ratio_distance, mean[i,j], max_mean, std_dev[i,j], max_std_dev):
                valid_blocks[i,j] = 1
    
    return valid_blocks.tolist()

def is_valid(ratio_distance: float, mean_block: float, max_mean: float, 
             std_dev_block: float, max_std_dev: float) -> bool:
    """
    Determine if a block is valid based on its properties.
    
    Args:
        ratio_distance (float): Ratio of block's distance from center to max distance.
        mean_block (float): Mean value of the block.
        max_mean (float): Maximum mean value across all blocks.
        std_dev_block (float): Standard deviation of the block.
        max_std_dev (float): Maximum standard deviation across all blocks.
    
    Returns:
        bool: True if the block is valid, False otherwise.
    """
    weight_mean = 0.5
    weight_std_dev = 0.5
    
    mean = mean_block / max_mean
    std_dev = std_dev_block / max_std_dev
    
    v = weight_mean * (1 - mean) + weight_std_dev * std_dev + ratio_distance
    
    return v > 0.8

def get_ratio(image_center: np.ndarray, block_center: np.ndarray, greatest_distance: float) -> float:
    """
    Calculate the ratio of a block's distance from the image center to the greatest possible distance.
    
    Args:
        image_center (np.ndarray): Coordinates of the image center.
        block_center (np.ndarray): Coordinates of the block center.
        greatest_distance (float): The greatest possible distance from the center.
    
    Returns:
        float: Ratio of block's distance to the greatest distance.
    """
    block_distance = np.linalg.norm(block_center - image_center)
    return 1 - block_distance / greatest_distance

def process_image(image_path: str, fing_id: argparse.Namespace, board: Board) -> None:
    """
    Process a single fingerprint image.
    
    Args:
        image_path (str): Path to the fingerprint image.
        fing_id (argparse.Namespace): Command-line arguments.
        board (Board): Visualization board.
    """
    try:
        print(f"Processing image: {image_path}")
        
        cvImage = loader.read_raw_image(image_path)
        if cvImage is None or cvImage.size == 0:
            print(f"Failed to load image: {image_path}")
            return
        
        if fing_id.draw:
            board.add_to_plot(cvImage, [0,0], 'original image')
        
        cvImage = enhance(cvImage)
        
        block_size = 11
        roi = detect_roi(cvImage, block_size)
        
        if fing_id.draw:
            board.add_to_plot(cvImage, [1,0], 'enhanced image')
        
        if fing_id.type_classification:
            classifier = TypeClassifier(fing_id, board)
            fingerprint_type = classifier.classify(cvImage, roi, block_size)
            print(f"Fingerprint type: {fingerprint_type}")
        
        if fing_id.min_extraction:
            extractor = MinutiaeExtractor(fing_id, board)
            fingerprint_minutiae = extractor.extract(cvImage, roi, block_size)
            print(f"Extracted {len(fingerprint_minutiae)} minutiae points")
        
        if fing_id.draw:
            board.plot()
    
    except Exception as e:
        print(f"Error processing image {image_path}: {str(e)}")

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser("fing-id")
    arg_parser.add_argument("--draw", help="enables drawing images (impacts performance).", action='store_true')
    arg_parser.add_argument("--type_classification", help="runs the type classification algorithm.", action='store_true')
    arg_parser.add_argument("--min_extraction", help="runs the minutiae extraction algorithm.", action='store_true')
    arg_parser.add_argument("--pattern_matching", help="executes the pattern matching for type and minutiae.", action='store_true')

    fing_id = arg_parser.parse_args()

    loader = Loader()
    images = loader.load_databases()
    board = Board()

    for image in images:
        process_image(image, fing_id, board)

    print("Fingerprint processing completed.")