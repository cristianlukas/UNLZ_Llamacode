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
    
    # Build patterns for each extension
    for ext in EXTENSIONS:
        # Ensure extension starts with a dot
        if not ext.startswith('.'):
            ext = '.' + ext
        pattern = os.path.join(SOURCE_DIR, '*' + ext)
        files = glob.glob(pattern)
        
        for file_path in files:
            if not os.path.isfile(file_path):
                continue
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(DEST_DIR, file_name)
            try:
                shutil.move(file_path, dest_path)
                transferred_files.append(file_name)
            except Exception as e:
                warnings.warn(f"Could not transfer file '{file_name}': {e}")
    
    return transferred_files
