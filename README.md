AVSD — Bot de sécurité et modération pour serveurs Discord

Version : V4.51 · Bilingue 🇫🇷 FR / 🇬🇧 EN · Basé sur discord.py

AVSD est un bot Discord tout-en-un conçu pour sécuriser, modérer et surveiller un serveur sans avoir à jongler entre dix bots différents. Tout passe par un panel de configuration centralisé accessible via une seule commande, avec des boutons plutôt que des dizaines de commandes à mémoriser.

Pourquoi ce bot

Beaucoup de serveurs Discord empilent plusieurs bots (un pour la modération, un pour l'anti-raid, un pour les logs, un pour la sécurité) qui ne communiquent pas entre eux et compliquent la gestion. AVSD regroupe ces fonctions dans un seul outil cohérent, avec un historique unifié et une configuration centralisée.

Fonctionnalités
🔍 Audit de sécurité
Audit complet noté de A+ à F couvrant les permissions à risque, les rôles administrateur mal attribués, les invitations sans expiration ni limite d'usage, les bots non vérifiés avec des droits sensibles, l'âge minimum des comptes autorisés et la présence de salons de logs
Configuration automatique de l'ensemble du serveur en une seule commande
Guide intégré des bonnes pratiques de sécurité
🚨 Protection anti-raid
Mode de protection renforcée activable/désactivable à la demande en cas d'afflux suspect de nouveaux membres
Filtrage par âge minimum de compte, resserré automatiquement en période de raid
Salon piège (honeypot) : un salon présenté comme normal qui sanctionne automatiquement quiconque y écrit, avec un compteur global du nombre de personnes piégées, cumulé sur tous les serveurs où le bot est ou a été présent
⚙️ Panel de configuration

Point d'entrée unique regroupant : gestion des webhooks, rôles staff, rôle Fondateur, liste blanche, liste de mots interdits, message et salon de bienvenue personnalisables, gestion des invitations, suivis de serveur et applications externes autorisées.

👮 Modération complète

Avertissements, mute/unmute, kick, ban/unban, notes internes sur un membre, historique détaillé par utilisateur, et système de rollback pour annuler une sanction.

🔎 Recherche et traçabilité

Recherche dans la configuration, l'historique de modération, les messages et les logs du serveur — utile pour retrouver rapidement une action passée sans avoir à tout parcourir manuellement.

🧩 Outils annexes

Détection des bots masqués/invisibles sur le serveur, resynchronisation des commandes slash en cas de souci d'affichage, et une commande d'aide qui oriente directement vers le panel.

Stockage des données

Au premier démarrage, un assistant en ligne de commande te demande de choisir :

Fichier local : simple, aucune dépendance externe, mais sans historique de modération détaillé ni index des membres
Serveur Discord dédié : les données sont réparties dans des salons d'un serveur Discord privé que tu contrôles, ce qui débloque l'historique complet et l'index des membres

Le token du bot est géré séparément, via un fichier .env, jamais mélangé aux données de configuration.

Prérequis
Python 3.x
La bibliothèque discord.py
Un token de bot Discord
Permissions recommandées sur le serveur : Administrateur (ou a minima Gérer les salons, Gérer les rôles, Envoyer des messages, Intégrer des liens)
