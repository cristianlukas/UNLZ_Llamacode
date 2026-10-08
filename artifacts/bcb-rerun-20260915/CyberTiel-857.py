import warnings
import os
import glob
import shutil
import time

def task_func(SOURCE_DIR, DEST_DIR, EXTENSIONS):
    """
    Transfer files from SOURCE_DIR to DEST_DIR based on specified extensions.
    
    Parameters:
    SOURCE_DIR (str): The directory to transfer files from.
    DEST_DIR (str): The directory to transfer files to.
    EXTENSIONS (list): A list of file extensions to transfer.
    
    Returns:
    list: A list of successfully transferred file names.
    """
    # Ensure the destination directory exists
    os.makedirs(DEST_DIR, exist_ok=True)
    
    transferred_files = []
    
    # Iterate over each extension
    for ext in EXTENSIONS:
        # Ensure the extension starts with a dot
        if not ext.startswith('.'):
            ext = '.' + ext
        
        # Find all files with the current extension in the source directory
        pattern = os.path.join(SOURCE_DIR, '*' + ext)
        files = glob.glob(pattern)
        
        for file_path in files:
            # Construct the destination file path
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(DEST_DIR, file_name)
            
            try:
                # Transfer the file
                shutil.copy2(file_path, dest_path)
                transferred_files.append(file_name)
            except Exception as e:
                # Issue a warning if the file could not be transferred
                warnings.warn(
                    f"Failed to transfer '{file_name}': {e}",
                    UserWarning
                )
    
    return transferred_files