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

    diff_parser = commands.add_parser('diff')
    diff_parser.set_defaults(func=_diff)
    diff_parser.add_argument('commit', type=oid, default='HEAD', nargs='?')

    merge_parser = commands.add_parser('merge')
    merge_parser.set_defaults(func=merge)
    merge_parser.add_argument('commit', type=oid)

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
    for refname, refvalue in data.iter_refs():
        refs.setdefault(refvalue.value, []).append(refname.replace("refs/heads/", "")
                                                   if "refs/heads/" in refname else f'tag: {refname.replace("refs/tags/", "")}')

    for oid in base.iter_commits_and_parents(args.object):
        commit = base.get_commit(oid)
        _print_commit(oid, commit, refs)
        oid = commit.parent

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

    head_tree = base.get_commit(HEAD).tree
    working_tree = base.get_working_directory()
    changed = diff.iter_changed_files(base.get_tree(head_tree), working_tree)
    if changed:
        print("Changes to be committed:")
        for path, action in changed:
            print(textwrap.indent(f'{data.COLORS["GREEN"]}{action}:   {path}{data.COLORS["RESET"]}', '      '))

def _print_commit(oid, commit, refs=None):
    BOLD_HEAD = f'{data.COLORS["BOLD"]}{data.COLORS["HEAD"]}'
    BOLD_REF = f'{data.COLORS["BOLD"]}{data.COLORS["GREEN"]}'
    RESET = f'{data.COLORS["RESET"]}'
    ref_string = f' ({", ".join(refs[oid])})' if refs is not None and oid in refs else ''
    ref_string = f' ({BOLD_HEAD}HEAD{RESET} -> {", ".join(refs[oid][1:])})' if 'HEAD' in ref_string else ref_string

    print(f'{data.COLORS["YELLOW"]}commit {oid}{data.COLORS["RESET"]}{ref_string}')
    print(textwrap.indent(commit.message, '     '))
    print()

def show(args):
    commit = base.get_commit(args.object)
    parent = base.get_commit(commit.parent)
    refs = {}
    for refname, refvalue in data.iter_refs():
        refs.setdefault(refvalue.value, []).append(refname.replace("refs/heads/", "")
                                                   if "refs/heads/" in refname else f'tag: {refname.replace("refs/tags/", "")}')

    for oid in base.iter_commits_and_parents(args.object):
        if oid == args.object or oid == commit.parent:
            _print_commit(oid, base.get_commit(oid), refs)

    commit_tree = base.get_tree(commit.tree)
    parent_tree = base.get_tree(parent.tree)
    sys.stdout.flush()
    sys.stdout.buffer.write(diff.diff_trees(commit_tree, parent_tree))

def _diff(args):
    tree = args.commit and base.get_commit(args.commit).tree
    sys.stdout.flush()
    sys.stdout.buffer.write(diff.diff_trees(base.get_tree(tree), base.get_working_directory()))

def merge(args):
    base.merge(args.commit)


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
    if commit.parent:
        #print('Parent', commit.parent)
        dot += f'"{oid}" -> "{commit.parent}"\n'
    dot += '}'

    with subprocess.Popen(
            ['dot', '-Tpng', '/dev/stdin'],
            stdin=subprocess.PIPE) as proc:
        proc.communicate(dot.encode())

if __name__ == '__main__':
    main()