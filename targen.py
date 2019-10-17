from pathlib import Path
from math import ceil
from sys import argv, stdout


class TarError(Exception):
    pass


def _normalize_and_prefix(f, base):
    f = Path(f)
    base = Path(base)

    if base == f.parent:
        prefix = ''
    else:
        prefix = f.relative_to(base).parent

    return f, base, prefix


def _pad(data, s, val=b'\0'):
    padsize = s - len(data)
    return data + val*padsize


def _as_multiple(a, m):
    return ceil(a / m) * m


def tar_header(f, prefix):
    f = Path(f)
    if f.is_dir():
        mode = b'000755 \0'
        ftype = b'5'
    elif f.is_file() and not f.is_symlink():
        mode = b'000644 \0'
        ftype = b'0'
    else:
        raise TarError(
            f'{f} is not a regular file or a directory'
        )

    name = f.name.encode('utf-8')
    prefix = str(prefix).encode('utf-8')
    if len(name) > 99:
        raise TarError(f'Length of file name of {f.name} exceeds 99')
    if len(prefix) > 154:
        raise TarError(f'Length of prefix name ({prefix}) exceeds 154')

    h = bytearray(_pad(name, 100))  # file name: 100 bytes
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
    h += _pad(prefix, 155)  # prefix name, 155 bytes

    h += b'\0' * 12  # pad to 512

    assert(len(h) == 512)

    h[148:148+8] = f'{sum(h):06o} \0'.encode('ascii')  # set the correct chksum
    return bytes(h)


def check(f, base):
    f, base, prefix = _normalize_and_prefix(f, base)
    try:
        tar_header(f, prefix)
        if f.is_dir():
            for e in f.iterdir():
                check(e, base)
    except TarError as e:
        print(e)
        return False
    return True


def calc_size(f):
    f = Path(f)
    if f.is_file():
        return _as_multiple(f.stat().st_size, 512) + 512
    elif f.is_dir():
        return sum(calc_size(e) for e in f.iterdir()) + 512


def targen(f, base, bc=1):
    f, base, prefix = _normalize_and_prefix(f, base)
    yield tar_header(f, prefix)

    if f.is_dir():
        for e in f.iterdir():
            yield from targen(e, base)
    else:
        with open(f, 'rb') as r:
            while True:
                data = r.read(512*bc)
                if len(data) < 512*bc:
                    yield _pad(
                        data, _as_multiple(len(data), 512)
                    ) if len(data) else b''
                    break
                yield data


if __name__ == '__main__':
    for b in targen(argv[1], argv[2]):
        stdout.buffer.write(b)
