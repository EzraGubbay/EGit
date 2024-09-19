import os, shutil, sys
import crypt, hashlib

def handle_input(args, content)

def sha1(content):
    return hashlib.sha1(content).hexdigest()

def execute(args):
    working = os.getcwd()
    result = ""

    if args.stdin:
        handle_standard_input(args, sys.stdin)
    else:
        file = args.filename
        if file not in os.listdir(working):
            print("Incorrect file or file does not exist.")
        else:
            with open(working + '/' + file, 'rb') as f:
                result = sha1(f.read())

    if args.w:
        destination_folder = working + f'/.egit/objects/{result[:2]}'
        os.mkdir(destination_folder)
        with open(f'{destination_folder}/{result}', 'wb') as f:
            f.write(result)



