"""
Core functionality for the Samplr package.

This module provides the ImageSampler class which handles the sampling and copying
of images based on various criteria.
"""

import os
import shutil
from datetime import datetime, time
from pathlib import Path
from typing import List, Optional, Tuple, Set

from PIL import Image
from dateutil.parser import parse

# Supported image extensions
SUPPORTED_EXTENSIONS: Set[str] = {'.jpg', '.jpeg', '.png', '.gif'}

class ImageSampler:
    """
    A class for sampling and copying images based on various criteria.
    
    This class provides methods to sample images from a source directory based on
    different strategies (every Nth image, closest to time, or within time range)
    and copy them to a destination directory with sequential naming.
    """

    def __init__(self, source_dir: str, dest_dir: str, base_name: Optional[str] = None) -> None:
        """
        Initialize the ImageSampler.

        Args:
            source_dir: Path to the source directory containing images
            dest_dir: Path to the destination directory for sampled images
            base_name: Optional base name for output files. If None, derived from first image
        """
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        self.base_name = base_name
        
    def _get_image_datetime(self, image_path: Path) -> Optional[datetime]:
        """
        Extract datetime from image metadata.

        Args:
            image_path: Path to the image file

        Returns:
            datetime object from EXIF data or file modification time, or None if not available
        """
        try:
            with Image.open(image_path) as img:
                exif = img._getexif()
                if exif:
                    # Try to get datetime from EXIF data
                    for tag_id in [36867, 306]:  # DateTimeOriginal, DateTime
                        if tag_id in exif:
                            return parse(exif[tag_id])
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
        
        # Fallback to file modification time
        return datetime.fromtimestamp(image_path.stat().st_mtime)

    def _is_within_time_range(self, dt: datetime, start_time: time, end_time: time) -> bool:
        """
        Check if datetime is within specified time range.

        Args:
            dt: Datetime to check
            start_time: Start of time range
            end_time: End of time range

        Returns:
            True if datetime is within range, False otherwise
        """
        current_time = dt.time()
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:  # Handle case where range crosses midnight
            return current_time >= start_time or current_time <= end_time

    def _get_default_base_name(self) -> str:
        """
        Get default base name from first image in source directory.

        Returns:
            Base name derived from first image, with 'CO' replaced by 'SM'
        """
        image_files = sorted([f for f in self.source_dir.glob("*") 
                            if f.suffix.lower() in SUPPORTED_EXTENSIONS])
        if not image_files:
            return "image"
        
        first_image = image_files[0]
        # Get the base name without the sequence number
        base_name = first_image.stem
        # If the name contains an underscore, take everything before the last underscore
        if '_' in base_name:
            base_name = '_'.join(base_name.split('_')[:-1])
        # Replace "CO" with "SM" in the base name
        return base_name.replace("CO", "SM")

    def _get_required_digits(self, base_name: str, suffix: str) -> int:
        """
        Determine the number of digits needed for unique sequential numbering.

        Args:
            base_name: Base name for the files
            suffix: File extension

        Returns:
            Number of digits required for unique sequential numbering
        """
        # Get all existing files with the same base name and suffix
        existing_files = list(self.dest_dir.glob(f"{base_name}_*{suffix}"))
        
        if not existing_files:
            return 4  # Default to 4 digits if no existing files
        
        # Find the highest number used
        max_num = 0
        for file in existing_files:
            try:
                # Extract the number from the filename
                num_str = file.stem.split('_')[-1]
                num = int(num_str)
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        
        # Calculate required digits based on max number and new files
        required_digits = max(4, len(str(max_num + len(existing_files))))
        return required_digits

    def sample_every_nth(self, n: int) -> List[Path]:
        """
        Sample every Nth image from the source directory.

        Args:
            n: Sample every Nth image

        Returns:
            List of paths to selected images
        """
        image_files = sorted([f for f in self.source_dir.glob("*") 
                            if f.suffix.lower() in SUPPORTED_EXTENSIONS])
        return image_files[::n]

    def sample_closest_to_time(self, target_time: time) -> List[Path]:
        """
        Sample images closest to the target time each day.

        Args:
            target_time: Target time to find closest images to

        Returns:
            List of paths to selected images
        """
        image_files = [f for f in self.source_dir.glob("*") 
                      if f.suffix.lower() in SUPPORTED_EXTENSIONS]
        
        # Group images by date
        images_by_date = {}
        for img_path in image_files:
            dt = self._get_image_datetime(img_path)
            if dt:
                date_key = dt.date()
                if date_key not in images_by_date:
                    images_by_date[date_key] = []
                images_by_date[date_key].append((img_path, dt))

        # Find closest image to target time for each day
        selected_images = []
        for date_images in images_by_date.values():
            if not date_images:
                continue
            
            # Find image closest to target time
            closest_image = min(date_images, 
                              key=lambda x: abs((x[1].time().hour * 60 + x[1].time().minute) - 
                                              (target_time.hour * 60 + target_time.minute)))
            selected_images.append(closest_image[0])

        return sorted(selected_images)

    def sample_every_nth_in_time_range(self, n: int, start_time: time, end_time: time) -> List[Path]:
        """
        Sample every Nth image within specified time range.

        Args:
            n: Sample every Nth image
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of paths to selected images
        """
        image_files = [f for f in self.source_dir.glob("*") 
                      if f.suffix.lower() in SUPPORTED_EXTENSIONS]
        
        # Filter images within time range
        filtered_images = []
        for img_path in image_files:
            dt = self._get_image_datetime(img_path)
            if dt and self._is_within_time_range(dt, start_time, end_time):
                filtered_images.append(img_path)

        return sorted(filtered_images)[::n]

    def copy_and_rename(self, selected_images: List[Path]) -> None:
        """
        Copy selected images to destination directory with sequential naming.

        Args:
            selected_images: List of paths to images to copy
        """
        base_name = self.base_name if self.base_name is not None else self._get_default_base_name()
        
        # Get the suffix from the first image (assuming all images have same suffix)
        suffix = selected_images[0].suffix if selected_images else '.jpg'
        
        # Determine required number of digits
        required_digits = self._get_required_digits(base_name, suffix)
        
        # Get the next available number
        existing_files = list(self.dest_dir.glob(f"{base_name}_*{suffix}"))
        next_num = 1
        if existing_files:
            try:
                # Find the highest number used
                max_num = max(int(f.stem.split('_')[-1]) for f in existing_files)
                next_num = max_num + 1
            except (ValueError, IndexError):
                pass
        
        # Copy and rename files
        for img_path in selected_images:
            new_name = f"{base_name}_{next_num:0{required_digits}d}{suffix}"
            shutil.copy2(img_path, self.dest_dir / new_name)
            next_num += 1 