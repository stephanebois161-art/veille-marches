# Veille des marchés

Veille boursière quotidienne : chaque matin de semaine, le programme du prochain jour de bourse (annonces économiques US, autres événements, introductions en bourse, résultats d'entreprises), avec pour chaque événement un scénario à la hausse et un scénario à la baisse. Toutes les heures sont en heure de Paris.

Ce dépôt garde l'historique de la page, du prompt et du modèle de mail, et sert la page sur un lien public lisible sans compte Claude.

## Contenu

| Fichier | Rôle |
| --- | --- |
| `index.html` | La page de veille (copie de la page Claude « Veille des marchés »). C'est elle que GitHub Pages publie. |
| `prompt/prompt-veille-marches.md` | Le prompt de la veille et son état. |
| `modeles/consigne-mail-html.md` | La consigne d'envoi du mail et de mise en forme HTML. |
| `modeles/modele-mail-veille.html` | Un exemple de mail HTML (programme du vendredi 30 octobre 2026). |
| `modeles/apercu-mail-veille.png` | Capture de ce mail tel qu'il s'affiche. |

Les adresses des destinataires du mail ne sont pas publiées ici, car le dépôt est public.

## Fonctionnement actuel

1. Une tâche planifiée Claude tourne du lundi au vendredi à 8h43 (heure de Paris).
2. Elle prépare le programme du prochain jour de bourse (le vendredi : celui du lundi, plus une ligne sur le week-end).
3. Elle met à jour la page Claude, puis envoie le mail depuis Gmail.

4. Elle pousse la page du jour sur une branche `claude/veille-AAAA-MM-JJ` partie de `main` (`index.html` + copie dans `archives/`).
5. Le workflow `.github/workflows/publier-veille.yml` vérifie que seuls ces fichiers changent et qu'aucune adresse mail n'y figure, avance `main` sur ce commit, puis supprime la branche. GitHub Pages republie alors la page.

## Page publique (GitHub Pages)

Une fois GitHub Pages activé, la page est lisible ici :
https://stephanebois161-art.github.io/veille-marches/

Pour l'activer : dans le dépôt, **Settings** → **Pages** → *Build and deployment* → Source : **Deploy from a branch**, branche **main**, dossier **/ (root)**, puis **Save**. Le lien apparaît en haut de la même page au bout d'une à deux minutes.

## Prochaines étapes envisagées

- Faire publier chaque nouvelle veille dans ce dépôt, pour garder un historique jour par jour.
- Un script de collecte des calendriers et consensus, plus fiable que la recherche web.
- Des graphiques.

Ceci n'est pas un conseil en investissement.
