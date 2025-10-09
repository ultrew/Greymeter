# stego_detector.py

import numpy as np
from PIL import Image, ExifTags
from stegano import lsb
import hashlib
from scipy.stats import chisquare
import subprocess
import os
import shutil
import re

def calculate_hashes(file_path):
    hashes = {}
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5.update(byte_block)
            sha1.update(byte_block)
            sha256.update(byte_block)
    hashes['md5'], hashes['sha1'], hashes['sha256'] = md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()
    return hashes

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, errors='ignore')
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing command:\n{e.stderr}"

def run_file_command(file_path): return run_command(f"file \"{file_path}\"")
def run_binwalk(file_path): return run_command(f"binwalk \"{file_path}\"")

def run_binwalk_extract_and_zip(file_path):
    output_dir = os.path.dirname(file_path)
    zip_output_path = os.path.join(output_dir, "binwalk_extraction.zip")
    command_to_run = f"binwalk --dd='.*' -eM \"{file_path}\" --directory=\"{output_dir}\""
    run_command(command_to_run)
    extraction_dir_name = f"_{os.path.basename(file_path)}.extracted"
    full_extraction_path = os.path.join(output_dir, extraction_dir_name)
    if os.path.exists(full_extraction_path) and os.listdir(full_extraction_path):
        shutil.make_archive(zip_output_path.replace('.zip', ''), 'zip', full_extraction_path)
        shutil.rmtree(full_extraction_path)
        return zip_output_path
    else:
        if os.path.exists(full_extraction_path): shutil.rmtree(full_extraction_path)
        return None

def carve_appended_file(file_path, binwalk_output):
    """
    Parses binwalk output to find appended files, carves them using dd,
    and intelligently renames the output file based on its actual content.
    """
    lines = binwalk_output.strip().split('\n')
    for line in lines[1:]: # Check from the second line onwards
        match = re.match(r'^(\d+)\s+', line)
        if match:
            offset = match.group(1)
            if int(offset) > 0:
                output_dir = os.path.dirname(file_path)
                carved_file_path = os.path.join(output_dir, f"carved_file_at_{offset}")
                
                # Use dd to carve the file from the offset to the end
                dd_command = f"dd if=\"{file_path}\" of=\"{carved_file_path}\" bs=1 skip={offset}"
                run_command(dd_command)

                # Intelligently determine the file type using the 'file' command
                file_type_info = run_command(f"file \"{carved_file_path}\"")
                
                new_ext = ".bin" # Default extension
                if "jpeg image data" in file_type_info.lower(): new_ext = ".jpg"
                elif "png image data" in file_type_info.lower(): new_ext = ".png"
                elif "zip archive data" in file_type_info.lower(): new_ext = ".zip"
                elif "pdf document" in file_type_info.lower(): new_ext = ".pdf"
                elif "ascii text" in file_type_info.lower(): new_ext = ".txt"

                final_filename = f"carved_file_at_{offset}{new_ext}"
                final_filepath = os.path.join(output_dir, final_filename)
                
                # Rename the file with the correct extension
                os.rename(carved_file_path, final_filepath)
                
                return final_filepath
    return None


def run_steghide_extract(file_path):
    if not file_path.lower().endswith(('.jpg', '.jpeg')): return "Steghide Error: This tool is primarily for JPEG files.", None
    output_dir = os.path.dirname(file_path)
    temp_output_name = "steghide_out"
    temp_output_path = os.path.join(output_dir, temp_output_name)
    command = f"steghide extract -sf \"{file_path}\" -p '' -f -xf \"{temp_output_path}\""
    run_command(command)
    if os.path.exists(temp_output_path):
        file_type_info = run_command(f"file \"{temp_output_path}\"")
        new_ext = ".txt"
        if "jpeg image data" in file_type_info.lower(): new_ext = ".jpg"
        elif "png image data" in file_type_info.lower(): new_ext = ".png"
        elif "zip archive data" in file_type_info.lower(): new_ext = ".zip"
        elif "pdf document" in file_type_info.lower(): new_ext = ".pdf"
        final_filename = f"steghide_extracted{new_ext}"
        final_filepath = os.path.join(output_dir, final_filename)
        os.rename(temp_output_path, final_filepath)
        try:
            content_preview = "Cannot display preview for this file type."
            if new_ext == ".txt":
                with open(final_filepath, 'r', errors='ignore') as f: content_preview = f.read(500)
            message = f"Steghide successfully extracted file: '{final_filename}'\n\n--- File Content Preview ---\n{content_preview}"
            return message, final_filepath
        except Exception as e: return f"Steghide extracted file '{final_filename}', but it could not be read. Error: {e}", final_filepath
    else: return "Steghide execution failed. No data was extracted.", None

def get_metadata(image):
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                if isinstance(value, bytes): value = value.decode(errors='ignore')
                exif_data[str(decoded)] = str(value)
    except Exception: return {}
    return exif_data

def detect_hidden_data(image):
    if image.mode != 'RGB': image = image.convert('RGB')
    img_array = np.array(image)
    p_values = []
    for i in range(3):
        lsbs = img_array[:, :, i] & 1
        flat_lsbs = lsbs.flatten()
        observed_freq = np.array([np.count_nonzero(flat_lsbs == 0), np.count_nonzero(flat_lsbs == 1)])
        if np.sum(observed_freq) == 0: continue
        _, p = chisquare(observed_freq)
        p_values.append(p)
    if not p_values: return False, 1.0
    avg_p_value = np.mean(p_values)
    is_suspect = avg_p_value < 0.05
    return is_suspect, avg_p_value

def extract_text(image_path):
    try: return lsb.reveal(image_path)
    except Exception: return None