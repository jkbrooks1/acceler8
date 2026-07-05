#!/usr/bin/env python3
"""
Acceler8-ai Stock Photo Processor v3
With Smart Bucket Suggestion using Image Analysis + Auto-Publishing

Workflow:
1. User manually moves photos to: /Users/jkbrookspersonal/JBLocal Files/PhotoStaging
2. Run this script to:
   - Analyze each image and suggest a bucket
   - User confirms or overrides with one keypress
   - Rename files with next sequence number
   - Move to canonical Stock_Photos folder
   - Generate HTML proof sheet (as index.html for root domain)
   - Push to GitHub → Cloudflare auto-deploys (~1 min)
   - Proof sheet live at: https://proofsheet.acceler8-ai.com

Usage:
    python3 a8_stock_photo_processor_v3.py

    Auto-publishes to https://proofsheet.acceler8-ai.com via GitHub → Cloudflare Pages.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import subprocess
import sys
from PIL import Image
import numpy as np
import boto3

# Configuration
STAGING_FOLDER = Path("/Users/jkbrookspersonal/JBLocal Files/PhotoStaging")
STOCK_PHOTOS_FOLDER = Path(
    "/Users/jkbrookspersonal/Library/CloudStorage/GoogleDrive-jb@acceler8-ai.com/My Drive/a8_Root/06a8_Marketing_Promotion/03_Brand_Assets/Stock_Photos"
)
GITHUB_REPO = Path.home() / "Projects" / "acceler8"
PROOFSHEET_OUTPUT = GITHUB_REPO / "public" / "proofsheet" / "index.html"

APPROVED_BUCKETS = ["TEAMS", "SYSTEMS", "REVENUE", "DATA-VIZ", "GRAPHIC-ELEMENTS"]
SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif"]

# R2 Configuration
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "proofsheetbucketb")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "https://pub-906aebdaaf22471faa576c94c2cdf07b.r2.dev")
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Colors for output
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


def log_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def log_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def log_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def log_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def log_suggest(msg):
    print(f"{Colors.CYAN}→ {msg}{Colors.END}")


def analyze_image_for_bucket(image_path):
    """
    Analyze image and suggest a bucket using visual characteristics.

    Returns: (suggested_bucket, confidence_score)
    """
    try:
        img = Image.open(image_path)
        img_array = np.array(img)

        # Get image properties
        height, width = img_array.shape[:2]
        aspect_ratio = width / height if height > 0 else 1

        # Analyze color distribution
        if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
            # RGB/RGBA
            r = img_array[:, :, 0].mean()
            g = img_array[:, :, 1].mean()
            b = img_array[:, :, 2].mean()
            brightness = (r + g + b) / 3
            saturation = max(r, g, b) - min(r, g, b)
        else:
            brightness = np.mean(img_array)
            saturation = 0

        # Analyze complexity (edge detection proxy)
        complexity = np.std(img_array) if img_array.size > 0 else 0

        # Analyze content regions (rough grid-based analysis)
        grid_size = 4
        cell_height = height // grid_size
        cell_width = width // grid_size

        cell_brightness = []
        for i in range(grid_size):
            for j in range(grid_size):
                y_start = i * cell_height
                y_end = (i + 1) * cell_height if i < grid_size - 1 else height
                x_start = j * cell_width
                x_end = (j + 1) * cell_width if j < grid_size - 1 else width

                cell = img_array[y_start:y_end, x_start:x_end]
                if cell.size > 0:
                    cell_brightness.append(np.mean(cell))

        brightness_variance = np.std(cell_brightness) if cell_brightness else 0

        # Heuristic scoring for each bucket
        scores = {
            "TEAMS": 0,           # People, warm tones, faces
            "SYSTEMS": 0,         # Geometric, structured, complexity
            "REVENUE": 0,         # Warm colors (gold, green), bright
            "DATA-VIZ": 0,        # High complexity, varied colors, structure
            "GRAPHIC-ELEMENTS": 0 # Abstract, soft focus, gradients, minimal
        }

        # Scoring logic based on image characteristics

        # TEAMS: Warm colors (high R), moderate brightness, some skin tones
        if r > g and r > b and brightness > 100 and brightness < 220:
            scores["TEAMS"] += 3

        # SYSTEMS: High contrast, geometric patterns, moderate-to-low saturation
        if brightness_variance > 30 or complexity > 30:
            scores["SYSTEMS"] += 3
        if saturation < 50:
            scores["SYSTEMS"] += 2

        # REVENUE: Warm colors (R/G dominance), bright, moderate saturation
        if (r > b or g > b) and brightness > 150 and saturation > 20:
            scores["REVENUE"] += 3
        if brightness > 180:
            scores["REVENUE"] += 2

        # DATA-VIZ: High complexity, good color variety, structured appearance
        if complexity > 40:
            scores["DATA-VIZ"] += 3
        if saturation > 40 and saturation < 100:
            scores["DATA-VIZ"] += 2
        if brightness_variance > 25:
            scores["DATA-VIZ"] += 2

        # GRAPHIC-ELEMENTS: Soft focus, gradual colors, lower complexity
        if complexity < 25:
            scores["GRAPHIC-ELEMENTS"] += 3
        if brightness_variance < 15:
            scores["GRAPHIC-ELEMENTS"] += 2
        if saturation < 30:
            scores["GRAPHIC-ELEMENTS"] += 1

        # Subtle cues based on size/aspect
        if aspect_ratio > 1.3 or aspect_ratio < 0.77:  # Very wide or tall
            scores["GRAPHIC-ELEMENTS"] += 1

        # Find best match
        best_bucket = max(scores, key=scores.get)
        max_score = scores[best_bucket]

        # Calculate confidence (0-100)
        total_score = sum(scores.values())
        confidence = int((max_score / max(total_score, 1)) * 100) if total_score > 0 else 50

        return best_bucket, confidence, scores

    except Exception as e:
        log_warning(f"Could not analyze image: {e}")
        return None, 0, {}


def suggest_bucket_for_user(filename, image_path):
    """
    Suggest a bucket and let user confirm or override.
    """
    print(f"\n{Colors.BOLD}📸 {filename}{Colors.END}")

    # Try to suggest a bucket
    suggested_bucket, confidence, scores = analyze_image_for_bucket(image_path)

    if suggested_bucket:
        log_suggest(f"Suggested: {Colors.BOLD}{suggested_bucket}{Colors.END} ({confidence}% confidence)")

        # Show quick confirm option
        print(f"\nOptions:")
        print(f"  {Colors.GREEN}Y{Colors.END} = Accept {suggested_bucket}")
        for i, bucket in enumerate(APPROVED_BUCKETS, 1):
            if bucket != suggested_bucket:
                print(f"  {i} = Select {bucket}")

        while True:
            choice = input(f"\nChoose [{Colors.GREEN}Y{Colors.END}/1-5]: ").strip().upper()

            if choice == "Y" or choice == "":
                return suggested_bucket

            try:
                num = int(choice)
                if 1 <= num <= len(APPROVED_BUCKETS):
                    selected = APPROVED_BUCKETS[num - 1]
                    if selected != suggested_bucket:
                        log_warning(f"Overriding suggestion: {selected} (was {suggested_bucket})")
                    return selected
            except ValueError:
                pass

            log_error("Invalid input. Enter Y or 1-5")
    else:
        # Fallback to manual selection
        log_warning("Could not analyze image, please select manually:")
        for i, bucket in enumerate(APPROVED_BUCKETS, 1):
            print(f"  {i}. {bucket}")

        while True:
            try:
                choice = int(input("Enter number (1-5): "))
                if 1 <= choice <= len(APPROVED_BUCKETS):
                    return APPROVED_BUCKETS[choice - 1]
            except ValueError:
                pass
            log_error("Invalid choice. Try again.")


def ensure_folders_exist():
    """Verify folders exist."""
    if not STAGING_FOLDER.exists():
        log_error(f"Staging folder not found: {STAGING_FOLDER}")
        STAGING_FOLDER.mkdir(parents=True, exist_ok=True)
        log_warning(f"Created staging folder. Please add photos there.")
        return False

    if not STOCK_PHOTOS_FOLDER.exists():
        log_error(f"Stock_Photos folder not found: {STOCK_PHOTOS_FOLDER}")
        return False

    return True


def get_next_sequence_number():
    """Find the highest existing sequence number and return next."""
    existing_files = list(STOCK_PHOTOS_FOLDER.glob("*.a8Stock.*"))
    if not existing_files:
        return 1

    max_num = 0
    for file in existing_files:
        try:
            num = int(file.name.split(".")[0])
            max_num = max(max_num, num)
        except (ValueError, IndexError):
            pass

    return max_num + 1


def process_staging_folder():
    """Process all files in staging folder."""
    log_info(f"Scanning staging folder: {STAGING_FOLDER}")

    staging_files = [
        f
        for f in STAGING_FOLDER.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not staging_files:
        log_warning("No image files found in staging folder.")
        return []

    log_info(f"Found {len(staging_files)} image(s) to process\n")

    processed_files = []
    next_num = get_next_sequence_number()

    for file in sorted(staging_files):
        # Suggest bucket
        bucket = suggest_bucket_for_user(file.name, file)

        # Create new filename
        ext = file.suffix.lower()
        new_filename = f"{next_num:03d}.a8Stock.{bucket}{ext}"
        new_path = STOCK_PHOTOS_FOLDER / new_filename

        try:
            # Move file
            shutil.move(str(file), str(new_path))
            log_success(f"Saved as: {new_filename}")

            processed_files.append(
                {
                    "original": file.name,
                    "new_name": new_filename,
                    "bucket": bucket,
                    "sequence": next_num,
                }
            )
            next_num += 1

        except Exception as e:
            log_error(f"Failed to move file: {e}")

    return processed_files


def get_all_stock_photos():
    """Get all properly-named stock photos."""
    photos = []
    for file in sorted(STOCK_PHOTOS_FOLDER.glob("*.a8Stock.*")):
        if file.suffix.lower() in SUPPORTED_EXTENSIONS:
            parts = file.name.split(".")
            if len(parts) >= 3:
                try:
                    num = int(parts[0])
                    bucket = ".".join(parts[2:-1])
                    photos.append(
                        {"number": num, "bucket": bucket, "path": file, "name": file.name}
                    )
                except (ValueError, IndexError):
                    pass

    return sorted(photos, key=lambda x: x["number"])


def upload_photos_to_r2(photos):
    """Upload photos to Cloudflare R2 and return R2 URLs."""
    if not R2_ACCESS_KEY or not R2_SECRET_KEY:
        log_warning("R2 credentials not found. Using local paths.")
        return None

    try:
        log_info(f"R2 Config: Endpoint={R2_ENDPOINT}, Bucket={R2_BUCKET_NAME}")

        # Create S3 client for R2
        s3 = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
            region_name="auto"
        )

        log_info(f"Uploading {len(photos)} photos to Cloudflare R2...")
        r2_urls = {}
        upload_count = 0

        for photo in photos:
            local_path = Path(photo["path"])
            if not local_path.exists():
                log_warning(f"File not found: {local_path}")
                continue

            # Upload to R2
            key = photo["name"]
            try:
                with open(local_path, "rb") as f:
                    s3.upload_fileobj(f, R2_BUCKET_NAME, key)
                r2_urls[photo["name"]] = f"{R2_PUBLIC_URL}/{key}"
                upload_count += 1
                log_info(f"  Uploaded: {key}")
            except Exception as e:
                log_error(f"Failed to upload {key}: {e}")

        if upload_count > 0:
            log_success(f"Uploaded {upload_count} photos to R2")
        else:
            log_warning("No photos uploaded to R2")

        return r2_urls if r2_urls else None

    except Exception as e:
        log_error(f"R2 upload failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_proof_sheet(photos, output_path=None, r2_urls=None):
    """Generate HTML proof sheet."""
    log_info("Generating proof sheet...")

    if not photos:
        log_warning("No photos to include in proof sheet.")
        return None

    if output_path is None:
        output_path = STOCK_PHOTOS_FOLDER / "Stock_Photos_ProofSheet.html"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    by_bucket = {}
    for photo in photos:
        bucket = photo["bucket"]
        if bucket not in by_bucket:
            by_bucket[bucket] = []
        by_bucket[bucket].append(photo)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_photos = len(photos)

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceler8-ai Stock Photos Proof Sheet</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5;
            padding: 2rem;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h1 { margin-bottom: 0.5rem; font-size: 2rem; color: #003366; }
        .metadata { color: #666; font-size: 0.9rem; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #ddd; }
        h2 { margin-top: 2rem; margin-bottom: 1rem; font-size: 1.3rem; color: #003366; border-bottom: 2px solid #003366; padding-bottom: 0.5rem; }
        .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2rem; margin-bottom: 2rem; }
        .photo-card { text-align: center; }
        .photo-container { background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; padding: 1rem; margin-bottom: 0.75rem; display: flex; align-items: center; justify-content: center; min-height: 250px; }
        img { max-width: 100%; max-height: 240px; object-fit: contain; }
        .filename { font-family: 'Courier New', monospace; font-size: 0.85rem; font-weight: 500; word-break: break-all; color: #333; }
        .bucket-tag { display: inline-block; background: #003366; color: white; font-size: 0.75rem; padding: 0.35rem 0.6rem; border-radius: 3px; margin-top: 0.5rem; font-weight: 500; }
        .footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; font-size: 0.85rem; color: #666; }
        .footer-link { color: #003366; text-decoration: none; }
        .footer-link:hover { text-decoration: underline; }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; gap: 1.5rem; }
            .container { padding: 1rem; }
            h1 { font-size: 1.5rem; }
        }
        @media print {
            body { padding: 0; background: white; }
            .container { max-width: 100%; padding: 1rem; box-shadow: none; }
            .metadata { display: none; }
            .footer { display: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 Acceler8-ai Stock Photos</h1>
        <div class="metadata">
            <p><strong>Generated:</strong> """ + timestamp + """</p>
            <p><strong>Total photos:</strong> """ + str(total_photos) + """</p>
            <p><strong>Source:</strong> <a href="https://drive.google.com/" class="footer-link">Google Drive</a></p>
        </div>
"""

    for bucket in APPROVED_BUCKETS:
        if bucket in by_bucket:
            photos_in_bucket = by_bucket[bucket]
            html += f'        <h2>{bucket} ({len(photos_in_bucket)})</h2>\n'
            html += '        <div class="grid">\n'

            for photo in photos_in_bucket:
                # Use R2 URL if available, otherwise use local path
                if r2_urls and photo["name"] in r2_urls:
                    img_src = r2_urls[photo["name"]]
                else:
                    img_src = str(photo["path"])

                html += f"""            <div class="photo-card">
                <div class="photo-container">
                    <img src="{img_src}" alt="{photo['name']}" loading="lazy">
                </div>
                <div class="filename">{photo["name"]}</div>
                <div class="bucket-tag">{photo["bucket"]}</div>
            </div>
"""

            html += "        </div>\n"

    html += f"""
        <div class="footer">
            <p><a href="https://proofsheet.acceler8-ai.com" class="footer-link">proofsheet.acceler8-ai.com</a> | Last updated {datetime.now().strftime("%Y-%m-%d")}</p>
        </div>
    </div>
</body>
</html>
"""

    output_path.write_text(html)
    log_success(f"Proof sheet created: {output_path.name}")

    return output_path


