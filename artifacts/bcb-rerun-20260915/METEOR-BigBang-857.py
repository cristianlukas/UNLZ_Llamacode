import warnings
import os
import glob
import shutil
import time

def task_func(SOURCE_DIR, DEST_DIR, EXTENSIONS):
    """
    Transfer files from SOURCE_DIR to DEST_DIR based on specified file extensions.
    
    Parameters:
    SOURCE_DIR (str): The source directory.
    DEST_DIR (str): The destination directory.
    EXTENSIONS (list): A list of file extensions to transfer (e.g., ['.txt', '.csv']).
    
    Returns:
    list: A list of successfully transferred file names.
    """
    # Ensure destination directory exists
    os.makedirs(DEST_DIR, exist_ok=True)
    
    transferred_files = []
    
    for ext in EXTENSIONS:
        # Use glob to find all files with the given extension in the source directory
        pattern = os.path.join(SOURCE_DIR, f'*{ext}')
        files = glob.glob(pattern)
        
        for file_path in files:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(DEST_DIR, file_name)
            
            try:
                # If destination file exists, skip it (or you could overwrite)
                if os.path.exists(dest_path):
                    warnings.warn(f"File {file_name} already exists in destination, skipping.")
                    continue
                
                # Copy the file
                shutil.copy2(file_path, dest_path)
                transferred_files.append(file_name)
            except Exception as e:
                warnings.warn(f"Could not transfer {file_name}: {e}")
    
    return transferred_files