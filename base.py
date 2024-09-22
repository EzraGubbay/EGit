import os
import data
import itertools
from collections import namedtuple, deque
import operator

# Retrieve list of ignored files
ignore_list = data.get_ignore_list()

def write_tree(directory='.'):
    tree = []
    with os.scandir(directory) as it:
        for entry in it:
            path = f'{directory}/{entry.name}'
            if is_ignored(path):
                continue

            if entry.is_file(follow_symlinks=False):
                tree.append(add_file_to_tree(path, entry.name))
            elif entry.is_dir(follow_symlinks=False):
                tree.append(add_tree_to_tree(write_tree(path), entry.name))

    tree_data = ''.join(tree)
    return data.hash_object('tree', tree_data.encode(), write=True)

def is_ignored(path):
    for ignored in ignore_list:
        if ignored in path.split('/'):
            return True
    return False

def add_file_to_tree(path, filename):
    with open(path, 'rb') as f:
        oid = data.hash_object('blob', f.read(), write=True)
        header = data.get_object_header(oid)
        return f'{data.OBJ_TYPES[header[0].decode()]} {header[0].decode()} {oid} {filename}\n'

def add_tree_to_tree(tree_oid, filename):
    return f'{data.OBJ_TYPES["tree"]} tree {tree_oid} {filename}\n'

def _iterate_tree(tree_id):
    if not tree_id:
        return
    content = data.get_object_content(tree_id)
    for line in content.decode().splitlines():
        _, type_, oid, filename = line.split(' ', 3)
        yield type_, oid, filename

def get_tree(tree_id, base_path=''):
    tree = {}
    for type_, oid, filename in _iterate_tree(tree_id):
        assert '/' not in filename
        assert filename not in ('.', '..')
        path = f'{base_path}{filename}'
        if type_ == 'blob':
            tree[path] = oid
        elif type_ == 'tree':
            tree.update(get_tree(oid, f'{path}/'))
        else:
            assert False, f'Unknown object type: {type_}'
    return tree

def read_tree(tree_id):
    _empty_current_directory()
    for path, oid in get_tree(tree_id).items():
        parent_directory = os.path.dirname(path)
        if parent_directory != '':
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object_content(oid))

def _empty_current_directory():
    for root_dir, dirnames, filenames in os.walk('.', topdown=False):
        for file in filenames:
            path = os.path.relpath(os.path.join(root_dir, file))
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)

        for directory in dirnames:
            path = os.path.relpath(os.path.join(root_dir, directory))
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                pass

Commit = namedtuple('Commit', ['tree', 'parent', 'message'])

def get_commit(oid):
    parent = None
    commit = data.get_object_content(oid).decode()
    lines = iter(commit.splitlines())
    for line in itertools.takewhile(operator.truth, lines):
        key, value = strip_nulls(line.split(' ', 1))
        if key == 'tree':
            tree = value
        elif key == 'commit':
            parent = value
        else:
            assert False, f'Unknown object type: {key}'
    message = '\n'.join(lines)
    return Commit(tree=tree, parent=parent, message=message)

def commit(message):
    oid = write_tree()
    content = f"tree {oid}\n"
    if data.get_ref('HEAD') != '':
        content += f"commit {data.get_ref('HEAD')}\n"
    content += f'\n{message}\n'
    commit_oid = data.hash_object('commit', content.encode(), write=True)
    data.update_ref('HEAD', commit_oid)
    return f"Created new commit: {commit_oid}"

def checkout(commit_id):
    tree = data.get_object_content(commit_id).decode().splitlines()[0]
    tree_id = tree.split(' ', 1)[1]
    read_tree(tree_id)
    data.update_ref('HEAD', commit_id)

def tag(tagname, commit_id):
    data.update_ref(f'refs/tags/{tagname}', commit_id)

def get_oid(tagname):
    if tagname == 'HEAD': return data.get_ref('HEAD')
    return data.get_ref(f'refs/tags/{tagname}') or data.get_ref(f'refs/heads/tagname') or tagname

def iter_commits_and_parents(oids):
    oids = deque(oids)
    visited = set()

    while oids:
        oid = oids.popleft()
        if not oid or oid in visited:
            continue
        else:
            visited.add(oid)
            yield oid
        commit = get_commit(oid)
        oids.appendleft(commit.parent)


def strip_nulls(line):

    return line[0].replace('\x00', ''), line[1].replace('\x00', '')

