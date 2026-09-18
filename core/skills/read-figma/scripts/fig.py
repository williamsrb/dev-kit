#!/usr/bin/env python3
"""Decode Figma .fig files and search the scene graph.

A .fig is a ZIP. The interesting member is canvas.fig, which is a two-section
kiwi container: a deflate-compressed schema, then a zstd-compressed scene graph.
See SKILL.md for the format details and the varint GUID gotcha.

Subcommands:
  unpack <file.fig> <outdir>     Unzip + decode the scene graph to <outdir>/scene.bin
  node <scene.bin> <S:L>         Locate node GUID S:L (varint-encoded) with context
  grep <scene.bin> <string>      Find literal text with readable context
  text <scene.bin>               Dump text-node contents
  names <scene.bin>              Dump component/symbol key references (ASCII S:L tokens)
"""

import contextlib
import io
import json
import re
import struct
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def varint(n: int) -> bytes:
    """Kiwi unsigned varint. Node GUIDs are encoded this way, not as ASCII."""
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | 0x80 if n else b)
        if not n:
            return bytes(out)


def guid_bytes(session: int, local: int) -> bytes:
    return varint(session) + varint(local)


def _unzstd(blob: bytes) -> bytes:
    """zstd via the `zstandard` module, falling back to the zstd CLI.

    The module is often absent while /usr/bin/zstd is present, so try both
    before giving up.
    """
    try:
        import zstandard

        return zstandard.ZstdDecompressor().decompressobj().decompress(blob)
    except ImportError:
        pass
    try:
        return subprocess.run(
            ["zstd", "-d", "-c"], input=blob, capture_output=True, check=True
        ).stdout
    except FileNotFoundError:
        sys.exit("need either the `zstandard` python module or the `zstd` CLI")
    except subprocess.CalledProcessError as e:
        sys.exit(f"zstd failed: {e.stderr[:200]!r}")


def decode_canvas(data: bytes):
    """Split canvas.fig into its sections and decompress each.

    Layout: b'fig-kiwi' | version:uint32 | (len:uint32 | payload)*
    Payloads are deflate (raw, wbits=-15) or zstd depending on section/version,
    so sniff rather than assume.
    """
    if data[:8] != b"fig-kiwi":
        sys.exit(f"not a kiwi canvas (magic={data[:8]!r})")
    version = struct.unpack("<I", data[8:12])[0]
    off, sections = 12, []
    while off < len(data) - 4:
        (n,) = struct.unpack("<I", data[off : off + 4])
        off += 4
        if n == 0 or off + n > len(data):
            break
        blob, off = data[off : off + n], off + n
        if blob[:4] == ZSTD_MAGIC:
            out = _unzstd(blob)
        else:
            try:
                out = zlib.decompress(blob, -15)
            except zlib.error:
                out = blob  # leave undecodable sections raw rather than dying
        sections.append(out)
    return version, sections


def readable(seg: bytes) -> str:
    """Collapse binary runs to ' | ' so text survives but noise doesn't.

    Decode first, then collapse: a bytes-level class can't tell a UTF-8
    continuation byte (Norwegian ø/å) from binary noise, and keeping the high
    bytes buries real names like 'varsling' under megabytes of garbage.
    """
    s = seg.decode("utf8", "replace")
    junk = r"[\x00-\x08\x0b-\x1f\x7f-\x9f�]"
    s = re.sub(rf"(?:{junk}){{2,}}", " | ", s)
    # Drop surviving lone control bytes too: leaving even one NUL in the output
    # makes grep/less treat the whole stream as binary and silently show nothing.
    return re.sub(junk, "", s)


def cmd_unpack(args):
    fig, outdir = Path(args[0]), Path(args[1])
    outdir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(fig) as z:
        names = z.namelist()
        z.extractall(outdir)
    canvas = outdir / "canvas.fig"
    if not canvas.exists():
        sys.exit(f"no canvas.fig inside {fig} (members: {names[:5]})")
    version, sections = decode_canvas(canvas.read_bytes())
    scene = max(sections, key=len)
    (outdir / "scene.bin").write_bytes(scene)
    if len(sections) > 1:
        (outdir / "schema.bin").write_bytes(min(sections, key=len))
    imgs = len([n for n in names if n.startswith("images/") and not n.endswith("/")])
    print(f"kiwi version : {version}")
    print(f"sections     : {[len(s) for s in sections]}")
    print(f"images       : {imgs}")
    print(f"scene graph  : {outdir/'scene.bin'} ({len(scene):,} bytes)")
    meta = outdir / "meta.json"
    if meta.exists():
        print(f"meta.json    : {meta.read_text()[:400]}")


