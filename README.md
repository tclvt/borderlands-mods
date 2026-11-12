# Borderlands 4 Difficulty Configurator

Local desktop tool that generates a customized version of the three-file mod supplied in `examples`. Requires Python 3.10 or later with Tkinter (available on this PC). No extra Python packages, SDK loader, or network connection are required.

## Start here

L’interface est maintenant en français, avec un thème sombre, des curseurs et un aperçu des effets combinés. Les onglets **Combat** et **Progression** regroupent les réglages. Les cartes à gauche appliquent un préréglage ; les boutons **Charger un profil** et **Enregistrer le profil** permettent de conserver plusieurs configurations JSON. Les curseurs vont de 0,01 à 100 avec 1 au centre ; vous pouvez aussi saisir une valeur précise, avec une virgule ou un point. Le bouton **Générer mon mod** enregistre les réglages et produit les trois fichiers dans `output`. **Ouvrir le dossier** permet de les retrouver. Le raccourci Ctrl+Entrée lance aussi la génération.

1. Double-click **Launch Configurator.cmd**.
2. Choose a preset or type your own multipliers. Click **Save settings & generate mod**.
3. Click **Open output folder**. The initial build is already generated there: enemy health ×2, incoming damage ×1.5, everything else neutral.
4. Close Borderlands 4. Back up the existing `000_BetterDifficultyHarder2_P.pak`, `.utoc`, and `.ucas` files somewhere **outside** the game's Paks folder.
5. Copy the three generated files from `output` into:

   ```text
   C:\Program Files (x86)\Steam\steamapps\common\Borderlands 4\OakGame\Content\Paks
   ```

   Replace the existing three files as one set. The generated files deliberately use the original filenames and container identity. Do not rename them or keep another version of this difficulty mod in a subfolder of Paks.
6. Both players should install the same generated set and select **Normal** difficulty. Restart the game after every change.

The configurator only writes its own settings and output folder. It has not changed your installed mod or saves.

## Controls

| Control | Example | Effect |
| --- | --- | --- |
| Enemy health | `3` | Enemy health multiplier of ×3. |
| Incoming damage | `2` | Damage received multiplier of ×2, before the durability control. Can also affect hazards and self-damage. |
| Player damage | `0.5` | Damage dealt multiplier of ×0.5. |
| Player durability | `2` | Divides incoming damage by 2. Applies to shield damage too. |
| Experience | `0.75` | XP gain multiplier of ×0.75. |
| Cash / Eridium | `2` | Resource gain multiplier of ×2. |

All controls accept numbers from `0.01` to `100`. `1` is neutral relative to the normal difficulty defaults. XP and resource behavior, like combat behavior, still needs verification in your installed game version.

**Actual player maximum HP is not implemented.** Player durability is a damage-received adjustment, not a change to the health bar, healing amounts, health-dependent skills, or health-gating thresholds. This example asset contains no player maximum-health field. A true maximum-health control needs a separate game asset or an SDK implementation, followed by runtime testing.

The two incoming-damage controls combine as:

```text
final incoming multiplier = incoming damage / player durability
```

For example, incoming damage `3` and player durability `2` give a final incoming multiplier of `1.5`. These are separate preferences in the tool, but compile into the same game property; they are not independent changes to enemy attack stats and your character's health.

Presets:

- **Neutral:** all multipliers 1. Useful for comparing against the base game.
- **Co-op challenge:** enemy HP 2, incoming damage 1.5.
- **Brutal:** enemy HP 4, incoming damage 2, player damage 0.8.
- **Supplied Harder 2:** reproduces the example files byte for byte (incoming damage 1.99, player damage 0.5, enemy HP 1).

## Compatibility and co-op verification

The [example mod author's documentation](https://www.nexusmods.com/borderlands4/mods/1?tab=description) says to use Normal: Easy/Hard override some values, and UVH modes are unsupported. It also advises installing on both PCs for multiplayer. These restrictions carry over to this asset-based version. Modifications to the same difficulty structure conflict rather than stack.

The generated container and controls have been checked locally, **not tested in a running game or a co-op session**. The signed-damage conversion is inferred from the example's stored values and the author's documented effects. Enemy health's neutral value of 1 was confirmed against the installed game's original asset. Game updates and runtime hotfixes can change behavior.

For a first playtest, use the same ordinary enemy type and unchanged weapon/gear:

1. Try Neutral on Normal. Record shots to kill and damage from one enemy hit.
2. Restart with enemy health 2 and everything else 1. Check that enemies take approximately twice the total damage to kill.
3. Restart with incoming damage 2 and everything else 1. Compare damage received. Then test player damage and durability separately.
4. Repeat with your friend hosting, checking both characters. Do not assume a solo result proves client-side co-op behavior.

Avoid changing several controls at once during this first check; shields, resistances, critical hits and random damage can obscure the result. The supplied example already has the game's original elemental defaults; this tool preserves them.

To uninstall, close the game and remove the three generated files from Paks. To restore your old mod, copy back your backup of the three original files.

## Command line / development

Edit `settings.json` and double-click **Build Mod.cmd**, or run:

```powershell
python difficulty.py
python difficulty.py --config settings.json --output output
python -m unittest discover -s . -v
```

`output/build-info.json` records the settings, combined incoming-damage multiplier, and SHA-256 hashes for sharing/verifying a matching build. Do not copy the settings JSON into the game's Paks folder expecting live updates: the game reads the generated binary files.

The builder checks the SHA-256 of the supplied template, rebuilds the unversioned structure defaults, adjusts the Zen export size and IoStore offsets/lengths, and updates BLAKE3 chunk hashes. It refuses unrecognized templates. The source `.pak` is an empty companion container and is copied unchanged. The original example remains in `examples`.

Binary integrity tests include byte-for-byte reproduction of the supplied mod, independent decoding of generated settings, chunk hash checks, export boundary checks, invalid input rejection, and corrupted container rejection. See [research/NOTES.md](research/NOTES.md) for the investigated layout.
