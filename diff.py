from collections import defaultdict
from tempfile import NamedTemporaryFile as Temp
import data
import subprocess

def compare_trees(*trees):
    files = defaultdict(lambda: [None] * len(trees))
    for index, tree in enumerate(trees):
        for path, oid in tree.items():
            files[path][index] = oid

    for path, oids in files.items():
        yield path, *oids

def diff_trees(tree_a, tree_b):

    diff_output = b''
    for path, o_from, o_to in compare_trees(tree_a, tree_b):
        if o_from != o_to:
            diff_output += diff_files(o_from, o_to, path)
    return diff_output

def diff_files(oid_a, oid_b, path='blob'):

    with Temp() as file_from, Temp() as file_to:
        for oid, f in (oid_a, file_from), (oid_b, file_to):
            if oid:
                f.write(data.get_object(oid))
                f.flush()
        with subprocess.Popen(['diff', '--text', '--unified', '--show-c-function', '--label',
            f'a/{path}', file_from.name, '--label', f'b/{path}', file_to.name,],
                              stdout=subprocess.PIPE) as proc:
            output, _ = proc.communicate()
    return output

def iter_changed_files(original, new):
    changed = {}
    for path, oid_original, oid_new in compare_trees(original, new):
        if path not in original:
            yield path, "created"
        elif path not in new:
            yield path, "deleted"
        elif oid_original != oid_new:
            yield path, "modified"

def merge_trees(HEAD_tree, other_tree, base):
    tree = {}
    for path, HEAD_object, other_object, base_object in compare_trees(HEAD_tree, other_tree, base):
        tree[path] = merge_blobs(HEAD_object, other_object, base_object)
    return tree

def merge_blobs(HEAD_object, other_object, base_object):
    with Temp() as HEAD_file, Temp() as other_file, Temp() as base_file:
        for oid, file in (HEAD_object, HEAD_file), (other_object, other_file), (base_object, base_file):
            if oid:
                file.write(data.get_object(oid))
                file.flush()
        with subprocess.Popen([
            'diff3', '--text', '-m',
            '-L', 'HEAD', HEAD_file.name,
            '-L', 'MERGE_HEAD', other_file.name,
            '-L', 'BASE', base_file.name
        ], stdout=subprocess.PIPE) as proc:
            output, _ = proc.communicate()
            assert proc.returncode in (0, 1)

        return output