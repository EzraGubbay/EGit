import argparse
import os
import data
import base


def main():

    args = parse_args()
    args.func(args)

def parse_args():

    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(dest='command')
    commands.required = True

    init_parser = commands.add_parser('init')
    init_parser.set_defaults(func=init)

    hash_object_parser = commands.add_parser('hash-object')
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument('file')
    hash_object_parser.add_argument('--write', '-w', action='store_true')

    cat_file_parser = commands.add_parser('cat-file')
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument('object')
    cat_file_parser.add_argument('-p', help="pretty print the object contents", action='store_true')
    cat_file_parser.add_argument('-t', help="Print the object file type only", action='store_true')

    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func=write_tree)

    return parser.parse_args()

def init(args):
    data.init()
    print(f"Initialized empty repository in {os.getcwd()}/{data.GIT_DIR}")

def hash_object(args):
    with open(args.file, 'rb') as f:
        print(data.hash_object(f.read(), args.write))

def cat_file(args):
    data.cat_file(args)

def write_tree(args):
    base.write_tree()

if __name__ == '__main__':
    main()