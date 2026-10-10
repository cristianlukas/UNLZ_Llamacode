import os
import shutil
import tempfile

from path_guard import safe_join

root = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(root, "a", "b"))
    with open(os.path.join(root, "a", "b", "file.txt"), "w") as fh:
        fh.write("ok")

    # subdirectorios normales y el propio root
    assert safe_join(root, "a") == os.path.realpath(os.path.join(root, "a"))
    assert safe_join(root, "a/b/file.txt") == os.path.realpath(
        os.path.join(root, "a", "b", "file.txt"))
    assert safe_join(root, "./a") == os.path.realpath(os.path.join(root, "a"))
    assert safe_join(root, ".") == os.path.realpath(root)
    assert safe_join(root, "a/./b/file.txt") == os.path.realpath(
        os.path.join(root, "a", "b", "file.txt"))

    # traversal con ..
    for bad in ("../secret", "a/../../etc/passwd", "..", "a/..", "a/../.."):
        try:
            safe_join(root, bad)
            raise AssertionError("no rechazo {}".format(bad))
        except ValueError:
            pass

    # ruta absoluta
    for bad in ("/etc/passwd", os.path.join(root, "a")):
        try:
            safe_join(root, bad)
            raise AssertionError("no rechazo absoluta {!r}".format(bad))
        except ValueError:
            pass

    # NUL
    for bad in ("a\x00b", "a\x00"):
        try:
            safe_join(root, bad)
            raise AssertionError("no rechazo NUL")
        except ValueError:
            pass

    # symlink existente que sale del root: no se sigue
    outside = os.path.join(root, "..", "outside_target.txt")
    outside_real = os.path.realpath(outside)
    with open(outside_real, "w") as fh:
        fh.write("outside")
    os.symlink(outside_real, os.path.join(root, "escape_link"))
    try:
        safe_join(root, "escape_link")
        raise AssertionError("no rechazo symlink fuera del root")
    except ValueError:
        pass

    # symlink dentro del root: permitido (realpath sigue dentro)
    os.symlink(os.path.join(root, "a", "b"), os.path.join(root, "link_b"))
    assert safe_join(root, "link_b/file.txt") == os.path.realpath(
        os.path.join(root, "a", "b", "file.txt"))

    # symlink que apunta a un directorio interno via .. dentro del root
    os.symlink(os.path.join(root, "a"), os.path.join(root, "link_a"))
    assert safe_join(root, "link_a/b/file.txt") == os.path.realpath(
        os.path.join(root, "a", "b", "file.txt"))

    # vacio / tipos invalidos
    for bad in ("", None, 123):
        try:
            safe_join(root, bad)
            raise AssertionError("no rechazo {!r}".format(bad))
        except ValueError:
            pass

    # commonpath, no prefijo textual: root con nombre que es prefijo de otro
    sibling = os.path.join(root, "..", os.path.basename(root) + "_evil")
    os.makedirs(sibling, exist_ok=True)
    try:
        safe_join(root, os.path.join("..", os.path.basename(root) + "_evil", "x"))
        raise AssertionError("no rechazo prefijo textual")
    except ValueError:
        pass

    print("OK")
finally:
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(os.path.join(root, "..", "outside_target.txt"), ignore_errors=True)
