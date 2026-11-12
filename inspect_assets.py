"""Read-only investigation of the example's matching game package."""
from pathlib import Path
import struct
import ctypes

def decompress(data, size):
    dll = ctypes.CDLL('C:/Program Files/Epic Games/UE_5.7/Engine/Binaries/DotNET/AutomationTool/oo2core_9_win64.dll')
    fn = dll.OodleLZ_Decompress
    fn.restype = ctypes.c_ssize_t
    fn.argtypes = [ctypes.c_void_p, ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_ssize_t] + [ctypes.c_int]*3 + [ctypes.c_void_p,ctypes.c_ssize_t,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ssize_t,ctypes.c_int]
    out = ctypes.create_string_buffer(size)
    result = fn(data, len(data), out, size, 1, 0, 0, None, 0, None, None, None, 0, 3)
    if result != size:
        raise ValueError(f'Oodle returned {result}, expected {size}')
    return out.raw

ROOT = Path(__file__).resolve().parent
GAME = Path('C:/Program Files (x86)/Steam/steamapps/common/Borderlands 4/OakGame/Content/Paks')

def u32(data, pos):
    return struct.unpack_from('<I', data, pos)[0]

def main():
    target = (ROOT / 'examples/000_BetterDifficultyHarder2_P.utoc').read_bytes()[144:156]
    for path in GAME.glob('pakchunk*.utoc'):
        data = path.read_bytes()
        count = u32(data, 24)
        ids = data[144:144 + count * 12]
        index = ids.find(target)
        if index < 0 or index % 12:
            continue
        index //= 12
        pair = data[144 + count * 12 + index * 10:][:10]
        offset, length = int.from_bytes(pair[:5], 'big'), int.from_bytes(pair[5:], 'big')
        block_start = 144 + count * 22 + 4 * (u32(data, 84) + u32(data, 96))
        bs = u32(data, 44)
        blocks = []
        for b in range(offset // bs, (offset + length - 1) // bs + 1):
            entry = data[block_start + b * 12:][:12]
            blocks.append((int.from_bytes(entry[:5], 'little'), int.from_bytes(entry[5:8], 'little'), int.from_bytes(entry[8:11], 'little'), entry[11]))
        print(path.name, 'offset', offset, 'length', length, 'blocks', blocks)
        if all(b[3] in (0, 1) for b in blocks):
            with path.with_suffix('.ucas').open('rb') as stream:
                pieces = []
                for pos, size, raw_size, method in blocks:
                    stream.seek(pos)
                    raw = stream.read(size)
                    pieces.append(decompress(raw, raw_size) if method else raw)
            asset = b''.join(pieces)[offset % bs:][:length]
            out = ROOT / 'research' / (path.stem + '.asset')
            out.parent.mkdir(exist_ok=True)
            out.write_bytes(asset)
            print('Extracted', out)

if __name__ == '__main__':
    main()
