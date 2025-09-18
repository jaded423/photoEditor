#!/usr/bin/env python3
"""
Combined Media Processor
Processes both photos (background removal) and videos (banner addition) from raw folder
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import argparse
import io
import cv2

# Photo processing imports
try:
    from rembg import remove, new_session
    from scipy import ndimage
    # Try to import HEIF support for iPhone photos
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        HEIF_SUPPORTED = True
    except ImportError:
        HEIF_SUPPORTED = False
        print("Note: pillow-heif not installed. HEIC files from iPhones won't be supported.")
        print("Install with: pip3 install pillow-heif")
except ImportError as e:
    print(f"Warning: Some photo processing libraries not found:")
    print("For photo processing, install with: pip3 install rembg pillow scipy numpy")
    if not HEIF_SUPPORTED:
        print("pip3 install pillow-heif  # For iPhone HEIC support")
    PHOTO_PROCESSING_AVAILABLE = False
else:
    PHOTO_PROCESSING_AVAILABLE = True

def add_banner_to_frame(frame, filename, banner_height=120):
    """
    Add a black banner at the top of a video frame with filename in white text.
    
    Args:
        frame: OpenCV frame (BGR format)
        filename: original filename (without extension)
        banner_height: height of the banner in pixels
    
    Returns:
        frame with banner added
    """
    
    # Convert BGR to RGB for PIL
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width = frame_rgb.shape[:2]
    
    # Convert to PIL Image
    frame_img = Image.fromarray(frame_rgb)
    
    # Create overlay for banner
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Calculate banner position (360px from top)
    banner_start_y = 360
    banner_end_y = banner_start_y + banner_height
    
    # Draw black banner rectangle
    overlay_draw.rectangle(
        [(0, banner_start_y), (width, banner_end_y)], 
        fill=(0, 0, 0, 255)  # Solid black
    )
    
    # Prepare text (filename in caps without extension)
    text = filename.upper()
    
    # Look for Inter font file in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    bundled_font_path = os.path.join(script_dir, "Inter-Bold.ttf")
    
    # Calculate target font size based on banner height and text length
    base_font_size = int(banner_height * 0.8)  # 80% of banner height
    
    # Adjust font size based on text length to ensure it fits
    text_length_adjustment = max(1.0, len(text) / 10.0)  # Scale down for longer text
    target_font_size = int(base_font_size / text_length_adjustment)
    
    # Try different font sizes starting from target
    font_sizes_to_try = [target_font_size, int(target_font_size * 1.2), int(target_font_size * 0.8), int(target_font_size * 0.6)]
    
    font = None
    
    try:
        # First try the bundled font
        if os.path.exists(bundled_font_path):
            for font_size in font_sizes_to_try:
                try:
                    test_font = ImageFont.truetype(bundled_font_path, font_size)
                    # Test if text fits in banner
                    test_bbox = overlay_draw.textbbox((0, 0), text, font=test_font)
                    text_width = test_bbox[2] - test_bbox[0]
                    if text_width <= width * 0.95:  # Text should fit with 5% margin
                        font = test_font
                        break
                except Exception:
                    continue
        
        # If bundled font didn't work, try system fonts
        if not font:
            system_font_paths = [
                "/System/Library/Fonts/Impact.ttf",  # macOS Impact
                "/System/Library/Fonts/Arial Bold.ttf",  # macOS
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # Linux
                "C:/Windows/Fonts/impact.ttf",  # Windows Impact
                "C:/Windows/Fonts/arialbd.ttf",  # Windows Arial Bold
            ]
            
            for font_size in font_sizes_to_try:
                for font_path in system_font_paths:
                    if os.path.exists(font_path):
                        try:
                            test_font = ImageFont.truetype(font_path, font_size)
                            test_bbox = overlay_draw.textbbox((0, 0), text, font=test_font)
                            text_width = test_bbox[2] - test_bbox[0]
                            if text_width <= width * 0.95:
                                font = test_font
                                break
                        except Exception:
                            continue
                    if font:
                        break
                if font:
                    break
    
    except Exception:
        pass
    
    # Draw the text
    if font:
        bbox = overlay_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center horizontally
        text_x = (width - text_width) // 2
        
        # Center vertically within the banner
        text_y = banner_start_y + (banner_height - text_height) // 2
        
        # Draw white text with subtle black outline for better visibility
        overlay_draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font, 
                         stroke_width=1, stroke_fill=(0, 0, 0, 255))
        
    else:
        # Fallback text drawing
        text_x = width // 2
        text_y = banner_start_y + (banner_height // 2)
        overlay_draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), anchor="mm")
    
    # Convert back to RGB and composite
    frame_with_overlay = Image.alpha_composite(frame_img.convert('RGBA'), overlay)
    
    # Convert back to BGR for OpenCV
    result_rgb = np.array(frame_with_overlay.convert('RGB'))
    result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
    
    return result_bgr

def add_banner_to_video(input_path, output_path):
    """Add filename banner to video."""
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input video not found: {input_path}")
    
    print(f"Processing video: {input_path}")
    print(f"Output will be saved to: {output_path}")
    
    # Get original filename without extension
    original_filename = Path(input_path).stem
    
    # Open video
    cap = cv2.VideoCapture(str(input_path))
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_path}")
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video properties: {width}x{height} @ {fps}fps, {total_frames} frames")
    
    # Set up video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    if not out.isOpened():
        raise ValueError(f"Could not create output video writer")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Add banner to frame
            frame_with_banner = add_banner_to_frame(frame, original_filename)
            
            # Write frame
            out.write(frame_with_banner)
            
            frame_count += 1
            
            # Progress indicator
            if frame_count % 30 == 0:  # Update every 30 frames
                progress = (frame_count / total_frames) * 100
                print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")
    
    finally:
        # Clean up
        cap.release()
        out.release()
        cv2.destroyAllWindows()
    
    print(f"Video processing complete!")
    print(f"Added banner '{original_filename.upper()}' to {frame_count} frames")
    
    return str(output_path)

# Photo processing functions (simplified versions from flower_extract.py)
def add_photo_banner(img_array, filename, banner_height=80):
    """Add a black banner overlaid on the bottom portion with filename in large white text."""
    
    # Work with the existing image dimensions
    height, width = img_array.shape[:2]
    
    # Convert to PIL Image for text drawing
    banner_img = Image.fromarray(img_array, 'RGBA')
    
    # Create a semi-transparent overlay for the banner area
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Calculate banner position (80 pixels up from bottom)
    banner_start_y = height - banner_height - 80  # 80 pixels up from bottom
    banner_end_y = height - 80  # End 80 pixels from bottom
    
    # Draw black banner rectangle
    overlay_draw.rectangle(
        [(0, banner_start_y), (width, banner_end_y)], 
        fill=(0, 0, 0, 255)  # Solid black
    )
    
    # Prepare text (filename in caps without extension)
    text = filename.upper()
    
    # Try to use bundled font first
    font = None
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    bundled_font_path = os.path.join(script_dir, "Inter-Bold.ttf")
    
    # Calculate target font size
    base_font_size = int(banner_height * 0.8)
    text_length_adjustment = max(1.0, len(text) / 10.0)
    target_font_size = int(base_font_size / text_length_adjustment)
    
    font_sizes_to_try = [target_font_size, int(target_font_size * 1.2), int(target_font_size * 0.8)]
    
    # Try bundled font first, then system fonts
    try:
        if os.path.exists(bundled_font_path):
            for font_size in font_sizes_to_try:
                try:
                    test_font = ImageFont.truetype(bundled_font_path, font_size)
                    test_bbox = overlay_draw.textbbox((0, 0), text, font=test_font)
                    text_width = test_bbox[2] - test_bbox[0]
                    if text_width <= width * 0.95:
                        font = test_font
                        break
                except Exception:
                    continue
    except Exception:
        pass
    
    # Draw the text
    if font:
        bbox = overlay_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (width - text_width) // 2
        text_y = banner_start_y + (banner_height - text_height) // 2
        
        overlay_draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font, 
                         stroke_width=1, stroke_fill=(0, 0, 0, 255))
    else:
        # Fallback
        text_x = width // 2
        text_y = banner_start_y + banner_height // 2
        overlay_draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), anchor="mm")
    
    # Composite the overlay onto the original image
    result_img = Image.alpha_composite(banner_img, overlay)
    
    return np.array(result_img)

def smart_resize_1000x1000(img_array):
    """Intelligently resize image to 1000x1000 while maintaining aspect ratio and centering the subject."""
    
    # Find the bounding box of the flower (non-transparent pixels)
    alpha = img_array[:, :, 3]
    y_coords, x_coords = np.where(alpha > 0)
    
    if len(y_coords) == 0:
        # If no flower found, just resize the whole image
        img = Image.fromarray(img_array, 'RGBA')
        return np.array(img.resize((1000, 1000), Image.Resampling.LANCZOS))
    
    # Check if this is likely a bulk/pile photo (high coverage)
    total_pixels = alpha.size
    non_transparent_pixels = len(y_coords)
    coverage_ratio = non_transparent_pixels / total_pixels
    
    if coverage_ratio > 0.8:  # More than 80% coverage suggests bulk/pile photo
        print("Detected bulk/pile photo - using full-image resize approach")
        img = Image.fromarray(img_array, 'RGBA')
        
        available_height = 1000 - 160  # 840px available above banner
        available_width = 1000
        
        original_height, original_width = img_array.shape[:2]
        scale_factor = min(available_width / original_width, available_height / original_height)
        
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        canvas = np.zeros((1000, 1000, 4), dtype=np.uint8)
        
        x_offset = (1000 - new_width) // 2
        y_offset = (840 - new_height) // 2
        
        canvas[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = np.array(resized_img)
        return canvas
    
    # For individual flower photos, use the original logic
    min_y, max_y = y_coords.min(), y_coords.max()
    min_x, max_x = x_coords.min(), x_coords.max()
    flower_width = max_x - min_x
    flower_height = max_y - min_y
    
    # Add padding around the flower
    padding_factor = 0.15
    h_padding = int(flower_height * padding_factor)
    w_padding = int(flower_width * padding_factor)
    
    padded_min_y = max(0, min_y - h_padding)
    padded_max_y = min(img_array.shape[0], max_y + h_padding)
    padded_min_x = max(0, min_x - w_padding)
    padded_max_x = min(img_array.shape[1], max_x + w_padding)
    
    flower_region = img_array[padded_min_y:padded_max_y, padded_min_x:padded_max_x]
    flower_img = Image.fromarray(flower_region, 'RGBA')
    
    available_height = 1000 - 80 - 80
    available_width = 1000
    
    region_width = flower_region.shape[1]
    region_height = flower_region.shape[0]
    
    scale_factor = min(available_width / region_width, available_height / region_height)
    
    if scale_factor > 2.0:
        scale_factor = 2.0
    
    new_width = int(region_width * scale_factor)
    new_height = int(region_height * scale_factor)
    
    resized_flower = flower_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    canvas = np.zeros((1000, 1000, 4), dtype=np.uint8)
    
    usable_area_height = 1000 - 160
    
    x_offset = (1000 - new_width) // 2
    y_offset = (usable_area_height - new_height) // 2
    
    resized_array = np.array(resized_flower)
    canvas[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = resized_array
    
    return canvas

def process_photo(input_path, output_path):
    """Process a single photo with background removal and banner."""
    
    if not PHOTO_PROCESSING_AVAILABLE:
        print(f"Skipping photo {input_path} - photo processing libraries not available")
        return False
    
    print(f"Processing photo: {input_path}")
    
    # Get original filename without extension
    original_filename = Path(input_path).stem
    
    # Check if filename starts with "Smalls" to skip background removal
    filename_starts_with_smalls = original_filename.lower().startswith('smalls')
    
    try:
        # Read input image data
        with open(input_path, 'rb') as input_file:
            input_data = input_file.read()
        
        # Skip background removal for files starting with "Smalls"
        if filename_starts_with_smalls:
            print("Skipping background removal for Smalls file - using original image")
            original_img = Image.open(input_path).convert('RGBA')
            output_buffer = io.BytesIO()
            original_img.save(output_buffer, format='PNG')
            output_data = output_buffer.getvalue()
        else:
            # Create session with specified model
            session = new_session('isnet-general-use')
            
            # Remove background
            output_data = remove(input_data, session=session)
            
            # Check if background removal worked
            img_test = Image.open(io.BytesIO(output_data)).convert('RGBA')
            img_test_array = np.array(img_test)
            alpha_test = img_test_array[:, :, 3]
            non_transparent_pixels = np.sum(alpha_test > 0)
            total_pixels = alpha_test.size
            coverage_ratio = non_transparent_pixels / total_pixels
            
            if coverage_ratio < 0.05:
                print("Warning: Background removal removed everything. Using original image.")
                original_img = Image.open(io.BytesIO(input_data)).convert('RGBA')
                output_buffer = io.BytesIO()
                original_img.save(output_buffer, format='PNG')
                output_data = output_buffer.getvalue()
        
        # Post-processing to remove small objects
        print("Cleaning up small objects...")
        img = Image.open(io.BytesIO(output_data)).convert('RGBA')
        img_array = np.array(img)
        
        # Get alpha channel
        alpha = img_array[:, :, 3]
        
        # Find connected components
        labeled_array, num_features = ndimage.label(alpha > 128)
        
        if num_features > 1:
            component_sizes = np.bincount(labeled_array.ravel())
            largest_component = np.argmax(component_sizes[1:]) + 1
            main_object_mask = (labeled_array == largest_component)
            
            from scipy.ndimage import binary_closing, binary_opening
            main_object_mask = binary_closing(main_object_mask, structure=np.ones((3,3)))
            main_object_mask = binary_opening(main_object_mask, structure=np.ones((2,2)))
            
            alpha_cleaned = alpha * main_object_mask.astype(np.uint8)
            img_array[:, :, 3] = alpha_cleaned
            
            img_cleaned = Image.fromarray(img_array, 'RGBA')
            output_buffer = io.BytesIO()
            img_cleaned.save(output_buffer, format='PNG')
            output_data = output_buffer.getvalue()
            
            print(f"Removed {num_features - 1} small objects")
        
        # Apply 1000x1000 smart resize
        print("Creating 1000x1000 smart resize...")
        img = Image.open(io.BytesIO(output_data)).convert('RGBA')
        img_array = np.array(img)
        img_array = smart_resize_1000x1000(img_array)
        
        # Add filename banner
        print("Adding filename banner...")
        img_array = add_photo_banner(img_array, original_filename)
        
        # Save result
        img_with_banner = Image.fromarray(img_array, 'RGBA')
        img_with_banner.save(output_path, format='PNG')
        
        print(f"Photo processing complete! Saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error processing photo {input_path}: {str(e)}")
        return False

def process_media_batch(raw_dir):
    """Process all photos and videos in the raw directory."""
    
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw directory not found: {raw_dir}")
    
    # Create output directories
    edited_dir = raw_path / "edited"
    original_dir = raw_path / "original"
    edited_dir.mkdir(exist_ok=True)
    original_dir.mkdir(exist_ok=True)
    
    # File extensions
    photo_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif']
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
    
    # Find all media files
    photo_files = []
    video_files = []
    
    for ext in photo_extensions:
        photo_files.extend(raw_path.glob(f"*{ext}"))
        photo_files.extend(raw_path.glob(f"*{ext.upper()}"))
    
    for ext in video_extensions:
        video_files.extend(raw_path.glob(f"*{ext}"))
        video_files.extend(raw_path.glob(f"*{ext.upper()}"))
    
    total_files = len(photo_files) + len(video_files)
    
    if total_files == 0:
        print(f"No media files found in {raw_dir}")
        print(f"Supported photo formats: {', '.join(photo_extensions)}")
        print(f"Supported video formats: {', '.join(video_extensions)}")
        return
    
    print(f"Found {len(photo_files)} photos and {len(video_files)} videos to process...")
    
    success_count = 0
    
    # Process photos
    if photo_files and PHOTO_PROCESSING_AVAILABLE:
        print("\n=== PROCESSING PHOTOS ===")
        for i, photo_file in enumerate(photo_files, 1):
            try:
                output_file = edited_dir / f"{photo_file.stem}.png"
                print(f"\n[{i}/{len(photo_files)}] Processing photo: {photo_file.name}")
                
                if process_photo(str(photo_file), str(output_file)):
                    # Move original to original folder
                    original_path = original_dir / photo_file.name
                    counter = 1
                    while original_path.exists():
                        stem = photo_file.stem
                        suffix = photo_file.suffix
                        original_path = original_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    os.rename(str(photo_file), str(original_path))
                    print(f"Moved original to: {original_path}")
                    success_count += 1
                
            except Exception as e:
                print(f"Failed to process photo {photo_file.name}: {str(e)}")
    
    elif photo_files and not PHOTO_PROCESSING_AVAILABLE:
        print(f"\nSkipping {len(photo_files)} photos - photo processing libraries not installed")
    
    # Process videos
    if video_files:
        print("\n=== PROCESSING VIDEOS ===")
        for i, video_file in enumerate(video_files, 1):
            try:
                output_file = edited_dir / video_file.name
                print(f"\n[{i}/{len(video_files)}] Processing video: {video_file.name}")
                
                add_banner_to_video(str(video_file), str(output_file))
                
                # Move original to original folder
                original_path = original_dir / video_file.name
                counter = 1
                while original_path.exists():
                    stem = video_file.stem
                    suffix = video_file.suffix
                    original_path = original_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                os.rename(str(video_file), str(original_path))
                print(f"Moved original to: {original_path}")
                success_count += 1
                
            except Exception as e:
                print(f"Failed to process video {video_file.name}: {str(e)}")
    
    print(f"\n=== BATCH COMPLETE ===")
    print(f"Successfully processed {success_count}/{total_files} files")
    print(f"Edited files saved to: {edited_dir}/")
    print(f"Original files moved to: {original_dir}/")

def main():
    parser = argparse.ArgumentParser(description='Combined photo and video processor')
    parser.add_argument('input_dir', help='Input directory containing raw photos and videos')
    
    args = parser.parse_args()
    
    try:
        process_media_batch(args.input_dir)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Combined Media Processor")
        print("=" * 40)
        print("\nProcesses both photos and videos from raw folder")
        print("\nUsage:")
        print("python3 combined_processor.py raw/")
        print("\nPhotos: Background removal, 1000x1000 resize, bottom banner")
        print("Videos: Top banner addition")
        print("\nOutput structure:")
        print("raw/edited/    - processed files")
        print("raw/original/  - original files")
        print("\nNote: Install required libraries:")
        print("pip3 install opencv-python pillow")
        print("pip3 install rembg scipy numpy  # for photo processing")
    else:
        main()
