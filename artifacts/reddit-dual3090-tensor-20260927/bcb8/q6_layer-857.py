import warnings
import os
import glob
import shutil
import time

def task_func(SOURCE_DIR, DEST_DIR, EXTENSIONS):
    transferred_files = []
    
    # Ensure destination directory exists
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
    
    # Normalize extensions to have leading dot
    normalized_extensions = []
    for ext in EXTENSIONS:
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized_extensions.append(ext.lower())
    
    # Iterate through all files in SOURCE_DIR
    for filename in os.listdir(SOURCE_DIR):
        source_path = os.path.join(SOURCE_DIR, filename)
        
        # Only process files, not directories
        if not os.path.isfile(source_path):
            continue
        
        # Check if file extension matches any of the specified extensions
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in normalized_extensions:
            continue
        
        # Attempt to transfer the file
        dest_path = os.path.join(DEST_DIR, filename)
        try:
            shutil.move(source_path, dest_path)
            transferred_files.append(filename)
        except Exception as e:
            warnings.warn(f"Failed to transfer file '{filename}': {str(e)}")
    
    return transferred_files
