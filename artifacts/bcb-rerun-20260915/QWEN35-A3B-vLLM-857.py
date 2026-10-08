import warnings
import os
import glob
import shutil
import time

def task_func(SOURCE_DIR, DEST_DIR, EXTENSIONS):
    transferred_files = []
    os.makedirs(DEST_DIR, exist_ok=True)
    
    # Normalize extensions to lowercase with leading dot
    normalized_exts = []
    for ext in EXTENSIONS:
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized_exts.append(ext.lower())
        
    try:
        files = os.listdir(SOURCE_DIR)
    except FileNotFoundError:
        warnings.warn(f"Source directory {SOURCE_DIR} does not exist.")
        return transferred_files
    except PermissionError:
        warnings.warn(f"Permission denied accessing {SOURCE_DIR}.")
        return transferred_files
        
    for filename in files:
        src_path = os.path.join(SOURCE_DIR, filename)
        if not os.path.isfile(src_path):
            continue
            
        _, ext = os.path.splitext(filename)
        if ext.lower() in normalized_exts:
            dst_path = os.path.join(DEST_DIR, filename)
            try:
                shutil.copy2(src_path, dst_path)
                transferred_files.append(filename)
            except Exception as e:
                warnings.warn(f"Failed to transfer file '{filename}': {e}")
                
    return transferred_files