def generate_report(processed_files):
    """Generate a processing report."""
    log_info("Generating processing report...")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = f"""# Stock Photo Processing Report

**Generated:** {timestamp}
**Staging Folder:** {STAGING_FOLDER}
**Destination Folder:** {STOCK_PHOTOS_FOLDER}
**Method:** Smart Bucket Suggestion (v3)

## Summary

- **Files Processed:** {len(processed_files)}
"""

    if processed_files:
        report += "\n## Files Processed\n\n"
        report += "| Original | New Name | Bucket | Sequence |\n"
        report += "|----------|----------|--------|----------|\n"

        for file in processed_files:
            report += f"| {file['original']} | {file['new_name']} | {file['bucket']} | {file['sequence']:03d} |\n"

    report += "\n## Proof Sheet\n\n"
    report += "View online: https://proofsheet.acceler8-ai.com\n\n"

    report += "## Next Steps\n\n"
    report += "1. Review the proof sheet: https://proofsheet.acceler8-ai.com\n"
    report += "2. Verify bucket assignments are accurate\n"
    report += "3. Repeat for new photos\n"

    report_file = (
        STOCK_PHOTOS_FOLDER
        / f"2026-{datetime.now().strftime('%m%d')}_Processing_Report.md"
    )
    report_file.write_text(report)
    log_success(f"Report created: {report_file.name}")

    return report


