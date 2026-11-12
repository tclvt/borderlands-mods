"""Build a configurable BL4 difficulty mod from the locally supplied example."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
from blake3_small import digest

ROOT = Path(__file__).resolve().parent
STEM = '000_BetterDifficultyHarder2_P'
HASHES = {
    '.pak': '75e7144577253917f6da7312ef5e585b12fb728226a22b0938323751a6b555cd',
    '.ucas': '1664f3a66574ac0cc870723232590b9f61347d4d994c09f870c5e407076732ca',
    '.utoc': '4389de8064c784b74446c3fbf5a8759f7a4a5f97e4c02d96516da3fb82746931',
}
DEFAULTS = dict(enemy_health=2.0, enemy_damage=1.5, player_damage=1.0,
                player_durability=1.0, experience=1.0, cash=1.0, eridium=1.0)

def validate(settings):
    if not isinstance(settings, dict):
        raise ValueError('Settings must be a JSON object.')
    unknown = settings.keys() - DEFAULTS.keys()
    if unknown:
        raise ValueError('Unknown setting(s): ' + ', '.join(sorted(unknown)))
    result = DEFAULTS | settings
    for key, value in result.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0.01 <= value <= 100:
            raise ValueError(f'{key} must be a number between 0.01 and 100 (1 = normal).')
    return result

def modifier(multiplier):
    # Gearbox signed scale: negatives divide by (1 - value), positives add to 1.
    return multiplier - 1 if multiplier >= 1 else 1 - 1 / multiplier

def template():
    files = {ext: (ROOT / 'examples' / (STEM + ext)).read_bytes() for ext in HASHES}
    for ext, data in files.items():
        if hashlib.sha256(data).hexdigest() != HASHES[ext]:
            raise ValueError(f'The example {ext} differs from the inspected version; refusing to patch unknown offsets.')
    return files

def verify_container(toc, cas):
    # Supported template: two uncompressed, unsigned chunks, one block each.
    if toc[:16] != b'-==--==--==--==-' or toc[16] != 5 or len(toc) != 376:
        raise ValueError('Unexpected container format.')
    for index in range(2):
        entry = toc[0xbc + index * 12:][:12]
        offset = int.from_bytes(entry[:5], 'little')
        size = int.from_bytes(entry[5:8], 'little')
        raw_size = int.from_bytes(entry[8:11], 'little')
        if entry[11] or size != raw_size or offset + size > len(cas):
            raise ValueError('Invalid compression block.')
        pair = toc[168 + index * 10:][:10]
        logical_offset = int.from_bytes(pair[:5], 'big')
        logical_length = int.from_bytes(pair[5:], 'big')
        if logical_offset != index * 65536 or logical_length != raw_size:
            raise ValueError('Chunk offsets and compression block lengths disagree.')
        expected = digest(cas[offset:offset+size])[:20] + bytes(12)
        if toc[310 + index * 33:][:32] != expected:
            raise ValueError(f'Chunk {index} integrity hash mismatch.')

def generate(settings):
    settings = validate(settings)
    files = template()
    verify_container(files['.utoc'], files['.ucas'])
    # Schema order, read from the UUserDefinedStruct property definitions:
    # DamageTaken, DamageDealt, LootLuck, AI time, AI accuracy, Cash, Eridium, XP,
    # twelve elemental substructures, EnemyHealth (direct multiplier).
    scalars = [modifier(settings['enemy_damage'] / settings['player_durability']),
               modifier(settings['player_damage']), 0, 0, 0,
               modifier(settings['cash']), modifier(settings['eridium']), modifier(settings['experience'])]
    zero_mask = sum(1 << i for i, value in enumerate(scalars) if value == 0)
    body = struct.pack('<HI', 0x2b80, zero_mask)
    body += b''.join(struct.pack('<d', x) for x in scalars if x != 0)
    body += b'\x80\x09\x0f' * 12  # four zero floats in each elemental structure
    body += struct.pack('<d', settings['enemy_health'])
    old = files['.ucas']
    asset = bytearray(old[:0xad3] + body + old[0xb15:0xb19])
    # Single Zen export: serialized size changes when zero-valued fields appear/disappear.
    struct.pack_into('<Q', asset, 0x632, len(asset) - 0x69a - 4)
    cas = bytes(asset) + old[0xb19:]
    toc = bytearray(files['.utoc'])
    toc[0xad:0xb2] = len(asset).to_bytes(5, 'big')
    toc[0xc1:0xc4] = len(asset).to_bytes(3, 'little')
    toc[0xc4:0xc7] = len(asset).to_bytes(3, 'little')
    toc[0xc8:0xcd] = len(asset).to_bytes(5, 'little')
    toc[310:342] = digest(asset)[:20] + bytes(12)
    verify_container(toc, cas)
    return {'.pak': files['.pak'], '.utoc': bytes(toc), '.ucas': cas}

def build(settings, output=None):
    settings = validate(settings)
    files = generate(settings)
    output = Path(output) if output else ROOT / 'output'
    # Generate into a workspace folder; users copy a complete set into the game.
    if output.resolve() == (ROOT / 'examples').resolve():
        raise ValueError('Choose an output folder other than examples.')
    output.mkdir(parents=True, exist_ok=True)
    for ext, data in files.items():
        (output / (STEM + ext)).write_bytes(data)
    manifest = dict(settings=settings, incoming_damage_multiplier=settings['enemy_damage']/settings['player_durability'],
                    sha256={STEM+ext: hashlib.sha256(data).hexdigest() for ext,data in files.items()})
    (output / 'build-info.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'settings.json')
    parser.add_argument('--output', type=Path, default=ROOT/'output')
    args = parser.parse_args()
    try:
        settings = json.loads(args.config.read_text(encoding='utf-8-sig'))
        print('Generated:', build(settings, args.output))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Cannot build: {exc}\n')

if __name__ == '__main__':
    main()
