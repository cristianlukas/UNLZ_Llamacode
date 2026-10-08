import warnings
import os
import glob
import shutil
import time

def task_func(SOURCE_DIR, DEST_DIR, EXTENSIONS):
    transferred_files = []
    
    # Ensure destination directory exists
    os.makedirs(DEST_DIR, exist_ok=True)
    
    # Convert extensions to a set for efficient lookup
    extensions_set = set(EXTENSIONS)
    
    # Get all files in the source directory
    try:
        all_files = glob.glob(os.path.join(SOURCE_DIR, '*'))
    except Exception as e:
        warnings.warn(f"Error accessing source directory: {e}")
        return transferred_files
    
    for file_path in all_files:
        # Skip if it's not a file
        if not os.path.isfile(file_path):
            continue
        
        # Get the file extension
        _, file_extension = os.path.splitext(file_path)
        
        # Check if the file extension matches any of the specified extensions
        if file_extension.lower() in extensions_set:
            try:
                # Get the filename without the path
                filename = os.path.basename(file_path)
                
                # Construct the destination path
                dest_path = os.path.join(DEST_DIR, filename)
                
                # Check if destination file already exists
                if os.path.exists(dest_path):
                    # Overwrite existing file
                    os.remove(dest_path)
                
                # Transfer the file
                shutil.copy2(file_path, dest_path)
                transferred_files.append(filename)
                
            except Exception as e:
                warnings.warn(f"Failed to transfer file {os.path.basename(file_path)}: {e}")
    
    return transferred_files