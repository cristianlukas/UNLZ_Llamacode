import warnings
import os
import glob
import shutil
import time

def task_func(SOURCE_DIR, DEST_DIR, EXTENSIONS):
    transferred_files = []
    
    if not os.path.exists(SOURCE_DIR):
        warnings.warn(f"Source directory '{SOURCE_DIR}' does not exist.")
        return transferred_files
    
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
    
    for ext in EXTENSIONS:
        pattern = os.path.join(SOURCE_DIR, f"*{ext}")
        files = glob.glob(pattern)
        
        for file_path in files:
            if os.path.isfile(file_path):
                try:
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(DEST_DIR, filename)
                    shutil.copy2(file_path, dest_path)
                    transferred_files.append(filename)
                except Exception as e:
                    warnings.warn(f"Failed to transfer '{filename}': {str(e)}")
    
    return transferred_files