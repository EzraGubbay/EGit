import os, sys
import hashlib

GIT_DIR = '.egit'
OBJ_DIR = os.path.join(GIT_DIR, 'objects')
OBJ_TYPES = {
    'blob': '100644',
    'tree': '040000'
}

def init():
    os.makedirs(GIT_DIR)
    os.makedirs(os.path.join(GIT_DIR, 'objects'))

def hash_object(data, write=False):

    header = create_object_header(data)
    object_id = hashlib.sha1(header + data).hexdigest()
    if write:
        os.makedirs(os.path.join(OBJ_DIR, object_id[:2]))
        with open(os.path.join(OBJ_DIR, object_id[:2], object_id[2:]), "wb") as out:
            out.write(header + data)
    return object_id

def get_object(oid):
    with open(os.path.join(OBJ_DIR, oid[:2], oid[2:]), 'rb') as infile:
        return infile.read()

def create_object_header(data):
    """
    In the future will determine the appropriate header for a given object that is to be hashed.
    :return: Encoded header string for an object staged to be hashed.
    """

    # Return header for blob files
    return f'blob {len(data)}\0'.encode()

def get_object_parts(data):
    header_bytes, _, content = data.partition(b'\x00')
    #header = [extract_object_type(header_bytes), extract_object_size(header_bytes)]
    type_, _, size = header_bytes.partition(b'\x20')
    header = [type_, size]
    content = data[len(header_bytes):]
    return header, content

def extract_object_header(data):
    return data.split(b'\x00')[0]

def extract_object_type(header):
    return header.decode().split(' ')[0].encode()

def extract_object_size(header):
    return header.decode().split(' ')[1].encode()

def cat_file(args):
    data = get_object(args.object)
    header, content = get_object_parts(data)

    if args.p:
        sys.stdout.flush()
        sys.stdout.buffer.write(content)

    elif args.t:
        sys.stdout.buffer.write(header[0] + '\n'.encode())


