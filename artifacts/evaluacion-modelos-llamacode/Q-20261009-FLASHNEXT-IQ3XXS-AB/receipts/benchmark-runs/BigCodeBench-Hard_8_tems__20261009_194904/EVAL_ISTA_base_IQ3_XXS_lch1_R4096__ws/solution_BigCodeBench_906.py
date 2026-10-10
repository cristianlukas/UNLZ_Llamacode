import zipfile
import os
import re
import shutil


def task_func(source_dir: str, target_dir: str, archive_name: str = 'archive.zip') -> str:
    os.makedirs(target_dir, exist_ok=True)
    archive_path = os.path.join(target_dir, archive_name)
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for filename in files:
                if '_processed' in filename:
                    file_path = os.path.join(root, filename)
                    zf.write(file_path, arcname=filename)
    return archive_path
