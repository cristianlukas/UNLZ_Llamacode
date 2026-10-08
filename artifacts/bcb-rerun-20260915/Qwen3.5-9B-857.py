import warnings
import os
import glob
import shutil
import time

def task_func(SOURCE_DIR, DEST_DIR, EXTENSIONS):
    transferred_files = []
    
    # Ensure destination directory exists
    os.makedirs(DEST_DIR, exist_ok=True)
    
    # Build glob patterns for each extension
    patterns = []
    for ext in EXTENSIONS:
        # Handle both .ext and ext formats
        if ext.startswith('.'):
            pattern = f"*{ext}"
        else:
            pattern = f"*.{ext}"
        patterns.append(os.path.join(SOURCE_DIR, pattern))
    
    # Collect all matching files
    all_files = []
    for pattern in patterns:
        all_files.extend(glob.glob(pattern))
    
    # Remove duplicates if any
    all_files = list(set(all_files))
    
    # Process each file
    for file_path in all_files:
        filename = os.path.basename(file_path)
        dest_path = os.path.join(DEST_DIR, filename)
        
        try:
            # Check if file exists and is readable
            if not os.path.isfile(file_path):
                warnings.warn(f"File not found or not a file: {file_path}")
                continue
            
            # Check if destination already exists
            if os.path.exists(dest_path):
                warnings.warn(f"File already exists in destination, skipping: {filename}")
                continue
            
            # Perform the transfer
            shutil.copy2(file_path, dest_path)
            transferred_files.append(filename)
            
        except PermissionError:
            warnings.warn(f"Permission denied: {file_path}")
        except OSError as e:
            warnings.warn(f"OS error transferring {file_path}: {str(e)}")
        except Exception as e:
            warnings.warn(f"Unexpected error transferring {file_path}: {str(e)}")
    
    return transferred_files