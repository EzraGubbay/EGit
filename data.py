import os, sys, shutil
import hashlib

GIT_DIR = '.egit'
OBJ_DIR = os.path.join(GIT_DIR, 'objects')
REF_DIR = os.path.join(GIT_DIR, 'refs')
OBJ_TYPES = {
    'blob': '100644',
    'tree': '040000'
}
COLORS = {
    'YELLOW': '\033[33m',
    'RESET': '\033[0m'
}

def init():
    if os.path.isdir(GIT_DIR):
        shutil.rmtree(GIT_DIR)
    # create directories
    os.makedirs(GIT_DIR)
    os.makedirs(os.path.join(OBJ_DIR))
    os.makedirs(os.path.join(REF_DIR))
    os.makedirs(os.path.join(REF_DIR, 'heads'))
    os.makedirs(os.path.join(REF_DIR, 'tags'))

    # create files
    with open(os.path.join(GIT_DIR, 'HEAD'), 'w') as f:
        pass

def hash_object(filetype, data, write=False):

    header = create_object_header(filetype, data)
    object_id = hashlib.sha1(header + data).hexdigest()
    if write:
        os.makedirs(os.path.join(OBJ_DIR, object_id[:2]), exist_ok=True)
        with open(os.path.join(OBJ_DIR, object_id[:2], object_id[2:]), "wb") as out:
            out.write(header + data)
    return object_id

### ALL OBJECT ACCESSORS RETURN BYTE ARRAYS ###

def get_object(oid):
    with open(os.path.join(OBJ_DIR, oid[:2], oid[2:]), 'rb') as infile:
        return infile.read()

def create_object_header(filetype, data):
    """
    In the future will determine the appropriate header for a given object that is to be hashed.
    :return: Encoded header string for an object staged to be hashed.
    """

    # Return header for blob files
    return f'{filetype} {len(data)}\0'.encode()

def _get_object_parts(data):
    header_bytes, _, content = data.partition(b'\x00')
    type_, _, size = header_bytes.partition(b'\x20')
    header = [type_, size]
    content = data[len(header_bytes):]
    return header, content

def _extract_object_header(data):
    return data.split(b'\x00')[0]

def _extract_object_type(header):
    return header.decode().split(' ')[0].encode()

def _extract_object_size(header):
    return header.decode().split(' ')[1].encode()

def get_object_header(oid):
    header, _ = _get_object_parts(get_object(oid))
    return header

def get_object_content(oid):
    _, content = _get_object_parts(get_object(oid))

    return content



def cat_file(args):
    try:
        data = get_object(args.object)
    except FileNotFoundError:
        sys.stdout.buffer.write(f'No object exists with ID: {args.object}\n'.encode())
        return
    header, content = _get_object_parts(data)

    if args.p:
        sys.stdout.flush()
        sys.stdout.buffer.write(content)

    elif args.t:
        sys.stdout.buffer.write(header[0] + '\n'.encode())

def get_ignore_list():
    try:
        with open('.egitignore', 'rb') as f:
            ignored_data = f.read()
    except FileNotFoundError:
        return []

    return ignored_data.decode().splitlines()

def rmobj(oid):
    shutil.rmtree(os.path.join(OBJ_DIR, oid[:2]))
    sys.stdout.flush()
    sys.stdout.buffer.write(f"Removed object: {oid}\n".encode())

def update_ref(ref, oid):
    ref_path = os.path.join(GIT_DIR, ref)
    with open(ref_path, 'w') as f:
        f.write(f'{oid}\n')

def get_ref(ref):
    ref_path = os.path.join(GIT_DIR, ref)
    if os.path.exists(ref_path):
        with open(ref_path, 'r') as f:
            return f.read().strip()
    else:
        return None

def iter_refs():
    for ref in os.listdir(os.path.join(REF_DIR, 'heads')):
        with open(os.path.join(REF_DIR, 'heads', ref), 'r') as f:
            yield f.read().strip(), f'refs/heads/{ref}'

    for ref in os.listdir(os.path.join(REF_DIR, 'tags')):
        with open(os.path.join(REF_DIR, 'tags', ref), 'r') as f:
            yield f.read().strip(), f'refs/tags/{ref}'

def show_ref():
    for oid, ref in iter_refs():
        print(oid, ref)
