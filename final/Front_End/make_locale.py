#!/usr/bin/env python3
"""Generate locale .mo files from embedded translations.

Run once to (re)build all binary translation catalogs:
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
    "&New File": "&Nouveau fichier",
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
    "Save As": "Enregistrer sous",
    "Implement": "Implémenter",
    "File Viewer": "Visionneuse",
    "Skip": "Passer",

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
    "Skip the trace drawing animation":
        "Passer l'animation du tracé",
    "Trace drawing animation speed":
        "Vitesse de l'animation du tracé",
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
    "Save file to a new location or name":
        "Enregistrer le fichier à un nouvel emplacement ou sous un nouveau nom",
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
    "3D view enabled — drag to rotate, scroll to zoom.":
        "Vue 3D activée — glisser pour pivoter, molette pour zoomer.",
    "2D view enabled.": "Vue 2D activée.",
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
    "Please implement a circuit file first.":
        "Veuillez d'abord implémenter un fichier de circuit.",
    "No Circuit": "Pas de circuit",
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
    "new file": "nouveau fichier",
    "To simulate press play": "Pour simuler, appuyez sur lecture",

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
        "     English, French and Greek.\n"
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
        "     l'anglais, le français et le grec.\n"
        "   - Activez le panneau de définition sous Vue → Afficher la visionneuse."
    ),
}


TRANSLATIONS_EL = {
    # GNU gettext metadata
    "": (
        "Content-Type: text/plain; charset=UTF-8\n"
        "Content-Transfer-Encoding: 8bit\n"
        "Language: el\n"
    ),

    # ── Menus ────────────────────────────────────────────────────────────────
    "&File": "&Αρχείο",
    "&New File": "&Νέο αρχείο",
    "&Open": "&Άνοιγμα",
    "&Save": "&Αποθήκευση",
    "&About": "&Σχετικά",
    "&Exit": "&Έξοδος",
    "&View": "&Προβολή",
    "&Show File Viewer\tCtrl+Shift+F": "&Εμφάνιση προβολής αρχείου\tCtrl+Shift+F",
    "&Help": "&Βοήθεια",
    "&Documentation": "&Τεκμηρίωση",

    # ── AUI pane captions ────────────────────────────────────────────────────
    "Simulation": "Προσομοίωση",
    "Switches": "Διακόπτες",
    "Monitors": "Παρακολουθητές",
    "Console": "Κονσόλα",

    # ── Widget labels ────────────────────────────────────────────────────────
    "Cycles": "Κύκλοι",
    "Last": "Τελευταίοι",
    "Select switch:": "Επιλογή διακόπτη:",
    "Switch": "Διακόπτης",
    "Value": "Τιμή",
    "Monitors:": "Παρακολουθητές:",
    "X Zoom:": "Ζουμ Χ:",

    # ── Buttons ──────────────────────────────────────────────────────────────
    "ON": "Ενεργό",
    "OFF": "Ανενεργό",
    "Save": "Αποθήκευση",
    "Save As": "Αποθήκευση ως",
    "Implement": "Υλοποίηση",
    "File Viewer": "Προβολή Αρχείου",
    "Skip": "Παράλειψη",

    # ── Logic Viewer ─────────────────────────────────────────────────────────
    "Logic Viewer": "Λογική Προβολή",
    "Fit": "Προσαρμογή",
    "Zoom out": "Σμίκρυνση",
    "Zoom in": "Μεγέθυνση",
    "Reset zoom to fit": "Επαναφορά ζουμ",
    "Scroll to zoom • drag to pan":
        "Κύλιση για ζουμ • σύρε για μετακίνηση",
    "No circuit implemented yet.":
        "Δεν έχει υλοποιηθεί κύκλωμα ακόμα.",
    "Move selected monitor up": "Μετακίνηση επιλεγμένου πάνω",
    "Move selected monitor down": "Μετακίνηση επιλεγμένου κάτω",

    # ── Tooltips ─────────────────────────────────────────────────────────────
    "Run the simulation from scratch for %d cycles":
        "Εκτέλεση προσομοίωσης από την αρχή για %d κύκλους",
    "Continue the simulation for %d additional cycles":
        "Συνέχιση προσομοίωσης για %d επιπλέον κύκλους",
    "Reset the simulation to its initial state":
        "Επαναφορά προσομοίωσης στην αρχική κατάσταση",
    "Skip the trace drawing animation":
        "Παράλειψη κινούμενης απεικόνισης",
    "Trace drawing animation speed":
        "Ταχύτητα κινούμενης απεικόνισης",
    "Click a switch to select it, then use ON / OFF":
        "Κλικ σε διακόπτη για επιλογή, μετά Ενεργό / Ανενεργό",
    "Set the selected switch to ON (1)":
        "Ενεργοποίηση επιλεγμένου διακόπτη (1)",
    "Set the selected switch to OFF (0)":
        "Απενεργοποίηση επιλεγμένου διακόπτη (0)",
    "Add a monitor to the selected signal":
        "Προσθήκη παρακολουθητή στο επιλεγμένο σήμα",
    "Remove the selected monitor":
        "Αφαίρεση επιλεγμένου παρακολουθητή",
    "Number of cycles to run or continue":
        "Αριθμός κύκλων για εκτέλεση ή συνέχιση",
    "Show only the most recent cycles":
        "Εμφάνιση μόνο των πιο πρόσφατων κύκλων",
    "Number of recent cycles to show":
        "Αριθμός πρόσφατων κύκλων για εμφάνιση",
    "Save changes to file":
        "Αποθήκευση αλλαγών στο αρχείο",
    "Save file to a new location or name":
        "Αποθήκευση αρχείου σε νέα τοποθεσία ή με νέο όνομα",
    "Run the simulator using this file":
        "Εκτέλεση προσομοιωτή με αυτό το αρχείο",
    "Close file viewer":
        "Κλείσιμο προβολής αρχείου",
    "Change interface language":
        "Αλλαγή γλώσσας διεπαφής",
    "Switch to 3D signal view":
        "Μετάβαση σε τρισδιάστατη προβολή",
    "Switch back to 2D signal view":
        "Επιστροφή σε δισδιάστατη προβολή",
    "Show gate-level circuit diagram":
        "Εμφάνιση διαγράμματος κυκλώματος",

    # ── Status bar – static messages ─────────────────────────────────────────
    "Ready": "Έτοιμο",
    "3D view enabled — drag to rotate, scroll to zoom.":
        "Τρισδιάστατη προβολή ενεργή — σύρε για περιστροφή, κύλιση για ζουμ.",
    "2D view enabled.": "Δισδιάστατη προβολή ενεργή.",
    "File viewer opened.": "Η προβολή αρχείου άνοιξε.",
    "File viewer closed.": "Η προβολή αρχείου έκλεισε.",
    "Error: network oscillating.": "Σφάλμα: δίκτυο ταλαντεύεται.",
    "Showing all recorded cycles.": "Εμφάνιση όλων των καταγεγραμμένων κύκλων.",
    "Error: nothing to continue. Run first.":
        "Σφάλμα: τίποτα για συνέχιση. Εκτελέστε πρώτα.",
    "Error: please select a switch first.":
        "Σφάλμα: επιλέξτε πρώτα έναν διακόπτη.",
    "Error: please select a signal first.":
        "Σφάλμα: επιλέξτε πρώτα ένα σήμα.",
    "Error: please select a monitor first.":
        "Σφάλμα: επιλέξτε πρώτα έναν παρακολουθητή.",
    "Error: selected signal was not found.":
        "Σφάλμα: το επιλεγμένο σήμα δεν βρέθηκε.",
    "Simulation reset.": "Επαναφορά προσομοίωσης.",
    "View reset to default dimensions.":
        "Επαναφορά προβολής στις προεπιλεγμένες διαστάσεις.",
    "Implement failed: parse errors in file.":
        "Αποτυχία υλοποίησης: σφάλματα ανάλυσης στο αρχείο.",

    # ── Status bar – format strings ───────────────────────────────────────────
    "Running for %d cycles...": "Εκτέλεση για %d κύκλους...",
    "Completed %d cycles.": "Ολοκληρώθηκαν %d κύκλοι.",
    "Continuing for %d cycles...": "Συνέχεια για %d κύκλους...",
    "Showing last %d cycles.": "Εμφάνιση τελευταίων %d κύκλων.",
    "Added monitor: %s": "Παρακολουθητής προστέθηκε: %s",
    "Monitor already active: %s": "Παρακολουθητής ήδη ενεργός: %s",
    "Error: could not add monitor %s":
        "Σφάλμα: αδύνατη προσθήκη παρακολουθητή %s",
    "Removed monitor: %s": "Παρακολουθητής αφαιρέθηκε: %s",
    "Error: monitor is not active: %s":
        "Σφάλμα: ο παρακολουθητής δεν είναι ενεργός: %s",
    "Switch %s set ON.": "Διακόπτης %s ενεργοποιήθηκε.",
    "Switch %s set OFF.": "Διακόπτης %s απενεργοποιήθηκε.",
    "Error: could not set switch %s.":
        "Σφάλμα: αδύνατη ρύθμιση διακόπτη %s.",
    "Saved: %s": "Αποθηκεύτηκε: %s",
    "Opened: %s": "Άνοιξε: %s",
    "Implemented: %s": "Υλοποιήθηκε: %s",
    "Implement failed: parse errors in %s":
        "Αποτυχία υλοποίησης: σφάλματα ανάλυσης στο %s",

    # ── Console log messages ──────────────────────────────────────────────────
    "File saved: %s": "Αρχείο αποθηκεύτηκε: %s",
    "Implemented file: %s": "Αρχείο υλοποιήθηκε: %s",
    "Opened file: %s": "Αρχείο άνοιξε: %s",
    "New spin control value: %d": "Νέα τιμή ελέγχου: %d",
    "Run clicked: %d cycles requested.": "Εκτέλεση: ζητήθηκαν %d κύκλοι.",
    "Completed %d total cycles.": "Ολοκληρώθηκαν %d κύκλοι συνολικά.",
    "Continue ignored: run the simulation first.":
        "Η συνέχεια αγνοήθηκε: εκτελέστε πρώτα.",
    "Continue clicked: %d cycles requested.": "Συνέχεια: ζητήθηκαν %d κύκλοι.",

    # ── Dialogs ──────────────────────────────────────────────────────────────
    "About Logic Simulator": "Σχετικά με τον Λογικό Προσομοιωτή",
    (
        "Logic Simulator\nGF2 Software Project\n"
        "Cambridge University Engineering Department\n2026"
    ): (
        "Λογικός Προσομοιωτής\nΕργασία Λογισμικού GF2\n"
        "Τμήμα Μηχανικής Πανεπιστημίου Cambridge\n2026"
    ),
    "GUI Usage Guide": "Οδηγός Χρήσης",
    "Open circuit definition file":
        "Άνοιγμα αρχείου ορισμού κυκλώματος",
    "Circuit definition files (*.txt)|*.txt|All files (*.*)|*.*":
        "Αρχεία ορισμού (*.txt)|*.txt|Όλα τα αρχεία (*.*)|*.*",
    "Save Image": "Αποθήκευση Εικόνας",
    "PNG files (*.png)|*.png|JPEG files (*.jpg)|*.jpg":
        "Αρχεία PNG (*.png)|*.png|Αρχεία JPEG (*.jpg)|*.jpg",
    "No file is open — nothing to save.":
        "Δεν είναι ανοιχτό αρχείο — τίποτα να αποθηκευτεί.",
    "Save Error": "Σφάλμα Αποθήκευσης",
    "No file is open - nothing to implement.":
        "Δεν είναι ανοιχτό αρχείο — τίποτα να υλοποιηθεί.",
    "Implement Error": "Σφάλμα Υλοποίησης",
    "Please implement a circuit file first.":
        "Παρακαλώ υλοποιήστε πρώτα ένα αρχείο κυκλώματος.",
    "No Circuit": "Χωρίς κύκλωμα",
    "Could not implement this file because it contains errors.":
        "Δεν ήταν δυνατή η υλοποίηση επειδή το αρχείο περιέχει σφάλματα.",
    "File Viewer — error": "Προβολή αρχείου — σφάλμα",
    "Could not save file:\n%s": "Δεν ήταν δυνατή η αποθήκευση:\n%s",
    "Could not open file:\n%s": "Δεν ήταν δυνατό το άνοιγμα:\n%s",

    # ── Canvas labels (rendered via OpenGL) ──────────────────────────────────
    "High": "Υψηλό",
    "Low": "Χαμηλό",
    "HIGH": "ΥΨΗΛΟ",
    "LOW": "ΧΑΜΗΛΟ",
    "new file": "νέο αρχείο",
    "To simulate press play": "Για προσομοίωση πατήστε αναπαραγωγή",

    # ── Monitor list suffix ───────────────────────────────────────────────────
    " (on)": " (ενεργό)",

    # ── Context menu ─────────────────────────────────────────────────────────
    "Reset View": "Επαναφορά Προβολής",
    "Save Image...": "Αποθήκευση Εικόνας...",
    "Copy Image": "Αντιγραφή Εικόνας",

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
        "     English, French and Greek.\n"
        "   - Toggle the live text definition panel under View -> Show File Viewer."
    ): (
        "Καλώς ήρθατε στον Λογικό Προσομοιωτή!\n\n"
        "Σύνοψη διαθέσιμων λειτουργιών:\n\n"
        "1. Στοιχεία ελέγχου προσομοίωσης:\n"
        "   - Χρησιμοποιήστε το πλαίσιο αριθμού για να ορίσετε τους κύκλους.\n"
        "   - Κλικ '▶' για εκκίνηση ή επανεκκίνηση από την αρχή.\n"
        "   - Κλικ '+N' για συνέχεια N επιπλέον κύκλων.\n"
        "   - Κλικ '↺' για εκκαθάριση ιστορικού και επαναφορά δικτύου.\n"
        "   - Τσεκάρετε 'Τελευταίοι' για εμφάνιση μόνο πρόσφατων κύκλων.\n\n"
        "2. Αλληλεπίδραση με τον καμβά:\n"
        "   - Σύρετε με το αριστερό κουμπί ποντικιού για μετακίνηση.\n"
        "   - Κυλήστε τη ρόδα για μεγέθυνση/σμίκρυνση.\n"
        "   - Χρησιμοποιήστε το ρυθμιστικό 'Ζουμ Χ' για οριζόντια τέντωση.\n"
        "   - Δεξί κλικ για αντιγραφή ή αποθήκευση εικόνας.\n"
        "   - Κλικ '3D' για τρισδιάστατη προβολή (σύρσιμο για περιστροφή,\n"
        "     κύλιση για ζουμ)· κλικ '2D' για επιστροφή.\n\n"
        "3. Διακόπτες και παρακολουθητές:\n"
        "   - Επιλέξτε διακόπτη και εναλλάξτε με 'ON' / 'OFF'.\n"
        "   - Προσθέστε (+) ή αφαιρέστε (-) σήματα από τη λίστα παρακολουθητών.\n"
        "   - Αναδιατάξτε παρακολουθητές με τα βέλη πάνω/κάτω.\n"
        "   - Παρακολουθητής που προστίθεται εν μέσω εκτέλεσης εμφανίζει\n"
        "     το ιστορικό σήματος για τους προηγούμενους κύκλους.\n\n"
        "4. Λογική Προβολή:\n"
        "   - Κλικ 'Λογική Προβολή' για το διάγραμμα κυκλώματος.\n"
        "   - Οι πύλες χρησιμοποιούν τυπικά σύμβολα· μια NAND μίας εισόδου\n"
        "     εμφανίζεται ως NOT, και AND/OR που τροφοδοτεί αναστροφέα\n"
        "     συγχωνεύεται σε NAND/NOR.\n"
        "   - Σύρσιμο για μετακίνηση, κύλιση για ζουμ, κουμπιά -/+/Προσαρμογή.\n\n"
        "5. Επιλογές γλώσσας και προβολής:\n"
        "   - Χρησιμοποιήστε τον επιλογέα γλώσσας για εναλλαγή μεταξύ\n"
        "     Αγγλικών, Γαλλικών και Ελληνικών.\n"
        "   - Εναλλαγή ζωντανού πίνακα ορισμού μέσω Προβολή → Εμφάνιση προβολής αρχείου."
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
    base = os.path.dirname(os.path.abspath(__file__))

    generate_mo(
        TRANSLATIONS_FR,
        os.path.join(base, "locale", "fr", "LC_MESSAGES", "logsim.mo"),
    )
    generate_mo(
        TRANSLATIONS_EL,
        os.path.join(base, "locale", "el", "LC_MESSAGES", "logsim.mo"),
    )