def deploy_to_github(deploy=False):
    """Commit and push to GitHub (Cloudflare auto-deploys)."""
    if not deploy:
        log_warning("Skipping GitHub deployment")
        return False

    if not GITHUB_REPO.exists():
        log_error(f"GitHub repo not found: {GITHUB_REPO}")
        return False

    try:
        log_info(f"Deploying to GitHub...")

        os.chdir(GITHUB_REPO)

        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)

        commit_msg = f"Update proof sheet - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True,
            capture_output=True,
        )

        subprocess.run(["git", "push"], check=True, capture_output=True)

        log_success("Pushed to GitHub")
        log_info("Live at: https://proofsheet.acceler8-ai.com")

        return True

    except subprocess.CalledProcessError as e:
        log_error(f"Git command failed: {e}")
        return False
    except Exception as e:
        log_error(f"Deployment failed: {e}")
        return False


def main():
    """Main workflow."""
    print(f"\n{Colors.BOLD}🖼  Acceler8-ai Stock Photo Processor v3{Colors.END}")
    print(f"{Colors.CYAN}Smart Bucket Suggestion + Auto-Publishing{Colors.END}\n")

    # Always deploy by default (auto-publishing enabled)
    deploy = True

    if not ensure_folders_exist():
        return

    processed_files = process_staging_folder()

    if processed_files:
        log_success(f"\nProcessed {len(processed_files)} file(s)")
    else:
        log_warning("No new files to process.")

    # Always generate and deploy proof sheet (even if no new files)
    all_photos = get_all_stock_photos()
    if all_photos:
        # Upload photos to R2
        r2_urls = upload_photos_to_r2(all_photos)

        # Generate proof sheet with R2 URLs
        local_path = STOCK_PHOTOS_FOLDER / "Stock_Photos_ProofSheet.html"
        generate_proof_sheet(all_photos, local_path, r2_urls)

        if GITHUB_REPO.exists():
            github_path = PROOFSHEET_OUTPUT
            generate_proof_sheet(all_photos, github_path, r2_urls)
            log_success(f"Also generated for GitHub: {github_path}")
    else:
        log_warning("No photos found in Stock_Photos folder.")
        return

    if processed_files:
        generate_report(processed_files)

    # Always deploy to GitHub (Cloudflare auto-publishes)
    deploy_to_github(deploy=True)

    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Complete!{Colors.END}\n")
    print(f"Proof sheet live at: https://proofsheet.acceler8-ai.com\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Cancelled.{Colors.END}")
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
