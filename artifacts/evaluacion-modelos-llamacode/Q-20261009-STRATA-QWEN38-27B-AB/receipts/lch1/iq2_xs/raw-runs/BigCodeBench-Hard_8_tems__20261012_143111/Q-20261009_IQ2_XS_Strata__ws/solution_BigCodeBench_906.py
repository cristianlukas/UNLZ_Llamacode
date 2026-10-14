import zipfile
import os
import re
import shutil

def task_func(source_dir: str, target_dir: str, archive_name: str = 'archive.zip') -> str:
    os.makedirs(target_dir, exist_ok=True)
    pattern = re.compile(r'_processed')

    matched = []
    for entry in sorted(os.listdir(source_dir)):
        path = os.path.join(source_dir, entry)
        if not os.path.isfile(path):
            continue
        if not pattern.search(entry):
            continue
        matched.append((entry, path))

    for entry, path in matched:
        shutil.copy(path, os.path.join(target_dir, entry))

    archive_path = os.path.join(target_dir, archive_name)
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for entry, path in matched:
            archive.write(path, entry)

    return archive_path
