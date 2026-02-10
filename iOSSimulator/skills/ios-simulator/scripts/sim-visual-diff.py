#!/usr/bin/env python3
"""
Compare two screenshots pixel-by-pixel for visual regression testing.

Usage:
    sim-visual-diff.py <baseline> <current> [--threshold 1.0] [--output /tmp/diff]

Options:
    baseline              Path to baseline (reference) screenshot
    current               Path to current screenshot to compare
    --threshold <pct>     Acceptable difference percentage (default: 1.0)
    --output <dir>        Directory to save diff artifacts (diff.png, side-by-side.png)
    --no-artifacts        Skip generating diff images (faster, just report)

Output:
    JSON object with comparison result, pixel counts, and pass/fail verdict.
    Exit code 0 = PASS (within threshold), 1 = FAIL (exceeds threshold).

Notes:
    - Requires Pillow: pip3 install Pillow
    - Both images must have the same dimensions
    - A pixel noise threshold of 10/255 is applied to ignore compression artifacts
"""

import json
import sys
import os
import argparse

try:
    from PIL import Image, ImageChops
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


def count_different_pixels(diff_image):
    """Count pixels that differ above the noise threshold."""
    gray = diff_image.convert('L')
    return sum(1 for pixel in gray.getdata() if pixel > 10)


def generate_diff_image(baseline, current, output_path):
    """Generate an image highlighting differences in red."""
    diff = ImageChops.difference(baseline, current)
    gray = diff.convert('L')

    # Create red overlay where differences exist
    result = current.copy()
    result_data = list(result.getdata())
    gray_data = list(gray.getdata())

    for i, g in enumerate(gray_data):
        if g > 10:
            result_data[i] = (255, 0, 0)

    result.putdata(result_data)
    result.save(output_path)


def generate_side_by_side(baseline, current, output_path):
    """Generate a side-by-side comparison image."""
    gap = 10
    width = baseline.size[0] * 2 + gap
    height = max(baseline.size[1], current.size[1])
    combined = Image.new('RGB', (width, height), (128, 128, 128))
    combined.paste(baseline, (0, 0))
    combined.paste(current, (baseline.size[0] + gap, 0))
    combined.save(output_path)


def main():
    parser = argparse.ArgumentParser(description='Compare screenshots for visual differences')
    parser.add_argument('baseline', help='Path to baseline screenshot')
    parser.add_argument('current', help='Path to current screenshot')
    parser.add_argument('--threshold', type=float, default=1.0,
                        help='Acceptable difference percentage (default: 1.0)')
    parser.add_argument('--output', help='Directory to save diff artifacts')
    parser.add_argument('--no-artifacts', action='store_true',
                        help='Skip generating diff images')

    args = parser.parse_args()

    if not HAS_PILLOW:
        print(json.dumps({
            'success': False,
            'error': 'Pillow is required for visual diff. Install with: pip3 install Pillow'
        }))
        sys.exit(1)

    # Validate files exist
    for path, label in [(args.baseline, 'Baseline'), (args.current, 'Current')]:
        if not os.path.exists(path):
            print(json.dumps({
                'success': False,
                'error': f'{label} image not found: {path}'
            }))
            sys.exit(1)

    # Load images
    try:
        baseline = Image.open(args.baseline).convert('RGB')
        current = Image.open(args.current).convert('RGB')
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Failed to load image: {e}'
        }))
        sys.exit(1)

    # Check dimensions
    if baseline.size != current.size:
        print(json.dumps({
            'success': False,
            'error': 'Image dimensions do not match',
            'baseline_size': list(baseline.size),
            'current_size': list(current.size),
        }))
        sys.exit(1)

    # Compare
    diff = ImageChops.difference(baseline, current)
    total_pixels = baseline.size[0] * baseline.size[1]
    diff_pixels = count_different_pixels(diff)
    diff_pct = round((diff_pixels / total_pixels) * 100, 3)
    passed = diff_pct <= args.threshold

    result = {
        'success': True,
        'passed': passed,
        'verdict': 'PASS' if passed else 'FAIL',
        'difference_percentage': diff_pct,
        'threshold_percentage': args.threshold,
        'different_pixels': diff_pixels,
        'total_pixels': total_pixels,
        'dimensions': list(baseline.size),
        'baseline': args.baseline,
        'current': args.current,
    }

    # Generate artifacts
    if args.output and not args.no_artifacts:
        os.makedirs(args.output, exist_ok=True)

        diff_path = os.path.join(args.output, 'diff.png')
        sbs_path = os.path.join(args.output, 'side-by-side.png')

        try:
            generate_diff_image(baseline, current, diff_path)
            generate_side_by_side(baseline, current, sbs_path)
            result['artifacts'] = {
                'diff_image': diff_path,
                'side_by_side': sbs_path,
            }
        except Exception as e:
            result['artifact_error'] = str(e)

    print(json.dumps(result, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
