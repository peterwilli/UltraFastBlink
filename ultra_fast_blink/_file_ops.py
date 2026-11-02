import errno
import os
import shutil

def move_without_overwrite(source, destination):
    """Reserve the destination atomically, including moves across filesystems."""
    created = False
    try:
        try:
            os.link(source, destination)
            created = True
        except OSError as exc:
            if exc.errno not in (errno.EXDEV, errno.EPERM, errno.EOPNOTSUPP):
                raise
            with open(source, 'rb') as src, open(destination, 'xb') as dst:
                created = True
                shutil.copyfileobj(src, dst, length=1024*1024)
            shutil.copystat(source, destination)
        os.unlink(source)
    except Exception:
        if created:
            os.unlink(destination)
        raise
