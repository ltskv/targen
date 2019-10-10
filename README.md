# Targen: a blockwise Python tar generator

## Usage

```python
from targen import targen
g = targen('directory_with/stuff', base='directory_with')

for block in g:  # len(block) is 512
    do_stuff(block)
```

Which is roughly equivalent to 

```
tar -cf stuff.tar -C directory_with stuff
```

## Why?

For me it was the easiest way to send folders from server without creating
intermediate archive files.
