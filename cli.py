import argparse
import subprocess
from dotenv import load_dotenv
import data
import base
import textwrap

from base import iter_commits_and_parents, get_oid
from data import get_ref


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
    branch_parser.add_argument('name')

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
    for oid in iter_commits_and_parents(args.object):
        commit = base.get_commit(oid)
        print(f'{data.COLORS["YELLOW"]}commit {oid}{data.COLORS["RESET"]}')
        print(textwrap.indent(commit.message, '     '))
        print()
        oid = commit.parent

def checkout(args):
    base.checkout(args.commit)

def tag(args):
    base.tag(args.tagname, args.commit)

def branch(args):
    data.new_branch(args.name)

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