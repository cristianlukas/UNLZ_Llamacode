import warnings
import os
import glob
import shutil
import time
import re

def task_func(SOURCE_DIR, DEST_DIR, EXTENSIONS):
    """
    Transfers files from SOURCE_DIR to DEST_DIR based on specified extensions.
    
    Parameters:
    SOURCE_DIR (str): Path to the source directory
    DEST_DIR (str): Path to the destination directory
    EXTENSIONS (list): List of file extensions to transfer (case-insensitive)
    
    Returns:
    list: List of names of successfully transferred files
    
    Raises:
    FileNotFoundError: If SOURCE_DIR does not exist
    PermissionError: If there are permission issues
    """
    # Validate inputs
    if not os.path.exists(SOURCE_DIR):
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")
    if not os.path.isdir(SOURCE_DIR):
        raise FileNotFoundError(f"Source path is not a directory: {SOURCE_DIR}")
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR, exist_ok=True)
    
    # Normalize extensions to lowercase for case-insensitive matching
    ext_pattern = re.compile(r'\.' + re.escape(EXTENSIONS).lower())
    
    transferred_files = []
    
    try:
        # Iterate through files in source directory
        for filename in os.listdir(SOURCE_DIR):
            source_path = os.path.join(SOURCE_DIR, filename)
            
            # Skip directories
            if os.path.isdir(source_path):
                continue
            
            # Check if file extension matches
            if ext_pattern.match(filename):
                dest_path = os.path.join(DEST_DIR, filename)
                
                try:
                    # Create destination directory if it doesn't exist
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    # Copy the file
                    shutil.copy2(source_path, dest_path)
                    transferred_files.append(filename)
                    
                except (PermissionError, OSError) as e:
                    warnings.warn(f"Could not transfer file '{filename}': {str(e)}")
                    continue
                    
    except PermissionError:
        raise PermissionError("Permission denied while copying files")
    except Exception as e:
        raise e
    
    return transferred_files