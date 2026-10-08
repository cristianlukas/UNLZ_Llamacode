import os

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    if not os.path.exists(file_path1) or not os.path.exists(file_path2):
        raise FileNotFoundError("File not found")
    
    try:
        with open(file_path1, 'r', newline='') as f1:
            lines1 = f1.readlines()
        with open(file_path2, 'r', newline='') as f2:
            lines2 = f2.readlines()
    except Exception as e:
        raise Exception(e)
        
    if not lines1 or not lines2:
        raise ValueError("File is empty")
        
    diff = ndiff(lines1, lines2)
    results = []
    line_num = 1
    for line in diff:
        if line.startswith('  '):
            status = ' '
            content = line[2:].rstrip('\n')
        elif line.startswith('- '):
            status = '-'
            content = line[2:].rstrip('\n')
        elif line.startswith('+ '):
            status = '+'
            content = line[2:].rstrip('\n')
        else:
            continue # Skip '? ' lines
        
        results.append({'Line Number': line_num, 'Status': status, 'Content': content})
        line_num += 1
        
    return pd.DataFrame(results, columns=['Line Number', 'Status', 'Content'])