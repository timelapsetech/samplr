"""
Core functionality for the Samplr package.

This module provides the ImageSampler class which handles the sampling and copying
of images based on various criteria.
"""

import os
import shutil
from datetime import datetime, time
from pathlib import Path
from typing import Callable, List, Optional, Set

ProgressCallback = Callable[[int, int, str], None]

from PIL import Image
from dateutil.parser import parse

# Supported image extensions
SUPPORTED_EXTENSIONS: Set[str] = {'.jpg', '.jpeg', '.png', '.gif'}

# Black-frame detection uses a small downsampled grayscale histogram for speed.
BLACK_FRAME_SAMPLE_SIZE = 64
BLACK_PIXEL_LUMINANCE_THRESHOLD = 10


class DirectoryValidationError(ValueError):
    """Raised when source and destination directories are unsafe to use together."""


def _is_descendant(path: Path, ancestor: Path) -> bool:
    """Return True if path is a strict descendant of ancestor."""
    path_resolved = path.resolve()
    ancestor_resolved = ancestor.resolve()
    if path_resolved == ancestor_resolved:
        return False
    try:
        path_resolved.relative_to(ancestor_resolved)
        return True
    except ValueError:
        return False


def validate_sample_directories(source_dir: Path, dest_dir: Path) -> None:
    """
    Validate that source and destination directories are safe to use together.

    Raises:
        DirectoryValidationError: If directories are missing or would put originals at risk.
    """
    source = source_dir.expanduser().resolve()
    dest = dest_dir.expanduser().resolve()

    if not source.exists():
        raise DirectoryValidationError(f"Source directory does not exist: {source_dir}")
    if not source.is_dir():
        raise DirectoryValidationError(f"Source path is not a directory: {source_dir}")

    if source == dest:
        raise DirectoryValidationError(
            "Source and destination must be different directories. "
            "Choose a separate folder for sampled images so originals are not at risk."
        )

    if _is_descendant(dest, source):
        raise DirectoryValidationError(
            "Destination cannot be inside the source directory. "
            "Choose a folder outside your image library."
        )

    if _is_descendant(source, dest):
        raise DirectoryValidationError(
            "Source cannot be inside the destination directory. "
            "Choose a source folder that is separate from prior output."
        )


class ImageSampler:
    """
    A class for sampling and copying images based on various criteria.
    
    This class provides methods to sample images from a source directory based on
    different strategies (every Nth image, closest to time, or within time range)
    and copy them to a destination directory with sequential naming.
    """

    def __init__(
        self,
        source_dir: str,
        dest_dir: str,
        base_name: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        """
        Initialize the ImageSampler.

        Args:
            source_dir: Path to the source directory containing images
            dest_dir: Path to the destination directory for sampled images
            base_name: Optional base name for output files. If None, derived from first image
            progress_callback: Optional callback(current, total, message) for progress updates
        """
        self.source_dir = Path(source_dir).expanduser()
        self.dest_dir = Path(dest_dir).expanduser()
        validate_sample_directories(self.source_dir, self.dest_dir)
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        self.base_name = base_name
        self.progress_callback = progress_callback

    def _report_progress(self, current: int, total: int, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(current, total, message)
        
    def _parse_exif_datetime(self, value: object) -> Optional[datetime]:
        """
        Parse an EXIF datetime string.

        EXIF uses ``YYYY:MM:DD HH:MM:SS`` (colons in the date). dateutil's parser
        mishandles that format and substitutes today's date, so we parse EXIF
        literally first and only fall back to dateutil for other formats.
        """
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        text = str(value).strip()
        if not text:
            return None
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y:%m:%d %H:%M"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        try:
            return parse(text)
        except (ValueError, TypeError):
            return None

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
                            dt = self._parse_exif_datetime(exif[tag_id])
                            if dt is not None:
                                return dt
        except (AttributeError, KeyError, TypeError, ValueError, OSError):
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

    def _black_pixel_fraction(self, image_path: Path) -> float:
        """
        Estimate the fraction of near-black pixels in an image.

        Uses JPEG draft decoding when possible and a downsampled grayscale
        histogram so large batches stay fast without reading every full pixel.
        """
        with Image.open(image_path) as img:
            img.draft("L", (BLACK_FRAME_SAMPLE_SIZE, BLACK_FRAME_SAMPLE_SIZE))
            gray = img.convert("L")
            if (
                gray.width > BLACK_FRAME_SAMPLE_SIZE
                or gray.height > BLACK_FRAME_SAMPLE_SIZE
            ):
                gray.thumbnail(
                    (BLACK_FRAME_SAMPLE_SIZE, BLACK_FRAME_SAMPLE_SIZE),
                    Image.Resampling.BILINEAR,
                )

            histogram = gray.histogram()
            black_count = sum(histogram[: BLACK_PIXEL_LUMINANCE_THRESHOLD + 1])
            total = gray.width * gray.height
            if total == 0:
                return 0.0
            return black_count / total

    def is_black_frame(self, image_path: Path, tolerance_percent: float) -> bool:
        """
        Return True if at least tolerance_percent of the frame is near-black.
        """
        fraction = self._black_pixel_fraction(image_path)
        return fraction * 100.0 >= tolerance_percent

    def filter_black_frames(
        self, images: List[Path], tolerance_percent: float
    ) -> List[Path]:
        """
        Remove frames that are at least tolerance_percent near-black.

        Args:
            images: Candidate image paths
            tolerance_percent: Percentage of frame that must be black to exclude
                the image (0 exclusive through 100 inclusive)

        Returns:
            Paths that are not considered black frames
        """
        if tolerance_percent <= 0 or tolerance_percent > 100:
            raise ValueError(
                "Black frame tolerance must be greater than 0 and at most 100."
            )

        kept: List[Path] = []
        total = len(images)
        for index, img_path in enumerate(images, start=1):
            self._report_progress(
                index, total, f"Checking black frames: {img_path.name}"
            )
            if not self.is_black_frame(img_path, tolerance_percent):
                kept.append(img_path)
        return kept

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
        total = len(image_files)

        # Group images by date
        images_by_date = {}
        for index, img_path in enumerate(image_files, start=1):
            self._report_progress(index, total, f"Reading metadata: {img_path.name}")
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
        total = len(image_files)

        # Filter images within time range
        filtered_images = []
        for index, img_path in enumerate(image_files, start=1):
            self._report_progress(index, total, f"Reading metadata: {img_path.name}")
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
        source_resolved = self.source_dir.resolve()
        source_files = {
            path.resolve()
            for path in source_resolved.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        }
        total = len(selected_images)
        for index, img_path in enumerate(selected_images, start=1):
            src_path = img_path.resolve()
            if src_path.parent != source_resolved:
                raise DirectoryValidationError(
                    f"Refusing to copy file outside the source directory: {img_path.name}"
                )

            new_name = f"{base_name}_{next_num:0{required_digits}d}{suffix}"
            dest_path = (self.dest_dir / new_name).resolve()
            if dest_path == src_path or dest_path in source_files:
                raise DirectoryValidationError(
                    f"Refusing to overwrite a file in the source directory: {dest_path.name}"
                )

            self._report_progress(index, total, f"Copying: {img_path.name} → {new_name}")
            shutil.copy2(img_path, dest_path)
            next_num += 1 