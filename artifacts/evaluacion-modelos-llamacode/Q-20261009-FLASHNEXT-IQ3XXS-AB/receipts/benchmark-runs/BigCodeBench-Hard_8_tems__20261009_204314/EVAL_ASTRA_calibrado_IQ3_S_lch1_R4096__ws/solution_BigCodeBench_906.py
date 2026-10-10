import zipfile
import os
import re
import shutil
def task_func(source_dir: str, target_dir: str, archive_name: str = 'archive.zip') -> str:
    os.makedirs(target_dir, exist_ok=True)
    archive_path = os.path.join(target_dir, archive_name)
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in os.listdir(source_dir):
            if re.search(r'_processed', filename):
                file_path = os.path.join(source_dir, filename)
                if os.path.isfile(file_path):
                    zf.write(file_path, filename)
    return archive_path
