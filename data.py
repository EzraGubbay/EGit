import os, sys, shutil
import hashlib
from collections import namedtuple

GIT_DIR = '.egit'
OBJ_DIR = os.path.join(GIT_DIR, 'objects')
REF_DIR = os.path.join(GIT_DIR, 'refs')
HEAD = os.path.join(GIT_DIR, 'HEAD')
OBJ_TYPES = {
    'blob': '100644',
    'tree': '040000'
}
COLORS = {
    'YELLOW': '\033[33m',
    'GREEN': '\033[32m',
    'HEAD': '\033[36m',
    'RESET': '\033[0m',
    'BOLD': '\033[1m'
}

RefValue = namedtuple('RefValue', ['symbolic', 'value'])

def init():
    exists = False
    if os.path.isdir(GIT_DIR):
        shutil.rmtree(GIT_DIR)
        exists = True

    # create directories
    os.makedirs(GIT_DIR)
    os.makedirs(os.path.join(OBJ_DIR))
    os.makedirs(os.path.join(REF_DIR))
    os.makedirs(os.path.join(REF_DIR, 'heads'))
    os.makedirs(os.path.join(REF_DIR, 'tags'))

    # create files
    update_ref('HEAD', RefValue(symbolic=False, value='ref: refs/heads/master'))

    # Print appropriate message to console
    sys.stdout.write(f'{"Rei" if exists else "I"}nitialized empty repository in {os.getcwd()}/{GIT_DIR}\n')

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

# Prints to stdout the contents of the provided object.
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

# Returns the list of ignored files as recorded in the .egitignore file.
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

# Changes the object ID of the provided reference to the provided value. If the reference does not exist,
# it creates one.
def update_ref(ref, oid, deref=True):
    ref = _get_ref_internal(ref, deref)[0]
    assert oid.value
    if oid.symbolic:
        value = f'ref: {oid.value}'
    else:
        value = oid.value
    ref_path = os.path.join(GIT_DIR, ref)
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, 'w') as f:
        f.write(f'{value}\n')

# Returns the object ID associated with the provided reference (if it exists, else None).
def get_ref(ref, deref=True):
    return _get_ref_internal(ref, deref)[1]

def delete_ref(ref, deref=True):
    ref = _get_ref_internal(ref, deref)[0]
    os.remove(f'{GIT_DIR}/{ref}')

def _get_ref_internal(ref, deref):
    ref_path = os.path.join(GIT_DIR, ref)
    result = None
    if os.path.isfile(ref_path):
        with open(ref_path, 'r') as f:
            result =  f.read().strip()

    symbolic = bool(result) and result.startswith('ref:')
    if symbolic:
        result = result.split(':', 1)[1].strip()
        if deref:
            return _get_ref_internal(result, deref=True)
    return ref, RefValue(symbolic=symbolic, value=result)

def new_branch(name):
    update_ref(f'refs/heads/{name}', get_ref('HEAD'))

def current_branch():
    with open(f'{GIT_DIR}/HEAD', 'r') as f:
        return f.read().split(':', 1)[1].strip()

# Iterates over all references (heads and tags) and yields each.
def iter_refs(prefix='', deref=True):
    refs = ['HEAD']
    if get_ref('MERGE_HEAD').value:
        refs.append('MERGE_HEAD')
    for root, _, filenames in os.walk(os.path.join(REF_DIR)):
        root = os.path.relpath(root, GIT_DIR)
        refs.extend(f'{root}/{filename}' for filename in filenames)

    for ref in refs:
        if not ref.startswith(prefix):
            continue
        else:
            yield ref, get_ref(ref, deref=deref)

# Prints list of all references (heads and tags) and their associated object IDs
def show_ref():
    for oid, ref in iter_refs():
        print(oid, ref)
