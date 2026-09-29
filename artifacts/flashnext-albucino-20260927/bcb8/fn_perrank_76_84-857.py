import warnings
import os
import glob
import shutil
import time

def task_func(SOURCE_DIR, DEST_DIR, EXTENSIONS):
    """
    Transfer files from SOURCE_DIR to DEST_DIR based on specified file extensions.
    
    Args:
        SOURCE_DIR: Source directory path
        DEST_DIR: Destination directory path
        EXTENSIONS: List of file extensions to transfer (e.g., ['.txt', '.pdf'])
    
    Returns:
        transferred_files: A list containing the names of files that were successfully transferred.
    """
    transferred_files = []
    
    # Ensure destination directory exists
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
    
    # Collect all files in source directory
    all_files = []
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            all_files.append(os.path.join(root, file))
    
    # Filter files by extension
    for filepath in all_files:
        _, ext = os.path.splitext(filepath)
        # Normalize extension to lowercase for comparison
        ext_lower = ext.lower()
        
        # Check if the extension matches any in the EXTENSIONS list
        matched = False
        for target_ext in EXTENSIONS:
            # Normalize target extension to lowercase and ensure it starts with a dot
            target_ext_normalized = target_ext.lower()
            if not target_ext_normalized.startswith('.'):
                target_ext_normalized = '.' + target_ext_normalized
            
            if ext_lower == target_ext_normalized:
                matched = True
                break
        
        if not matched:
            continue
        
        # Attempt to transfer the file
        filename = os.path.basename(filepath)
        dest_path = os.path.join(DEST_DIR, filename)
        
        try:
            shutil.copy2(filepath, dest_path)
            transferred_files.append(filename)
        except Exception as e:
            warnings.warn(f"Could not transfer file '{filename}': {e}")
    
    return transferred_files
