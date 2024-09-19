from commands import *

def execute(args):
    if args.init:
        init.execute()
    elif args.hash_object:
        hash_object.execute()
    