#!/usr/bin/env python3
"""Generate locale/fr/LC_MESSAGES/logsim.mo from embedded French translations.

Run this script once to (re)build the binary translation catalog:
    python make_locale.py
"""

import os
import struct

TRANSLATIONS_FR = {
    # GNU gettext metadata (empty-string key is mandatory)
    "": (
        "Content-Type: text/plain; charset=UTF-8\n"
        "Content-Transfer-Encoding: 8bit\n"
        "Language: fr\n"
    ),

    # ── Menus ────────────────────────────────────────────────────────────────
    "&File": "&Fichier",
    "&Open": "&Ouvrir",
    "&Save": "&Enregistrer",
    "&About": "À &propos",
    "&Exit": "&Quitter",
    "&View": "&Vue",
    "&Show File Viewer\tCtrl+Shift+F": "&Afficher la visionneuse\tCtrl+Shift+F",
    "&Help": "&Aide",
    "&Documentation": "&Documentation",

    # ── AUI pane captions ────────────────────────────────────────────────────
    "Simulation": "Simulation",
    "Switches": "Commutateurs",
    "Monitors": "Moniteurs",
    "Console": "Console",

    # ── Widget labels ────────────────────────────────────────────────────────
    "Cycles": "Cycles",
    "Last": "Derniers",
    "Select switch:": "Commutateur :",
    "Switch": "Commutateur",
    "Value": "Valeur",
    "Monitors:": "Moniteurs :",
    "X Zoom:": "Zoom X :",

    # ── Buttons ──────────────────────────────────────────────────────────────
    "ON": "Marche",
    "OFF": "Arrêt",
    "Save": "Enregistrer",
    "Implement": "Implémenter",
    "File Viewer": "Visionneuse",

    # ── Logic Viewer ─────────────────────────────────────────────────────────
    "Logic Viewer": "Visionneuse logique",
    "Fit": "Ajuster",
    "Zoom out": "Zoom arrière",
    "Zoom in": "Zoom avant",
    "Reset zoom to fit": "Réinitialiser le zoom pour ajuster",
    "Scroll to zoom • drag to pan":
        "Molette pour zoomer • glisser pour déplacer",
    "No circuit implemented yet.":
        "Aucun circuit implémenté pour l'instant.",
    "Move selected monitor up": "Déplacer le moniteur sélectionné vers le haut",
    "Move selected monitor down": "Déplacer le moniteur sélectionné vers le bas",

    # ── Tooltips ─────────────────────────────────────────────────────────────
    "Run the simulation from scratch for %d cycles":
        "Exécuter la simulation depuis zéro pour %d cycles",
    "Continue the simulation for %d additional cycles":
        "Poursuivre la simulation pour %d cycles supplémentaires",
    "Reset the simulation to its initial state":
        "Réinitialiser la simulation à son état initial",
    "Click a switch to select it, then use ON / OFF":
        "Cliquez sur un commutateur pour le sélectionner, "
        "puis utilisez Marche / Arrêt",
    "Set the selected switch to ON (1)":
        "Activer le commutateur sélectionné (1)",
    "Set the selected switch to OFF (0)":
        "Désactiver le commutateur sélectionné (0)",
    "Add a monitor to the selected signal":
        "Ajouter un moniteur au signal sélectionné",
    "Remove the selected monitor":
        "Supprimer le moniteur sélectionné",
    "Number of cycles to run or continue":
        "Nombre de cycles à exécuter ou poursuivre",
    "Show only the most recent cycles":
        "Afficher uniquement les cycles les plus récents",
    "Number of recent cycles to show":
        "Nombre de cycles récents à afficher",
    "Save changes to file":
        "Enregistrer les modifications dans le fichier",
    "Run the simulator using this file":
        "Exécuter le simulateur avec ce fichier",
    "Close file viewer":
        "Fermer la visionneuse",
    "Change interface language":
        "Changer la langue de l'interface",
    "Switch to 3D signal view":
        "Passer à la vue 3D des signaux",
    "Switch back to 2D signal view":
        "Revenir à la vue 2D des signaux",
    "Show gate-level circuit diagram":
        "Afficher le schéma logique du circuit",

    # ── Status bar – static messages ─────────────────────────────────────────
    "Ready": "Prêt",
    "File viewer opened.": "Visionneuse ouverte.",
    "File viewer closed.": "Visionneuse fermée.",
    "Error: network oscillating.": "Erreur : réseau oscillant.",
    "Showing all recorded cycles.": "Affichage de tous les cycles enregistrés.",
    "Error: nothing to continue. Run first.":
        "Erreur : rien à continuer. Exécutez d'abord.",
    "Error: please select a switch first.":
        "Erreur : veuillez d'abord sélectionner un commutateur.",
    "Error: please select a signal first.":
        "Erreur : veuillez d'abord sélectionner un signal.",
    "Error: please select a monitor first.":
        "Erreur : veuillez d'abord sélectionner un moniteur.",
    "Error: selected signal was not found.":
        "Erreur : le signal sélectionné est introuvable.",
    "Simulation reset.": "Simulation réinitialisée.",
    "View reset to default dimensions.":
        "Vue réinitialisée aux dimensions par défaut.",
    "Implement failed: parse errors in file.":
        "Implémentation échouée : erreurs d'analyse dans le fichier.",

    # ── Status bar – format strings (use % formatting after _()) ─────────────
    "Running for %d cycles...": "Exécution pour %d cycles...",
    "Completed %d cycles.": "%d cycles effectués.",
    "Continuing for %d cycles...": "Poursuite sur %d cycles...",
    "Showing last %d cycles.": "Affichage des %d derniers cycles.",
    "Added monitor: %s": "Moniteur ajouté : %s",
    "Monitor already active: %s": "Moniteur déjà actif : %s",
    "Error: could not add monitor %s":
        "Erreur : impossible d'ajouter le moniteur %s",
    "Removed monitor: %s": "Moniteur supprimé : %s",
    "Error: monitor is not active: %s":
        "Erreur : le moniteur n'est pas actif : %s",
    "Switch %s set ON.": "Commutateur %s activé.",
    "Switch %s set OFF.": "Commutateur %s désactivé.",
    "Error: could not set switch %s.":
        "Erreur : impossible de définir le commutateur %s.",
    "Saved: %s": "Enregistré : %s",
    "Opened: %s": "Ouvert : %s",
    "Implemented: %s": "Implémenté : %s",
    "Implement failed: parse errors in %s":
        "Implémentation échouée : erreurs d'analyse dans %s",

    # ── Console log messages ──────────────────────────────────────────────────
    "File saved: %s": "Fichier enregistré : %s",
    "Implemented file: %s": "Fichier implémenté : %s",
    "Opened file: %s": "Fichier ouvert : %s",
    "New spin control value: %d": "Nouvelle valeur du contrôle : %d",
    "Run clicked: %d cycles requested.": "Exécution demandée : %d cycles.",
    "Completed %d total cycles.": "%d cycles au total effectués.",
    "Continue ignored: run the simulation first.":
        "Poursuite ignorée : lancez d'abord la simulation.",
    "Continue clicked: %d cycles requested.": "Poursuite demandée : %d cycles.",

    # ── Dialogs ──────────────────────────────────────────────────────────────
    "About Logic Simulator": "À propos du simulateur logique",
    (
        "Logic Simulator\nGF2 Software Project\n"
        "Cambridge University Engineering Department\n2026"
    ): (
        "Simulateur logique\nProjet logiciel GF2\n"
        "Département de génie de l'Université de Cambridge\n2026"
    ),
    "GUI Usage Guide": "Guide d'utilisation",
    "Open circuit definition file":
        "Ouvrir un fichier de définition de circuit",
    "Circuit definition files (*.txt)|*.txt|All files (*.*)|*.*":
        "Fichiers de définition (*.txt)|*.txt|Tous les fichiers (*.*)|*.*",
    "Save Image": "Enregistrer l'image",
    "PNG files (*.png)|*.png|JPEG files (*.jpg)|*.jpg":
        "Fichiers PNG (*.png)|*.png|Fichiers JPEG (*.jpg)|*.jpg",
    "No file is open — nothing to save.":
        "Aucun fichier ouvert — rien à enregistrer.",
    "Save Error": "Erreur d'enregistrement",
    "No file is open - nothing to implement.":
        "Aucun fichier ouvert — rien à implémenter.",
    "Implement Error": "Erreur d'implémentation",
    "Could not implement this file because it contains errors.":
        "Impossible d'implémenter ce fichier car il contient des erreurs.",
    "File Viewer — error": "Visionneuse — erreur",
    "Could not save file:\n%s": "Impossible d'enregistrer le fichier :\n%s",
    "Could not open file:\n%s": "Impossible d'ouvrir le fichier :\n%s",

    # ── Canvas labels (rendered via OpenGL) ──────────────────────────────────
    "High": "Haut",
    "Low": "Bas",
    "HIGH": "HAUT",
    "LOW": "BAS",

    # ── Monitor list suffix ───────────────────────────────────────────────────
    " (on)": " (actif)",

    # ── Context menu ─────────────────────────────────────────────────────────
    "Reset View": "Réinitialiser la vue",
    "Save Image...": "Enregistrer l'image...",
    "Copy Image": "Copier l'image",

    # ── Help dialog ───────────────────────────────────────────────────────────
    (
        "Welcome to the Logic Simulator!\n\n"
        "Here is a summary of the available interface functions:\n\n"
        "1. Simulation Controls:\n"
        "   - Use the spin box to set the number of cycles to run or continue.\n"
        "   - Click '▶' to start or restart the simulation from zero.\n"
        "   - Click '+N' to continue running N further cycles.\n"
        "   - Click '↺' to clear the current history and reset the network.\n"
        "   - Tick 'Last' and set a number to show only the most recent cycles.\n\n"
        "2. Interacting with the Canvas:\n"
        "   - Drag with the Left Mouse Button to pan across the logic waveforms.\n"
        "   - Scroll the Mouse Wheel to zoom in/out on active lines.\n"
        "   - Use the 'X Zoom' slider to stretch the time axis horizontally.\n"
        "   - Right-click inside the canvas to copy or save a snapshot image.\n"
        "   - Click '3D' for a three-dimensional view of the signals (drag to\n"
        "     rotate, scroll to zoom); click '2D' to switch back.\n\n"
        "3. Switches & Monitors:\n"
        "   - Select a switch from the list and toggle it with 'ON' / 'OFF'.\n"
        "   - Add (+) or remove (-) signals using the Monitors list.\n"
        "   - Reorder monitors with the up/down arrows.\n"
        "   - A monitor added mid-run shows the signal's history for the\n"
        "     cycles before it was monitored.\n\n"
        "4. Logic Viewer:\n"
        "   - Click 'Logic Viewer' to open the gate-level circuit diagram.\n"
        "   - Gates use standard symbols with their names inside; a single-input\n"
        "     NAND is shown as a NOT (inverter), and an AND/OR feeding an\n"
        "     inverter is merged into a NAND/NOR gate.\n"
        "   - Wires leave each gate from its output, beside the inversion bubble.\n"
        "   - Drag to pan, scroll to zoom, and use the -/+/Fit buttons.\n\n"
        "5. Language & View Options:\n"
        "   - Use the language selector (next to '3D') to switch between\n"
        "     English and French.\n"
        "   - Toggle the live text definition panel under View -> Show File Viewer."
    ): (
        "Bienvenue dans le Simulateur Logique !\n\n"
        "Voici un résumé des fonctions disponibles :\n\n"
        "1. Contrôles de simulation :\n"
        "   - Utilisez la zone de saisie pour définir le nombre de cycles à exécuter ou poursuivre.\n"
        "   - Cliquez sur '▶' pour démarrer ou redémarrer la simulation depuis zéro.\n"
        "   - Cliquez sur '+N' pour poursuivre l'exécution de N cycles supplémentaires.\n"
        "   - Cliquez sur '↺' pour effacer l'historique et réinitialiser le réseau.\n"
        "   - Cochez « Derniers » et indiquez un nombre pour n'afficher que les cycles récents.\n\n"
        "2. Interaction avec le canevas :\n"
        "   - Glissez avec le bouton gauche pour parcourir les formes d'ondes.\n"
        "   - Faites défiler la molette pour zoomer sur les lignes actives.\n"
        "   - Utilisez le curseur « Zoom X » pour étirer l'axe du temps horizontalement.\n"
        "   - Clic droit dans le canevas pour copier ou enregistrer une image.\n"
        "   - Cliquez sur « 3D » pour une vue tridimensionnelle des signaux (glisser\n"
        "     pour pivoter, molette pour zoomer) ; cliquez sur « 2D » pour revenir.\n\n"
        "3. Commutateurs et moniteurs :\n"
        "   - Sélectionnez un commutateur dans la liste et basculez-le avec « Marche » / « Arrêt ».\n"
        "   - Ajoutez (+) ou retirez (-) des signaux via la liste des moniteurs.\n"
        "   - Réorganisez les moniteurs avec les flèches haut/bas.\n"
        "   - Un moniteur ajouté en cours d'exécution affiche l'historique du signal\n"
        "     pour les cycles précédant sa surveillance.\n\n"
        "4. Visionneuse logique :\n"
        "   - Cliquez sur « Visionneuse logique » pour ouvrir le schéma du circuit.\n"
        "   - Les portes utilisent des symboles standard avec leur nom à l'intérieur ; une\n"
        "     NAND à une entrée s'affiche comme une porte NON (inverseur), et une porte\n"
        "     ET/OU alimentant un inverseur est fusionnée en porte NAND/NOR.\n"
        "   - Les fils sortent de chaque porte au niveau de sa sortie, près de la bulle d'inversion.\n"
        "   - Glissez pour déplacer, molette pour zoomer, et boutons -/+/Ajuster.\n\n"
        "5. Options de langue et d'affichage :\n"
        "   - Utilisez le sélecteur de langue (à côté de « 3D ») pour basculer entre\n"
        "     le français et l'anglais.\n"
        "   - Activez le panneau de définition sous Vue → Afficher la visionneuse."
    ),
}


