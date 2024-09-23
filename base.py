import os
import string
from string import hexdigits

import data
import itertools
from collections import namedtuple, deque
import operator

from data import RefValue

# Retrieve list of ignored files
ignore_list = data.get_ignore_list()

# Writes a tree object to the object directory. Returns the SHA1 checksum of the newly created tree object.
def write_tree(directory='.'):
    tree = []
    with os.scandir(directory) as it:
        for entry in it:
            path = f'{directory}/{entry.name}'
            if is_ignored(path):
                continue

            if entry.is_file(follow_symlinks=False):
                tree.append(_add_file_to_tree(path, entry.name))
            elif entry.is_dir(follow_symlinks=False):
                tree.append(_add_tree_to_tree(write_tree(path), entry.name))

    tree_data = ''.join(tree)
    return data.hash_object('tree', tree_data.encode(), write=True)

# Returns True if the given file is on the ignored list, False otherwise.
def is_ignored(path):
    for ignored in ignore_list:
        if ignored in path.split('/'):
            return True
    return False

def _add_file_to_tree(path, filename):
    with open(path, 'rb') as f:
        oid = data.hash_object('blob', f.read(), write=True)
        header = data.get_object_header(oid)
        return f'{data.OBJ_TYPES[header[0].decode()]} {header[0].decode()} {oid} {filename}\n'

def _add_tree_to_tree(tree_oid, filename):
    return f'{data.OBJ_TYPES["tree"]} tree {tree_oid} {filename}\n'

# Iterates over all items in the given tree, yielding the object type, object ID and filename in the tree.
# Method is non-recursive.
def _iterate_tree(tree_id):
    if not tree_id:
        return
    content = data.get_object_content(tree_id)
    for line in content.decode().splitlines():
        _, type_, oid, filename = line.split(' ', 3)
        yield type_, oid, filename

# Returns a dictionary object containing paths of all files in the given base_path value.
# By default, uses the current working directory.
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

# Low level plumbing command. Reads a tree into the working directory.
# Effectively like rolling back to a previous commit.
def read_tree(tree_id):
    _empty_current_directory()
    for path, oid in get_tree(tree_id).items():
        parent_directory = os.path.dirname(path)
        if parent_directory != '':
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object_content(oid))

# Empties the entire working directory (except for .egit, .egitignore and all ignored files).
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

# Returns a Commit namedtuple of the commit associated with the given object ID.
def get_commit(oid):
    # Resolve method parameter to the actual object ID, if it is a tagname for example.
    oid = get_oid(oid)
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

# Commit the working directory. Currently, commits its entirety. Writes the tree, creates commit object and updates HEAD
# TODO: Commit only the contents of the index file.
def commit(message):
    oid = write_tree()
    content = f"tree {oid}\n"

    # Check if HEAD points to an empty reference. This will generally only happen if no commit has been made since
    # initialization.
    HEAD = data.get_ref('HEAD')
    if HEAD.value is not None:
        content += f"commit {HEAD.value}\n"
    content += f'\n{message}\n'
    commit_oid = data.hash_object('commit', content.encode(), write=True)
    data.update_ref('HEAD', RefValue(symbolic=False, value=commit_oid))
    return f"Created new commit: {commit_oid}"

def checkout(refname):
    commit = get_commit(refname)
    read_tree(commit.tree)
    data.update_ref('HEAD', data.RefValue(symbolic=True, value=f'ref: refs/heads/{refname}'), deref=False)

    if is_branch(refname):
        HEAD = data.RefValue(symbolic=True, value=f'refs/heads/{refname}')
    else:
        HEAD = data.RefValue(symbolic=False, value=refname)
    data.update_ref('HEAD', HEAD, deref=False)

def is_branch(name):
    return data.get_ref(f'refs/heads/{name}').value is not None

def tag(tagname, commit_id):
    data.update_ref(f'refs/tags/{tagname}', commit_id, deref=True)

def get_oid(tagname):
    if tagname == 'HEAD': return data.get_ref('HEAD').value
    options = [
        f'{tagname}',
        f'refs/{tagname}',
        f'refs/heads/{tagname}',
        f'refs/tags/{tagname}',
    ]
    for option in options:
        if data.get_ref(option, deref=False).value:
            return data.get_ref(option).value

    # Check if the provided tagname is actually an object ID
    is_sha1 = all(char in string.hexdigits for char in tagname)
    if len(tagname) == 40 and is_sha1:
        return tagname

    assert False, f'No such reference or object: {tagname}'

def iter_commits_and_parents(oids):
    oids = deque({get_oid(oids)})
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

