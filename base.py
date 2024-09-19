import os
import data

IGNORE_LIST = ['.egit', '.git', '.gitignore']

def write_tree(directory='.'):
    tree = []
    with os.scandir(directory) as it:
        for entry in it:
            path = f'{directory}/{entry.name}'
            if is_ignored(path):
                continue

            if entry.is_file(follow_symlinks=False):
                tree.append(add_to_tree(path, entry.name))
            elif entry.is_dir(follow_symlinks=False):
                write_tree(path)

    tree_data = '\n'.join(tree)
    print(data.hash_object(tree_data.encode(), write=True))

def is_ignored(path):
    for ignored in IGNORE_LIST:
        if ignored in path.split('/'):
            return True
    return False

def add_to_tree(path, filename):
    with open(path, 'rb') as f:
        oid = data.hash_object(f.read(), write=False)
        obj = data.get_object(oid)
        header, content = data.get_object_parts(obj)
        return f'{data.OBJ_TYPES[header[0]]} {header[0]} {oid} {filename}'