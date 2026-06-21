"""Tests for the core functionality of the Samplr package."""

import os
import shutil
from datetime import datetime, time
from pathlib import Path
import pytest
from PIL import Image

from samplr.core import DirectoryValidationError, ImageSampler, validate_sample_directories

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary source and destination directories."""
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()
    return source_dir, dest_dir

@pytest.fixture
def sample_images(temp_dirs):
    """Create sample images with different timestamps."""
    source_dir, _ = temp_dirs
    
    # Create test images at hours 9, 11, 13, 15
    for i, hour in enumerate([9, 11, 13, 15]):
        img = Image.new('RGB', (100, 100), color='red')
        img_path = source_dir / f"CO_{hour:03d}.jpg"
        img.save(img_path)
        
        # Set modification time to the specific hour
        timestamp = datetime(2024, 1, 1, hour, 0, 0).timestamp()
        os.utime(img_path, (timestamp, timestamp))
    
    return source_dir

def test_sample_every_nth(temp_dirs, sample_images):
    """Test sampling every Nth image."""
    source_dir, dest_dir = temp_dirs
    sampler = ImageSampler(source_dir, dest_dir)
    
    # Test sampling every 2nd image
    selected = sampler.sample_every_nth(2)
    assert len(selected) == 2
    
    # Test copying and renaming
    sampler.copy_and_rename(selected)
    dest_files = list(dest_dir.glob("*.jpg"))
    assert len(dest_files) == 2
    assert all(f.name.startswith("SM_") for f in dest_files)

def test_sample_closest_to_time(temp_dirs, sample_images):
    """Test sampling images closest to a specific time."""
    source_dir, dest_dir = temp_dirs
    sampler = ImageSampler(source_dir, dest_dir)
    
    # Test sampling closest to 14:00
    target_time = time(14, 0)
    selected = sampler.sample_closest_to_time(target_time)
    assert len(selected) == 1  # Should get one image per day
    
    sampler.copy_and_rename(selected)
    dest_files = list(dest_dir.glob("*.jpg"))
    assert len(dest_files) == 1


def test_sample_closest_to_time_multiple_days_exif(temp_dirs):
    """EXIF dates must group images by day, not collapse to today."""
    piexif = pytest.importorskip("piexif")
    source_dir, dest_dir = temp_dirs

    for day in range(1, 4):
        for hour in [9, 13, 15]:
            img_path = source_dir / f"CO_{day:02d}_{hour:02d}.jpg"
            img = Image.new("RGB", (100, 100), color="red")
            exif_dict = {
                "0th": {},
                "Exif": {},
                "GPS": {},
                "1st": {},
                "thumbnail": None,
            }
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = (
                f"2024:01:{day:02d} {hour:02d}:00:00".encode()
            )
            img.save(img_path, exif=piexif.dump(exif_dict))

    sampler = ImageSampler(source_dir, dest_dir)
    selected = sampler.sample_closest_to_time(time(14, 0))
    assert len(selected) == 3

    sampler.copy_and_rename(selected)
    dest_files = list(dest_dir.glob("*.jpg"))
    assert len(dest_files) == 3

def test_sample_time_range(temp_dirs, sample_images):
    """Test sampling within time range."""
    source_dir, dest_dir = temp_dirs
    sampler = ImageSampler(source_dir, dest_dir)
    
    # Test sampling every 2nd image between 9:00 and 15:00
    start_time = time(9, 0)
    end_time = time(15, 0)
    selected = sampler.sample_every_nth_in_time_range(2, start_time, end_time)
    
    # Should get every 2nd image from 4 available (so 2 images)
    assert len(selected) == 2

def test_custom_base_name(temp_dirs, sample_images):
    """Test custom base name for output files."""
    source_dir, dest_dir = temp_dirs
    sampler = ImageSampler(source_dir, dest_dir, base_name="custom")
    
    selected = sampler.sample_every_nth(2)
    sampler.copy_and_rename(selected)
    
    dest_files = list(dest_dir.glob("*.jpg"))
    assert all(f.name.startswith("custom_") for f in dest_files)

def test_required_digits(temp_dirs, sample_images):
    """Test automatic adjustment of required digits."""
    source_dir, dest_dir = temp_dirs
    sampler = ImageSampler(source_dir, dest_dir)
    
    # Use an existing file from the fixture
    src_file = next(source_dir.glob("CO_*.jpg"))
    for i in range(10000, 10010):
        shutil.copy2(src_file, dest_dir / f"SM_{i:04d}.jpg")
    
    selected = sampler.sample_every_nth(2)
    sampler.copy_and_rename(selected)
    
    # Check that new files use 5 digits
    dest_files = list(dest_dir.glob("SM_*.jpg"))
    assert any(len(f.stem.split('_')[-1]) == 5 for f in dest_files)


def test_validate_rejects_same_directory(temp_dirs):
    """Source and destination cannot be the same folder."""
    source_dir, _ = temp_dirs
    with pytest.raises(DirectoryValidationError, match="different directories"):
        validate_sample_directories(source_dir, source_dir)


def test_validate_rejects_destination_inside_source(tmp_path):
    """Destination cannot be nested inside the source directory."""
    source_dir = tmp_path / "library"
    dest_dir = source_dir / "sampled"
    source_dir.mkdir()
    dest_dir.mkdir()
    with pytest.raises(DirectoryValidationError, match="inside the source"):
        validate_sample_directories(source_dir, dest_dir)


def test_validate_rejects_source_inside_destination(tmp_path):
    """Source cannot be nested inside the destination directory."""
    dest_dir = tmp_path / "output"
    source_dir = dest_dir / "originals"
    dest_dir.mkdir()
    source_dir.mkdir()
    with pytest.raises(DirectoryValidationError, match="inside the destination"):
        validate_sample_directories(source_dir, dest_dir)


def test_image_sampler_rejects_same_directory(temp_dirs):
    """ImageSampler refuses to initialize with identical source and destination."""
    source_dir, _ = temp_dirs
    with pytest.raises(DirectoryValidationError, match="different directories"):
        ImageSampler(source_dir, source_dir) 