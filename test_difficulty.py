import math
from pathlib import Path
import struct
import tempfile
import unittest
from blake3_small import digest
import difficulty as mod

def read_defaults(cas):
    """Independently decode the unversioned structure default data."""
    fragment, mask = struct.unpack_from('<HI', cas, 0xad3)
    assert fragment == 0x2b80
    pos = 0xad9
    result = []
    for i in range(8):
        if mask & (1 << i):
            result.append(0.0)
        else:
            result.append(struct.unpack_from('<d', cas, pos)[0])
            pos += 8
    assert cas[pos:pos+36] == b'\x80\x09\x0f' * 12
    result.append(struct.unpack_from('<d', cas, pos+36)[0])
    return result

class DifficultyTests(unittest.TestCase):
    def test_hash_vectors(self):
        self.assertEqual(digest(b'').hex(), 'af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262')
        self.assertEqual(digest(b'abc').hex(), '6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85')

    def test_reproduce_example_byte_for_byte(self):
        generated = mod.generate(dict(enemy_health=1, enemy_damage=1.99, player_damage=0.5))
        self.assertEqual(generated, mod.template())

    def test_neutral_and_modified_values_and_boundaries(self):
        cases = [dict.fromkeys(mod.DEFAULTS, 1), dict(enemy_health=5, enemy_damage=3, player_damage=0.25,
                   player_durability=2, experience=2, cash=0.5, eridium=4),
                 dict.fromkeys(mod.DEFAULTS, 0.01), dict.fromkeys(mod.DEFAULTS, 100)]
        for settings in cases:
            with self.subTest(settings=settings):
                files = mod.generate(settings)
                toc, cas = files['.utoc'], files['.ucas']
                mod.verify_container(toc, cas)
                actual = read_defaults(cas)
                s = mod.validate(settings)
                expected = [mod.modifier(s['enemy_damage']/s['player_durability']), mod.modifier(s['player_damage']),
                            0, 0, 0, mod.modifier(s['cash']), mod.modifier(s['eridium']), mod.modifier(s['experience']), s['enemy_health']]
                self.assertEqual(actual, expected)
                asset_length = int.from_bytes(toc[173:178], 'big')
                self.assertEqual(asset_length, len(cas) - 80)
                self.assertEqual(struct.unpack_from('<Q', cas, 0x632)[0] + 0x69a + 4, asset_length)
                self.assertEqual(cas[asset_length:], mod.template()['.ucas'][0xb19:])

    def test_invalid_input(self):
        for value in [True, None, '2', 0, -1, 101, math.inf, math.nan]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                mod.generate(dict(enemy_health=value))
        with self.assertRaises(ValueError):
            mod.generate(dict(player_health=2))
        with self.assertRaises(ValueError):
            mod.generate([])

    def test_corrupted_container_rejected(self):
        files = mod.template()
        corrupted = bytearray(files['.ucas'])
        corrupted[100] ^= 1
        with self.assertRaises(ValueError):
            mod.verify_container(files['.utoc'], corrupted)

    def test_build_complete_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = mod.build(mod.DEFAULTS, temp)
            self.assertEqual(len(list(output.glob('*.pak'))), 1)
            self.assertEqual(len(list(output.glob('*.utoc'))), 1)
            self.assertEqual(len(list(output.glob('*.ucas'))), 1)
            self.assertTrue((output/'build-info.json').is_file())

if __name__ == '__main__':
    unittest.main()
