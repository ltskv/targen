from pathlib import Path


def tar_header(f, prefix):
    f = Path(f)
    if f.is_dir():
        mode = b'000755 \0'
        ftype = b'5'
    elif f.is_file() and not f.is_symlink():
        mode = b'000644 \0'
        ftype = b'0'
    else:
        raise ValueError(
            f'{f} is not a regular file or a directory'
        )

    name = f.name.encode('utf-8')
    prefix = str(prefix).encode('utf-8')
    if len(name) > 99:
        raise ValueError(f'Length of file name of {f.name} exceeds 99')
    if len(prefix) > 154:
        raise ValueError(f'Length of prefix name ({prefix}) exceeds 154')

    h = bytearray(name + b'\0'*(100-len(name)))  # file name: 100 bytes
    h += mode # file mode: 8 bytes
    h += b'000777 \0'  # file owner id: 8 bytes
    h += b'000777 \0'  # file group id: 8 bytes

    # size (octal): 12 B
    if f.is_dir():
        h += b'0' * 11 + b' '
    else:
        h += f'{int(f.stat().st_size):011o} '.encode('ascii')

    h += f'{int(f.stat().st_mtime):011o} '.encode('ascii')  # time (octal): 12 B
    h += b' ' * 8  # checksum, init to ' ', 8 bytes
    h += ftype  # type, 1 byte
    h += b'\0' * 100  # name of the linked file, not possible here, 100 bytes
    h += b'ustar\0' # ustar, 6 bytes
    h += b'00' # ustar version, 2 bytes
    h += b'\0' * 32  # symbolic owner name, drop it, 32 bytes
    h += b'\0' * 32  # symbolic group name, drop it, 32 bytes
    h += b'\0' * 8  # major device number, drop it, 8 bytes
    h += b'\0' * 8  # minor device number, drop it, 8 bytes
    h += prefix + b'\0'*(155-len(prefix))  # prefix name, 155 bytes

    h += b'\0' * 12  # pad to 512

    assert(len(h) == 512)

    h[148:148+8] = f'{sum(h):06o} \0'.encode('ascii')  # set the correct chksum
    return bytes(h)


def targen(f, base):
    f = Path(f)
    base = Path(base)

    if base == f.parent:
        prefix = ''
    else:
        prefix = f.relative_to(base).parent

    yield tar_header(f, prefix)

    if f.is_dir():
        for e in f.iterdir():
            yield from targen(e, base)
    else:
        with open(f, 'rb') as r:
            while True:
                data = r.read(512)
                if len(data) < 512:
                    padsize = 0 if not len(data) else (512 - (len(data) % 512))
                    yield data + b'\0' * padsize
                    break
                yield data