def cmd_node(args):
    scene = Path(args[0]).read_bytes()
    session, local = (int(x) for x in re.split(r"[:\-]", args[1]))
    window = int(args[2]) if len(args) > 2 else 900
    key = guid_bytes(session, local)
    hits = [m.start() for m in re.finditer(re.escape(key), scene)]
    # A 5-ish byte needle in a 30MB haystack should occur ~0 times by chance;
    # a handful of hits is real. Report the math so the reader can judge.
    expected = len(scene) / (2 ** (8 * len(key)))
    print(f"GUID {session}:{local} -> varint {key.hex()} ({len(key)} bytes)")
    print(f"hits: {len(hits)}  (expected by chance in {len(scene):,} bytes: {expected:.6f})")
    if not hits:
        print("\nNo hits. Before concluding the node is absent, confirm you decoded")
        print("the right section -- and remember ASCII 'S:L' search is meaningless here.")
        return
    for i in hits:
        print(f"\n=== hit at {i} ===")
        print(readable(scene[max(0, i - window) : i + window]))


def cmd_verify_node(args):
    """Return a compact machine-readable node-presence result."""
    scene_path = Path(args[0]).resolve()
    scene = scene_path.read_bytes()
    session, local = (int(x) for x in re.split(r"[:\-]", args[1]))
    key = guid_bytes(session, local)
    hits = [match.start() for match in re.finditer(re.escape(key), scene)]
    expected = len(scene) / (2 ** (8 * len(key)))
    print(json.dumps({
        "scene": str(scene_path),
        "node": f"{session}:{local}",
        "varint_hex": key.hex(),
        "needle_bytes": len(key),
        "hits": len(hits),
        "offsets": hits[:20],
        "expected_random_hits": expected,
        "present": bool(hits),
    }, indent=2, sort_keys=True))


def cmd_grep(args):
    scene = Path(args[0]).read_bytes()
    needle = args[1].encode("utf8")
    limit = int(args[2]) if len(args) > 2 else 5
    hits = [m.start() for m in re.finditer(re.escape(needle), scene)]
    print(f"{args[1]!r}: {len(hits)} hits")
    for i in hits[:limit]:
        print(f"\n=== hit at {i} ===")
        print(readable(scene[max(0, i - 300) : i + 300]))


# Text runs are NUL-delimited and introduced by b'\x00*' plus one length/tag
# byte, e.g. b'HankenGrotesk-Medium\x00*\x01Hva gjør du...'. The delimiters are
# NULs, not spaces -- worth stating because a space-based regex silently
# matches nothing and looks like "the file has no text".
TEXT_RUN = re.compile(rb"\x00\*.([\x20-\x7e\xc2-\xf4][^\x00]{2,299})")


def cmd_text(args):
    scene = Path(args[0]).read_bytes()
    needle = args[1].lower() if len(args) > 1 else None
    seen = []
    for m in TEXT_RUN.finditer(scene):
        s = m.group(1).decode("utf8", "replace").strip()
        if len(s) > 3 and s not in seen:
            seen.append(s)
    if needle:
        seen = [s for s in seen if needle in s.lower()]
        print(f"{len(seen)} text runs matching {args[1]!r}\n")
    else:
        print(f"{len(seen)} distinct text runs\n")
    for s in seen:
        print(" -", s)


def cmd_names(args):
    scene = Path(args[0]).read_bytes()
    ids = sorted(set(re.findall(rb"\b\d{2,5}:\d{1,6}\b", scene)))
    print(f"{len(ids)} ASCII 'S:L' tokens -- these are component/symbol KEY references,")
    print("NOT the node GUID index. Do not conclude a node is absent from these.\n")
    print(", ".join(x.decode() for x in ids[:80]))


COMMANDS = {
    "unpack": (cmd_unpack, 2),
    "node": (cmd_node, 2),
    "grep": (cmd_grep, 2),
    "text": (cmd_text, 1),
    "names": (cmd_names, 1),
    "verify-node": (cmd_verify_node, 2),
}


def main():
    argv = sys.argv[1:]
    json_mode = "--json" in argv
    argv = [arg for arg in argv if arg != "--json"]
    if len(argv) < 1 or argv[0] not in COMMANDS:
        sys.exit(__doc__)
    command = argv[0]
    fn, argc = COMMANDS[command]
    rest = argv[1:]
    if len(rest) < argc:
        sys.exit(f"{command}: expected at least {argc} argument(s)\n\n{__doc__}")
    if not json_mode or command == "verify-node":
        fn(rest)
        return
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        fn(rest)
    print(json.dumps({"command": command, "output": capture.getvalue().rstrip()},
                     indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
