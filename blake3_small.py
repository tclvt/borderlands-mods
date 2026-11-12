"""Small unkeyed BLAKE3-256 implementation for IoStore integrity metadata.

Algorithm: https://github.com/BLAKE3-team/BLAKE3-specs/blob/master/blake3.pdf
No third-party dependencies; tested against the supplied container's chunk hashes.
"""
import struct

IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
      0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)
PERM = (2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8)
MASK = 0xffffffff

def compress(cv, words, counter, length, flags):
    v = list(cv) + list(IV[:4]) + [counter & MASK, counter >> 32, length, flags]
    def rotate(x, n):
        return ((x >> n) | (x << (32 - n))) & MASK
    def g(a, b, c, d, x, y):
        v[a] = (v[a] + v[b] + x) & MASK
        v[d] = rotate(v[d] ^ v[a], 16)
        v[c] = (v[c] + v[d]) & MASK
        v[b] = rotate(v[b] ^ v[c], 12)
        v[a] = (v[a] + v[b] + y) & MASK
        v[d] = rotate(v[d] ^ v[a], 8)
        v[c] = (v[c] + v[d]) & MASK
        v[b] = rotate(v[b] ^ v[c], 7)
    m = list(words)
    for _ in range(7):
        for a, b, c, d, i in ((0,4,8,12,0), (1,5,9,13,2), (2,6,10,14,4),
                              (3,7,11,15,6), (0,5,10,15,8), (1,6,11,12,10),
                              (2,7,8,13,12), (3,4,9,14,14)):
            g(a, b, c, d, m[i], m[i+1])
        m = [m[i] for i in PERM]
    return tuple(v[i] ^ v[i+8] for i in range(8)) + tuple(v[i+8] ^ cv[i] for i in range(8))

def digest(data):
    def chaining(output):
        return compress(*output)[:8]
    def parent(left, right):
        return IV, tuple(left) + tuple(right), 0, 64, 4
    def subtree(start, end):
        if end - start > 1:
            split = 1 << ((end - start - 1).bit_length() - 1)
            return parent(chaining(subtree(start, start+split)), chaining(subtree(start+split, end)))
        chunk = data[start*1024:(start+1)*1024]
        cv = IV
        count = max(1, (len(chunk) + 63) // 64)
        for i in range(count):
            block = chunk[i*64:(i+1)*64]
            flags = (1 if i == 0 else 0) | (2 if i == count - 1 else 0)
            output = cv, struct.unpack('<16I', block.ljust(64, b'\0')), start, len(block), flags
            cv = chaining(output)
        return output
    cv, words, _, length, flags = subtree(0, max(1, (len(data)+1023)//1024))
    return struct.pack('<16I', *compress(cv, words, 0, length, flags | 8))[:32]
