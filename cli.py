import argparse
import subprocess
from dotenv import load_dotenv
import data
import base
import textwrap
import diff
import sys

def main():
    load_dotenv()
    args = parse_args()
    args.func(args)

def parse_args():

    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(dest='command')
    commands.required = True

    oid = base.get_oid

    init_parser = commands.add_parser('init')
    init_parser.set_defaults(func=init)

    hash_object_parser = commands.add_parser('hash-object')
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument('file')
    hash_object_parser.add_argument('--write', '-w', action='store_true')

    cat_file_parser = commands.add_parser('cat-file')
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument('object', type=oid)
    cat_file_parser.add_argument('-p', help="pretty print the object contents", action='store_true')
    cat_file_parser.add_argument('-t', help="Print the object file type only", action='store_true')

    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func=write_tree)

    read_tree_parser = commands.add_parser('read-tree')
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument('tree')

    remove_parser = commands.add_parser('rmobj')
    remove_parser.set_defaults(func=rmobj)
    remove_parser.add_argument('object')

    commit_parser = commands.add_parser('commit')
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('-m', '--message', required=True, help='Enter a commit message')

    log_parser = commands.add_parser('log')
    log_parser.set_defaults(func=log)
    log_parser.add_argument('object', help='Enter a commit object ID', type=oid, default='HEAD', nargs='?')

    checkout_parser = commands.add_parser('checkout')
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument('commit')

    tag_parser = commands.add_parser('tag')
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument('tagname')
    tag_parser.add_argument('commit')

    branch_parser = commands.add_parser('branch')
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument('name', nargs='?')

    status_parser = commands.add_parser('status')
    status_parser.set_defaults(func=status)

    show_parser = commands.add_parser('show')
    show_parser.set_defaults(func=show)
    show_parser.add_argument('object', type=oid, default='HEAD', nargs='?')

    reset_parser = commands.add_parser('reset')
    reset_parser.set_defaults(func=reset)
    reset_parser.add_argument('commit', type=oid)

    diff_parser = commands.add_parser('diff')
    diff_parser.set_defaults(func=_diff)
    diff_parser.add_argument('commit', type=oid, default='HEAD', nargs='?')

    merge_parser = commands.add_parser('merge')
    merge_parser.set_defaults(func=merge)
    merge_parser.add_argument('commit', type=oid)

    merge_base_parser = commands.add_parser('merge-base')
    merge_base_parser.set_defaults(func=merge_base)
    merge_base_parser.add_argument('commit_1', type=oid)
    merge_base_parser.add_argument('commit_2', type=oid)

    show_ref_parser = commands.add_parser('show-ref')
    show_ref_parser.set_defaults(func=show_ref)

    viz_refs_parser = commands.add_parser('viz-refs')
    viz_refs_parser.set_defaults(func=viz_refs)

    tester_parser = commands.add_parser('test')
    tester_parser.add_argument('--object')
    tester_parser.set_defaults(func=tester)

    return parser.parse_args()

def tester(args):
    print(base.get_tree(args.object))

def init(args):
    data.init()

def hash_object(args):
    with open(args.file, 'rb') as f:
        print(data.hash_object('blob', f.read(), args.write))

def cat_file(args):
    data.cat_file(args)

def write_tree(args):
    print(base.write_tree())

def read_tree(args):
    base.read_tree(args.tree)

def rmobj(args):
    data.rmobj(args.object)

def commit(args):
    print(base.commit(args.message))

def log(args):
    refs = {}
    for refname, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(refname)

    for oid in base.iter_commits_and_parents({args.object}):
        commit = base.get_commit(oid)
        _print_commit(oid, commit, refs.get(oid))

def checkout(args):
    base.checkout(args.commit)

def tag(args):
    base.tag(args.tagname, args.commit)

def branch(args):
    if args.name:
        data.new_branch(args.name)
    else:
        current_branch = base.get_branch_name()
        for branch_item in base.iter_branches():
            prefix = '*' if branch_item == current_branch else ' '
            print(f'{prefix} {branch_item}')

def status(args):
    HEAD = base.get_oid('HEAD')
    current_branch = base.get_branch_name()
    if current_branch:
        print(f'On branch {current_branch}')
    else:
        print(f'HEAD detached at {HEAD[:10]}')

    MERGE_VALUE = data.get_ref('MERGE_HEAD').value
    if MERGE_VALUE:
        print(f'Merging HEAD with {MERGE_VALUE[:10]}')

    head_tree = base.get_commit(HEAD).tree
    working_tree = base.get_working_directory()

    changed = {}
    for path, action in diff.iter_changed_files(base.get_tree(head_tree), working_tree):
        changed[path] = action
    if changed and len(changed) > 0:
        print("Changes to be committed:")
        for path, action in changed.items():
            print(textwrap.indent(f'{data.COLORS["GREEN"]}{action}:   {path}{data.COLORS["RESET"]}', '      '))

def _print_commit(oid, commit, refs=None):
    refs_str = f' ({format_ref_str(refs)})' if refs else ''
    print(f'{data.COLORS["YELLOW"]}commit {oid}{data.COLORS["RESET"]}{refs_str}\n')
    print(textwrap.indent(commit.message, '    '))
    print('')

def format_ref_str(refs):
    if not refs:
        return ''
    BOLD_HEAD = f'{data.COLORS["BOLD"]}{data.COLORS["HEAD"]}'
    BOLD_REF = f'{data.COLORS["BOLD"]}{data.COLORS["GREEN"]}'
    RESET = f'{data.COLORS["RESET"]}'

    for index, ref in enumerate(refs[1:]):
        refs[index + 1] = f'{BOLD_REF}{clean_ref_str(ref)}{RESET}'
    if 'HEAD' in refs[0]:
        refs[0] = f'{BOLD_HEAD}{refs[0]}{RESET} -> '
        return refs[0] + ', '.join(refs[1:])
    refs[0] = f'{BOLD_REF}{clean_ref_str(refs[0])}{RESET}'
    return ', '.join(refs)


def clean_ref_str(ref_str):
    return ref_str.replace('refs/heads/', '').replace('refs/tags/', '')

def show(args):
    if not args.object:
        return
    commit = base.get_commit(args.object)
    parent_tree = None
    if commit.parents:
        parent_tree = base.get_commit(commit.parents[0]).tree
    result = diff.diff_trees(base.get_tree(parent_tree), base.get_tree(commit.tree))
    sys.stdout.flush()
    sys.stdout.buffer.write(result)

def reset(args):
    base.reset(args.commit)

def _diff(args):
    tree = args.commit and base.get_commit(args.commit).tree
    sys.stdout.flush()
    sys.stdout.buffer.write(diff.diff_trees(base.get_tree(tree), base.get_working_directory()))

def merge(args):
    base.merge(args.commit)

def merge_base(args):
    print(f'Commits share common parent: {base.merge_base(args.commit_1, args.commit_2)}')

def show_ref(args):
    data.show_ref()

def viz_refs(args):
    dot = 'digraph commits {\n'
    oids = set()
    for ref, refname in data.iter_refs():
         dot += f'"{refname}" [shape=note]\n'
         dot += f'"{refname}" -> "{ref}"\n'
         oids.add(ref)

    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot += f'"{oid}" [shape=box style=filled label="{oid[:10]}"]\n'
        for parent in commit.parents:
            dot += f'"{oid}" -> "{parent}"\n'
    dot += '}'

    with subprocess.Popen(
            ['dot', '-Tpng', '/dev/stdin'],
            stdin=subprocess.PIPE) as proc:
        proc.communicate(dot.encode())

if __name__ == '__main__':
    main()