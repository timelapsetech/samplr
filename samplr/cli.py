import argparse
from datetime import time
from pathlib import Path
from .core import DirectoryValidationError, ImageSampler, validate_sample_directories

def parse_time(time_str: str) -> time:
    """Parse time string in HH:MM format."""
    try:
        hour, minute = map(int, time_str.split(':'))
        return time(hour, minute)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Time must be in HH:MM format, got {time_str}")

def main():
    parser = argparse.ArgumentParser(description="Sample images based on various criteria")
    parser.add_argument("source_dir", help="Source directory containing images")
    parser.add_argument("dest_dir", help="Destination directory for sampled images")
    parser.add_argument("--base-name", help="Base name for output files (default: derived from first image, replacing 'CO' with 'SM')")
    parser.add_argument(
        "--remove-black-frames",
        action="store_true",
        help="Exclude frames that are mostly black before copying",
    )
    parser.add_argument(
        "--black-frame-tolerance",
        type=float,
        default=95.0,
        metavar="PCT",
        help="When removing black frames, exclude images with at least this "
        "percentage of near-black pixels (default: 95)",
    )
    
    # Create a group for mutually exclusive sampling methods
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--every-nth", type=int, help="Sample every Nth image")
    group.add_argument("--closest-to", type=parse_time, 
                      help="Sample image closest to specified time (HH:MM) each day")
    group.add_argument("--time-range", nargs=3, metavar=('N', 'START', 'END'),
                      help="Sample every Nth image within time range (HH:MM-HH:MM)")

    args = parser.parse_args()

    # Validate directories
    source_dir = Path(args.source_dir)
    dest_dir = Path(args.dest_dir)
    
    if not source_dir.exists():
        parser.error(f"Source directory does not exist: {source_dir}")

    try:
        validate_sample_directories(source_dir, dest_dir)
    except DirectoryValidationError as exc:
        parser.error(str(exc))
    
    # Create sampler instance
    sampler = ImageSampler(source_dir, dest_dir, base_name=args.base_name)
    
    # Process based on selected sampling method
    if args.every_nth:
        selected_images = sampler.sample_every_nth(args.every_nth)
    elif args.closest_to:
        selected_images = sampler.sample_closest_to_time(args.closest_to)
    else:  # time-range
        try:
            n = int(args.time_range[0])
            start_time = parse_time(args.time_range[1])
            end_time = parse_time(args.time_range[2])
            selected_images = sampler.sample_every_nth_in_time_range(n, start_time, end_time)
        except ValueError as e:
            parser.error(f"Invalid time range format: {e}")

    if args.remove_black_frames:
        if args.black_frame_tolerance <= 0 or args.black_frame_tolerance > 100:
            parser.error(
                "Black frame tolerance must be greater than 0 and at most 100."
            )
        selected_images = sampler.filter_black_frames(
            selected_images, args.black_frame_tolerance
        )

    # Copy and rename selected images
    sampler.copy_and_rename(selected_images)
    print(f"Successfully copied {len(selected_images)} images to {dest_dir}")

if __name__ == "__main__":
    main() 