def generate_mo(translations: dict, filepath: str) -> None:
    """Write a GNU gettext binary .mo file from a {original: translated} dict."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Sort pairs by original string (gettext requires sorted original strings)
    pairs = sorted(translations.items(), key=lambda x: x[0].encode("utf-8"))
    N = len(pairs)

    orig_bytes = [k.encode("utf-8") for k, _ in pairs]
    trans_bytes = [v.encode("utf-8") for _, v in pairs]

    # File layout:
    #   28 bytes   header
    #   N×8 bytes  original string descriptors (length, file-offset)
    #   N×8 bytes  translation string descriptors
    #   variable   string data (originals, then translations)
    orig_tab_offset = 28
    trans_tab_offset = 28 + N * 8
    data_start = 28 + N * 16

    orig_descs: list[tuple[int, int]] = []
    trans_descs: list[tuple[int, int]] = []
    string_data = b""

    cur = data_start
    for b in orig_bytes:
        orig_descs.append((len(b), cur))
        string_data += b + b"\x00"
        cur += len(b) + 1

    for b in trans_bytes:
        trans_descs.append((len(b), cur))
        string_data += b + b"\x00"
        cur += len(b) + 1

    with open(filepath, "wb") as fh:
        fh.write(struct.pack(
            "<IIIIIII",
            0x950412DE,  # magic (little-endian)
            0,           # revision
            N,
            orig_tab_offset,
            trans_tab_offset,
            0,           # no hash table
            0,
        ))
        for length, offset in orig_descs:
            fh.write(struct.pack("<II", length, offset))
        for length, offset in trans_descs:
            fh.write(struct.pack("<II", length, offset))
        fh.write(string_data)

    print(f"Wrote {N} translation entries to: {filepath}")


if __name__ == "__main__":
    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "locale", "fr", "LC_MESSAGES", "logsim.mo",
    )
    generate_mo(TRANSLATIONS_FR, out)
