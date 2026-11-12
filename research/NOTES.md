# Asset investigation

Local inputs: `examples/000_BetterDifficultyHarder2_P.*`. Source mod: Caites' [Difficulty And Loot Tweaks](https://www.nexusmods.com/borderlands4/mods/1?tab=description).

The installed game was read through its Steam path. `inspect_assets.py` extracted only the matching `Struct_Player_Difficulty_Balance` package, using the existing Unreal Engine Oodle DLL for decompression. No installed files were written. The extracted asset is a local research artifact, not needed by the builder.

- Matching package ID bytes: `fe d0 2b 65 c3 c3 49 50`.
- Found in `pakchunk0-Windows_0_P.utoc`; no later base-game container contained that package ID during inspection.
- Original package size: 2,839 bytes. Original default scalars are zero except EnemyHealth = 1. The example stores DamageTaken = 0.99, DamageDealt = -1, EnemyHealth = 1.
- Property definitions identify eight doubles, twelve elemental substructures, then the EnemyHealth double. No player maximum-health or shield-capacity property exists here.
- The signed damage conversion is inferred from the original mod's documented approximately doubled incoming and halved outgoing damage: positive `v` maps to `1+v`; negative `v` maps to `1/(1-v)`. Runtime confirmation is outstanding.

Template layout (offsets are specific to this exact template, guarded by SHA-256):

| File | Offset | Meaning |
| --- | --- | --- |
| ucas | `0x632` | Single Zen export serialized size, uint64 little endian |
| ucas | `0x69a` | Zen header end / export data start |
| ucas | `0xad3` | Unversioned default structure header, 21 fields |
| ucas | `0xad9` | Default payload after fragment and 32-bit zero mask |
| ucas | `0xb15` | Original export end; followed by 4-byte package tag |
| ucas | `0xb19` | Container header chunk begins, length 80 |
| utoc | `0xa8` | Two 10-byte logical chunk offset/length pairs |
| utoc | `0xbc` | Two 12-byte compression block entries |
| utoc | `0x136` | Two 33-byte chunk hash/flag records |

The first eight scalar schema fields are DamageTaken, DamageDealt, LootLuck, AITimeToBestAccuracy, AIDmgPercentToWorstAccuracy, Cash, Eridium, CombatExperience. Twelve elemental fields use zero-valued four-float substructures (`80 09 0f`), then EnemyHealth is serialized as a double. Loot and AI defaults are preserved.

Format references: [retoc](https://github.com/trumank/retoc), [UAssetAPI unversioned fragments](https://github.com/atenfyr/UAssetAPI/blob/master/UAssetAPI/Unversioned/FFragment.cs), [BLAKE3 specification](https://github.com/BLAKE3-team/BLAKE3-specs/blob/master/blake3.pdf). BLAKE3-256 is truncated to 20 bytes and padded to 32 bytes for this TOC version's chunk metadata. Both original chunk digests match the local implementation.
