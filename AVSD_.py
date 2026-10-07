import json
import os
import sys


def _load_dotenv_manually(path: str = ".env") -> None:
    """Charge un fichier .env à la main (sans dépendance externe), très tôt
    dans l'exécution, avant même que python-dotenv soit potentiellement installé.
    Le .env ne sert QUE pour le token (DISCORD_TOKEN) — le bot n'y écrit jamais."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, path)

    if not os.path.isfile(env_path):
        print("=" * 62)
        print(f"⚠️  Fichier .env introuvable à cet emplacement précis :")
        print(f"    {env_path}")
        print("    Vérifie que le fichier est bien nommé '.env' (et pas '.env.txt' —")
        print("    Windows cache souvent les extensions) et qu'il est dans CE dossier :")
        print(f"    {script_dir}")
        try:
            candidates = [f for f in os.listdir(script_dir) if "env" in f.lower()]
            if candidates:
                print(f"    Fichiers contenant 'env' trouvés dans ce dossier : {candidates}")
        except OSError:
            pass
        print("=" * 62)
        return

    try:
        with open(env_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        print(f"✅ Fichier .env chargé depuis : {env_path}")
    except OSError as e:
        print(f"⚠️  Erreur lors de la lecture du .env : {e}")


_load_dotenv_manually()

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_FILE_PATH = os.path.join(_SCRIPT_DIR, "bot_config.json")


def _load_config() -> dict:
    """Lit bot_config.json (réglages du bot : mode de stockage, serveur de
    stockage...). Fichier séparé du .env, qui lui reste réservé au token."""
    if not os.path.isfile(_CONFIG_FILE_PATH):
        return {}
    try:
        with open(_CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"⚠️  Impossible de lire bot_config.json ({e}). Réglages ignorés pour cette exécution.")
        return {}


def _write_config_values(values: dict) -> None:
    """Ajoute/met à jour des réglages dans bot_config.json (jamais dans le .env)."""
    global _CONFIG
    config = _load_config()
    config.update(values)
    try:
        with open(_CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"⚠️  Impossible d'écrire dans bot_config.json ({e}). Les valeurs ne seront valables que pour cette exécution.")
    _CONFIG = config


_HONEYPOT_GLOBAL_COUNT_KEY = "HONEYPOT_GLOBAL_CATCH_COUNT"


def _get_honeypot_global_catch_count() -> int:
    try:
        return int(_CONFIG.get(_HONEYPOT_GLOBAL_COUNT_KEY, 0))
    except (TypeError, ValueError):
        return 0


def _increment_honeypot_global_catch_count() -> int:
    """Incrémente (de 1) et sauvegarde immédiatement le compteur global de
    personnes piégées, puis renvoie la nouvelle valeur."""
    new_count = _get_honeypot_global_catch_count() + 1
    _write_config_values({_HONEYPOT_GLOBAL_COUNT_KEY: new_count})
    return new_count


def _honeypot_counter_footer_text() -> str:
    """Texte affiché en pied (footer) de l'embed de l'image d'avertissement
    du salon piège — donc juste EN DESSOUS de l'image dans Discord. Compteur
    global (voir _get_honeypot_global_catch_count), identique sur tous les
    serveurs."""
    count = _get_honeypot_global_catch_count()
    return (
        f"📊 {count} personne(s) piégée(s) au total, sur tous les serveurs où ce bot est (ou a été)."
        if LANG == "fr"
        else f"📊 {count} people caught in total, across all servers this bot is (or has been) in."
    )


_CONFIG = _load_config()


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def bot_setup_wizard() -> None:
    """Assistant terminal lancé une seule fois (au tout premier démarrage) pour
    choisir où le bot stocke ses données : fichier local sur l'appareil, ou
    serveur Discord dédié. Ne fait rien si BOT_STORAGE_MODE est déjà réglé dans
    bot_config.json (donc ne redemande jamais rien aux lancements suivants).
    N'écrit jamais dans le .env, qui reste réservé au token."""
    if _CONFIG.get("BOT_STORAGE_MODE"):
        return

    print("=" * 62)
    print("🧭 PREMIÈRE CONFIGURATION — CHOIX DU STOCKAGE")
    print("=" * 62)
    print("Ce bot a besoin d'un endroit où garder ses données (réglages par")
    print("serveur, liste blanche, état anti-raid, historique de modération...).")
    print()
    print("  1) Stockage local — un fichier créé sur cet appareil. Simple, ne")
    print("     dépend d'aucun serveur Discord externe.")
    print("  2) Serveur Discord dédié — les données sont réparties dans des")
    print("     salons d'un serveur Discord privé que vous contrôlez. Nécessaire")
    print("     pour l'historique de modération détaillé et l'index des membres.")
    print()

    choice = ""
    while choice not in ("1", "2"):
        choice = _ask("Votre choix (1 ou 2) : ")

    if choice == "1":
        storage_path = os.path.join(_SCRIPT_DIR, "bot_storage.json")
        _write_config_values({"BOT_STORAGE_MODE": "file", "BOT_STORAGE_FILE": storage_path})
        print(f"✅ Stockage local choisi. Le fichier sera créé ici : {storage_path}")
        print("   (L'historique de modération détaillé, l'index des membres et les")
        print("   logs complets nécessitent le mode « serveur Discord » et resteront")
        print("   désactivés en mode fichier local — le reste du bot fonctionne normalement.)")
        print("=" * 62)
        return

    print()
    print("Mode « serveur Discord » choisi. Avant de continuer, préparez un")
    print("serveur qui servira UNIQUEMENT de base de données pour ce bot :")
    print("  • Le bot doit déjà être invité sur ce serveur.")
    print("  • Il doit y avoir la permission Administrateur (ou au minimum Gérer")
    print("    les salons, Gérer les rôles, Envoyer des messages, Intégrer des liens).")
    print("  • Ce serveur doit être entièrement privé — personne d'autre que")
    print("    vous/votre équipe ne doit pouvoir le rejoindre.")
    print("  • Il ne doit contenir AUCUN salon, à part éventuellement un seul")
    print("    salon réservé aux commandes internes du bot : tous les autres")
    print("    salons dont il a besoin, le bot les crée lui-même.")
    print()

    guild_id = ""
    while not guild_id.isdigit():
        guild_id = _ask("ID du serveur Discord de stockage (obligatoire) : ")
        if not guild_id.isdigit():
            print("   -> Invalide. Il faut l'ID numérique du serveur (clic droit sur le serveur")
            print("      dans Discord > Copier l'ID, avec le mode développeur activé).")

    values = {"BOT_STORAGE_MODE": "discord", "STORAGE_GUILD_ID": guild_id}

    _write_config_values(values)
    print("✅ Configuration enregistrée dans bot_config.json.")
    print("=" * 62)


bot_setup_wizard()


_LOG_LIMIT_CHOICE_FILE = os.path.join(_SCRIPT_DIR, "botconfig_log_oui_non.txt")
_LOG_LIMIT_ENV_FILE_NAME = os.environ.get("AUDIT_BOT_LOG_FILE", "audit_bot.log")


def log_limit_setup_wizard() -> bool:
    """Demande, à CHAQUE démarrage tant que le fichier _LOG_LIMIT_CHOICE_FILE
    n'existe pas, si on veut activer la limitation automatique de la taille du
    fichier de log (utile si le bot tourne sur beaucoup de serveurs : sans ça,
    le fichier de log peut grossir indéfiniment pour pas grand-chose).

    Comportement voulu (important, ne pas simplifier) :
    - Si le fichier existe déjà -> on utilise directement son contenu
      ("oui"/"non"), SANS RIEN DEMANDER. C'est la seule façon de ne plus être
      interrogé à chaque démarrage.
    - S'il n'existe pas -> on demande oui/non dans le terminal, et on
      enregistre la réponse dans ce fichier (créé spécialement pour ça, séparé
      de bot_config.json). Pour être reinterrogé un jour, il suffit de
      supprimer ce fichier.
    - Taper « annuler » répond « non » pour CETTE session uniquement, SANS
      RIEN ENREGISTRER : la question sera reposée au prochain démarrage."""
    if os.path.isfile(_LOG_LIMIT_CHOICE_FILE):
        try:
            with open(_LOG_LIMIT_CHOICE_FILE, "r", encoding="utf-8") as f:
                return f.read().strip().lower() == "oui"
        except OSError:
            pass  # lecture impossible -> on repose la question ci-dessous

    print("=" * 62)
    print("🧹 LIMITATION DU FICHIER DE LOG")
    print("=" * 62)
    print(f"Fichier de log actuel : {_LOG_LIMIT_ENV_FILE_NAME}")
    print("Sur un bot présent sur beaucoup de serveurs, ce fichier peut grossir")
    print("indéfiniment pour un intérêt limité une fois qu'il devient énorme.")
    print("Si tu actives cette option, le bot vérifiera toutes les minutes la")
    print("taille du fichier et le videra totalement dès qu'il dépasse 2 Mo.")
    print()
    print("  oui      -> activer la limitation automatique")
    print("  non      -> ne rien changer (comportement actuel)")
    print("  annuler  -> ne pas décider maintenant (question reposée au prochain démarrage)")
    print()

    answer = ""
    while answer not in ("oui", "non", "annuler"):
        answer = _ask("Ton choix (oui / non / annuler) : ").strip().lower()

    if answer == "annuler":
        print("ℹ️  Choix non enregistré — la question sera reposée au prochain démarrage.")
        print("=" * 62)
        return False

    try:
        with open(_LOG_LIMIT_CHOICE_FILE, "w", encoding="utf-8") as f:
            f.write(answer)
        print(f"✅ Choix « {answer} » enregistré dans : {_LOG_LIMIT_CHOICE_FILE}")
        print("   (Supprime ce fichier si tu veux qu'on te repose la question un jour.)")
    except OSError as e:
        print(f"⚠️  Impossible d'enregistrer le choix ({e}). Il sera reposé au prochain démarrage.")
    print("=" * 62)
    return answer == "oui"


LOG_FILE_LIMIT_ENABLED = log_limit_setup_wizard()
LOG_FILE_LIMIT_MAX_BYTES = 2_000_000  # 2 Mo : au-delà, le fichier est totalement vidé
LOG_FILE_LIMIT_CHECK_SECONDS = 60


def vpn_provider_setup_wizard() -> None:
    """Assistant terminal (une seule fois, comme bot_setup_wizard) pour choisir
    la détection VPN/proxy de la vérification par lien : gratuite (ip-api.com,
    par défaut, sans inscription), via une clé proxycheck.io (payant au-delà
    de son quota gratuit, un peu plus précis), ou via un compte Cloudflare
    (API Intelligence IP — nécessite un Account ID + un token API). La
    réponse est sauvegardée définitivement dans bot_config.json
    (VPN_PROVIDER_MODE) : plus jamais redemandée aux lancements suivants,
    comme le mode de stockage. Si aucun fournisseur n'est choisi, la
    vérification fonctionne quand même : le bot se débrouille tout seul avec
    la détection gratuite (ip-api.com + liste de fournisseurs VPN connus)."""
    if _CONFIG.get("VPN_PROVIDER_MODE"):
        return

    print("=" * 62)
    print("🌐 VÉRIFICATION PAR LIEN — DÉTECTION VPN/PROXY")
    print("=" * 62)
    print("Par défaut, la détection VPN/proxy pour la vérification par lien est")
    print("100% gratuite et sans inscription (ip-api.com + liste de fournisseurs")
    print("VPN connus) : si tu ne choisis aucun fournisseur ci-dessous, le bot")
    print("se débrouille tout seul avec cette détection gratuite.")
    print()
    print("Tu peux à la place sélectionner un fournisseur dédié, si tu as déjà")
    print("un compte chez l'un d'eux :")
    print("  1) Aucun — détection gratuite par défaut (ip-api.com)")
    print("  2) proxycheck.io (clé API) — un peu plus précis")
    print("  3) Cloudflare (API Intelligence IP — Account ID + token API)")
    print()

    choice = ""
    while choice not in ("1", "2", "3"):
        choice = _ask("Ton choix (1, 2 ou 3) : ")

    if choice == "1":
        _write_config_values({"VPN_PROVIDER_MODE": "free"})
        print("✅ Détection gratuite (ip-api.com) choisie et fixée définitivement.")
        print("   (Ce choix ne sera plus jamais redemandé.)")
        print("=" * 62)
        return

    if choice == "2":
        key = ""
        while not key:
            key = _ask("Clé API proxycheck.io : ")
        _write_config_values({"VPN_PROVIDER_MODE": "paid", "PROXYCHECK_API_KEY": key})
        print("✅ Fournisseur payant (proxycheck.io) enregistré définitivement dans bot_config.json.")
        print("=" * 62)
        return

    account_id = ""
    while not account_id:
        account_id = _ask("Cloudflare Account ID : ")
    token = ""
    while not token:
        token = _ask("Cloudflare API Token (permission Intel: Read) : ")
    _write_config_values({
        "VPN_PROVIDER_MODE": "cloudflare",
        "CLOUDFLARE_ACCOUNT_ID": account_id,
        "CLOUDFLARE_API_TOKEN": token,
    })
    print("✅ Fournisseur Cloudflare enregistré définitivement dans bot_config.json.")
    print("=" * 62)


vpn_provider_setup_wizard()

TOKEN = os.environ.get("DISCORD_TOKEN", "")


def _config_int(name: str):
    """Lit un réglage entier optionnel depuis bot_config.json (0/vide = non défini)."""
    raw = str(_CONFIG.get(name, "")).strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value or None


STORAGE_GUILD_ID = _config_int("STORAGE_GUILD_ID")

MOD_REQUEST_COOLDOWN_SECONDS = 10

AUDIT_DB_GUILD_ID = STORAGE_GUILD_ID
AUDIT_LANG_VALUE = os.environ.get("BOT_LANG", "fr")

STORAGE_MODE = _CONFIG.get("BOT_STORAGE_MODE", "file")
STORAGE_FILE_PATH = _CONFIG.get(
    "BOT_STORAGE_FILE",
    os.path.join(_SCRIPT_DIR, "bot_storage.json"),
)

VERIFY_WEB_PORT = _config_int("VERIFY_WEB_PORT") or 8080
VERIFY_PUBLIC_BASE_URL = str(_CONFIG.get("VERIFY_PUBLIC_BASE_URL", "")).strip().rstrip("/")
VPN_PROVIDER_MODE = _CONFIG.get("VPN_PROVIDER_MODE", "free")
PROXYCHECK_API_KEY = str(_CONFIG.get("PROXYCHECK_API_KEY", "")).strip() if VPN_PROVIDER_MODE == "paid" else ""
CLOUDFLARE_ACCOUNT_ID = str(_CONFIG.get("CLOUDFLARE_ACCOUNT_ID", "")).strip() if VPN_PROVIDER_MODE == "cloudflare" else ""
CLOUDFLARE_API_TOKEN = str(_CONFIG.get("CLOUDFLARE_API_TOKEN", "")).strip() if VPN_PROVIDER_MODE == "cloudflare" else ""

if TOKEN in ("", "COLLE_TON_TOKEN_ICI"):
    print("❌ Aucun token valide renseigné. Mets ton token Discord dans le fichier .env "
          "(variable DISCORD_TOKEN), à côté de ce script.")
    sys.exit(1)

import importlib
import subprocess

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

REQUIRED_PACKAGES = [
    ("discord", "discord.py", "API Discord (connexion et fonctionnement du bot)"),
    ("aiohttp", "aiohttp", "requêtes HTTP (téléchargement d'images, etc.)"),
]

OPTIONAL_PACKAGES = [
    ("dotenv", "python-dotenv", "chargement du fichier .env (token / config)"),
    ("PIL", "Pillow", "traitement d'images (CAPTCHA de vérification, avertissement du salon piège, carte de bienvenue)"),
]


def _is_installed(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def _pip_install(pip_name: str) -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", pip_name],
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def _check_and_install_dependencies():
    missing_required = [pkg for pkg in REQUIRED_PACKAGES if not _is_installed(pkg[0])]
    missing_optional = [pkg for pkg in OPTIONAL_PACKAGES if not _is_installed(pkg[0])]
    missing = missing_required + missing_optional

    if not missing:
        return

    print("=" * 62)
    print("📦 Paquets Python manquants détectés :")
    print("=" * 62)
    for module_name, pip_name, description in missing_required:
        print(f"  - {pip_name:<15} [REQUIS]    — {description}")
    for module_name, pip_name, description in missing_optional:
        print(f"  - {pip_name:<15} [optionnel] — {description}")
    print("=" * 62)
    if missing_required:
        print("⚠️  Sans les paquets REQUIS, le bot ne peut pas démarrer du tout.")
    print("🤖 Installation automatique de tous les paquets manquants (requis + optionnels)...")

    print()
    failed_modules = set()
    for module_name, pip_name, description in missing:
        print(f"⏳ Installation de {pip_name}...")
        if _pip_install(pip_name):
            print(f"✅ {pip_name} installé.")
        else:
            print(f"❌ Échec de l'installation de {pip_name}.")
            failed_modules.add(module_name)

    if failed_modules:
        print()
        print("⚠️  Certains paquets n'ont pas pu être installés automatiquement — installe-les à la main.")
        required_failed = [p for m, p, _ in missing_required if m in failed_modules]
        if required_failed:
            print("❌ Un paquet REQUIS n'a pas pu être installé — arrêt du bot.")
            print(f"   {sys.executable} -m pip install " + " ".join(required_failed))
            sys.exit(1)
        optional_failed = [p for m, p, _ in missing_optional if m in failed_modules]
        if optional_failed:
            print("   Paquets optionnels non installés (fonctionnalités concernées désactivées) :")
            print(f"   {sys.executable} -m pip install " + " ".join(optional_failed))

    print()
    print("✅ Vérification des dépendances terminée.")
    print("=" * 62)


_check_and_install_dependencies()

import asyncio
import io
import json
import logging
import mimetypes
import os
import re
import random
import secrets
import threading
import time
import typing
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone, date as date_cls
from zoneinfo import ZoneInfo

import aiohttp
import discord
from discord.ext import commands

PARIS_TZ = ZoneInfo("Europe/Paris")


def utc_time_str() -> str:
    return discord.utils.utcnow().strftime("%H:%M:%S UTC")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


RUNTIME_TOGGLES = {
    "antinuke": True,
    "automod": True,
    "honeypot": True,
    "antispam": True,
}

RUNTIME_TOGGLE_LABELS = {
    "antinuke": "Anti-nuke (mass ban/kick/salons/rôles)",
    "automod": "Auto-modération de contenu (phishing, arnaques, mentions, majuscules)",
    "honeypot": "Salon piège (sanction de quiconque y écrit)",
    "antispam": "Anti-spam (messages répétés)",
}

MODULE_KEYS = ("antinuke", "automod", "honeypot", "antispam", "messagelog", "serverlog", "verification", "wordfilter")

MODULE_SETTING_KEY = {key: f"module_{key}_enabled" for key in MODULE_KEYS}


def _module_enabled(guild_id: int, key: str) -> bool:
    if not RUNTIME_TOGGLES.get(key, True):
        return False
    return bool(_get_setting(guild_id, MODULE_SETTING_KEY[key]))


def _print_toggle_status():
    print("=" * 62)
    print("📋 État actuel des modules (console terminal)")
    print("=" * 62)
    for key, label in RUNTIME_TOGGLE_LABELS.items():
        state = "ACTIVÉ  ✅" if RUNTIME_TOGGLES[key] else "DÉSACTIVÉ ❌"
        print(f"  {key:<12} {state:<12} — {label}")
    print("=" * 62)


def _print_terminal_help():
    print("Commandes disponibles :")
    print("  <module> on|off   — active/désactive un module (ex: 'antispam off')")
    print("  <module>          — bascule l'état du module (ex: 'antispam' → inverse on/off)")
    print("  status            — affiche l'état de tous les modules")
    print("  help              — affiche cette aide")
    print("  Modules : " + ", ".join(RUNTIME_TOGGLES.keys()))


def _terminal_console_loop():
    print()
    print("💻 Console de contrôle du bot — tape 'help' pour la liste des commandes.")
    _print_toggle_status()
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue

        parts = line.lower().split()
        cmd = parts[0]

        if cmd in ("help", "aide", "?"):
            _print_terminal_help()
            continue
        if cmd in ("status", "etat", "état"):
            _print_toggle_status()
            continue
        if cmd in ("quit", "exit"):
            print("(console fermée ; le bot continue de tourner normalement)")
            break

        if cmd in RUNTIME_TOGGLES and len(parts) >= 2 and parts[1] in ("on", "off", "1", "0"):
            new_state = parts[1] in ("on", "1")
            RUNTIME_TOGGLES[cmd] = new_state
            label = RUNTIME_TOGGLE_LABELS[cmd]
            state_txt = "ACTIVÉ ✅" if new_state else "DÉSACTIVÉ ❌"
            print(f"{state_txt} — {label}")
            log.warning(f"[Console terminal] {label} -> {'activé' if new_state else 'désactivé'}.")
        elif cmd in RUNTIME_TOGGLES and len(parts) == 1:
            new_state = not RUNTIME_TOGGLES[cmd]
            RUNTIME_TOGGLES[cmd] = new_state
            label = RUNTIME_TOGGLE_LABELS[cmd]
            state_txt = "ACTIVÉ ✅" if new_state else "DÉSACTIVÉ ❌"
            print(f"{state_txt} — {label}")
            log.warning(f"[Console terminal] {label} -> {'activé' if new_state else 'désactivé'} (toggle).")
        else:
            print("❓ Commande non reconnue. Tape 'help' pour la liste des commandes.")


MAX_ADMIN_ROLES = 2

MAX_ADMIN_MEMBERS = 5

MAX_WEBHOOKS = 10

MASS_BAN_THRESHOLD = 2
MASS_KICK_THRESHOLD = 2
MASS_CHANNEL_DELETE_THRESHOLD = 1


AUTOMOD_TIMEOUT_MINUTES = 10

MAX_WARNINGS_BEFORE_SANCTION = 3

WARNING_ROLE_NAMES = (
    ["Avertissement 1", "Avertissement 2", "Avertissement 3"] if AUDIT_LANG_VALUE.lower() == "fr"
    else ["Warning 1", "Warning 2", "Warning 3"]
)

WARN_LIMIT_MESSAGE = (
    "❌ This member already has too many warnings — I'd recommend giving them "
    "a real sanction instead."
)

RAID_NEW_ACCOUNT_MAX_AGE_DAYS = 30
RAID_NEW_ACCOUNT_KICK_WINDOW_HOURS = 2

RAID_DM_START_EN = (
    "🚨 **{guild}** has activated its anti-raid protocol. Some roles, invites, webhooks "
    "and voice connections may be temporarily restricted or reset as a precaution. "
    "This isn't about you personally — sit tight, it'll be lifted shortly."
)
RAID_DM_END_EN = (
    "✅ The anti-raid protocol on **{guild}** has ended. Everything is back to normal."
)
RAID_DM_NEW_ACCOUNT_KICK_EN = (
    "🚨 **{guild}** is currently on red alert (anti-raid protocol in progress). Accounts "
    "younger than {days} days can't join right now for security reasons. Please try "
    "rejoining in about 2 hours."
)


async def _send_raid_dm_broadcast(guild: discord.Guild, message: str, context_label: str) -> None:
    failures = 0
    for guild_member in guild.members:
        if guild_member.bot:
            continue
        try:
            await guild_member.send(message)
        except Exception:
            failures += 1
        await asyncio.sleep(0.2)
    log.info(f"MP {context_label} sur {guild.name} : {failures} échec(s)/MP fermé(s).")


async def _keep_invites_paused(guild: discord.Guild) -> None:
    while True:
        await asyncio.sleep(20 * 3600)
        raid_state = _raid_state.get(guild.id)
        if not raid_state or not raid_state.get("active"):
            return
        try:
            await guild.edit(
                invites_disabled_until=discord.utils.utcnow() + timedelta(hours=24),
                reason="Protocole anti-raid toujours actif (renouvellement de la suspension des invitations)",
            )
        except Exception:
            log.exception(f"Impossible de renouveler la suspension des invitations sur {guild.name}.")

INVITE_REGEX = re.compile(
    r"(?:discord\.gg|discord(?:app)?\.com/invite)/([A-Za-z0-9-]+)", re.IGNORECASE
)

PHISHING_DOMAIN_PATTERNS = [
    r"discocl", r"discrod", r"dlscord", r"discord-nltro", r"discordnitro",
    r"discord-gift", r"discord-airdrop", r"steamcommunity-?gift", r"steamcomunity",
    r"steam-?community\.[a-z]{2,}\.[a-z]{2,}", r"xn--discord",
]
PHISHING_DOMAIN_REGEX = re.compile("|".join(PHISHING_DOMAIN_PATTERNS), re.IGNORECASE)

IP_URL_REGEX = re.compile(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)

SCAM_GIVEAWAY_PATTERNS = [
    r"withdraw(?:al)?\s+(?:success|of\s+\$?\d)", r"claim your (?:reward|bonus|giveaway)",
    r"enter the (?:special )?promo\s*code", r"registering.{0,20}(?:bonus|giveaway)",
    r"will be deleted (?:in|after) (?:an? |1 ?)hour", r"crypto casino",
    r"launch(?:ing)? (?:of )?my own crypto", r"giving away \$?\d[\d,.]*\s*(?:to everyone|usdt|dollars)?",
]
SCAM_GIVEAWAY_REGEX = re.compile("|".join(SCAM_GIVEAWAY_PATTERNS), re.IGNORECASE)

try:
    from PIL import Image as _WelcomeImage, ImageDraw as _WelcomeImageDraw, ImageFont as _WelcomeImageFont
    import io as _welcome_io
    _WELCOME_CARD_AVAILABLE = True
except ImportError:
    _WELCOME_CARD_AVAILABLE = False

MASS_MENTION_THRESHOLD = 5

CAPS_MIN_LENGTH = 12
CAPS_RATIO_THRESHOLD = 0.7


SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

SEVERITY_META = {
    "CRITICAL": {"emoji": "🔴", "color": 0xE01E1E, "fr": "Critique", "en": "Critical"},
    "HIGH":     {"emoji": "🟠", "color": 0xFF8C00, "fr": "Élevée",   "en": "High"},
    "MEDIUM":   {"emoji": "🟡", "color": 0xFFD700, "fr": "Moyenne",  "en": "Medium"},
    "LOW":      {"emoji": "🔵", "color": 0x3498DB, "fr": "Faible",   "en": "Low"},
    "INFO":     {"emoji": "⚪", "color": 0x95A5A6, "fr": "Info",     "en": "Info"},
}

DANGEROUS_EVERYONE_PERMS = {
    "administrator": {
        "severity": "CRITICAL",
        "fr": {
            "label": "Administrateur accordé à @everyone",
            "risk": "N'importe quel membre (même un compte piraté ou un faux compte créé le jour même) a un accès total : suppression de salons, bannissements, modification du serveur, création de bots malveillants, etc.",
            "fix": "Retirez immédiatement la permission Administrateur du rôle @everyone. Réservez-la à un rôle de confiance restreint (staff fondateur uniquement).",
        },
        "en": {
            "label": "Administrator granted to @everyone",
            "risk": "Any member (even a compromised or brand-new account) has full control: deleting channels, banning members, editing the server, adding malicious bots, etc.",
            "fix": "Immediately remove the Administrator permission from @everyone. Restrict it to a small trusted role (founders/core staff only).",
        },
    },
    "manage_guild": {
        "severity": "CRITICAL",
        "fr": {
            "label": "Gérer le serveur accordé à @everyone",
            "risk": "Tout membre peut changer le nom, la région, le niveau de vérification, activer/désactiver des fonctionnalités, ou créer des invitations vanity — une prise de contrôle presque totale.",
            "fix": "Retirez 'Gérer le serveur' du rôle @everyone et ne l'attribuez qu'aux administrateurs.",
        },
        "en": {
            "label": "Manage Server granted to @everyone",
            "risk": "Any member can rename the server, change its region/verification level, toggle features, or set a vanity URL — near-total takeover.",
            "fix": "Remove 'Manage Server' from @everyone and keep it for admins only.",
        },
    },
    "manage_roles": {
        "severity": "CRITICAL",
        "fr": {
            "label": "Gérer les rôles accordé à @everyone",
            "risk": "Un membre peut se créer/modifier un rôle avec plus de droits que le sien (jusqu'à la limite de hiérarchie du bot le plus haut placé), et ainsi s'auto-promouvoir administrateur.",
            "fix": "Retirez 'Gérer les rôles' de @everyone. Ne l'accordez qu'aux rôles modérateurs/admins de confiance.",
        },
        "en": {
            "label": "Manage Roles granted to @everyone",
            "risk": "A member can create/edit roles up to the hierarchy limit and effectively self-promote to admin-level access.",
            "fix": "Remove 'Manage Roles' from @everyone. Only grant it to trusted moderator/admin roles.",
        },
    },
    "manage_channels": {
        "severity": "HIGH",
        "fr": {
            "label": "Gérer les salons accordé à @everyone",
            "risk": "Un membre peut supprimer tous les salons, créer des salons de spam/phishing, ou modifier les permissions de salons existants.",
            "fix": "Retirez 'Gérer les salons' de @everyone.",
        },
        "en": {
            "label": "Manage Channels granted to @everyone",
            "risk": "A member can delete all channels, create spam/phishing channels, or alter existing channel permissions.",
            "fix": "Remove 'Manage Channels' from @everyone.",
        },
    },
    "manage_webhooks": {
        "severity": "HIGH",
        "fr": {
            "label": "Gérer les webhooks accordé à @everyone",
            "risk": "Un membre peut créer un webhook et l'utiliser pour usurper l'identité d'utilisateurs/annonces officielles (phishing, faux messages 'staff'), ou exfiltrer des messages en continu.",
            "fix": "Retirez 'Gérer les webhooks' de @everyone. Auditez régulièrement les webhooks existants.",
        },
        "en": {
            "label": "Manage Webhooks granted to @everyone",
            "risk": "A member can create a webhook to impersonate staff/official announcements (phishing) or continuously exfiltrate channel messages.",
            "fix": "Remove 'Manage Webhooks' from @everyone. Periodically audit existing webhooks.",
        },
    },
    "kick_members": {
        "severity": "HIGH",
        "fr": {
            "label": "Expulser des membres accordé à @everyone",
            "risk": "N'importe qui peut vider le serveur de ses membres en les expulsant un par un (raid).",
            "fix": "Retirez 'Expulser des membres' de @everyone, réservez-la aux modérateurs.",
        },
        "en": {
            "label": "Kick Members granted to @everyone",
            "risk": "Anyone can empty the server by kicking members one by one (raid).",
            "fix": "Remove 'Kick Members' from @everyone, keep it for moderators only.",
        },
    },
    "ban_members": {
        "severity": "CRITICAL",
        "fr": {
            "label": "Bannir des membres accordé à @everyone",
            "risk": "N'importe qui peut bannir massivement tous les membres, y compris les fondateurs, en quelques secondes.",
            "fix": "Retirez 'Bannir des membres' de @everyone, réservez-la aux modérateurs de confiance.",
        },
        "en": {
            "label": "Ban Members granted to @everyone",
            "risk": "Anyone can mass-ban every member, including founders, within seconds.",
            "fix": "Remove 'Ban Members' from @everyone, keep it for trusted moderators only.",
        },
    },
    "manage_nicknames": {
        "severity": "LOW",
        "fr": {
            "label": "Gérer les pseudos accordé à @everyone",
            "risk": "Un membre peut renommer les autres de façon abusive ou usurper des pseudos (imitation d'un staff).",
            "fix": "Réservez cette permission aux modérateurs.",
        },
        "en": {
            "label": "Manage Nicknames granted to @everyone",
            "risk": "A member can rename others abusively or impersonate staff via nickname.",
            "fix": "Keep this permission for moderators only.",
        },
    },
    "manage_emojis_and_stickers": {
        "severity": "LOW",
        "fr": {
            "label": "Gérer les emojis/stickers accordé à @everyone",
            "risk": "Ajout d'emojis/stickers inappropriés ou usage pour saturer le serveur (limite d'emojis atteinte).",
            "fix": "Réservez cette permission à un rôle de confiance.",
        },
        "en": {
            "label": "Manage Emojis/Stickers granted to @everyone",
            "risk": "Adding inappropriate emojis/stickers or exhausting the server's emoji slot limit.",
            "fix": "Keep this permission for a trusted role only.",
        },
    },
    "mention_everyone": {
        "severity": "MEDIUM",
        "fr": {
            "label": "Mentionner @everyone/@here accordé à @everyone",
            "risk": "Utilisé pour du spam de masse, harcèlement, ou pour propager un lien de phishing à tout le serveur d'un coup.",
            "fix": "Retirez 'Mentionner tout le monde' de @everyone ; accordez-la seulement aux modérateurs/annonces officielles.",
        },
        "en": {
            "label": "Mention @everyone/@here granted to @everyone",
            "risk": "Used for mass spam, harassment, or blasting a phishing link to the entire server at once.",
            "fix": "Remove 'Mention Everyone' from @everyone; grant it only to moderators/official announcement roles.",
        },
    },
    "manage_messages": {
        "severity": "MEDIUM",
        "fr": {
            "label": "Gérer les messages accordé à @everyone",
            "risk": "Un membre peut supprimer les messages d'autrui pour masquer des preuves (arnaques, harcèlement) ou saboter des discussions.",
            "fix": "Réservez 'Gérer les messages' aux modérateurs.",
        },
        "en": {
            "label": "Manage Messages granted to @everyone",
            "risk": "A member can delete others' messages to hide evidence (scams, harassment) or sabotage conversations.",
            "fix": "Keep 'Manage Messages' for moderators only.",
        },
    },
    "manage_threads": {
        "severity": "LOW",
        "fr": {
            "label": "Gérer les fils de discussion accordé à @everyone",
            "risk": "Fermeture/suppression abusive de fils créés par d'autres membres.",
            "fix": "Réservez cette permission aux modérateurs.",
        },
        "en": {
            "label": "Manage Threads granted to @everyone",
            "risk": "Abusive closing/deleting of threads created by other members.",
            "fix": "Keep this permission for moderators only.",
        },
    },
    "moderate_members": {
        "severity": "HIGH",
        "fr": {
            "label": "Mettre en sourdine (timeout) accordé à @everyone",
            "risk": "N'importe qui peut réduire au silence tous les autres membres, y compris les modérateurs, paralysant la modération.",
            "fix": "Retirez cette permission de @everyone.",
        },
        "en": {
            "label": "Timeout Members granted to @everyone",
            "risk": "Anyone can silence every other member, including moderators, paralyzing moderation.",
            "fix": "Remove this permission from @everyone.",
        },
    },
    "create_instant_invite": {
        "severity": "LOW",
        "fr": {
            "label": "Créer une invitation accordé à @everyone",
            "risk": "Des invitations peuvent être générées en masse pour faire venir des faux comptes ou revendre l'accès au serveur.",
            "fix": "Si non nécessaire, réservez la création d'invitations aux modérateurs.",
        },
        "en": {
            "label": "Create Invite granted to @everyone",
            "risk": "Invites can be mass-generated to bring in fake accounts or resell server access.",
            "fix": "If not needed, restrict invite creation to moderators.",
        },
    },
}

ADMIN_ROLE_FINDING = {
    "severity": "HIGH",
    "fr": {
        "label": "Rôle « {role} » possède Administrateur",
        "risk": "Tout membre ayant ce rôle a un contrôle total du serveur. Si ce rôle est distribué largement ou automatiquement (bot de niveaux, auto-rôle), c'est une porte dérobée de fait.",
        "fix": "Vérifiez qui possède ce rôle et pourquoi. Limitez Administrateur au strict minimum de personnes de confiance ; utilisez des permissions détaillées plutôt qu'Administrateur pour les autres rôles.",
    },
    "en": {
        "label": "Role \u201c{role}\u201d has Administrator",
        "risk": "Any member with this role has full server control. If the role is handed out broadly or automatically (leveling bot, self-assign), it's effectively a backdoor.",
        "fix": "Check who holds this role and why. Limit Administrator to the strict minimum of trusted people; use granular permissions instead of Administrator for other roles.",
    },
}

TOO_MANY_ADMIN_ROLES_FINDING = {
    "severity": "HIGH",
    "fr": {
        "label": "Trop de rôles possèdent Administrateur ({count})",
        "risk": "Plus il y a de rôles distincts avec Administrateur, plus la surface d'attaque est grande : chaque rôle est une cible potentielle (compromission d'un membre l'ayant, mauvaise attribution, auto-rôle mal configuré).",
        "fix": "Regroupez les accès admin sur un minimum de rôles (idéalement un seul), et remplacez Administrateur par des permissions détaillées pour les rôles qui n'en ont pas réellement besoin.",
    },
    "en": {
        "label": "Too many roles have Administrator ({count})",
        "risk": "The more distinct roles hold Administrator, the larger the attack surface: each role is a potential target (a compromised holder, a misconfigured assignment, a broken self-assign setup).",
        "fix": "Consolidate admin access onto as few roles as possible (ideally one), and replace Administrator with granular permissions for roles that don't truly need it.",
    },
}

TOO_MANY_ADMIN_MEMBERS_FINDING = {
    "severity": "HIGH",
    "fr": {
        "label": "Trop de membres ont un accès Administrateur ({count})",
        "risk": "Chaque personne (ou bot) avec Administrateur est un point de compromission possible : mot de passe faible, phishing, appareil infecté, token de bot qui fuite. Plus ce nombre est élevé, plus le risque global augmente.",
        "fix": "Passez en revue la liste des membres/bots administrateurs et retirez ce droit à ceux qui n'en ont pas un besoin réel et permanent. Envisagez des permissions plus fines pour la majorité d'entre eux.",
    },
    "en": {
        "label": "Too many members have Administrator access ({count})",
        "risk": "Each person (or bot) with Administrator is a possible point of compromise: weak password, phishing, infected device, leaked bot token. The higher this number, the higher the overall risk.",
        "fix": "Review the list of admin members/bots and remove the right from anyone who doesn't have a genuine, ongoing need for it. Consider more granular permissions for most of them.",
    },
}

CHANNEL_OVERWRITE_FINDING = {
    "severity": "HIGH",
    "fr": {
        "label": "Salon « {channel} » : @everyone a « {perm} »",
        "risk": "Cette permission dangereuse a été explicitement accordée à @everyone sur ce salon précis, contournant les restrictions globales du serveur.",
        "fix": "Ouvrez les permissions du salon et retirez cette autorisation pour @everyone (repassez-la en 'Neutre' ou 'Refusé').",
    },
    "en": {
        "label": "Channel \u201c{channel}\u201d: @everyone has \u201c{perm}\u201d",
        "risk": "This dangerous permission was explicitly granted to @everyone on this specific channel, bypassing the server-wide restrictions.",
        "fix": "Open the channel permissions and remove this grant for @everyone (set it back to Neutral or Deny).",
    },
}

GUILD_SETTINGS_FINDINGS = {
    "verification_low": {
        "severity": "MEDIUM",
        "fr": {
            "label": "Niveau de vérification faible ou nul",
            "risk": "Des comptes tout juste créés ou sans email/téléphone vérifié peuvent rejoindre et agir immédiatement : facilite les raids et le phishing.",
            "fix": "Passez le niveau de vérification à 'Élevé' (ou 'Moyen' minimum) dans Paramètres du serveur > Modération.",
        },
        "en": {
            "label": "Low or no verification level",
            "risk": "Brand-new accounts or accounts without a verified email/phone can join and act immediately: makes raids and phishing easier.",
            "fix": "Raise the verification level to 'High' (or at least 'Medium') in Server Settings > Moderation.",
        },
    },
    "mfa_disabled": {
        "severity": "MEDIUM",
        "fr": {
            "label": "Authentification à deux facteurs (2FA) non exigée pour la modération",
            "risk": "Si le compte d'un modérateur/admin est piraté (mot de passe seul), l'attaquant peut immédiatement utiliser tous les pouvoirs de modération.",
            "fix": "Activez 'Exiger la vérification en 2 étapes' dans Paramètres du serveur > Modération, pour forcer tous les modérateurs/admins à activer la 2FA.",
        },
        "en": {
            "label": "Two-factor authentication (2FA) not required for moderation",
            "risk": "If a moderator/admin account is compromised (password only), the attacker can immediately use all moderation powers.",
            "fix": "Enable 'Require 2FA for moderation' in Server Settings > Moderation to force all mods/admins to enable 2FA.",
        },
    },
    "content_filter_disabled": {
        "severity": "LOW",
        "fr": {
            "label": "Filtre de contenu explicite désactivé",
            "risk": "Des images à caractère explicite peuvent être postées sans filtrage automatique, y compris par des nouveaux membres.",
            "fix": "Activez le filtrage des médias explicites pour tous les membres dans Paramètres du serveur > Modération.",
        },
        "en": {
            "label": "Explicit content filter disabled",
            "risk": "Explicit images can be posted without automatic scanning, including by brand-new members.",
            "fix": "Enable explicit media scanning for all members in Server Settings > Moderation.",
        },
    },
    "open_invite": {
        "severity": "MEDIUM",
        "fr": {
            "label": "Invitation permanente sans expiration ni limite d'utilisations",
            "risk": "Ce lien, s'il fuite (capture d'écran, revente, indexation par un site tiers), permet à un nombre illimité de personnes de rejoindre indéfiniment.",
            "fix": "Recréez les invitations importantes avec une expiration et/ou un nombre d'utilisations limité, et supprimez les anciennes invitations permanentes inutiles.",
        },
        "en": {
            "label": "Permanent invite with no expiration or use limit",
            "risk": "If this link leaks (screenshot, resale, third-party indexing), unlimited people can join forever.",
            "fix": "Recreate important invites with an expiration and/or a max-use limit, and delete old unused permanent invites.",
        },
    },
}

BOT_ADMIN_FINDING = {
    "severity": "INFO",
    "fr": {
        "label": "Le bot d'audit a lui-même la permission Administrateur",
        "risk": "Ce n'est pas nécessaire au fonctionnement du bot : si son token venait à fuiter, l'attaquant aurait un contrôle total au lieu d'un contrôle limité.",
        "fix": "Retirez Administrateur au rôle du bot et donnez-lui uniquement : Voir les salons, Gérer les salons, Gérer les rôles (en dessous de la hiérarchie admin), Envoyer des messages, Intégrer des liens, Voir l'historique.",
    },
    "en": {
        "label": "The audit bot itself has the Administrator permission",
        "risk": "This isn't required for the bot to function: if its token ever leaks, the attacker gets full control instead of a limited one.",
        "fix": "Remove Administrator from the bot's role and grant only: View Channels, Manage Channels, Manage Roles (below the admin hierarchy), Send Messages, Embed Links, Read Message History.",
    },
}


BOT_ADMIN_MEMBER_FINDING = {
    "severity": "CRITICAL",
    "fr": {
        "label": "Le bot « {bot} » possède Administrateur (non vérifié par Discord)",
        "risk": "Ce bot (et donc quiconque contrôle son token/son propriétaire) a un accès total au serveur, et Discord n'a pas validé son éditeur. Si ce bot est piraté, mal codé, ou revendu/abandonné par son créateur, c'est une porte dérobée complète et personne ne garantit son sérieux.",
        "fix": "Retirez Administrateur à ce bot et ne lui accordez que les permissions strictement nécessaires à ses fonctions (voir sa documentation). Vu qu'il n'est pas vérifié, envisagez de le remplacer par une alternative vérifiée.",
    },
    "en": {
        "label": "Bot \u201c{bot}\u201d has Administrator (not Discord-verified)",
        "risk": "This bot (and whoever controls its token/owner) has full server access, and Discord has not validated its publisher. If the bot is hacked, poorly coded, or resold/abandoned by its creator, that's a complete backdoor with no vetting behind it.",
        "fix": "Remove Administrator from this bot and only grant the permissions strictly required for its features (check its documentation). Since it's unverified, consider replacing it with a verified alternative.",
    },
}

BOT_ADMIN_MEMBER_VERIFIED_FINDING = {
    "severity": "HIGH",
    "fr": {
        "label": "Le bot vérifié « {bot} » possède Administrateur",
        "risk": "Ce bot est vérifié par Discord, ce qui réduit le risque mais ne l'élimine pas : si son token fuite (piratage chez l'éditeur, employé malveillant), l'attaquant a un accès total au serveur au lieu d'un accès limité à ses fonctions habituelles.",
        "fix": "Consultez la documentation du bot pour connaître les permissions réellement nécessaires (la plupart des bots de modération/utilitaires n'ont pas besoin d'Administrateur) et remplacez Administrateur par ces permissions précises.",
    },
    "en": {
        "label": "Verified bot \u201c{bot}\u201d has Administrator",
        "risk": "This bot is Discord-verified, which lowers the risk but doesn't remove it: if its token leaks (a breach at the publisher, a malicious employee), the attacker gets full server access instead of access limited to the bot's normal features.",
        "fix": "Check the bot's documentation for the permissions it actually needs (most moderation/utility bots don't require Administrator) and replace Administrator with those specific permissions.",
    },
}

UNVERIFIED_BOT_DANGEROUS_FINDING = {
    "severity": "HIGH",
    "fr": {
        "label": "Bot non vérifié par Discord avec des permissions sensibles : « {bot} »",
        "risk": "Discord n'a pas validé ce bot (pas de badge « Vérifié »). Un bot non vérifié peut changer de code à tout moment sans contrôle, et s'il a des permissions comme Gérer les rôles/salons/webhooks, Bannir, Mentionner tout le monde, il peut servir à prendre le contrôle du serveur ou à spammer/phisher tous les membres. Vérifiez aussi que le lien de sa politique de confidentialité et ses conditions d'utilisation (visibles sur sa fiche dans l'onglet Membres > clic sur le bot, ou sur le site de son créateur) sont valides et correspondent à un éditeur identifiable.",
        "fix": "Vérifiez qui a ajouté ce bot et pourquoi. Si son utilité est incertaine ou sa politique de confidentialité absente/invalide, retirez-le. Sinon, réduisez ses permissions au strict minimum.",
    },
    "en": {
        "label": "Discord-unverified bot with sensitive permissions: \u201c{bot}\u201d",
        "risk": "Discord has not validated this bot (no 'Verified' badge). An unverified bot's code can change at any time with no oversight, and if it holds permissions like Manage Roles/Channels/Webhooks, Ban, or Mention Everyone, it could be used to take over the server or spam/phish every member. Also check that its privacy policy and terms of service links (visible on its profile under Members, or on its creator's site) are valid and point to an identifiable publisher.",
        "fix": "Check who added this bot and why. If its purpose is unclear or its privacy policy is missing/invalid, remove it. Otherwise, reduce its permissions to the strict minimum.",
    },
}


WEBHOOK_UNKNOWN_OWNER_FINDING = {
    "severity": "MEDIUM",
    "fr": {
        "label": "Webhook sans propriétaire identifiable dans « {channel} » : « {name} »",
        "risk": "Ce webhook n'a pas de créateur clairement identifié (compte supprimé, ancienne intégration...). Si son URL a fuité ou est encore utilisée par un service oublié, n'importe qui la possédant peut poster des messages qui semblent officiels dans ce salon (phishing, fausses annonces).",
        "fix": "Ouvrez les paramètres du salon > Intégrations > Webhooks, identifiez à quoi sert ce webhook. S'il est inutilisé ou inconnu, supprimez-le et régénérez-en un nouveau si nécessaire.",
    },
    "en": {
        "label": "Webhook with no identifiable owner in \u201c{channel}\u201d: \u201c{name}\u201d",
        "risk": "This webhook has no clearly identified creator (deleted account, old integration...). If its URL has leaked or is still used by a forgotten service, anyone holding it can post messages that look official in this channel (phishing, fake announcements).",
        "fix": "Open the channel's Integrations > Webhooks settings and identify what this webhook is for. If unused or unknown, delete it and regenerate a new one if needed.",
    },
}

WEBHOOK_TOO_MANY_FINDING = {
    "severity": "LOW",
    "fr": {
        "label": "Nombre élevé de webhooks actifs ({count})",
        "risk": "Plus il y a de webhooks actifs, plus la surface d'attaque est grande : chaque URL de webhook qui fuite permet de poster des messages dans le salon concerné sans avoir besoin d'un compte Discord.",
        "fix": "Faites un audit régulier des webhooks (Paramètres du serveur > Intégrations) et supprimez ceux qui ne sont plus utilisés.",
    },
    "en": {
        "label": "High number of active webhooks ({count})",
        "risk": "The more active webhooks exist, the larger the attack surface: any leaked webhook URL allows posting messages in that channel without needing a Discord account.",
        "fix": "Regularly audit webhooks (Server Settings > Integrations) and delete unused ones.",
    },
}


AUDIT_LOG_NO_PERM_FINDING = {
    "severity": "INFO",
    "fr": {
        "label": "Journal d'audit inaccessible au bot",
        "risk": "Sans la permission « Voir le journal d'audit », le bot ne peut pas vérifier l'activité récente (bannissements en masse, changements de permissions, nouveaux webhooks/bots) pour détecter une attaque en cours ou passée.",
        "fix": "Donnez la permission « Voir le journal d'audit » au rôle du bot pour activer cette vérification.",
    },
    "en": {
        "label": "Audit log not accessible to the bot",
        "risk": "Without the 'View Audit Log' permission, the bot cannot check recent activity (mass bans, permission changes, new webhooks/bots) to detect an ongoing or past attack.",
        "fix": "Grant the 'View Audit Log' permission to the bot's role to enable this check.",
    },
}

WEBHOOK_NO_PERM_FINDING = {
    "severity": "INFO",
    "fr": {
        "label": "Liste des webhooks inaccessible au bot",
        "risk": "Sans la permission « Gérer les webhooks », le bot ne peut pas lister les webhooks existants pour repérer ceux qui sont suspects ou abandonnés.",
        "fix": "Donnez la permission « Gérer les webhooks » au rôle du bot pour activer cette vérification (le bot ne les modifiera ni ne les supprimera jamais automatiquement).",
    },
    "en": {
        "label": "Webhook list not accessible to the bot",
        "risk": "Without the 'Manage Webhooks' permission, the bot cannot list existing webhooks to spot suspicious or abandoned ones.",
        "fix": "Grant the 'Manage Webhooks' permission to the bot's role to enable this check (the bot will never modify or delete them automatically).",
    },
}

MASS_BAN_RECENT_FINDING = {
    "severity": "CRITICAL",
    "fr": {
        "label": "Vague de bannissements récente ({count} en 24h)",
        "risk": "Un nombre inhabituel de bannissements a eu lieu récemment. Cela peut être une modération légitime (anti-raid) ou au contraire un compte modérateur/admin compromis en train de vider le serveur.",
        "fix": "Vérifiez immédiatement dans le journal d'audit qui a effectué ces bannissements et si c'était volontaire. Si un compte semble compromis, retirez-lui ses rôles, forcez une réinitialisation de mot de passe et activez la 2FA obligatoire.",
    },
    "en": {
        "label": "Recent wave of bans ({count} in 24h)",
        "risk": "An unusual number of bans happened recently. This could be legitimate moderation (anti-raid) or a compromised mod/admin account emptying the server.",
        "fix": "Immediately check the audit log for who performed these bans and whether it was intentional. If an account looks compromised, strip its roles, force a password reset, and enforce 2FA.",
    },
}

MASS_KICK_RECENT_FINDING = {
    "severity": "HIGH",
    "fr": {
        "label": "Vague d'expulsions récente ({count} en 24h)",
        "risk": "Un nombre inhabituel d'expulsions a eu lieu récemment, ce qui peut indiquer un abus de permission ou un compte compromis.",
        "fix": "Vérifiez dans le journal d'audit qui a effectué ces expulsions et pourquoi.",
    },
    "en": {
        "label": "Recent wave of kicks ({count} in 24h)",
        "risk": "An unusual number of kicks happened recently, which may indicate permission abuse or a compromised account.",
        "fix": "Check the audit log for who performed these kicks and why.",
    },
}

MASS_CHANNEL_DELETE_FINDING = {
    "severity": "CRITICAL",
    "fr": {
        "label": "Plusieurs salons supprimés récemment ({count} en 24h)",
        "risk": "C'est le signe classique d'un raid ou d'un compte admin/modérateur compromis en train de détruire le serveur.",
        "fix": "Vérifiez immédiatement le journal d'audit pour identifier le responsable, retirez-lui ses accès si besoin, et restaurez les salons depuis une sauvegarde si vous en avez une.",
    },
    "en": {
        "label": "Several channels deleted recently ({count} in 24h)",
        "risk": "This is a classic sign of a raid or a compromised admin/mod account destroying the server.",
        "fix": "Immediately check the audit log to identify who did it, revoke their access if needed, and restore channels from a backup if you have one.",
    },
}

ROLE_ADMIN_GRANTED_RECENT_FINDING = {
    "severity": "CRITICAL",
    "fr": {
        "label": "Administrateur accordé récemment au rôle « {role} » par {user}",
        "risk": "Un rôle vient de recevoir la permission Administrateur. Si ce n'est pas une action volontaire et documentée de votre part, c'est potentiellement une élévation de privilèges malveillante en cours.",
        "fix": "Si ce changement n'est pas prévu, retirez immédiatement Administrateur à ce rôle et vérifiez qui a fait cette modification (compte compromis ?).",
    },
    "en": {
        "label": "Administrator recently granted to role \u201c{role}\u201d by {user}",
        "risk": "A role just received the Administrator permission. If this wasn't an intentional, documented action on your part, this could be an ongoing malicious privilege escalation.",
        "fix": "If this change wasn't planned, immediately remove Administrator from this role and check who made the change (compromised account?).",
    },
}

BOT_ADDED_RECENT_FINDING = {
    "severity": "INFO",
    "fr": {
        "label": "Nouveau bot ajouté récemment : « {bot} » (par {user})",
        "risk": "Tout nouveau bot est une nouvelle surface d'attaque potentielle : vérifiez ses permissions, s'il est vérifié par Discord, et si sa politique de confidentialité est valide, avant de lui faire confiance.",
        "fix": "Si vous ne reconnaissez pas ce bot ou la personne qui l'a ajouté, retirez-le et enquêtez.",
    },
    "en": {
        "label": "New bot added recently: \u201c{bot}\u201d (by {user})",
        "risk": "Any new bot is a new potential attack surface: check its permissions, whether it's Discord-verified, and whether its privacy policy is valid before trusting it.",
        "fix": "If you don't recognize this bot or whoever added it, remove it and investigate.",
    },
}

WEBHOOK_CREATED_RECENT_FINDING = {
    "severity": "LOW",
    "fr": {
        "label": "Nouveau webhook créé récemment dans « {channel} » par {user}",
        "risk": "Un nouveau webhook a été créé récemment. Si ce n'est pas vous ou un membre de confiance, ce webhook peut servir à poster des messages usurpant l'identité du serveur.",
        "fix": "Vérifiez que ce webhook est légitime. Sinon, supprimez-le immédiatement (Paramètres du salon > Intégrations > Webhooks).",
    },
    "en": {
        "label": "New webhook created recently in \u201c{channel}\u201d by {user}",
        "risk": "A new webhook was recently created. If it wasn't you or a trusted member, it could be used to post messages impersonating the server.",
        "fix": "Verify this webhook is legitimate. Otherwise, delete it immediately (Channel Settings > Integrations > Webhooks).",
    },
}


class Finding:

    def __init__(self, severity, title, risk, fix, lang="fr"):
        self.severity = severity
        self.title = title
        self.risk = risk
        self.fix = fix
        self.lang = lang

    def as_field(self):
        risk_label = "Risque" if self.lang == "fr" else "Risk"
        fix_label = "Correction" if self.lang == "fr" else "Fix"
        value = f"**{risk_label} :** {self.risk}\n**{fix_label} :** {self.fix}"
        if len(value) > 1024:
            value = value[:1000] + "…"
        return self.title, value


def _mk(entry, lang, **kwargs):
    text = entry[lang]
    label = text["label"].format(**kwargs) if kwargs else text["label"]
    risk = text["risk"].format(**kwargs) if kwargs else text["risk"]
    fix = text["fix"].format(**kwargs) if kwargs else text["fix"]
    return Finding(entry["severity"], label, risk, fix, lang)


async def audit_guild(guild: discord.Guild, lang: str = "fr", bot_member: discord.Member = None):
    findings = []

    everyone_role = guild.default_role
    everyone_perms = everyone_role.permissions

    for perm_key, entry in DANGEROUS_EVERYONE_PERMS.items():
        if getattr(everyone_perms, perm_key, False):
            findings.append(_mk(entry, lang))

    admin_roles = [r for r in guild.roles if not r.is_default() and r.permissions.administrator]
    for role in admin_roles:
        findings.append(_mk(ADMIN_ROLE_FINDING, lang, role=role.name))

    if len(admin_roles) > _get_setting(guild.id, "max_admin_roles"):
        findings.append(_mk(TOO_MANY_ADMIN_ROLES_FINDING, lang, count=len(admin_roles)))

    admin_member_count = sum(1 for m in guild.members if m.guild_permissions.administrator)
    if admin_member_count > _get_setting(guild.id, "max_admin_members"):
        findings.append(_mk(TOO_MANY_ADMIN_MEMBERS_FINDING, lang, count=admin_member_count))

    channel_dangerous_keys = [
        "manage_channels", "manage_roles", "manage_webhooks",
        "manage_messages", "mention_everyone", "kick_members", "ban_members",
        "administrator", "moderate_members",
    ]
    for channel in guild.channels:
        try:
            overwrite = channel.overwrites_for(everyone_role)
        except Exception:
            continue
        for perm_key in channel_dangerous_keys:
            allowed = getattr(overwrite, perm_key, None)
            if allowed is True:
                label = perm_key.replace("_", " ")
                findings.append(
                    _mk(
                        CHANNEL_OVERWRITE_FINDING,
                        lang,
                        channel=channel.name,
                        perm=label,
                    )
                )

    if int(guild.verification_level.value) <= 1:
        findings.append(_mk(GUILD_SETTINGS_FINDINGS["verification_low"], lang))

    if int(guild.mfa_level.value) == 0:
        findings.append(_mk(GUILD_SETTINGS_FINDINGS["mfa_disabled"], lang))

    if int(guild.explicit_content_filter.value) == 0:
        findings.append(_mk(GUILD_SETTINGS_FINDINGS["content_filter_disabled"], lang))

    try:
        invites = await guild.invites()
        for invite in invites:
            no_expiry = invite.max_age == 0
            no_use_limit = invite.max_uses == 0
            if no_expiry and no_use_limit:
                findings.append(_mk(GUILD_SETTINGS_FINDINGS["open_invite"], lang))
                break
    except discord.Forbidden:
        pass
    except Exception:
        pass

    if bot_member is not None and bot_member.guild_permissions.administrator:
        findings.append(_mk(BOT_ADMIN_FINDING, lang))

    return findings


DANGEROUS_BOT_PERM_KEYS = [
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "manage_webhooks", "ban_members", "kick_members", "mention_everyone",
    "manage_messages", "moderate_members",
]


def audit_bots(guild: discord.Guild, lang: str = "fr"):
    findings = []

    for member in guild.members:
        if not member.bot:
            continue
        if member.id == guild.me.id:
            continue

        perms = member.guild_permissions
        is_verified = bool(member.public_flags.verified_bot)

        if perms.administrator:
            if is_verified:
                findings.append(_mk(BOT_ADMIN_MEMBER_VERIFIED_FINDING, lang, bot=member.display_name))
            else:
                findings.append(_mk(BOT_ADMIN_MEMBER_FINDING, lang, bot=member.display_name))
            continue

        has_dangerous_perm = any(getattr(perms, key, False) for key in DANGEROUS_BOT_PERM_KEYS)

        if not is_verified and has_dangerous_perm:
            findings.append(_mk(UNVERIFIED_BOT_DANGEROUS_FINDING, lang, bot=member.display_name))

    return findings


async def audit_webhooks(guild: discord.Guild, lang: str = "fr"):
    findings = []

    try:
        webhooks = await guild.webhooks()
    except discord.Forbidden:
        findings.append(_mk(WEBHOOK_NO_PERM_FINDING, lang))
        return findings
    except Exception:
        return findings

    if len(webhooks) > _get_setting(guild.id, "max_webhooks"):
        findings.append(_mk(WEBHOOK_TOO_MANY_FINDING, lang, count=len(webhooks)))

    for wh in webhooks:
        if wh.user is None:
            channel_name = wh.channel.name if wh.channel else "?"
            findings.append(
                _mk(
                    WEBHOOK_UNKNOWN_OWNER_FINDING,
                    lang,
                    channel=channel_name,
                    name=wh.name or "(sans nom)",
                )
            )

    return findings


async def audit_recent_activity(guild: discord.Guild, lang: str = "fr", hours: int = 24, scan_limit: int = 200):
    findings = []

    try:
        entries = [entry async for entry in guild.audit_logs(limit=scan_limit)]
    except discord.Forbidden:
        findings.append(_mk(AUDIT_LOG_NO_PERM_FINDING, lang))
        return findings
    except Exception:
        return findings

    now = discord.utils.utcnow()
    window_start = now - timedelta(hours=hours)
    recent = [e for e in entries if e.created_at >= window_start]

    def _count(action):
        return len([e for e in recent if e.action == action])

    ban_count = _count(discord.AuditLogAction.ban)
    if ban_count >= _get_setting(guild.id, "mass_ban_threshold"):
        findings.append(_mk(MASS_BAN_RECENT_FINDING, lang, count=ban_count))

    kick_count = _count(discord.AuditLogAction.kick)
    if kick_count >= _get_setting(guild.id, "mass_kick_threshold"):
        findings.append(_mk(MASS_KICK_RECENT_FINDING, lang, count=kick_count))

    channel_delete_count = _count(discord.AuditLogAction.channel_delete)
    if channel_delete_count >= _get_setting(guild.id, "mass_channel_delete_threshold"):
        findings.append(_mk(MASS_CHANNEL_DELETE_FINDING, lang, count=channel_delete_count))

    for entry in recent:
        if entry.action != discord.AuditLogAction.role_update:
            continue
        try:
            before_admin = bool(entry.before.permissions.administrator)
        except AttributeError:
            before_admin = False
        try:
            after_admin = bool(entry.after.permissions.administrator)
        except AttributeError:
            after_admin = False
        if after_admin and not before_admin:
            role_name = getattr(entry.target, "name", str(entry.target))
            user_name = str(entry.user) if entry.user else "?"
            findings.append(
                _mk(ROLE_ADMIN_GRANTED_RECENT_FINDING, lang, role=role_name, user=user_name)
            )

    for entry in recent:
        if entry.action != discord.AuditLogAction.bot_add:
            continue
        bot_name = getattr(entry.target, "name", str(entry.target))
        user_name = str(entry.user) if entry.user else "?"
        findings.append(_mk(BOT_ADDED_RECENT_FINDING, lang, bot=bot_name, user=user_name))

    for entry in recent:
        if entry.action != discord.AuditLogAction.webhook_create:
            continue
        channel_name = getattr(entry.extra, "name", None) or "?"
        user_name = str(entry.user) if entry.user else "?"
        findings.append(
            _mk(WEBHOOK_CREATED_RECENT_FINDING, lang, channel=channel_name, user=user_name)
        )

    return findings


LANG = AUDIT_LANG_VALUE.lower()

BOT_VERSION = "V6.64"
if LANG not in ("fr", "en"):
    LANG = "fr"

AUDIT_CHANNEL_NAME = "🔒-audit-securite" if LANG == "fr" else "🔒-security-audit"

LOG_FILE = os.environ.get("AUDIT_BOT_LOG_FILE", "audit_bot.log")

from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=2, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("audit-bot")


def _log_send_failure(context: str, e: Exception) -> None:
    """Log court pour un échec d'envoi Discord, SANS le traceback complet.
    Utile pour les 429 Cloudflare (erreur 1015) : Discord renvoie alors une
    page HTML complète (des centaines de lignes) au lieu d'un JSON, et
    log.exception() la recopierait intégralement dans les logs à chaque
    occurrence. Un statut + message court suffit pour diagnostiquer."""
    if isinstance(e, discord.HTTPException):
        detail = "429 Too Many Requests (Discord/Cloudflare)" if e.status == 429 else f"{e.status} {e.text[:200]}"
        log.warning(f"{context} : {detail}")
    else:
        log.warning(f"{context} : {type(e).__name__}: {e}")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)



_bot_owner_ids: set[int] = set()


async def _refresh_bot_owner_ids() -> None:
    """Interroge Discord pour savoir qui possède ce bot (solo ou équipe) et
    remplit _bot_owner_ids en conséquence. Ne nécessite aucun ID en dur."""
    global _bot_owner_ids
    try:
        info = await bot.application_info()
        if info.team:
            _bot_owner_ids = {m.id for m in info.team.members}
        else:
            _bot_owner_ids = {info.owner.id}
        log.info(f"Propriétaire(s) du bot détecté(s) automatiquement : {_bot_owner_ids}")
    except Exception:
        log.exception("Impossible de récupérer le/la propriétaire du bot depuis l'API Discord.")


def _is_bot_owner(user_id: int) -> bool:
    """Propriétaire ou copropriétaire du BOT (pas du serveur) : accès total à
    toutes les commandes, quels que soient ses rôles/permissions sur le serveur.
    Détecté automatiquement (voir _refresh_bot_owner_ids), jamais saisi à la main."""
    return user_id in _bot_owner_ids


def _member_is_staff(user: discord.abc.User) -> bool:
    """Est staff quiconque a, sur ce serveur, au moins la permission Discord
    « Modérer les membres » (mute) — ou est propriétaire du serveur,
    Administrateur, porteur du rôle Fondateur (owner_role_id, optionnel), ou
    propriétaire/copropriétaire du bot. Plus aucun rôle à assigner à la
    main : c'est la permission Discord réelle qui décide."""
    member = user
    if not isinstance(member, discord.Member) and getattr(user, "guild", None) is not None:
        member = user.guild.get_member(user.id) or member
    if _is_bot_owner(user.id):
        return True
    if not isinstance(member, discord.Member):
        return False
    if member.guild is not None and member.id == member.guild.owner_id:
        return True
    if member.guild_permissions.administrator:
        return True
    if member.guild is not None:
        owner_role_id = _get_setting(member.guild.id, "owner_role_id")
        if owner_role_id and any(r.id == owner_role_id for r in member.roles):
            return True
    return bool(member.guild_permissions.moderate_members)


async def _global_staff_only_check(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        raise discord.app_commands.CheckFailure(
            "❌ Ce bot ne fonctionne que sur un serveur, pas en message privé."
            if LANG == "fr"
            else "❌ This bot only works on a server, not in DMs."
        )

    member = interaction.guild.get_member(interaction.user.id) or interaction.user

    if _member_is_staff(member):
        return True

    log.warning(
        "Accès refusé à /%s pour %s (id=%s) sur %s : permissions insuffisantes (pas au moins Modérer les membres).",
        getattr(interaction.command, "name", "?"),
        interaction.user,
        interaction.user.id,
        interaction.guild.id,
    )
    raise discord.app_commands.CheckFailure(
        "❌ Tu n'as aucune permission." if LANG == "fr" else "❌ You have no permission."
    )


bot.tree.interaction_check = _global_staff_only_check


TXT = {
    "fr": {
        "channel_topic": "Salon privé généré automatiquement — visible uniquement par les rôles Administrateur.",
        "intro_title": "🛡️ Rapport d'audit de sécurité",
        "intro_desc": (
            "Voici l'analyse automatique de la configuration de sécurité de **{guild}**.\n"
            "Ce salon n'est visible que par les rôles possédant la permission **Administrateur**.\n\n"
            "Pour chaque point : la faille, ce qu'un attaquant pourrait en faire, et comment la corriger."
        ),
        "no_findings": "✅ Aucune faille évidente détectée. Le serveur suit les bonnes pratiques de base !",
        "summary_title": "Résumé",
        "summary_line": "{emoji} **{sev}** : {count}",
        "footer": "Analyse automatique — vérifiez et appliquez les corrections dès que possible.",
        "rerun_desc": "Nouvelle analyse demandée par {user}.",
        "no_perm": "❌ Il faut la permission **Administrateur** pour lancer cette commande.",
        "channel_exists": "ℹ️ Le salon d'audit existe déjà : {mention}",
        "no_perm_moderate": "❌ Il faut la permission **Modérer les membres** pour lancer cette commande.",
        "no_perm_kick": "❌ Il faut la permission **Expulser des membres** pour lancer cette commande.",
        "no_perm_ban": "❌ Il faut la permission **Bannir des membres** pour lancer cette commande.",
        "target_too_high": "❌ Ce membre a un rôle égal ou supérieur au tien (ou au mien) : action impossible.",
        "warn_done": "⚠️ {target} a été averti(e). (avertissement n°{n})",
        "mute_done": "🔇 {target} a été mis(e) en sourdine pour {minutes} min.",
        "kick_done": "👢 {target} a été expulsé(e).",
        "ban_done": "🔨 {target} a été banni(e).",
        "action_failed": "❌ Action impossible (permissions du bot insuffisantes ou hiérarchie de rôles).",
        "no_reason": "Aucune raison fournie",
        "history_title": "📜 Historique de modération — {target}",
        "history_empty": "✅ Aucun historique de modération pour {target}.",
        "history_line": "{emoji} `{date}` **{type}** sur *{guild_name}* par {moderator} — {reason}",
        "automod_invite": "🔗 Message supprimé ({author} dans {channel}) : invitation Discord vers un autre serveur.",
        "automod_link_blocked": "🔗 Message supprimé ({author} dans {channel}) : les liens sont interdits sur ce serveur.",
        "automod_phishing": "🚨 Message supprimé et {author} mis en sourdine {minutes} min ({channel}) : lien correspondant à un motif de phishing connu.",
        "automod_mentions": "🚨 Message supprimé et {author} mis en sourdine {minutes} min ({channel}) : {count} mentions dans un seul message (mention-bombing).",
        "automod_caps": "🔠 Message supprimé ({author} dans {channel}) : trop de majuscules.",
        "automod_wordfilter": "🚯 Message supprimé ({author} dans {channel}) : mot interdit détecté (« {word} »).",
        "automod_wordfilter_sanction": "🚯 {author} a eu 3 messages supprimés par le filtre de mots en 24h ({channel}) : {sanction} appliqué(e).",
        "automod_wordfilter_sanction_failed": "⚠️ {author} a eu 3 messages supprimés par le filtre de mots en 24h ({channel}), mais la sanction automatique a échoué (permission manquante).",
        "automod_scam_text": "🚨 Message supprimé et {author} mis en sourdine {minutes} min ({channel}) : texte correspondant à un modèle d'arnaque connu (faux giveaway crypto/influenceur).",
        "automod_image": "🚨 Message supprimé et {author} mis en sourdine {minutes} min ({channel}) : image correspondant à une arnaque connue en blocklist ({label}).",
        "welcome_dm": "👋 Bienvenue sur **{guild}**, {member} ! Prends le temps de lire le règlement du serveur — on est content(e) de t'avoir parmi nous.\n\n*Message envoyé de la part de {bot_name}.*",
        "no_perm_admin_rollback": "❌ Seul le **propriétaire du serveur** peut lancer un rollback.",
        "rollback_target_bot_owner": "❌ Impossible de cibler le propriétaire du serveur ou un membre avec un rôle supérieur/égal au tien.",
        "rollback_scanning": "🔍 Analyse de l'audit log pour {target} sur les {minutes} dernières minutes…",
        "rollback_nothing": "✅ Aucune action de {target} trouvée dans l'audit log sur cette période.",
        "rollback_dry_run_title": "🧪 Simulation de rollback — {target}",
        "rollback_live_title": "⏪ Rollback en cours — {target}",
        "rollback_dry_run_footer": "Mode simulation : rien n'a été modifié. Relance avec confirmer:True pour exécuter.",
        "rollback_line_channel_create": "📁 Supprimerait le salon **#{name}** (créé)",
        "rollback_line_channel_delete": "♻️ Recréerait le salon **#{name}** (type {ctype}) — contenu des messages non récupérable",
        "rollback_line_role_create": "🎭 Supprimerait le rôle **{name}**",
        "rollback_line_overwrite": "🔐 Restaurerait les permissions du salon **#{name}**",
        "rollback_line_webhook": "🔗 Supprimerait le webhook **{name}** sur #{channel}",
        "rollback_line_role_delete": "🎭 Recréerait le rôle **{name}** (permissions, couleur, mentionnable, affiché séparément)",
        "rollback_line_message_delete": "💬 Republierait le message supprimé de **{author}** dans #{channel}",
        "rollback_line_guild_name": "✏️ Restaurerait le nom du serveur : **{name}**",
        "rollback_line_guild_icon": "🖼️ Restaurerait l'icône précédente du serveur",
        "rollback_done": "✅ Rollback terminé pour {target} : {n} action(s) annulée(s). Détails dans {modlog}.",
        "rollback_done_no_modlog": "✅ Rollback terminé pour {target} : {n} action(s) annulée(s).",
        "rollback_error_line": "⚠️ Échec sur une action ({label}) : {error}",
        "rollback_confirm_hint": "ℹ️ Ceci est une simulation (dry_run). Ajoute confirmer:True pour exécuter réellement ces actions.",
    },
    "en": {
        "channel_topic": "Auto-generated private channel — visible only to Administrator roles.",
        "intro_title": "🛡️ Security Audit Report",
        "intro_desc": (
            "Here is the automatic security configuration analysis for **{guild}**.\n"
            "This channel is only visible to roles with the **Administrator** permission.\n\n"
            "For each item: the flaw, what an attacker could do with it, and how to fix it."
        ),
        "no_findings": "✅ No obvious flaw detected. The server follows basic best practices!",
        "summary_title": "Summary",
        "summary_line": "{emoji} **{sev}** : {count}",
        "footer": "Automatic scan — review and apply the fixes as soon as possible.",
        "rerun_desc": "New scan requested by {user}.",
        "no_perm": "❌ You need the **Administrator** permission to run this command.",
        "channel_exists": "ℹ️ The audit channel already exists: {mention}",
        "no_perm_moderate": "❌ You need the **Moderate Members** permission to run this command.",
        "no_perm_kick": "❌ You need the **Kick Members** permission to run this command.",
        "no_perm_ban": "❌ You need the **Ban Members** permission to run this command.",
        "target_too_high": "❌ This member's role is equal to or higher than yours (or mine): action not possible.",
        "warn_done": "⚠️ {target} has been warned. (warning #{n})",
        "mute_done": "🔇 {target} has been muted for {minutes} min.",
        "kick_done": "👢 {target} has been kicked.",
        "ban_done": "🔨 {target} has been banned.",
        "action_failed": "❌ Action failed (insufficient bot permissions or role hierarchy).",
        "no_reason": "No reason provided",
        "history_title": "📜 Moderation history — {target}",
        "history_empty": "✅ No moderation history for {target}.",
        "history_line": "{emoji} `{date}` **{type}** on *{guild_name}* by {moderator} — {reason}",
        "automod_invite": "🔗 Message deleted ({author} in {channel}): Discord invite to another server.",
        "automod_link_blocked": "🔗 Message deleted ({author} in {channel}): links are disabled on this server.",
        "automod_phishing": "🚨 Message deleted and {author} muted {minutes} min ({channel}): link matching a known phishing pattern.",
        "automod_mentions": "🚨 Message deleted and {author} muted {minutes} min ({channel}): {count} mentions in a single message (mention-bombing).",
        "automod_caps": "🔠 Message deleted ({author} in {channel}): excessive caps.",
        "automod_wordfilter": "🚯 Message deleted ({author} in {channel}): banned word detected (\"{word}\").",
        "automod_wordfilter_sanction": "🚯 {author} had 3 messages removed by the word filter in 24h ({channel}): {sanction} applied.",
        "automod_wordfilter_sanction_failed": "⚠️ {author} had 3 messages removed by the word filter in 24h ({channel}), but the automatic sanction failed (missing permission).",
        "automod_scam_text": "🚨 Message deleted and {author} muted {minutes} min ({channel}): text matching a known scam template (fake influencer crypto giveaway).",
        "automod_image": "🚨 Message deleted and {author} muted {minutes} min ({channel}): image matching a known blocklisted scam ({label}).",
        "welcome_dm": "👋 Welcome to **{guild}**, {member}! Take a moment to check the server rules — glad to have you here.\n\n*Sent on behalf of {bot_name}.*",
        "no_perm_admin_rollback": "❌ Only the **server owner** can run a rollback.",
        "rollback_target_bot_owner": "❌ Cannot target the server owner or a member with a role equal to or higher than yours.",
        "rollback_scanning": "🔍 Scanning the audit log for {target} over the last {minutes} minutes…",
        "rollback_nothing": "✅ No actions by {target} found in the audit log for this period.",
        "rollback_dry_run_title": "🧪 Rollback simulation — {target}",
        "rollback_live_title": "⏪ Rolling back — {target}",
        "rollback_dry_run_footer": "Simulation mode: nothing was changed. Re-run with confirmer:True to execute.",
        "rollback_line_channel_create": "📁 Would delete channel **#{name}** (created)",
        "rollback_line_channel_delete": "♻️ Would recreate channel **#{name}** (type {ctype}) — message content cannot be recovered",
        "rollback_line_role_create": "🎭 Would delete role **{name}**",
        "rollback_line_overwrite": "🔐 Would restore permissions on channel **#{name}**",
        "rollback_line_webhook": "🔗 Would delete webhook **{name}** on #{channel}",
        "rollback_line_role_delete": "🎭 Would recreate role **{name}** (permissions, color, mentionable — shown separately)",
        "rollback_line_message_delete": "💬 Would repost the deleted message from **{author}** in #{channel}",
        "rollback_line_guild_name": "✏️ Would restore the server name: **{name}**",
        "rollback_line_guild_icon": "🖼️ Would restore the previous server icon",
        "rollback_done": "✅ Rollback complete for {target}: {n} action(s) undone. Details in {modlog}.",
        "rollback_done_no_modlog": "✅ Rollback complete for {target}: {n} action(s) undone.",
        "rollback_error_line": "⚠️ Failed on one action ({label}): {error}",
        "rollback_confirm_hint": "ℹ️ This is a simulation (dry_run). Add confirmer:True to actually execute these actions.",
    },
}


def t(key, **kwargs):
    text = TXT[LANG][key]
    return text.format(**kwargs) if kwargs else text


async def get_or_create_audit_channel(guild: discord.Guild) -> discord.TextChannel:

    existing = discord.utils.get(guild.text_channels, name=AUDIT_CHANNEL_NAME)
    if existing:
        return existing

    everyone = guild.default_role

    overwrites = {
        everyone: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, embed_links=True, read_message_history=True
        ),
    }

    for role in guild.roles:
        if role.permissions.administrator and not role.is_default():
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    channel = await guild.create_text_channel(
        name=AUDIT_CHANNEL_NAME,
        overwrites=overwrites,
        topic=t("channel_topic"),
        reason="Création automatique du salon d'audit de sécurité",
    )

    try:
        await channel.edit(position=0)
    except discord.HTTPException:
        pass

    return channel


def build_embeds(guild: discord.Guild, findings, requester: str = None):

    embeds = []

    intro = discord.Embed(
        title=t("intro_title"),
        description=t("intro_desc", guild=guild.name),
        color=0x2ECC71 if not findings else 0xE74C3C,
    )
    if requester:
        intro.set_footer(text=t("rerun_desc", user=requester))
    embeds.append(intro)

    if not findings:
        empty = discord.Embed(description=t("no_findings"), color=0x2ECC71)
        embeds.append(empty)
        return embeds

    findings_sorted = sorted(findings, key=lambda f: SEVERITY_ORDER.index(f.severity))

    counts = {}
    for f in findings_sorted:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary_lines = []
    for sev in SEVERITY_ORDER:
        if sev in counts:
            meta = SEVERITY_META[sev]
            summary_lines.append(
                t("summary_line", emoji=meta["emoji"], sev=meta[LANG], count=counts[sev])
            )
    summary_embed = discord.Embed(
        title=t("summary_title"), description="\n".join(summary_lines), color=0xE74C3C
    )
    embeds.append(summary_embed)

    MAX_FIELDS_PER_EMBED = 25
    MAX_CHARS_PER_EMBED = 5500

    current = discord.Embed(color=0xE74C3C)
    field_count = 0
    char_count = 0
    for f in findings_sorted:
        meta = SEVERITY_META[f.severity]
        name, value = f.as_field()
        name = f"{meta['emoji']} {name}"[:256]
        added_len = len(name) + len(value)

        if field_count >= MAX_FIELDS_PER_EMBED or (char_count + added_len) > MAX_CHARS_PER_EMBED:
            embeds.append(current)
            current = discord.Embed(color=0xE74C3C)
            field_count = 0
            char_count = 0

        current.add_field(name=name, value=value, inline=False)
        field_count += 1
        char_count += added_len

    current.set_footer(text=t("footer"))
    embeds.append(current)

    return embeds


def _embed_char_count(embed: discord.Embed) -> int:
    total = 0
    if embed.title:
        total += len(str(embed.title))
    if embed.description:
        total += len(str(embed.description))
    if embed.footer and embed.footer.text:
        total += len(str(embed.footer.text))
    if embed.author and embed.author.name:
        total += len(str(embed.author.name))
    for field in embed.fields:
        total += len(str(field.name)) + len(str(field.value))
    return total


async def _send_embeds_safely(channel, embeds, max_count: int = 10, max_chars: int = 5800):
    batch = []
    batch_chars = 0

    for embed in embeds:
        e_chars = _embed_char_count(embed)
        if batch and (len(batch) >= max_count or batch_chars + e_chars > max_chars):
            await channel.send(embeds=batch)
            await asyncio.sleep(0.5)
            batch = []
            batch_chars = 0
        batch.append(embed)
        batch_chars += e_chars

    if batch:
        await channel.send(embeds=batch)


SPAM_MESSAGE_COUNT = 6
SPAM_WINDOW_SECONDS = 5
SPAM_TIMEOUT_MINUTES = 10

CHANNEL_ACTION_COUNT = 3
CHANNEL_ACTION_WINDOW_SECONDS = 10
CHANNEL_ACTION_TIMEOUT_MINUTES = 10

ANTINUKE_ACTION_COUNT_HUMAN_DEFAULT = 3
ANTINUKE_WINDOW_SECONDS_HUMAN_DEFAULT = 3
ANTINUKE_ACTION_COUNT_BOT_UNVERIFIED_DEFAULT = 2
ANTINUKE_WINDOW_SECONDS_BOT_UNVERIFIED_DEFAULT = 5
ANTINUKE_ACTION_COUNT_BOT_VERIFIED_DEFAULT = 3
ANTINUKE_WINDOW_SECONDS_BOT_VERIFIED_DEFAULT = 2
ANTINUKE_HUMAN_TIMEOUT_MINUTES_DEFAULT = 8


CONFIG_CHANNEL_NAME = "⚙️-configuration-bot" if LANG == "fr" else "⚙️-bot-config"

CONFIG_MESSAGE_MARKER = "AUDITBOT_CONFIG_V1"


WELCOME_TEXT_DEFAULT = (
    "🎉 {mention} vient de rejoindre **{serveur}** ! Bienvenue à toi, tu es notre {nombre}e membre."
    if LANG == "fr"
    else "🎉 {mention} just joined **{server}**! Welcome, you're our {count}th member."
)

JOIN_MODIFIED_NOTE_DEFAULT = (
    "**Ceci est une version modifiée** du bot d'origine."
    if LANG == "fr"
    else "**This is a modified version** of the original bot."
)

DEFAULT_SETTINGS = {
    "max_admin_roles": MAX_ADMIN_ROLES,
    "max_admin_members": MAX_ADMIN_MEMBERS,
    "max_webhooks": MAX_WEBHOOKS,
    "mass_ban_threshold": MASS_BAN_THRESHOLD,
    "mass_kick_threshold": MASS_KICK_THRESHOLD,
    "mass_channel_delete_threshold": MASS_CHANNEL_DELETE_THRESHOLD,
    "spam_message_count": SPAM_MESSAGE_COUNT,
    "spam_window_seconds": SPAM_WINDOW_SECONDS,
    "spam_timeout_minutes": SPAM_TIMEOUT_MINUTES,
    "channel_action_count": CHANNEL_ACTION_COUNT,
    "channel_action_window_seconds": CHANNEL_ACTION_WINDOW_SECONDS,
    "channel_action_timeout_minutes": CHANNEL_ACTION_TIMEOUT_MINUTES,
    "automod_timeout_minutes": AUTOMOD_TIMEOUT_MINUTES,
    "mass_mention_threshold": MASS_MENTION_THRESHOLD,
    "caps_min_length": CAPS_MIN_LENGTH,
    "caps_ratio_threshold": CAPS_RATIO_THRESHOLD,
    "welcome_dm_enabled": True,
    "min_account_age_hours": 0,
    "welcome_channel_id": 0,
    "welcome_text": WELCOME_TEXT_DEFAULT,
    "welcome_ping_enabled": True,
    "owner_role_id": 0,
    "mod_request_enabled": True,
    "mod_request_channel_id": 0,
    "audit_search_enabled": True,
    "audit_search_channel_id": 0,
    "storage_staff_role_id": 0,
    "storage_command_channel_id": 0,
    "module_antinuke_enabled": True,
    "module_automod_enabled": True,
    "module_antispam_enabled": False,
    "module_messagelog_enabled": False,
    "message_log_channel_id": 0,
    "module_serverlog_enabled": False,
    "server_log_channel_id": 0,
    "module_verification_enabled": False,
    "verification_method": "channel",
    "verification_difficulty": "hard",
    "verification_channel_timeout_minutes": 15,
    "verification_dm_timeout_minutes": 15,
    "verification_captcha_max_attempts": 3,
    "verification_link_timeout_minutes": 15,
    "verification_channel_category_id": 0,
    "verification_link_channel_id": 0,
    "verification_role_id": 0,
    "verification_unverified_role_id": 0,
    "verification_remove_role_ids": [],
    "module_honeypot_enabled": False,
    "honeypot_channel_id": 0,
    "honeypot_sanction_type": "mute",
    "honeypot_mute_minutes": 10080,
    "honeypot_delete_lookback_hours": 168,
    "honeypot_warning_text": (
        "⚠️🚫 NE RIEN ÉCRIRE ICI !!! 🚫⚠️ SALON PIÈGE ⛔ Tu seras banni(e)/sanctionné(e) automatiquement !!! 🍯☠️" if LANG == "fr"
        else "⚠️🚫 DO NOT WRITE HERE !!! 🚫⚠️ HONEYPOT CHANNEL ⛔ You will be automatically sanctioned !!! 🍯☠️"
    ),
    "honeypot_warning_message_id": 0,
    "honeypot_manual_delete_log": [],
    "module_wordfilter_enabled": False,
    "banned_words_list": [],
    "wordfilter_sanction_type": "mute",
    "wordfilter_mute_minutes": 60,
    "antinuke_action_count_human": ANTINUKE_ACTION_COUNT_HUMAN_DEFAULT,
    "antinuke_window_seconds_human": ANTINUKE_WINDOW_SECONDS_HUMAN_DEFAULT,
    "antinuke_action_count_bot_unverified": ANTINUKE_ACTION_COUNT_BOT_UNVERIFIED_DEFAULT,
    "antinuke_window_seconds_bot_unverified": ANTINUKE_WINDOW_SECONDS_BOT_UNVERIFIED_DEFAULT,
    "unverified_bot_lockdown_minutes": 5,
    "antinuke_action_count_bot_verified": ANTINUKE_ACTION_COUNT_BOT_VERIFIED_DEFAULT,
    "antinuke_window_seconds_bot_verified": ANTINUKE_WINDOW_SECONDS_BOT_VERIFIED_DEFAULT,
    "antinuke_human_timeout_minutes": ANTINUKE_HUMAN_TIMEOUT_MINUTES_DEFAULT,
    "antinuke_bot_sanction": "ban",
    "antinuke_human_sanction": "timeout",
    "freeze_role_id": 0,
    "freeze_category_id": 0,
    "freeze_channel_id": 0,
    "freeze_tickets_enabled": True,
    "freeze_ticket_ping_role_ids": [],
    "freeze_allowed_role_ids": [],
    "freeze_allowed_user_ids": [],
    "frozen_members": {},
}

ANTINUKE_SANCTION_CHOICES = {
    "ban": {"fr": "Bannir", "en": "Ban"},
    "kick": {"fr": "Expulser", "en": "Kick"},
    "timeout": {"fr": "Mettre en sourdine + retirer rôles dangereux", "en": "Timeout + strip dangerous roles"},
    "strip_roles": {"fr": "Retirer uniquement les rôles dangereux (sans sourdine)", "en": "Strip dangerous roles only (no timeout)"},
    "warn": {"fr": "Avertir seulement (aucune sanction)", "en": "Warn only (no sanction)"},
}

HONEYPOT_SANCTION_CHOICES = {
    "mute": {"fr": "Mettre en sourdine (durée réglable)", "en": "Timeout (configurable duration)"},
    "kick": {"fr": "Expulser", "en": "Kick"},
    "ban": {"fr": "Bannir", "en": "Ban"},
}

WORDFILTER_SANCTION_CHOICES = {
    "mute": {"fr": "Mettre en sourdine (durée réglable)", "en": "Timeout (configurable duration)"},
    "kick": {"fr": "Expulser", "en": "Kick"},
    "ban": {"fr": "Bannir", "en": "Ban"},
}

CONFIG_META = {
    "max_admin_roles": {"fr": "Nb max de rôles Administrateur avant alerte", "en": "Max Administrator roles before alert", "float": False, "min": 1, "max": 50},
    "max_admin_members": {"fr": "Nb max de membres avec accès Administrateur avant alerte", "en": "Max members with Administrator access before alert", "float": False, "min": 1, "max": 200},
    "max_webhooks": {"fr": "Nb max de webhooks avant alerte", "en": "Max webhooks before alert", "float": False, "min": 1, "max": 200},
    "mass_ban_threshold": {"fr": "Nb de bannissements en 24h avant alerte", "en": "Bans in 24h before alert", "float": False, "min": 1, "max": 1000},
    "mass_kick_threshold": {"fr": "Nb d'expulsions en 24h avant alerte", "en": "Kicks in 24h before alert", "float": False, "min": 1, "max": 1000},
    "mass_channel_delete_threshold": {"fr": "Nb de salons supprimés en 24h avant alerte", "en": "Channel deletions in 24h before alert", "float": False, "min": 1, "max": 1000},
    "spam_message_count": {"fr": "Nb de messages avant détection de spam", "en": "Messages before spam is detected", "float": False, "min": 2, "max": 100},
    "spam_window_seconds": {"fr": "Fenêtre (secondes) de détection du spam de messages", "en": "Time window (seconds) for message spam detection", "float": False, "min": 1, "max": 300},
    "spam_timeout_minutes": {"fr": "Durée (minutes) de sourdine infligée par l'anti-spam", "en": "Timeout duration (minutes) applied by anti-spam", "float": False, "min": 1, "max": 40320},
    "channel_action_count": {"fr": "Nb de créations/suppressions de salons avant alerte anti-nuke", "en": "Channel creations/deletions before anti-nuke alert", "float": False, "min": 1, "max": 100},
    "channel_action_window_seconds": {"fr": "Fenêtre (secondes) de détection anti-nuke", "en": "Time window (seconds) for anti-nuke detection", "float": False, "min": 1, "max": 300},
    "channel_action_timeout_minutes": {"fr": "Durée (minutes) de sourdine infligée par l'anti-nuke", "en": "Timeout duration (minutes) applied by anti-nuke", "float": False, "min": 1, "max": 40320},
    "automod_timeout_minutes": {"fr": "Durée (minutes) de sourdine infligée par l'auto-modération de contenu", "en": "Timeout duration (minutes) applied by content auto-moderation", "float": False, "min": 1, "max": 40320},
    "mass_mention_threshold": {"fr": "Nb de mentions distinctes dans un message avant suppression", "en": "Distinct mentions in one message before removal", "float": False, "min": 1, "max": 100},
    "caps_min_length": {"fr": "Longueur mini d'un message avant de vérifier le ratio de majuscules", "en": "Minimum message length before checking the caps ratio", "float": False, "min": 1, "max": 500},
    "caps_ratio_threshold": {"fr": "Ratio de majuscules (0 à 1) déclenchant la suppression", "en": "Caps ratio (0 to 1) triggering removal", "float": True, "min": 0.0, "max": 1.0},
    "welcome_dm_enabled": {"fr": "Envoyer un MP de bienvenue aux nouveaux membres (oui/non)", "en": "Send a welcome DM to new members (yes/no)", "bool": True},
    "owner_role_id": {"fr": "ID du rôle Fondateur (accès total aux commandes du bot)", "en": "Founder role ID (full access to bot commands)", "role": True},
    "mod_request_enabled": {"fr": "Activer le système de demande (mute/kick/ban) quand la permission manque", "en": "Enable the request system (mute/kick/ban) when the permission is missing", "bool": True},
    "mod_request_channel_id": {"fr": "ID du salon des demandes de sanction", "en": "Sanction-request channel ID", "channel": True},
    "message_log_channel_id": {"fr": "ID du salon de logs de messages (sur CE serveur, pas le serveur de stockage)", "en": "Message log channel ID (on THIS server, not the storage server)", "channel": True},
    "server_log_channel_id": {"fr": "ID du salon de logs d'actions du serveur (sur CE serveur)", "en": "Server action log channel ID (on THIS server)", "channel": True},
    "audit_search_enabled": {"fr": "Activer /recherche-historique et /recherche-messages sur ce serveur", "en": "Enable /history-search and /recherche-messages on this server", "bool": True},
    "audit_search_channel_id": {"fr": "ID du salon dédié à /recherche-historique et /recherche-messages (0 = n'importe où)", "en": "Dedicated channel ID for /history-search and /recherche-messages (0 = anywhere)", "channel": True},
    "antinuke_action_count_human": {"fr": "Nb d'actions suspectes avant sanction d'un humain", "en": "Suspicious actions before sanctioning a human", "float": False, "min": 1, "max": 50},
    "antinuke_window_seconds_human": {"fr": "Fenêtre (secondes) de détection anti-nuke pour un humain", "en": "Time window (seconds) for anti-nuke detection on a human", "float": False, "min": 1, "max": 120},
    "antinuke_action_count_bot_unverified": {"fr": "Nb d'actions suspectes avant sanction d'un bot NON certifié", "en": "Suspicious actions before sanctioning an unverified bot", "float": False, "min": 1, "max": 50},
    "antinuke_window_seconds_bot_unverified": {"fr": "Fenêtre (secondes) de détection anti-nuke pour un bot NON certifié", "en": "Time window (seconds) for anti-nuke detection on an unverified bot", "float": False, "min": 1, "max": 120},
    "unverified_bot_lockdown_minutes": {"fr": "Verrouillage nom/icône serveur pour un bot NON certifié après son arrivée (minutes), 0 = désactivé", "en": "Server name/icon lockdown for an unverified bot after joining (minutes), 0 = disabled", "float": False, "min": 0, "max": 1440},
    "antinuke_action_count_bot_verified": {"fr": "Nb d'actions suspectes avant sanction d'un bot certifié Discord", "en": "Suspicious actions before sanctioning a Discord-verified bot", "float": False, "min": 1, "max": 50},
    "antinuke_window_seconds_bot_verified": {"fr": "Fenêtre (secondes) de détection anti-nuke pour un bot certifié Discord", "en": "Time window (seconds) for anti-nuke detection on a Discord-verified bot", "float": False, "min": 1, "max": 120},
    "antinuke_human_timeout_minutes": {"fr": "Durée (minutes) de sourdine infligée à un humain par l'anti-nuke", "en": "Timeout duration (minutes) applied to a human by anti-nuke", "float": False, "min": 1, "max": 40320},
    "min_account_age_hours": {"fr": "Âge minimum du compte (heures) pour rejoindre, 0 = désactivé", "en": "Minimum account age (hours) to join, 0 = disabled", "float": False, "min": 0, "max": 87600},
    "honeypot_mute_minutes": {"fr": "Durée (minutes) de la sourdine infligée par le salon piège", "en": "Timeout duration (minutes) applied by the honeypot channel", "float": False, "min": 1, "max": 40320},
    "wordfilter_mute_minutes": {"fr": "Durée (minutes) de la sourdine infligée après 3 messages supprimés par le filtre de mots en 24h (5 min à 24h)", "en": "Timeout duration (minutes) applied after 3 messages removed by the word filter in 24h (5 min to 24h)", "float": False, "min": 5, "max": 1440},
    "honeypot_delete_lookback_hours": {"fr": "Purge des messages de l'auteur sur tout le serveur : fenêtre (heures)", "en": "Server-wide purge of the author's messages: window (hours)", "float": False, "min": 1, "max": 336},
}

_guild_store = defaultdict(lambda: {"settings": {}, "whitelist": {}})


def _get_setting(guild_id: int, key: str):
    return _guild_store[guild_id]["settings"].get(key, DEFAULT_SETTINGS[key])


def _set_setting(guild_id: int, key: str, value) -> None:
    _guild_store[guild_id]["settings"][key] = value


async def get_or_create_config_channel(guild: discord.Guild) -> discord.TextChannel:
    existing = discord.utils.get(guild.text_channels, name=CONFIG_CHANNEL_NAME)
    if existing:
        return existing

    everyone = guild.default_role
    overwrites = {
        everyone: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, embed_links=True, read_message_history=True, manage_messages=True
        ),
    }
    for role in guild.roles:
        if role.permissions.administrator and not role.is_default():
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)

    topic = (
        "⚠️ Ne rien écrire ici — ce salon stocke la configuration du bot. "
        "Utilisez /config-voir et /config-modifier pour la consulter/modifier."
        if LANG == "fr"
        else "⚠️ Do not write here — this channel stores the bot's configuration. "
        "Use /config-view and /config-set to read/change it."
    )
    channel = await guild.create_text_channel(
        name=CONFIG_CHANNEL_NAME,
        overwrites=overwrites,
        topic=topic,
        reason="Création automatique du salon de configuration du bot",
    )
    return channel


def _build_config_embed(guild_id: int) -> discord.Embed:
    # "frozen_members" est exclu ici et persisté séparément (voir
    # _save_frozen_members / _build_frozen_store_embed) : cette liste peut
    # grossir sans limite prévisible, et la mélanger au reste des réglages
    # exposait ce message à la troncature à 4096 caractères plus bas — ce qui
    # corrompait le JSON et faisait perdre le suivi des membres gelés.
    settings = {key: _get_setting(guild_id, key) for key in DEFAULT_SETTINGS if key != "frozen_members"}
    whitelist = {str(entity_id): kind for entity_id, kind in _guild_store[guild_id]["whitelist"].items()}
    title = "⚙️ Configuration du bot — NE PAS MODIFIER CE MESSAGE" if LANG == "fr" else "⚙️ Bot configuration — DO NOT EDIT THIS MESSAGE"
    desc = (
        "Ce message est géré automatiquement par le bot (via `/config-modifier` et "
        "`/liste-blanche-*`). Il contient tous les seuils configurables ainsi que la "
        "liste blanche, au format JSON.\n```json\n"
        if LANG == "fr"
        else "This message is managed automatically by the bot (via `/config-set` and "
        "`/whitelist-*`). It contains every configurable threshold as well as the "
        "whitelist, in JSON.\n```json\n"
    )
    payload = {"settings": settings, "whitelist": whitelist}
    desc += json.dumps(payload, indent=2, ensure_ascii=False) + "\n```"
    embed = discord.Embed(title=title, description=desc[:4096], color=0x5865F2, timestamp=discord.utils.utcnow())
    embed.add_field(name="Heure" if LANG == "fr" else "Time", value=utc_time_str(), inline=True)
    embed.set_footer(text=CONFIG_MESSAGE_MARKER)
    return embed


async def _find_config_message(channel: discord.TextChannel):
    try:
        async for msg in channel.history(limit=50):
            for embed in msg.embeds:
                if embed.footer and embed.footer.text == CONFIG_MESSAGE_MARKER:
                    return msg
    except Exception:
        log.exception("Impossible de relire le salon de configuration.")
    return None


async def _edit_or_resend(channel: discord.TextChannel, existing_msg, embed: discord.Embed):
    """Édite `existing_msg` avec le nouvel embed, ou envoie un nouveau message
    si `existing_msg` est None. En cas de 'Cannot edit a message authored by
    another user' (403/50005) — typique quand une AUTRE instance du bot
    (jeton différent, ex. un bot de test en local) partage le même serveur de
    stockage et a créé ce message à l'origine — on supprime l'ancien message
    et on en renvoie un nouveau à la place plutôt que de faire planter tout
    l'enregistrement de la configuration."""
    if existing_msg is None:
        await channel.send(embed=embed)
        return
    try:
        await existing_msg.edit(embed=embed)
    except discord.Forbidden as e:
        if getattr(e, "code", None) != 50005:
            raise
        log.warning(
            f"Message de {channel.mention} appartient à une autre instance du bot (jeton différent) : "
            "suppression et recréation au lieu d'une édition."
        )
        try:
            await existing_msg.delete()
        except (discord.Forbidden, discord.NotFound):
            pass
        await channel.send(embed=embed)


def _parse_config_embed(embed: discord.Embed) -> typing.Optional[dict]:
    raw = embed.description or ""
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return None
    data = json.loads(raw[start:end + 1])
    if "settings" in data or "whitelist" in data:
        return {"settings": data.get("settings", {}), "whitelist": data.get("whitelist", {})}
    return {"settings": data, "whitelist": {}}


def _apply_config_data(guild_id: int, data: dict) -> tuple[int, int]:
    settings_data = data.get("settings", {})
    whitelist_data = data.get("whitelist", {})
    for key, value in settings_data.items():
        if key in DEFAULT_SETTINGS:
            _set_setting(guild_id, key, value)
    _guild_store[guild_id]["whitelist"] = {
        int(entity_id): kind for entity_id, kind in whitelist_data.items()
    }
    return len(settings_data), len(whitelist_data)


async def save_guild_config_local(guild: discord.Guild) -> None:
    channel = await get_or_create_config_channel(guild)
    embed = _build_config_embed(guild.id)
    existing_msg = await _find_config_message(channel)
    await _edit_or_resend(channel, existing_msg, embed)


async def load_guild_config_local(guild: discord.Guild) -> bool:
    channel = discord.utils.get(guild.text_channels, name=CONFIG_CHANNEL_NAME)
    if not channel:
        return False
    msg = await _find_config_message(channel)
    if not msg or not msg.embeds:
        return False
    data = _parse_config_embed(msg.embeds[0])
    if data is None:
        return False
    n_settings, n_whitelist = _apply_config_data(guild.id, data)
    log.info(
        f"Configuration chargée depuis le salon local pour {guild.name} "
        f"({n_settings} réglage(s), {n_whitelist} entrée(s) en liste blanche)."
    )
    return True


async def save_guild_config_db(db_guild: discord.Guild, guild: discord.Guild) -> None:
    channel = await get_or_create_db_channel(db_guild, guild, "config")
    embed = _build_config_embed(guild.id)
    existing_msg = await _find_config_message(channel)
    await _edit_or_resend(channel, existing_msg, embed)


async def load_guild_config_db(db_guild: discord.Guild, guild: discord.Guild) -> bool:
    channel = await get_or_create_db_channel(db_guild, guild, "config")
    msg = await _find_config_message(channel)
    if not msg or not msg.embeds:
        return False
    data = _parse_config_embed(msg.embeds[0])
    if data is None:
        return False
    n_settings, n_whitelist = _apply_config_data(guild.id, data)
    log.info(
        f"Configuration chargée depuis le serveur base de données pour {guild.name} "
        f"({n_settings} réglage(s), {n_whitelist} entrée(s) en liste blanche)."
    )
    return True


RAID_MESSAGE_MARKER = "AUDITBOT_RAID_V1"


def _build_raid_embed(guild: discord.Guild, state: dict) -> discord.Embed:
    title = (
        "🚨 Protocole anti-raid — NE PAS MODIFIER CE MESSAGE" if LANG == "fr"
        else "🚨 Anti-raid protocol — DO NOT EDIT THIS MESSAGE"
    )
    payload = {
        "active": state.get("active", False),
        "role_id": state.get("role_id"),
        "member_ids": state.get("member_ids", []),
        "left_during_raid": state.get("left_during_raid", []),
        "started_at": state["started_at"].isoformat() if state.get("started_at") else None,
        "started_by": state.get("started_by"),
        "previous_webhooks_allowed": state.get("previous_webhooks_allowed"),
        "previous_invites_allowed": state.get("previous_invites_allowed"),
        "locked_channels": state.get("locked_channels", []),
        "new_account_kick_until": (
            state["new_account_kick_until"].isoformat() if state.get("new_account_kick_until") else None
        ),
    }
    desc = (
        "Ce message est géré automatiquement par le bot (via `/protocole-anti-raid` et "
        "`/fin-protocole-anti-raid`). Il contient l'état courant du protocole pour ce "
        "serveur, au format JSON — sert à tout restaurer même après un redémarrage du bot.\n```json\n"
        if LANG == "fr"
        else "This message is managed automatically by the bot (via `/anti-raid-protocol` and "
        "`/end-anti-raid-protocol`). It contains the current protocol state for this "
        "server, in JSON — used to restore everything even after a bot restart.\n```json\n"
    )
    desc += json.dumps(payload, indent=2, ensure_ascii=False) + "\n```"
    color = 0xFF0000 if payload["active"] else 0x2ECC71
    embed = discord.Embed(title=title, description=desc[:4096], color=color, timestamp=discord.utils.utcnow())
    embed.add_field(name="Heure" if LANG == "fr" else "Time", value=utc_time_str(), inline=True)
    embed.set_footer(text=RAID_MESSAGE_MARKER)
    return embed


async def _find_raid_message(channel: discord.TextChannel):
    try:
        async for msg in channel.history(limit=50):
            for embed in msg.embeds:
                if embed.footer and embed.footer.text == RAID_MESSAGE_MARKER:
                    return msg
    except Exception:
        log.exception("Impossible de relire le salon du protocole anti-raid.")
    return None


def _parse_raid_embed(embed: discord.Embed) -> typing.Optional[dict]:
    raw = embed.description or ""
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return None
    data = json.loads(raw[start:end + 1])
    if data.get("started_at"):
        data["started_at"] = datetime.fromisoformat(data["started_at"])
    if data.get("new_account_kick_until"):
        data["new_account_kick_until"] = datetime.fromisoformat(data["new_account_kick_until"])
    return data


async def _save_raid_state(db_guild: discord.Guild, guild: discord.Guild, state: dict) -> None:
    channel = await get_or_create_db_channel(db_guild, guild, "raid")
    embed = _build_raid_embed(guild, state)
    existing_msg = await _find_raid_message(channel)
    await _edit_or_resend(channel, existing_msg, embed)


async def _load_raid_state(db_guild: discord.Guild, guild: discord.Guild) -> typing.Optional[dict]:
    channel = await get_or_create_db_channel(db_guild, guild, "raid")
    msg = await _find_raid_message(channel)
    if not msg or not msg.embeds:
        return None
    return _parse_raid_embed(msg.embeds[0])


def _load_file_raid_state(guild: discord.Guild) -> typing.Optional[dict]:
    data = _file_store_guild(guild.id).get("raid_state")
    if not data:
        return None
    data = dict(data)
    if data.get("started_at"):
        data["started_at"] = datetime.fromisoformat(data["started_at"])
    if data.get("new_account_kick_until"):
        data["new_account_kick_until"] = datetime.fromisoformat(data["new_account_kick_until"])
    return data


def _is_new_account(member: discord.Member) -> bool:
    age = discord.utils.utcnow() - member.created_at
    return age < timedelta(days=RAID_NEW_ACCOUNT_MAX_AGE_DAYS)


def _account_too_young(member: discord.Member) -> bool:
    """Vérification permanente et indépendante du protocole anti-raid : le
    compte du membre est-il plus jeune que le minimum réglé sur CE serveur
    via le panel / /age-minimum-comptes (0 = vérification désactivée) ?"""
    min_hours = _get_setting(member.guild.id, "min_account_age_hours")
    if not min_hours:
        return False
    age = discord.utils.utcnow() - member.created_at
    return age < timedelta(hours=min_hours)


def _has_role_id(member: discord.Member, role_id: int) -> bool:
    return any(r.id == role_id for r in member.roles)


def _has_effective_administrator(member: discord.Member) -> bool:
    """Retourne True si le membre a réellement la permission Administrateur,
    s'il est propriétaire/copropriétaire du bot, propriétaire du serveur, ou
    porteur du rôle Fondateur configuré (owner_role_id, optionnel) — ce sont
    les « chefs », tout en haut de la hiérarchie, quelles que soient leurs
    autres permissions Discord."""
    if _is_bot_owner(member.id):
        return True
    if member.guild_permissions.administrator:
        return True
    if member.guild is None:
        return False
    if member.id == member.guild.owner_id:
        return True
    owner_role_id = _get_setting(member.guild.id, "owner_role_id")
    return bool(owner_role_id and any(r.id == owner_role_id for r in member.roles))


ANTINUKE_ACCESS_EQUIVALENT_PERMS = (
    "manage_guild", "manage_roles", "manage_channels", "kick_members", "moderate_members",
)


def _has_antinuke_access(member: discord.Member) -> bool:
    """Détermine si `member` a accès au protocole/panneau anti-nuke & anti-raid.
    Toujours vrai pour le/la propriétaire du serveur, le/la propriétaire/
    copropriétaire du bot, le rôle Fondateur, ou Administrateur. Sinon,
    automatique : accès accordé si le membre possède réellement, sur ce
    serveur, au moins une des permissions Discord listées dans
    ANTINUKE_ACCESS_EQUIVALENT_PERMS (pas besoin de case à cocher dédiée)."""
    if member.guild is None:
        return False
    if member.id == member.guild.owner_id or _is_bot_owner(member.id):
        return True
    perms = member.guild_permissions
    if perms.administrator:
        return True
    role_ids = {r.id for r in member.roles}
    owner_role_id = _get_setting(member.guild.id, "owner_role_id")
    if owner_role_id and owner_role_id in role_ids:
        return True
    return any(getattr(perms, perm_name, False) for perm_name in ANTINUKE_ACCESS_EQUIVALENT_PERMS)


def _raid_command_allowed(interaction: discord.Interaction) -> bool:
    """Le protocole anti-raid n'est utilisable que par le propriétaire du serveur,
    le/la propriétaire/copropriétaire du bot, le rôle Fondateur, un membre
    Administrateur, ou un membre dont le rôle a réellement au moins une des
    permissions Discord équivalentes à l'anti-nuke (voir _has_antinuke_access)."""
    guild = interaction.guild
    if guild is None:
        return False
    member = guild.get_member(interaction.user.id) or interaction.user
    if not isinstance(member, discord.Member):
        return False
    return _has_antinuke_access(member)


ANTINUKE_ACCESS_PERM_LABELS = {
    "manage_guild": ("Gérer le serveur", "Manage Server"),
    "manage_roles": ("Gérer les rôles", "Manage Roles"),
    "manage_channels": ("Gérer les salons", "Manage Channels"),
    "kick_members": ("Expulser des membres", "Kick Members"),
    "moderate_members": ("Mettre en sourdine (Modérer les membres)", "Timeout (Moderate Members)"),
}


def _antinuke_access_status_line(guild: discord.Guild, role_id: int) -> str:
    """Ligne de statut à afficher dans le panel : indique clairement si le rôle
    d'un niveau donne accès à l'anti-nuke/anti-raid, et via QUELLE(S)
    permission(s) Discord précisément — pour ne plus avoir à deviner."""
    if not role_id:
        return (
            "🚨 **Accès anti-nuke** : *aucun rôle assigné à ce niveau pour le moment*"
            if LANG == "fr"
            else "🚨 **Anti-nuke access**: *no role assigned to this level yet*"
        )
    role = guild.get_role(role_id)
    if role is None:
        return (
            "🚨 **Accès anti-nuke** : rôle introuvable (supprimé ?)" if LANG == "fr"
            else "🚨 **Anti-nuke access**: role not found (deleted?)"
        )
    matched = [
        (label_fr if LANG == "fr" else label_en)
        for key, (label_fr, label_en) in ANTINUKE_ACCESS_PERM_LABELS.items()
        if getattr(role.permissions, key, False)
    ]
    if role.permissions.administrator:
        return (
            f"🚨 **Accès anti-nuke** : ✅ activé (le rôle {role.mention} a Administrateur)."
            if LANG == "fr"
            else f"🚨 **Anti-nuke access**: ✅ enabled ({role.mention} has Administrator)."
        )
    if matched:
        joined = ", ".join(matched)
        return (
            f"🚨 **Accès anti-nuke** : ✅ activé automatiquement — {role.mention} a : {joined}."
            if LANG == "fr"
            else f"🚨 **Anti-nuke access**: ✅ auto-enabled — {role.mention} has: {joined}."
        )
    all_labels = ", ".join(label_fr if LANG == "fr" else label_en for label_fr, label_en in ANTINUKE_ACCESS_PERM_LABELS.values())
    return (
        f"🚨 **Accès anti-nuke** : ⛔ désactivé — {role.mention} n'a aucune des permissions suivantes : {all_labels}."
        if LANG == "fr"
        else f"🚨 **Anti-nuke access**: ⛔ disabled — {role.mention} has none of: {all_labels}."
    )


async def save_guild_config(guild: discord.Guild) -> bool:
    if STORAGE_MODE == "file":
        settings = {key: _get_setting(guild.id, key) for key in DEFAULT_SETTINGS}
        whitelist = {str(k): v for k, v in _guild_store[guild.id]["whitelist"].items()}
        g = _file_store_guild(guild.id)
        g["settings"] = settings
        g["whitelist"] = whitelist
        _file_store_save()
        return True

    db_guild = get_db_guild()
    if db_guild is None:
        return False
    try:
        await save_guild_config_db(db_guild, guild)
        return True
    except Exception:
        log.exception(f"Impossible d'enregistrer la configuration sur le serveur base de données pour {guild.name}.")
        return False


async def load_guild_config(guild: discord.Guild) -> None:
    if STORAGE_MODE == "file":
        g = _file_store_guild(guild.id)
        if "settings" in g or "whitelist" in g:
            n_settings, n_whitelist = _apply_config_data(guild.id, {
                "settings": g.get("settings", {}), "whitelist": g.get("whitelist", {}),
            })
            log.info(
                f"Configuration chargée depuis le fichier local pour {guild.name} "
                f"({n_settings} réglage(s), {n_whitelist} entrée(s) en liste blanche)."
            )
        return

    db_guild = get_db_guild()
    if db_guild is not None:
        try:
            if await load_guild_config_db(db_guild, guild):
                return
        except Exception:
            log.exception(f"Échec de la lecture de la configuration sur le serveur base de données pour {guild.name} — repli sur le salon local.")
    try:
        await load_guild_config_local(guild)
    except Exception:
        log.exception(f"Impossible de charger la configuration locale pour {guild.name}.")

DANGEROUS_PERMS_TO_STRIP = [
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "manage_webhooks", "ban_members", "kick_members",
]

ANTINUKE_ROLLBACK_MINUTES = 10
ANTINUKE_ROLLBACK_DELAY_SECONDS = 2

ANTINUKE_NOTIFY_COOLDOWN_SECONDS = 600
_antinuke_last_notify: dict[int, "datetime"] = {}


def _antinuke_notification_allowed(guild_id: int) -> bool:
    """Renvoie True (et enregistre l'envoi) si aucune alerte anti-nuke n'a été
    envoyée pour ce serveur dans les ANTINUKE_NOTIFY_COOLDOWN_SECONDS dernières
    secondes. La détection/sanction/rollback anti-nuke, elles, ne sont JAMAIS
    ralenties ou sautées par ce cooldown : seul l'envoi du message l'est."""
    now = discord.utils.utcnow()
    last = _antinuke_last_notify.get(guild_id)
    if last is not None and (now - last).total_seconds() < ANTINUKE_NOTIFY_COOLDOWN_SECONDS:
        return False
    _antinuke_last_notify[guild_id] = now
    return True

WHITELIST_FILE = "audit_bot_whitelist.json"


async def _migrate_legacy_whitelist_file() -> None:
    if not os.path.exists(WHITELIST_FILE):
        return
    try:
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)
    except Exception:
        log.exception("Impossible de lire l'ancien fichier local de liste blanche pour migration.")
        return

    migrated_guild_names = []
    for gid_str, entries in legacy_data.items():
        try:
            guild_id = int(gid_str)
        except (TypeError, ValueError):
            continue
        guild = bot.get_guild(guild_id)
        if guild is None:
            continue

        current = _guild_store[guild_id]["whitelist"]
        changed = False
        for entity_id_str, kind in entries.items():
            try:
                entity_id = int(entity_id_str)
            except (TypeError, ValueError):
                continue
            if entity_id not in current:
                current[entity_id] = kind
                changed = True

        if changed:
            await save_guild_config(guild)
            migrated_guild_names.append(guild.name)

    try:
        os.replace(WHITELIST_FILE, WHITELIST_FILE + ".migrated")
    except Exception:
        log.exception("Migration de la liste blanche effectuée mais impossible de renommer l'ancien fichier local.")

    if migrated_guild_names:
        log.info(
            "Liste blanche migrée du fichier local vers la configuration Discord pour : "
            + ", ".join(migrated_guild_names)
        )


def _is_whitelisted(guild_id: int, member, channel=None) -> bool:
    entries = _guild_store.get(guild_id, {}).get("whitelist")
    if not entries:
        return False
    if member.id in entries:
        return True
    if any(r.id in entries for r in getattr(member, "roles", [])):
        return True
    if channel is not None and channel.id in entries:
        return True
    return False



MODLOG_EMOJI = {"warn": "⚠️", "mute": "🔇", "kick": "👢", "ban": "🔨", "unmute": "🔈", "unban": "🔓", "gel": "🥶", "degel": "🔥"}
MODLOG_HISTORY_SCAN_LIMIT = 2000
MODLOG_CACHE_TTL_SECONDS = 300


def _build_modlog_embed(
    kind: str, guild: discord.Guild, target: discord.abc.User, moderator: str,
    reason: str, duration_minutes: int = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"{MODLOG_EMOJI.get(kind, '•')} {kind.upper()}",
        color=0xE74C3C,
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Membre" if LANG == "fr" else "Member", value=f"{target.mention} ({target})", inline=False)
    embed.add_field(name="ID membre" if LANG == "fr" else "Member ID", value=f"`{target.id}`", inline=False)
    embed.add_field(name="Serveur" if LANG == "fr" else "Server", value=f"{guild.name} (`{guild.id}`)", inline=False)
    embed.add_field(name="Modérateur" if LANG == "fr" else "Moderator", value=moderator, inline=False)
    if duration_minutes:
        embed.add_field(name="Durée" if LANG == "fr" else "Duration", value=f"{duration_minutes} min", inline=False)
    embed.add_field(name="Raison" if LANG == "fr" else "Reason", value=reason, inline=False)
    embed.add_field(name="Heure" if LANG == "fr" else "Time", value=utc_time_str(), inline=True)
    embed.set_footer(text=f"ID:{target.id}")
    return embed


TARGET_RESPONSE_WINDOW_SECONDS = 3600
TARGET_RESPONSE_MAX_LENGTH = 100


async def _post_member_response_entry(
    guild: discord.Guild, target: discord.abc.User, kind: str, moderator: str, reason: str, response_text: str | None,
) -> None:
    """Poste une entrée de SUIVI dans l'historique (jamais une modification
    de l'entrée d'origine) donnant la version de la personne concernée, ou
    signalant l'absence de réponse dans le délai d'une heure."""
    embed = discord.Embed(
        title="📝 Version de la personne concernée" if LANG == "fr" else "📝 Target's version",
        color=0x5865F2,
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(
        name="Concernant" if LANG == "fr" else "Regarding",
        value=f"{getattr(target, 'mention', str(target))} ({target})", inline=False,
    )
    embed.add_field(
        name="Note/sanction d'origine" if LANG == "fr" else "Original note/sanction",
        value=f"{kind} — {reason}", inline=False,
    )
    if response_text:
        embed.add_field(
            name="Version donnée" if LANG == "fr" else "Version given",
            value=response_text, inline=False,
        )
    else:
        embed.add_field(
            name="Version donnée" if LANG == "fr" else "Version given",
            value=(
                "_(Aucune réponse reçue dans le délai d'une heure.)_" if LANG == "fr"
                else "_(No response received within the one-hour window.)_"
            ),
            inline=False,
        )
    embed.set_footer(text=f"ID:{target.id}")

    db_guild = get_db_guild()
    try:
        if db_guild is not None:
            guild_channel = await get_or_create_db_channel(db_guild, guild, kind)
            await guild_channel.send(embed=embed)
            thread = await get_or_create_member_thread(db_guild, target)
            await thread.send(embed=embed)
        else:
            channel = await get_or_create_local_modlog_channel(guild)
            await channel.send(embed=embed)
    except Exception:
        log.exception("Impossible de poster la version de la personne concernée dans l'historique.")


class TargetResponseModal(discord.ui.Modal):
    def __init__(self, parent_view: "TargetResponseView"):
        super().__init__(title="Ta version des faits" if LANG == "fr" else "Your version of events")
        self.parent_view = parent_view
        self.text_input = discord.ui.TextInput(
            label="Version (100 caractères max)" if LANG == "fr" else "Version (100 chars max)",
            style=discord.TextStyle.paragraph,
            max_length=TARGET_RESPONSE_MAX_LENGTH,
            required=True,
        )
        self.add_item(self.text_input)

    async def on_submit(self, interaction: discord.Interaction):
        view = self.parent_view
        if view.responded:
            await interaction.response.send_message(
                "ℹ️ Tu as déjà donné ta version." if LANG == "fr" else "ℹ️ You already gave your version.",
                ephemeral=True,
            )
            return
        view.responded = True
        text = self.text_input.value.strip()

        guild = bot.get_guild(view.guild_id)
        if guild is not None:
            await _post_member_response_entry(guild, view.target, view.kind, view.moderator_label, view.reason, text)

        view.version_button.disabled = True
        try:
            await interaction.response.edit_message(view=view)
        except Exception:
            pass
        await interaction.followup.send(
            "✅ Ta version a été ajoutée à l'historique." if LANG == "fr"
            else "✅ Your version was added to the history.",
            ephemeral=True,
        )


class TargetResponseView(discord.ui.View):
    def __init__(
        self, guild_id: int, target: discord.abc.User, kind: str, moderator_label: str, reason: str,
    ):
        super().__init__(timeout=TARGET_RESPONSE_WINDOW_SECONDS)
        self.guild_id = guild_id
        self.target = target
        self.kind = kind
        self.moderator_label = moderator_label
        self.reason = reason
        self.responded = False
        self.cancellation_requested = False

        self.version_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Donner ma version" if LANG == "fr" else "Give my version",
            emoji="📝",
            custom_id=f"target_resp_version_{target.id}_{random.randint(0, 999999)}",
        )
        self.version_button.callback = self._on_version_click
        self.add_item(self.version_button)

        self.cancel_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Demander l'annulation" if LANG == "fr" else "Request cancellation",
            emoji="⚠️",
            custom_id=f"target_resp_cancel_{target.id}_{random.randint(0, 999999)}",
        )
        self.cancel_button.callback = self._on_cancel_click
        self.add_item(self.cancel_button)

    async def _on_version_click(self, interaction: discord.Interaction):
        if self.responded:
            await interaction.response.send_message(
                "ℹ️ Tu as déjà donné ta version." if LANG == "fr" else "ℹ️ You already gave your version.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(TargetResponseModal(self))

    async def _on_cancel_click(self, interaction: discord.Interaction):
        if self.cancellation_requested:
            await interaction.response.send_message(
                "ℹ️ Ta demande a déjà été transmise." if LANG == "fr" else "ℹ️ Your request was already sent.",
                ephemeral=True,
            )
            return
        guild = bot.get_guild(self.guild_id)
        owner = None
        if guild is not None:
            try:
                owner = guild.owner or await guild.fetch_member(guild.owner_id)
            except Exception:
                owner = None

        if owner is None:
            await interaction.response.send_message(
                "❌ Impossible de joindre le/la propriétaire du serveur." if LANG == "fr"
                else "❌ Couldn't reach the server owner.",
                ephemeral=True,
            )
            return

        self.cancellation_requested = True
        embed = discord.Embed(
            title="⚠️ Demande d'annulation" if LANG == "fr" else "⚠️ Cancellation request",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Serveur" if LANG == "fr" else "Server", value=guild.name, inline=False)
        embed.add_field(
            name="Personne concernée" if LANG == "fr" else "Target",
            value=f"{getattr(self.target, 'mention', str(self.target))} ({self.target})", inline=False,
        )
        embed.add_field(name="Note/sanction" if LANG == "fr" else "Note/sanction", value=self.kind, inline=True)
        embed.add_field(name="Modérateur" if LANG == "fr" else "Moderator", value=self.moderator_label, inline=True)
        embed.add_field(name="Raison" if LANG == "fr" else "Reason", value=self.reason, inline=False)
        try:
            await owner.send(embed=embed)
        except Exception:
            log.exception("Impossible d'envoyer la demande d'annulation au/à la propriétaire du serveur.")

        self.cancel_button.disabled = True
        try:
            await interaction.response.edit_message(view=self)
        except Exception:
            pass
        await interaction.followup.send(
            "✅ Ta demande a été transmise au/à la propriétaire du serveur." if LANG == "fr"
            else "✅ Your request was sent to the server owner.",
            ephemeral=True,
        )

    async def on_timeout(self):
        if self.responded:
            return
        guild = bot.get_guild(self.guild_id)
        if guild is None:
            return
        await _post_member_response_entry(guild, self.target, self.kind, self.moderator_label, self.reason, None)


async def _start_target_response_flow(
    guild: discord.Guild, target: discord.abc.User, kind: str, moderator_label: str, reason: str,
) -> None:
    """Envoie le MP « donne ta version » à la personne concernée par une
    note ou une sanction. Échoue silencieusement (MP fermés, bot bloqué,
    etc.) — journalisé sans bloquer le reste du flux."""
    if getattr(target, "bot", False) or not hasattr(target, "send"):
        return
    view = TargetResponseView(guild.id, target, kind, moderator_label, reason)
    embed = discord.Embed(
        title="📋 Une note/sanction te concernant a été enregistrée" if LANG == "fr"
        else "📋 A note/sanction concerning you was logged",
        color=0x5865F2,
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Serveur" if LANG == "fr" else "Server", value=guild.name, inline=False)
    embed.add_field(name="Type" if LANG == "fr" else "Type", value=kind, inline=True)
    embed.add_field(name="Raison" if LANG == "fr" else "Reason", value=reason, inline=False)
    embed.add_field(
        name="Ta version" if LANG == "fr" else "Your version",
        value=(
            "Tu as **1 heure** pour donner ta version des faits (100 caractères max). "
            "Quoi qu'il arrive, elle sera aussi ajoutée à ton historique."
            if LANG == "fr" else
            "You have **1 hour** to give your version of events (100 chars max). "
            "Either way, it will also be added to your history."
        ),
        inline=False,
    )
    try:
        await target.send(embed=embed, view=view)
    except Exception:
        log.warning(f"Impossible d'envoyer le MP « donne ta version » à {target} ({getattr(target, 'id', '?')}).")


_MODLOG_SERVER_FIELD_RE = re.compile(r"\(`?(\d+)`?\)\s*$")


def _parse_modlog_embed(embed: discord.Embed) -> dict:
    footer = embed.footer.text if embed.footer else None
    if not footer or not footer.startswith("ID:"):
        return None
    fields = {f.name: f.value for f in embed.fields}
    kind = (embed.title or "").split(" ")[-1].lower()
    server_field = fields.get("Serveur") or fields.get("Server") or ""
    guild_id = None
    guild_name = server_field or None
    m = _MODLOG_SERVER_FIELD_RE.search(server_field)
    if m:
        guild_id = int(m.group(1))
        guild_name = server_field[:m.start()].strip()
    return {
        "type": kind,
        "moderator": fields.get("Modérateur") or fields.get("Moderator") or "?",
        "reason": fields.get("Raison") or fields.get("Reason") or "?",
        "date": embed.timestamp or discord.utils.utcnow(),
        "guild_name": guild_name,
        "guild_id": guild_id,
    }


MODLOG_CHANNEL_NAME = "📋-journal-moderation" if LANG == "fr" else "📋-moderation-log"

_modlog_cache_local: dict[int, dict] = {}


async def get_or_create_local_modlog_channel(guild: discord.Guild) -> discord.TextChannel:
    existing = discord.utils.get(guild.text_channels, name=MODLOG_CHANNEL_NAME)
    if existing:
        return existing

    everyone = guild.default_role
    overwrites = {
        everyone: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, embed_links=True, read_message_history=True
        ),
    }
    for role in guild.roles:
        if role.permissions.administrator and not role.is_default():
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    topic = (
        "Historique de modération (warn/mute/kick/ban) — base de données du bot, ne pas supprimer les messages."
        if LANG == "fr"
        else "Moderation history (warn/mute/kick/ban) — this is the bot's database, do not delete messages."
    )
    return await guild.create_text_channel(
        name=MODLOG_CHANNEL_NAME,
        overwrites=overwrites,
        topic=topic,
        reason="Création automatique du salon d'historique de modération",
    )


async def _scan_modlog_channel_local(channel: discord.TextChannel) -> dict:
    by_member: dict[int, list] = defaultdict(list)
    try:
        async for msg in channel.history(limit=MODLOG_HISTORY_SCAN_LIMIT):
            for embed in msg.embeds:
                entry = _parse_modlog_embed(embed)
                if entry is None:
                    continue
                footer = embed.footer.text
                member_id = int(footer[len("ID:"):])
                by_member[member_id].append(entry)
    except discord.Forbidden:
        log.warning(f"Permission manquante pour lire le salon d'historique #{channel.name}.")
    except Exception:
        log.exception("Impossible de relire le salon d'historique de modération.")

    for entries in by_member.values():
        entries.reverse()

    return {"by_member": dict(by_member), "scanned_at": discord.utils.utcnow()}


async def _get_modlog_cache_local(channel: discord.TextChannel) -> dict:
    cached = _modlog_cache_local.get(channel.id)
    if cached is not None:
        age = (discord.utils.utcnow() - cached["scanned_at"]).total_seconds()
        if age < MODLOG_CACHE_TTL_SECONDS:
            return cached
    cached = await _scan_modlog_channel_local(channel)
    _modlog_cache_local[channel.id] = cached
    return cached


async def _post_modlog_entry_local(guild: discord.Guild, kind: str, target: discord.abc.User, moderator: str, reason: str, duration_minutes: int = None) -> int:
    channel = await get_or_create_local_modlog_channel(guild)
    prior = await _fetch_modlog_entries_local(channel, target.id)
    embed = _build_modlog_embed(kind, guild, target, moderator, reason, duration_minutes)
    new_entry = {
        "type": kind, "moderator": moderator, "reason": reason, "date": discord.utils.utcnow(),
        "guild_name": guild.name, "guild_id": guild.id,
    }
    try:
        await channel.send(embed=embed)
        cache = await _get_modlog_cache_local(channel)
        cache["by_member"].setdefault(target.id, []).append(new_entry)
    except Exception:
        log.exception("Impossible de poster l'entrée d'historique de modération.")
    return len(prior) + 1


async def _fetch_modlog_entries_local(channel: discord.TextChannel, member_id: int):
    cache = await _get_modlog_cache_local(channel)
    return list(cache["by_member"].get(member_id, []))


DB_CHANNEL_NAMES = {
    "warn": ("⚠️-avertissements", "⚠️-warnings"),
    "mute": ("🔇-mutes", "🔇-mutes"),
    "unmute": ("🔈-retraits-de-sourdine", "🔈-unmutes"),
    "kick": ("👢-expulsions", "👢-kicks"),
    "ban": ("🔨-bannissements", "🔨-bans"),
    "unban": ("🔓-retraits-de-bannissement", "🔓-unbans"),
    "gel": ("🥶-gels", "🥶-freezes"),
    "degel": ("🔥-degels", "🔥-unfreezes"),
    "autre": ("📝-notes", "📝-notes"),
    "settings": ("📌-paramètres-serveur", "📌-server-settings"),
    "config": ("⚙️-config-liste-blanche", "⚙️-config-whitelist"),
    "raid": ("🚨-protocole-anti-raid", "🚨-anti-raid-protocol"),
}
MEMBER_INDEX_CATEGORY_NAME = "🗂️ Index Membres" if LANG == "fr" else "🗂️ Member Index"
MEMBER_INDEX_CHANNEL_NAME = "index"
MEMBER_THREAD_AUTO_ARCHIVE_MINUTES = 10080

_db_category_cache: dict[int, int] = {}
_db_channel_cache: dict[tuple, int] = {}
_db_index_channel_cache: dict[int, int] = {}
_db_member_thread_cache: dict[int, int] = {}
_modlog_cache_db: dict[int, dict] = {}

_raid_state: dict[int, dict] = {}

FULL_LOG_INDEX_CATEGORY_NAME = "📡 Logs Complets" if LANG == "fr" else "📡 Full Logs"
FULL_LOG_INDEX_CHANNEL_NAME = "index-logs"
FULL_LOG_THREAD_AUTO_ARCHIVE_MINUTES = 10080
FULL_LOG_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024

_full_log_index_channel_cache: dict[int, int] = {}
_full_log_thread_cache: dict[int, int] = {}

_message_log_thread_cache: dict[tuple[int, int], int] = {}


def get_db_guild() -> discord.Guild:
    if STORAGE_MODE != "discord" or not AUDIT_DB_GUILD_ID:
        return None
    return bot.get_guild(AUDIT_DB_GUILD_ID)



_file_store_cache: typing.Optional[dict] = None
_file_store_lock = threading.Lock()


def _file_store_load() -> dict:
    global _file_store_cache
    if _file_store_cache is not None:
        return _file_store_cache
    with _file_store_lock:
        if _file_store_cache is not None:
            return _file_store_cache
        if os.path.isfile(STORAGE_FILE_PATH):
            try:
                with open(STORAGE_FILE_PATH, "r", encoding="utf-8") as f:
                    _file_store_cache = json.load(f)
            except Exception:
                log.exception(f"Fichier de stockage local illisible ({STORAGE_FILE_PATH}), redémarre avec un fichier vide.")
                _file_store_cache = {}
        else:
            _file_store_cache = {}
        _file_store_cache.setdefault("guilds", {})
        return _file_store_cache


def _file_store_save() -> None:
    store = _file_store_load()
    tmp_path = STORAGE_FILE_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, STORAGE_FILE_PATH)
    except OSError:
        log.exception(f"Impossible d'écrire le fichier de stockage local ({STORAGE_FILE_PATH}).")


def _file_store_guild(guild_id: int) -> dict:
    store = _file_store_load()
    return store["guilds"].setdefault(str(guild_id), {})



IP_SECURITY_FILE = os.path.join(_SCRIPT_DIR, "audit_bot_ip_security.json")
_ip_security_lock = threading.Lock()
_ip_security_cache: typing.Optional[dict] = None


def _ip_security_load() -> dict:
    global _ip_security_cache
    if _ip_security_cache is not None:
        return _ip_security_cache
    with _ip_security_lock:
        if _ip_security_cache is not None:
            return _ip_security_cache
        if os.path.isfile(IP_SECURITY_FILE):
            try:
                with open(IP_SECURITY_FILE, "r", encoding="utf-8") as f:
                    _ip_security_cache = json.load(f)
            except Exception:
                log.exception(f"Fichier de sécurité IP illisible ({IP_SECURITY_FILE}), redémarre avec un fichier vide.")
                _ip_security_cache = {}
        else:
            _ip_security_cache = {}
        _ip_security_cache.setdefault("exclusion_counts", {})
        _ip_security_cache.setdefault("honeypot_flagged", [])
        _ip_security_cache.setdefault("member_last_ip", {})
        return _ip_security_cache


def _ip_security_save() -> None:
    store = _ip_security_load()
    tmp_path = IP_SECURITY_FILE + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, IP_SECURITY_FILE)
    except OSError:
        log.exception(f"Impossible d'écrire le fichier de sécurité IP ({IP_SECURITY_FILE}).")


def _ip_is_blacklisted(ip: str) -> bool:
    store = _ip_security_load()
    if ip in store["honeypot_flagged"]:
        return True
    return store["exclusion_counts"].get(ip, 0) >= 3


def _ip_register_exclusion(ip: str) -> int:
    """Incrémente le compteur d'exclusions (kick pour échec de vérification)
    de cette IP et renvoie le nouveau total (>= 3 = liste noire)."""
    store = _ip_security_load()
    count = store["exclusion_counts"].get(ip, 0) + 1
    store["exclusion_counts"][ip] = count
    _ip_security_save()
    return count


def _ip_flag_honeypot(ip: str) -> None:
    store = _ip_security_load()
    if ip not in store["honeypot_flagged"]:
        store["honeypot_flagged"].append(ip)
        _ip_security_save()


def _ip_remember_member(member_id: int, ip: str) -> None:
    store = _ip_security_load()
    store["member_last_ip"][str(member_id)] = ip
    _ip_security_save()


def _ip_lookup_member(member_id: int) -> typing.Optional[str]:
    store = _ip_security_load()
    return store["member_last_ip"].get(str(member_id))


_http_session: typing.Optional[aiohttp.ClientSession] = None


async def _get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session


async def _cloudflare_ip_lookup(ip: str) -> typing.Optional[dict]:
    """Détection VPN/proxy via l'API Intelligence IP de Cloudflare
    (GET /accounts/{account_id}/intel/ip). Nécessite CLOUDFLARE_ACCOUNT_ID +
    CLOUDFLARE_API_TOKEN (voir vpn_provider_setup_wizard). Renvoie None en
    cas d'erreur/indisponibilité : la détection VPN est alors simplement
    ignorée, sans bloquer le reste de la vérification."""
    if not (CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN):
        return None
    try:
        session = await _get_http_session()
        url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/intel/ip?ipv4={ip}"
        headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
    except Exception:
        log.exception(f"Cloudflare : échec de la requête Intel IP pour {ip}.")
        return None

    if not isinstance(data, dict) or not data.get("success"):
        return None
    result = data.get("result")
    info = result[0] if isinstance(result, list) and result else None
    if not isinstance(info, dict):
        return None

    risk_types = info.get("risk_types") or []
    risk_names = [str(r.get("name", "")).lower() for r in risk_types if isinstance(r, dict)]
    vpn_keywords = ("vpn", "proxy", "anonymizer", "tor")
    is_flagged = any(any(kw in name for kw in vpn_keywords) for name in risk_names)

    belongs_to = info.get("belongs_to_ref") or {}
    is_hosting = belongs_to.get("type") == "hosting_provider"

    if is_flagged:
        vpn_type = "proxy/vpn/tor (Cloudflare)"
    elif is_hosting:
        vpn_type = "hosting/datacenter (Cloudflare)"
    else:
        vpn_type = None

    return {
        "is_vpn_or_proxy": is_flagged or is_hosting,
        "type": vpn_type,
        "risk": None,
    }


async def _proxycheck_lookup(ip: str) -> typing.Optional[dict]:
    """Détection VPN/proxy/hébergement GRATUITE et SANS CLÉ via ip-api.com
    (champs `proxy`/`hosting` de leur API JSON, aucune inscription requise).
    Limité à 45 requêtes/minute par IP du bot — largement suffisant pour de
    la vérification à l'arrivée. Renvoie None en cas d'erreur/indisponibilité
    : la détection VPN est alors simplement ignorée, sans bloquer le reste
    de la vérification. Optionnel : si un fournisseur dédié a été choisi une
    fois pour toutes via vpn_provider_setup_wizard() (voir plus haut),
    Cloudflare (API Intelligence IP) ou proxycheck.io est utilisé à la place
    (détection un peu plus fine, mais nécessitant un compte)."""
    if VPN_PROVIDER_MODE == "cloudflare":
        result = await _cloudflare_ip_lookup(ip)
        if result is not None:
            return result

    if PROXYCHECK_API_KEY:
        try:
            session = await _get_http_session()
            url = f"https://proxycheck.io/v2/{ip}?key={PROXYCHECK_API_KEY}&vpn=1&asn=1"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json(content_type=None)
        except Exception:
            log.exception(f"proxycheck.io : échec de la requête pour {ip}.")
            return None
        info = data.get(ip) if isinstance(data, dict) else None
        if not isinstance(info, dict):
            return None
        return {
            "is_vpn_or_proxy": str(info.get("proxy", "no")).lower() == "yes",
            "type": info.get("type"),
            "risk": info.get("risk"),
        }

    try:
        session = await _get_http_session()
        url = f"http://ip-api.com/json/{ip}?fields=status,proxy,hosting,isp,org,as"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
    except Exception:
        log.exception(f"ip-api.com : échec de la requête pour {ip}.")
        return None
    if not isinstance(data, dict) or data.get("status") != "success":
        return None

    haystack = " ".join(
        str(data.get(field, "")) for field in ("isp", "org", "as")
    ).lower()
    keyword_hit = any(keyword in haystack for keyword in _VPN_PROVIDER_KEYWORDS)

    is_proxy = bool(data.get("proxy"))
    is_hosting = bool(data.get("hosting"))
    if is_proxy:
        vpn_type = "proxy/vpn/tor"
    elif keyword_hit:
        vpn_type = "vpn/hosting (fournisseur reconnu)" if LANG == "fr" else "vpn/hosting (known provider)"
    elif is_hosting:
        vpn_type = "hosting/datacenter"
    else:
        vpn_type = None

    return {
        "is_vpn_or_proxy": is_proxy or is_hosting or keyword_hit,
        "type": vpn_type,
        "risk": None,
    }


_VPN_PROVIDER_KEYWORDS = (
    "nordvpn", "expressvpn", "surfshark", "protonvpn", "proton vpn", "mullvad",
    "privateinternetaccess", "private internet access", "cyberghost", "ipvanish",
    "torguard", "windscribe", "vyprvpn", "hidemyass", "hotspot shield",
    "tunnelbear", "purevpn", "zenmate", "hola vpn", "atlasvpn", "atlas vpn",
    "vpn", "proxy", "tor exit", "tor network",
    "digitalocean", "ovh", "hetzner", "linode", "vultr", "scaleway",
    "amazon", "aws", "microsoft azure", "google cloud", "oracle cloud",
    "m247", "leaseweb", "choopa", "datacamp limited", "psychz",
)


def _db_category_name(guild: discord.Guild) -> str:
    suffix = f" ({guild.id})"
    max_len = max(1, 100 - len(suffix))
    return f"{guild.name[:max_len]}{suffix}"[:100]


async def get_or_create_db_category(db_guild: discord.Guild, guild: discord.Guild) -> discord.CategoryChannel:
    cached_id = _db_category_cache.get(guild.id)
    if cached_id:
        cat = db_guild.get_channel(cached_id)
        if isinstance(cat, discord.CategoryChannel):
            return cat

    suffix = f"({guild.id})"
    for cat in db_guild.categories:
        if cat.name.endswith(suffix):
            _db_category_cache[guild.id] = cat.id
            return cat

    cat = await db_guild.create_category(
        name=_db_category_name(guild),
        reason=f"Nouveau serveur modéré à historiser : {guild.name} ({guild.id})",
    )
    _db_category_cache[guild.id] = cat.id
    return cat


async def get_or_create_db_channel(db_guild: discord.Guild, guild: discord.Guild, kind: str) -> discord.TextChannel:
    key = (guild.id, kind)
    cached_id = _db_channel_cache.get(key)
    if cached_id:
        ch = db_guild.get_channel(cached_id)
        if isinstance(ch, discord.TextChannel):
            return ch

    category = await get_or_create_db_category(db_guild, guild)
    name = DB_CHANNEL_NAMES[kind][0 if LANG == "fr" else 1]
    for ch in category.text_channels:
        if ch.name == name:
            _db_channel_cache[key] = ch.id
            return ch

    ch = await category.create_text_channel(name=name, reason=f"Salon d'historique ({kind}) pour {guild.name}")
    _db_channel_cache[key] = ch.id
    return ch


async def get_or_create_member_index_channel(db_guild: discord.Guild) -> discord.TextChannel:
    cached_id = _db_index_channel_cache.get(db_guild.id)
    if cached_id:
        ch = db_guild.get_channel(cached_id)
        if isinstance(ch, discord.TextChannel):
            return ch

    category = discord.utils.get(db_guild.categories, name=MEMBER_INDEX_CATEGORY_NAME)
    if category is None:
        category = await db_guild.create_category(
            name=MEMBER_INDEX_CATEGORY_NAME, reason="Index cross-serveur des membres (historique global)"
        )
    channel = discord.utils.get(category.text_channels, name=MEMBER_INDEX_CHANNEL_NAME)
    if channel is None:
        topic = (
            "Un fil par membre, tous serveurs confondus — base de l'historique cross-serveur. Ne pas supprimer."
            if LANG == "fr"
            else "One thread per member, across all servers — backs the cross-server history. Do not delete."
        )
        channel = await category.create_text_channel(
            name=MEMBER_INDEX_CHANNEL_NAME, topic=topic, reason="Index cross-serveur des membres"
        )
    _db_index_channel_cache[db_guild.id] = channel.id
    return channel


async def _purge_member_db_traces(db_guild: discord.Guild, member_id: int) -> int:
    marker = f"ID:{member_id}"
    deleted = 0
    for category in db_guild.categories:
        if category.name == MEMBER_INDEX_CATEGORY_NAME:
            continue
        for channel in category.text_channels:
            try:
                async for msg in channel.history(limit=None):
                    if msg.author.id != bot.user.id:
                        continue
                    match = any(
                        embed.footer and embed.footer.text == marker
                        for embed in msg.embeds
                    )
                    if not match:
                        continue
                    try:
                        await msg.delete()
                        deleted += 1
                    except Exception:
                        log.exception(f"Impossible de supprimer un message d'historique dans #{channel.name}.")
                    await asyncio.sleep(0.5)
            except discord.Forbidden:
                log.warning(f"Permission manquante pour lire #{channel.name} lors de la purge.")
            except Exception:
                log.exception(f"Erreur lors de la purge du salon #{channel.name}.")
    return deleted


SERVER_SETTINGS_MESSAGE_MARKER = "AUDITBOT_SERVER_SETTINGS_V1"

SERVER_TOGGLES = {
    "webhooks": ("Webhooks allowed", True),
    "links": ("Links allowed", True),
    "invites": ("Invite links allowed", True),
    "apps": ("Applications allowed", True),
    "followers": ("Channel followers allowed", True),
}

SERVER_TOGGLE_INHERIT = {"followers": "webhooks"}

_server_toggle_cache: dict = {}


def _build_server_toggle_summary_embed(values: dict) -> discord.Embed:
    embed = discord.Embed(
        title="📌 Server settings — DO NOT EDIT THIS MESSAGE",
        color=0x5865F2,
        timestamp=discord.utils.utcnow(),
    )
    for key, (field_name, default) in SERVER_TOGGLES.items():
        embed.add_field(name=field_name, value="✅ Yes" if values.get(key, default) else "❌ No", inline=False)
    embed.add_field(name="Time", value=utc_time_str(), inline=True)
    embed.set_footer(text=SERVER_SETTINGS_MESSAGE_MARKER)
    return embed


async def _find_server_settings_message(channel: discord.TextChannel):
    async for msg in channel.history(limit=50):
        if msg.author.id == bot.user.id and msg.embeds:
            if msg.embeds[0].footer and msg.embeds[0].footer.text == SERVER_SETTINGS_MESSAGE_MARKER:
                return msg
    return None


async def get_server_toggle(guild: discord.Guild, key: str) -> bool:
    cache_key = (guild.id, key)
    if cache_key in _server_toggle_cache:
        return _server_toggle_cache[cache_key]

    field_name, value = SERVER_TOGGLES[key]
    found = False

    if STORAGE_MODE == "file":
        stored = _file_store_guild(guild.id).get("toggles", {})
        if key in stored:
            value = stored[key]
            found = True
        if not found and key in SERVER_TOGGLE_INHERIT:
            value = await get_server_toggle(guild, SERVER_TOGGLE_INHERIT[key])
        _server_toggle_cache[cache_key] = value
        return value

    db_guild = get_db_guild()
    if db_guild is not None:
        try:
            channel = await get_or_create_db_channel(db_guild, guild, "settings")
            msg = await _find_server_settings_message(channel)
            if msg is not None:
                for f in msg.embeds[0].fields:
                    if f.name == field_name:
                        value = f.value.endswith("Yes")
                        found = True
                        break
        except Exception:
            log.exception(f"Impossible de lire le réglage '{key}' pour {guild.name} — valeur par défaut utilisée.")

    if not found and key in SERVER_TOGGLE_INHERIT:
        value = await get_server_toggle(guild, SERVER_TOGGLE_INHERIT[key])

    _server_toggle_cache[cache_key] = value
    return value


async def set_server_toggle(guild: discord.Guild, key: str, allowed: bool) -> bool:
    _server_toggle_cache[(guild.id, key)] = allowed

    values = {}
    for other_key in SERVER_TOGGLES:
        values[other_key] = allowed if other_key == key else await get_server_toggle(guild, other_key)

    if STORAGE_MODE == "file":
        g = _file_store_guild(guild.id)
        g.setdefault("toggles", {}).update(values)
        _file_store_save()
        return True

    db_guild = get_db_guild()
    if db_guild is None:
        return False
    try:
        channel = await get_or_create_db_channel(db_guild, guild, "settings")
        msg = await _find_server_settings_message(channel)
        embed = _build_server_toggle_summary_embed(values)
        await _edit_or_resend(channel, msg, embed)
        return True
    except Exception:
        log.exception(f"Impossible d'enregistrer le réglage '{key}' pour {guild.name}.")
        return False


async def get_webhooks_allowed(guild: discord.Guild) -> bool:
    return await get_server_toggle(guild, "webhooks")


async def set_webhooks_allowed(guild: discord.Guild, allowed: bool) -> bool:
    return await set_server_toggle(guild, "webhooks", allowed)


async def get_apps_allowed(guild: discord.Guild) -> bool:
    return await get_server_toggle(guild, "apps")


async def set_apps_allowed(guild: discord.Guild, allowed: bool) -> bool:
    return await set_server_toggle(guild, "apps", allowed)


async def get_followers_allowed(guild: discord.Guild) -> bool:
    return await get_server_toggle(guild, "followers")


async def set_followers_allowed(guild: discord.Guild, allowed: bool) -> bool:
    return await set_server_toggle(guild, "followers", allowed)


async def get_links_allowed(guild: discord.Guild) -> bool:
    return await get_server_toggle(guild, "links")


async def set_links_allowed(guild: discord.Guild, allowed: bool) -> bool:
    return await set_server_toggle(guild, "links", allowed)


async def get_invites_allowed(guild: discord.Guild) -> bool:
    return await get_server_toggle(guild, "invites")


async def set_invites_allowed(guild: discord.Guild, allowed: bool) -> bool:
    return await set_server_toggle(guild, "invites", allowed)


async def _find_member_thread(index_channel: discord.TextChannel, member_id: int):
    name = str(member_id)
    for th in index_channel.threads:
        if th.name == name:
            return th
    try:
        async for th in index_channel.archived_threads(limit=None):
            if th.name == name:
                return th
    except Exception:
        pass
    return None


async def get_or_create_member_thread(db_guild: discord.Guild, target: discord.abc.User):
    index_channel = await get_or_create_member_index_channel(db_guild)

    cached_id = _db_member_thread_cache.get(target.id)
    if cached_id:
        thread = index_channel.get_thread(cached_id)
        if thread is not None:
            return thread

    thread = await _find_member_thread(index_channel, target.id)
    if thread is None:
        thread = await index_channel.create_thread(
            name=str(target.id),
            auto_archive_duration=MEMBER_THREAD_AUTO_ARCHIVE_MINUTES,
            type=discord.ChannelType.public_thread,
            reason="Nouveau fil d'historique cross-serveur pour ce membre",
        )
        try:
            intro = discord.Embed(
                title=str(target),
                description=f"{target.mention} — `{target.id}`",
                color=0x5865F2,
            )
            await thread.send(embed=intro)
        except Exception:
            pass
    elif thread.archived:
        try:
            await thread.edit(archived=False)
        except Exception:
            pass

    _db_member_thread_cache[target.id] = thread.id
    return thread


async def _scan_member_thread(thread) -> list:
    entries = []
    try:
        async for msg in thread.history(limit=MODLOG_HISTORY_SCAN_LIMIT, oldest_first=True):
            for embed in msg.embeds:
                entry = _parse_modlog_embed(embed)
                if entry is not None:
                    entries.append(entry)
    except discord.Forbidden:
        log.warning(f"Permission manquante pour lire le fil d'historique #{thread.name}.")
    except Exception:
        log.exception("Impossible de relire le fil d'historique de modération cross-serveur.")
    return entries


async def _get_member_cache_db(member_id: int, thread) -> dict:
    cached = _modlog_cache_db.get(member_id)
    if cached is not None:
        age = (discord.utils.utcnow() - cached["scanned_at"]).total_seconds()
        if age < MODLOG_CACHE_TTL_SECONDS:
            return cached
    entries = await _scan_member_thread(thread)
    cached = {"entries": entries, "scanned_at": discord.utils.utcnow()}
    _modlog_cache_db[member_id] = cached
    return cached


async def _fetch_modlog_entries_db(db_guild: discord.Guild, member_id: int, thread=None) -> list:
    if thread is None:
        index_channel = await get_or_create_member_index_channel(db_guild)
        thread = await _find_member_thread(index_channel, member_id)
        if thread is None:
            return []
    cache = await _get_member_cache_db(member_id, thread)
    return list(cache["entries"])


async def _post_modlog_entry_db(db_guild: discord.Guild, guild: discord.Guild, kind: str, target: discord.abc.User, moderator: str, reason: str, duration_minutes: int = None) -> int:
    embed = _build_modlog_embed(kind, guild, target, moderator, reason, duration_minutes)

    try:
        guild_channel = await get_or_create_db_channel(db_guild, guild, kind)
        await guild_channel.send(embed=embed)
    except Exception:
        log.exception("Impossible de poster l'entrée d'historique dans la catégorie du serveur.")

    thread = await get_or_create_member_thread(db_guild, target)
    prior = await _fetch_modlog_entries_db(db_guild, target.id, thread=thread)
    new_entry = {
        "type": kind, "moderator": moderator, "reason": reason, "date": discord.utils.utcnow(),
        "guild_name": guild.name, "guild_id": guild.id,
    }
    try:
        await thread.send(embed=embed)
        cache = _modlog_cache_db.setdefault(target.id, {"entries": [], "scanned_at": discord.utils.utcnow()})
        cache["entries"].append(new_entry)
    except Exception:
        log.exception("Impossible de poster l'entrée d'historique dans le fil du membre.")

    return len(prior) + 1


async def _post_modlog_entry(guild: discord.Guild, kind: str, target: discord.abc.User, moderator: str, reason: str, duration_minutes: int = None) -> int:
    db_guild = get_db_guild()
    if db_guild is not None:
        try:
            return await _post_modlog_entry_db(db_guild, guild, kind, target, moderator, reason, duration_minutes)
        except Exception:
            log.exception("Échec de l'écriture dans le serveur base de données — repli sur le salon local.")
    return await _post_modlog_entry_local(guild, kind, target, moderator, reason, duration_minutes)


async def get_member_history(guild: discord.Guild, member: discord.abc.User) -> list:
    db_guild = get_db_guild()
    if db_guild is not None:
        try:
            return await _fetch_modlog_entries_db(db_guild, member.id)
        except Exception:
            log.exception("Échec de la lecture du serveur base de données — repli sur le salon local.")
    channel = await get_or_create_local_modlog_channel(guild)
    return await _fetch_modlog_entries_local(channel, member.id)


async def get_or_create_full_log_index_channel(db_guild: discord.Guild) -> discord.TextChannel:
    cached_id = _full_log_index_channel_cache.get(db_guild.id)
    if cached_id:
        ch = db_guild.get_channel(cached_id)
        if isinstance(ch, discord.TextChannel):
            return ch

    category = discord.utils.get(db_guild.categories, name=FULL_LOG_INDEX_CATEGORY_NAME)
    if category is None:
        category = await db_guild.create_category(
            name=FULL_LOG_INDEX_CATEGORY_NAME,
            reason="Index cross-serveur des logs complets (un fil par membre)",
        )
    channel = discord.utils.get(category.text_channels, name=FULL_LOG_INDEX_CHANNEL_NAME)
    if channel is None:
        topic = (
            "Un fil par membre — journal complet de son activité (messages, éditions, suppressions). "
            "Ne pas supprimer." if LANG == "fr"
            else "One thread per member — full activity log (messages, edits, deletions). Do not delete."
        )
        channel = await category.create_text_channel(
            name=FULL_LOG_INDEX_CHANNEL_NAME, topic=topic, reason="Index cross-serveur des logs complets"
        )
    _full_log_index_channel_cache[db_guild.id] = channel.id
    return channel


async def _find_full_log_thread(index_channel: discord.TextChannel, member_id: int):
    name = str(member_id)
    for th in index_channel.threads:
        if th.name == name:
            return th
    try:
        async for th in index_channel.archived_threads(limit=None):
            if th.name == name:
                return th
    except Exception:
        pass
    return None


async def get_or_create_full_log_thread(db_guild: discord.Guild, target: discord.abc.User):
    index_channel = await get_or_create_full_log_index_channel(db_guild)

    cached_id = _full_log_thread_cache.get(target.id)
    if cached_id:
        thread = index_channel.get_thread(cached_id)
        if thread is not None:
            return thread

    thread = await _find_full_log_thread(index_channel, target.id)
    if thread is None:
        thread = await index_channel.create_thread(
            name=str(target.id),
            auto_archive_duration=FULL_LOG_THREAD_AUTO_ARCHIVE_MINUTES,
            type=discord.ChannelType.public_thread,
            reason="Nouveau fil de logs complets pour ce membre",
        )
        try:
            intro = discord.Embed(
                title=str(target),
                description=f"{target.mention} — `{target.id}`",
                color=0x2ECC71,
            )
            avatar = getattr(target, "display_avatar", None)
            if avatar:
                intro.set_thumbnail(url=avatar.url)
            await thread.send(embed=intro)
        except Exception:
            pass
    elif thread.archived:
        try:
            await thread.edit(archived=False)
        except Exception:
            pass

    _full_log_thread_cache[target.id] = thread.id
    return thread


async def _rebuild_attachments_for_log(attachments) -> tuple[list, list]:
    """Retélécharge les pièces jointes d'origine pour les reposter telles quelles (image/vidéo lisible en
    pièce jointe dans le fil de logs), avec repli en lien texte si le fichier est trop lourd ou inaccessible."""
    files = []
    notes = []
    for attachment in attachments:
        if attachment.size and attachment.size > FULL_LOG_MAX_ATTACHMENT_BYTES:
            mo = attachment.size // 1_048_576
            notes.append(
                f"📎 `{attachment.filename}` ({mo} Mo, trop lourd pour être rejoint) — lien d'origine : {attachment.url}"
            )
            continue
        try:
            data = await attachment.read()
        except Exception:
            notes.append(f"📎 `{attachment.filename}` — téléchargement impossible, lien d'origine : {attachment.url}")
            continue
        files.append(discord.File(io.BytesIO(data), filename=attachment.filename))
    return files, notes


async def _find_log_thread_by_name(channel: discord.TextChannel, name: str):
    for th in channel.threads:
        if th.name == name:
            return th
    try:
        async for th in channel.archived_threads(limit=None):
            if th.name == name:
                return th
    except Exception:
        pass
    return None


async def _find_message_log_thread(channel: discord.TextChannel, member_id: int):
    return await _find_log_thread_by_name(channel, str(member_id))


async def get_or_create_message_log_thread(channel: discord.TextChannel, target: discord.abc.User):
    """Retourne (en le créant si besoin) le fil dédié à `target` dans le salon
    de logs de messages PAR SERVEUR. Un fil = un membre, comme pour les logs
    complets sur le serveur de stockage, mais ici c'est local à ce salon."""
    cache_key = (channel.guild.id, target.id)
    cached_id = _message_log_thread_cache.get(cache_key)
    if cached_id:
        thread = channel.get_thread(cached_id)
        if thread is not None:
            return thread

    thread = await _find_message_log_thread(channel, target.id)
    if thread is None:
        thread = await channel.create_thread(
            name=str(target.id),
            auto_archive_duration=FULL_LOG_THREAD_AUTO_ARCHIVE_MINUTES,
            type=discord.ChannelType.public_thread,
            reason="Nouveau fil de logs de messages pour ce membre",
        )
        try:
            intro = discord.Embed(
                title=str(target),
                description=f"{target.mention} — `{target.id}`",
                color=0x2ECC71,
            )
            avatar = getattr(target, "display_avatar", None)
            if avatar:
                intro.set_thumbnail(url=avatar.url)
            await thread.send(embed=intro)
        except Exception:
            pass
    elif thread.archived:
        try:
            await thread.edit(archived=False)
        except Exception:
            pass

    _message_log_thread_cache[cache_key] = thread.id
    return thread


async def _post_full_log_entry(message: discord.Message, kind: str, before_content: str = None) -> None:
    """Journalise un message (envoi / édition / suppression) dans un salon DÉDIÉ
    et choisi PAR SERVEUR (jamais sur le serveur de stockage : la plupart des
    serveurs publics utilisant le bot n'y ont pas accès). Ne fait rien tant que
    le module « messagelog » n'est pas activé ET qu'un salon n'a pas été choisi
    depuis Configuration serveur. Les logs de modération (sanctions), eux,
    restent inchangés et continuent d'aller sur le serveur de stockage."""
    if message.guild is None or message.author is None or message.author.id == bot.user.id:
        return

    if not _module_enabled(message.guild.id, "messagelog"):
        return

    channel_id = _get_setting(message.guild.id, "message_log_channel_id")
    if not channel_id:
        return

    channel = message.guild.get_channel(channel_id)
    if channel is None:
        return

    if message.channel.id == channel_id:
        return

    titles = {
        "message": ("💬 Message envoyé", "💬 Message sent"),
        "edition": ("✏️ Message édité", "✏️ Message edited"),
        "suppression": ("🗑️ Message supprimé", "🗑️ Message deleted"),
    }
    title = titles.get(kind, titles["message"])[0 if LANG == "fr" else 1]

    embed = discord.Embed(title=title, color=0x2ECC71, timestamp=discord.utils.utcnow())
    avatar = getattr(message.author, "display_avatar", None)
    embed.set_author(name=str(message.author), icon_url=avatar.url if avatar else None)
    embed.add_field(
        name="Serveur" if LANG == "fr" else "Server",
        value=f"{message.guild.name} (`{message.guild.id}`)",
        inline=False,
    )
    embed.add_field(
        name="Salon" if LANG == "fr" else "Channel",
        value=getattr(message.channel, "mention", f"#{message.channel}"),
        inline=False,
    )
    if kind == "edition":
        embed.add_field(name="Avant" if LANG == "fr" else "Before", value=(before_content or "*(vide)*")[:1024], inline=False)
        embed.add_field(name="Après" if LANG == "fr" else "After", value=(message.content or "*(vide)*")[:1024], inline=False)
    else:
        embed.add_field(name="Contenu" if LANG == "fr" else "Content", value=(message.content or "*(vide)*")[:1024], inline=False)
    embed.set_footer(text=f"ID:{message.author.id}")

    files, notes = await _rebuild_attachments_for_log(message.attachments)
    if notes:
        embed.add_field(
            name="Pièces jointes non rejointes" if LANG == "fr" else "Attachments not re-attached",
            value="\n".join(notes)[:1024],
            inline=False,
        )

    try:
        thread = await get_or_create_message_log_thread(channel, message.author)
    except discord.Forbidden:
        log.warning(f"Impossible de créer/récupérer le fil de logs de messages sur {message.guild.name} (permission manquante).")
        return
    except Exception:
        log.exception(f"Impossible de créer/récupérer le fil de logs de messages sur {message.guild.name}.")
        return

    try:
        if files:
            await thread.send(embed=embed, files=files)
        else:
            await thread.send(embed=embed)
    except discord.Forbidden:
        log.warning(f"Impossible de poster dans le fil de logs de messages sur {message.guild.name} (permission manquante).")
        return
    except Exception:
        log.exception(f"Impossible de poster l'entrée de logs de messages sur {message.guild.name}.")
        return


async def _find_archived_message_content(author: discord.abc.User, channel, before_time, lookback_minutes: int = 15):
    """Cherche, dans le fil de logs complets de l'auteur, l'archive du message tel
    qu'il a été envoyé à l'origine (contenu garanti complet, contrairement à
    l'entrée de suppression qui peut arriver après expiration du cache Discord).
    Utilisé par le rollback anti-nuke pour republier un message supprimé."""
    db_guild = get_db_guild()
    if db_guild is None:
        return None
    try:
        thread = await get_or_create_full_log_thread(db_guild, author)
    except Exception:
        return None

    since = before_time - timedelta(minutes=lookback_minutes)
    try:
        async for msg in thread.history(limit=200, before=before_time, after=since, oldest_first=False):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]
            title = embed.title or ""
            if "envoyé" not in title and "sent" not in title:
                continue
            channel_field = discord.utils.get(embed.fields, name="Salon") or discord.utils.get(embed.fields, name="Channel")
            if channel_field is None:
                continue
            if getattr(channel, "mention", None) and channel_field.value != channel.mention:
                continue
            content_field = discord.utils.get(embed.fields, name="Contenu") or discord.utils.get(embed.fields, name="Content")
            content = content_field.value if content_field else ""
            files = []
            for att in msg.attachments:
                try:
                    files.append(await att.to_file())
                except Exception:
                    pass
            return content, files
    except Exception:
        log.exception("Erreur lors de la recherche du message archivé pour restauration.")
    return None



_message_hits = defaultdict(deque)
_channel_action_hits = defaultdict(deque)
_wordfilter_delete_hits: dict[tuple[int, int], deque] = defaultdict(deque)
"""(guild_id, user_id) -> horodatages des suppressions du filtre de mots sur
les 24 dernières heures. Fenêtre fixe, non personnalisable (seule la durée
de la sourdine infligée l'est) : voir WORDFILTER_SANCTION_THRESHOLD/
WORDFILTER_SANCTION_WINDOW_SECONDS et _handle_wordfilter_repeat_offender."""

WORDFILTER_SANCTION_THRESHOLD = 3
WORDFILTER_SANCTION_WINDOW_SECONDS = 86400  # 24h
_antinuke_rollback_in_progress = set()

_antinuke_actor_lock: dict[tuple[int, int], "datetime"] = {}

ANTINUKE_LOCK_MIN_SECONDS = 60


def _antinuke_lock_active(key: tuple[int, int]) -> bool:
    expires = _antinuke_actor_lock.get(key)
    if expires is None:
        return False
    if discord.utils.utcnow() >= expires:
        _antinuke_actor_lock.pop(key, None)
        return False
    return True


def _antinuke_set_lock(key: tuple[int, int], seconds: float) -> None:
    seconds = max(seconds, ANTINUKE_LOCK_MIN_SECONDS)
    _antinuke_actor_lock[key] = discord.utils.utcnow() + timedelta(seconds=seconds)


def _containment_status_text(guild: discord.Guild, member, acted: bool) -> str:
    if member is not None and getattr(member, "id", None) == guild.owner_id:
        return (
            "**PAS pu être bloqué (c'est le/la propriétaire du serveur — Discord l'interdit à "
            "n'importe quel bot, quelles que soient ses permissions)**" if LANG == "fr"
            else "**could NOT be contained (they're the server owner — Discord blocks this for "
            "any bot, regardless of its permissions)**"
        )
    return (
        ("mis en sourdine et ses rôles dangereux retirés" if acted else "**PAS pu être bloqué (permissions insuffisantes du bot)**")
        if LANG == "fr"
        else ("timed out and stripped of dangerous roles" if acted else "**could NOT be contained (insufficient bot permissions)**")
    )


def _prune_and_push(dq: deque, window_seconds: int) -> int:
    now = discord.utils.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)
    while dq and dq[0] < cutoff:
        dq.popleft()
    dq.append(now)
    return len(dq)


async def _log_security_event(guild: discord.Guild, message: str):
    try:
        channel = await get_or_create_audit_channel(guild)
        await channel.send(message)
    except Exception:
        log.exception(f"Impossible de poster l'événement de sécurité sur {guild.name}.")


async def _contain_member(guild: discord.Guild, member: discord.Member, reason: str, minutes: int = None) -> bool:
    if member.id == guild.owner_id:
        log.warning(
            f"{member} est le/la propriétaire de {guild.name} : Discord interdit à un bot de le/la "
            "mettre en sourdine ou de lui retirer des rôles, quelles que soient ses permissions. "
            "Neutralisation impossible par nature (teste avec un compte qui n'est pas propriétaire)."
        )
        return False

    acted = False
    if minutes is None:
        minutes = _get_setting(guild.id, "spam_timeout_minutes")

    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        acted = True
    except discord.Forbidden:
        log.warning(f"Impossible de mettre {member} en sourdine (permission manquante).")
    except Exception:
        log.exception(f"Erreur en tentant de mettre {member} en sourdine.")

    dangerous_roles = [
        r for r in member.roles
        if any(getattr(r.permissions, p, False) for p in DANGEROUS_PERMS_TO_STRIP)
    ]
    if dangerous_roles:
        try:
            await member.remove_roles(*dangerous_roles, reason=reason)
            acted = True
        except discord.Forbidden:
            log.warning(f"Impossible de retirer les rôles de {member} (permission/hiérarchie insuffisante).")
        except Exception:
            log.exception(f"Erreur en tentant de retirer les rôles de {member}.")

    return acted


async def _notify_guild_owner_welcome(guild: discord.Guild) -> None:
    """Envoie un MP au/à la propriétaire du serveur (et seulement à
    lui/elle) dès que le bot rejoint — TOUJOURS, sans condition. Explique ce
    qu'est le bot (Open Source), à quoi il sert, comment le configurer, et
    donne les liens d'invitation vers le serveur de support et le serveur
    du bot dédié. Le nom du bot/développeur et les deux liens viennent du
    .env : BOT_DISPLAY_NAME, BOT_DEVELOPER_NAME, BOT_SUPPORT_SERVER_INVITE,
    BOT_DEV_SERVER_INVITE — si un lien n'est pas configuré, la ligne
    correspondante est simplement omise, le reste du message part quand
    même. La ligne "version modifiée" est FIXE (JOIN_MODIFIED_NOTE_DEFAULT) :
    aucune commande ne permet plus de la modifier ou de la masquer, par
    serveur ou autrement."""
    display_name = os.environ.get("BOT_DISPLAY_NAME", "").strip() or bot.user.name
    dev_name = os.environ.get("BOT_DEVELOPER_NAME", "").strip()
    bot_invite = os.environ.get("BOT_SUPPORT_SERVER_INVITE", "https://discord.gg/xkgP9rv84k").strip()
    dev_invite = os.environ.get("BOT_DEV_SERVER_INVITE", "https://discord.gg/6S4Mvp7Q8v").strip()
    join_note = JOIN_MODIFIED_NOTE_DEFAULT.strip()

    try:
        owner = guild.owner or await guild.fetch_member(guild.owner_id)
    except Exception:
        owner = None
    if owner is None:
        log.warning(f"Impossible de retrouver le/la propriétaire de {guild.name} pour le MP de bienvenue.")
        return

    if LANG == "fr":
        lines = [
            f"👋 Bonjour ! Je suis **{display_name}**, et je viens d'être ajouté(e) sur "
            f"**{guild.name}**.",
            (f"Je suis un bot **Open Source**, développé par **{dev_name}**." if dev_name
             else "Je suis un bot **Open Source**."),
        ]
        if join_note:
            lines.append(f"⚠️ {join_note}")
        lines += [
            "",
            "**🛡️ À quoi je sers**",
            "Modération et sécurité automatisées pour ton serveur : anti-raid, anti-nuke "
            "(détection et annulation des actions destructrices), gestion des sanctions "
            "(avertissements, mises en sourdine, bannissements avec historique), liste "
            "blanche de webhooks/liens/invitations, et audit de sécurité du serveur.",
            "",
            "**⚙️ Comment me configurer**",
            "Tape `/panel` sur ton serveur (réservé aux administrateurs) : c'est le panel "
            "unique qui regroupe tous les réglages — webhooks, liens, invitations, rôles "
            "staff, liste blanche, audit. Tu peux aussi lancer `/protocole-anti-raid` pour "
            "activer une protection renforcée en cas d'attaque en cours.",
        ]
        if bot_invite or dev_invite:
            lines += ["", "**🔗 Besoin d'aide ?**"]
            if bot_invite:
                lines.append(f"Serveur de support du bot : {bot_invite}")
            if dev_invite:
                lines.append(f"Serveur dédié du développeur : {dev_invite}")
    else:
        lines = [
            f"👋 Hi! I'm **{display_name}**, and I've just been added to **{guild.name}**.",
            (f"I'm an **Open Source** bot, developed by **{dev_name}**." if dev_name
             else "I'm an **Open Source** bot."),
        ]
        if join_note:
            lines.append(f"⚠️ {join_note}")
        lines += [
            "",
            "**🛡️ What I do**",
            "Automated moderation and security for your server: anti-raid, anti-nuke "
            "(detects and reverts destructive actions), sanctions management (warnings, "
            "mutes, bans with history), webhook/link/invite whitelisting, and server "
            "security audits.",
            "",
            "**⚙️ How to configure me**",
            "Run `/panel` on your server (admins only): it's the single panel for every "
            "setting — webhooks, links, invites, staff roles, whitelist, audit. You can "
            "also run `/anti-raid-protocol` to enable stronger protection during an "
            "ongoing attack.",
        ]
        if bot_invite or dev_invite:
            lines += ["", "**🔗 Need help?**"]
            if bot_invite:
                lines.append(f"Bot support server: {bot_invite}")
            if dev_invite:
                lines.append(f"Developer's dedicated server: {dev_invite}")

    text = "\n".join(lines)

    try:
        await owner.send(text)
        log.info(f"MP de bienvenue envoyé au/à la propriétaire de {guild.name} ({guild.owner_id}).")
    except Exception:
        log.warning(f"Impossible d'envoyer le MP de bienvenue au/à la propriétaire de {guild.name} (MP fermés ?).")


async def _notify_guild_owner_antinuke_detected(
    guild: discord.Guild, actor: discord.abc.User, count: int, label: str, status: str, window_seconds: int,
) -> None:
    """Prévient le/la propriétaire du serveur qu'un auteur (bot OU humain) a
    été repéré par l'anti-nuke — pas seulement loggé dans le salon d'audit.
    Soumis au cooldown anti-spam (voir _antinuke_notification_allowed) : ce
    n'est PAS cette fonction qui décide si elle doit parler, l'appelant a déjà
    vérifié le cooldown avant de la lancer."""
    try:
        owner = guild.owner or await guild.fetch_member(guild.owner_id)
    except Exception:
        owner = None
    if owner is None:
        log.warning(f"Impossible de retrouver le/la propriétaire de {guild.name} pour le notifier.")
        return

    who = ("le bot" if getattr(actor, "bot", False) else "le membre") if LANG == "fr" else ("bot" if getattr(actor, "bot", False) else "member")

    text = (
        f"🚨 **Alerte anti-nuke** sur **{guild.name}** : {who} **{actor}** (`{actor.id}`) a fait "
        f"{count} {label} en {window_seconds}s. Il/elle a été {status}, "
        f"et ses actions des {ANTINUKE_ROLLBACK_MINUTES} dernières minutes ont été annulées.\n"
        f"-# D'autres alertes anti-nuke ont pu survenir depuis ; retrouve le détail complet dans le salon "
        f"d'audit de sécurité (au plus une notification anti-nuke ici toutes les "
        f"{ANTINUKE_NOTIFY_COOLDOWN_SECONDS // 60} minutes)."
        if LANG == "fr"
        else
        f"🚨 **Anti-nuke alert** on **{guild.name}**: the {who} **{actor}** (`{actor.id}`) performed "
        f"{count} {label} in {window_seconds}s. They were {status}, "
        f"and their actions from the last {ANTINUKE_ROLLBACK_MINUTES} minutes have been reverted.\n"
        f"-# More anti-nuke alerts may have happened since; check the security audit channel for full "
        f"details (at most one anti-nuke notification here every {ANTINUKE_NOTIFY_COOLDOWN_SECONDS // 60} minutes)."
    )
    try:
        await owner.send(text)
    except Exception:
        log.warning(f"Impossible d'envoyer un MP au/à la propriétaire de {guild.name} (MP fermés ?).")


async def _apply_antinuke_sanction(
    guild: discord.Guild, actor: discord.abc.User, reason: str, sanction: str,
) -> tuple[bool, str]:
    """Applique la sanction anti-nuke choisie ('ban', 'kick' ou 'timeout') sur
    l'auteur repéré. 'timeout' met en sourdine + retire les rôles dangereux
    (impossible pour un membre qui a déjà quitté/été banni)."""
    if sanction == "ban":
        try:
            await guild.ban(actor, reason=reason, delete_message_seconds=0)
            return True, "ban"
        except discord.Forbidden:
            log.warning(f"Impossible de bannir {actor} (permission/hiérarchie insuffisante).")
            return False, "ban_failed"
        except Exception:
            log.exception(f"Erreur en tentant de bannir {actor}.")
            return False, "ban_failed"

    if sanction == "kick":
        member = actor if isinstance(actor, discord.Member) else guild.get_member(actor.id)
        if member is None:
            return False, "not_found"
        try:
            await guild.kick(member, reason=reason)
            return True, "kick"
        except discord.Forbidden:
            log.warning(f"Impossible d'expulser {actor} (permission/hiérarchie insuffisante).")
            return False, "kick_failed"
        except Exception:
            log.exception(f"Erreur en tentant d'expulser {actor}.")
            return False, "kick_failed"

    if sanction == "strip_roles":
        member = actor if isinstance(actor, discord.Member) else guild.get_member(actor.id)
        if member is None:
            return False, "not_found"
        dangerous_roles = [
            r for r in member.roles
            if any(getattr(r.permissions, p, False) for p in DANGEROUS_PERMS_TO_STRIP)
        ]
        if not dangerous_roles:
            return True, "strip_roles"
        try:
            await member.remove_roles(*dangerous_roles, reason=reason)
            return True, "strip_roles"
        except discord.Forbidden:
            log.warning(f"Impossible de retirer les rôles de {actor} (permission/hiérarchie insuffisante).")
            return False, "strip_roles_failed"
        except Exception:
            log.exception(f"Erreur en tentant de retirer les rôles de {actor}.")
            return False, "strip_roles_failed"

    if sanction == "warn":
        return True, "warn"

    member = actor if isinstance(actor, discord.Member) else guild.get_member(actor.id)
    if member is None:
        return False, "not_found"
    minutes = _get_setting(guild.id, "antinuke_human_timeout_minutes")
    acted = await _contain_member(guild, member, reason, minutes=minutes)
    return acted, "timeout" if acted else "timeout_failed"


async def _punish_antinuke_actor(guild: discord.Guild, actor: discord.abc.User, reason: str) -> tuple[bool, str]:
    """Sanction anti-nuke : la sanction appliquée dépend du type d'auteur (bot
    ou humain) et du choix fait dans le panel de configuration du serveur
    ('antinuke_bot_sanction' / 'antinuke_human_sanction')."""
    if actor.id == guild.owner_id:
        return False, "owner"

    is_bot = getattr(actor, "bot", False)
    setting_key = "antinuke_bot_sanction" if is_bot else "antinuke_human_sanction"
    default_sanction = "ban" if is_bot else "timeout"
    sanction = _get_setting(guild.id, setting_key) or default_sanction
    return await _apply_antinuke_sanction(guild, actor, reason, sanction)


async def _resolve_invite_is_foreign(guild: discord.Guild, code: str) -> bool:
    try:
        invite = await bot.fetch_invite(code)
        target_guild = getattr(invite, "guild", None)
        if target_guild is None:
            return True
        return target_guild.id != guild.id
    except Exception:
        return True


async def _safe_delete(message: discord.Message):
    try:
        await message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    except Exception:
        log.exception(f"Impossible de supprimer le message {message.id}.")


async def check_phishing(message: discord.Message) -> bool:
    content = message.content or ""
    if not (PHISHING_DOMAIN_REGEX.search(content) or IP_URL_REGEX.search(content)):
        return False

    guild, author, channel = message.guild, message.author, message.channel
    await _safe_delete(message)
    automod_minutes = _get_setting(guild.id, "automod_timeout_minutes")
    reason = "Auto-modération : lien de phishing détecté" if LANG == "fr" else "Automated moderation: phishing link detected"
    acted = await _contain_member(guild, author, reason, minutes=automod_minutes) if isinstance(author, discord.Member) else False
    await _post_modlog_entry(
        guild, "mute" if acted else "warn", author, str(bot.user),
        "Lien de phishing détecté" if LANG == "fr" else "Phishing link detected",
    )
    await _log_security_event(
        guild, t("automod_phishing", author=str(author), channel=channel.name, minutes=automod_minutes),
    )
    return True


async def check_scam_text(message: discord.Message) -> bool:
    content = message.content or ""
    scam_hits = sum(1 for pattern in SCAM_GIVEAWAY_PATTERNS if re.search(pattern, content, re.IGNORECASE))
    if scam_hits < 2:
        return False

    guild, author, channel = message.guild, message.author, message.channel
    await _safe_delete(message)
    automod_minutes = _get_setting(guild.id, "automod_timeout_minutes")
    reason = (
        "Auto-modération : texte correspondant à un modèle d'arnaque (faux giveaway crypto)" if LANG == "fr"
        else "Automated moderation: text matches a scam pattern (fake crypto giveaway)"
    )
    acted = await _contain_member(guild, author, reason, minutes=automod_minutes) if isinstance(author, discord.Member) else False
    await _post_modlog_entry(
        guild, "mute" if acted else "warn", author, str(bot.user),
        "Arnaque de type faux giveaway crypto détectée" if LANG == "fr" else "Fake crypto giveaway scam detected",
    )
    await _log_security_event(
        guild, t("automod_scam_text", author=str(author), channel=channel.name, minutes=automod_minutes),
    )
    return True


async def check_mass_mentions(message: discord.Message) -> bool:
    guild, author, channel = message.guild, message.author, message.channel
    distinct_mentions = len(set(m.id for m in message.mentions))
    if distinct_mentions < _get_setting(guild.id, "mass_mention_threshold"):
        return False

    await _safe_delete(message)
    automod_minutes = _get_setting(guild.id, "automod_timeout_minutes")
    reason = (
        f"Auto-modération : {distinct_mentions} mentions dans un seul message" if LANG == "fr"
        else f"Automated moderation: {distinct_mentions} mentions in a single message"
    )
    acted = await _contain_member(guild, author, reason, minutes=automod_minutes) if isinstance(author, discord.Member) else False
    await _post_modlog_entry(guild, "mute" if acted else "warn", author, str(bot.user), reason)
    await _log_security_event(
        guild, t("automod_mentions", author=str(author), channel=channel.name, minutes=automod_minutes, count=distinct_mentions),
    )
    return True


async def check_invite(message: discord.Message) -> bool:
    content = message.content or ""
    guild, author, channel = message.guild, message.author, message.channel
    invite_match = INVITE_REGEX.search(content)
    if not invite_match:
        return False

    invites_allowed = await get_invites_allowed(guild)
    if invites_allowed:
        return False

    reason = (
        "Invitation Discord alors que les invitations sont interdites sur ce serveur (/server-invites)"
        if LANG == "fr"
        else "Discord invite while invites are disabled on this server (/server-invites)"
    )

    await _safe_delete(message)
    await _post_modlog_entry(guild, "warn", author, str(bot.user), reason)
    await _log_security_event(guild, t("automod_invite", author=str(author), channel=channel.name))
    return True


async def check_links(message: discord.Message) -> bool:
    if await get_links_allowed(message.guild):
        return False
    content = message.content or ""
    if not URL_REGEX.search(content):
        return False

    guild, author, channel = message.guild, message.author, message.channel
    await _safe_delete(message)
    await _post_modlog_entry(
        guild, "warn", author, str(bot.user),
        "Lien posté alors que les liens sont interdits sur ce serveur (/server-links)" if LANG == "fr"
        else "Posted a link while links are disabled on this server (/server-links)",
    )
    await _log_security_event(guild, t("automod_link_blocked", author=str(author), channel=channel.name))
    return True


async def check_caps(message: discord.Message) -> bool:
    content = message.content or ""
    guild, author, channel = message.guild, message.author, message.channel
    letters = [c for c in content if c.isalpha()]
    if len(content) < _get_setting(guild.id, "caps_min_length") or not letters:
        return False
    caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if caps_ratio < _get_setting(guild.id, "caps_ratio_threshold"):
        return False

    await _safe_delete(message)
    await _log_security_event(guild, t("automod_caps", author=str(author), channel=channel.name))
    return True


def _compile_banned_word_pattern(word: str) -> "re.Pattern | None":
    escaped = re.escape(word.strip())
    if not escaped:
        return None
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE | re.UNICODE)


async def check_banned_words(message: discord.Message) -> bool:
    """Filtre de mots interdits — liste 100% manuelle par serveur, vide par
    défaut. Module séparé de l'auto-modération (/mots-interdits, panel),
    activable/désactivable indépendamment.

    Anti-spam : chaque suppression déclenchée par ce filtre est comptée sur
    une fenêtre glissante de 24h par membre. Au-delà de
    WORDFILTER_SANCTION_THRESHOLD (3) suppressions, une sanction automatique
    (mute/kick/ban, choisie dans le panel) est appliquée EN PLUS de la simple
    suppression du message — voir _handle_wordfilter_repeat_offender. Cette
    sanction ne peut pas être désactivée tant que le module filtre de mots
    est actif : sans elle, une personne qui spam des mots interdits ferait
    supprimer message après message par le bot sans jamais être arrêtée, ce
    qui finit par déclencher des rate limits Discord à répétition (risque
    réel de ban IP pour le compte du bot)."""
    guild = message.guild
    if not _module_enabled(guild.id, "wordfilter"):
        return False
    words = _get_setting(guild.id, "banned_words_list") or []
    if not words:
        return False
    content = message.content or ""
    if not content:
        return False
    for word in words:
        pattern = _compile_banned_word_pattern(word)
        if pattern is not None and pattern.search(content):
            await _safe_delete(message)
            await _log_security_event(
                guild, t("automod_wordfilter", author=str(message.author), channel=message.channel.name, word=word),
            )
            await _handle_wordfilter_repeat_offender(message)
            return True
    return False


async def _handle_wordfilter_repeat_offender(message: discord.Message) -> None:
    """Compte les suppressions du filtre de mots par membre sur une fenêtre
    glissante fixe de 24h (WORDFILTER_SANCTION_WINDOW_SECONDS, non
    personnalisable) ; au WORDFILTER_SANCTION_THRESHOLD-ième (3) message
    supprimé, applique automatiquement la sanction configurée par le serveur
    (mute/kick/ban — 'wordfilter_sanction_type', mute par défaut) puis
    réinitialise le compteur. La durée du mute ('wordfilter_mute_minutes')
    est la SEULE valeur personnalisable par les serveurs, entre 5 minutes et
    24h (voir CONFIG_META)."""
    guild = message.guild
    member = message.author if isinstance(message.author, discord.Member) else None
    if member is None or member.bot:
        return

    key = (guild.id, member.id)
    hits = _prune_and_push(_wordfilter_delete_hits[key], WORDFILTER_SANCTION_WINDOW_SECONDS)
    if hits < WORDFILTER_SANCTION_THRESHOLD:
        return

    _wordfilter_delete_hits[key].clear()

    sanction_type = _get_setting(guild.id, "wordfilter_sanction_type") or "mute"
    if sanction_type not in ("mute", "kick", "ban"):
        sanction_type = "mute"
    mute_minutes = _get_setting(guild.id, "wordfilter_mute_minutes") or 60
    reason = (
        f"Auto-modération : {WORDFILTER_SANCTION_THRESHOLD} messages supprimés par le filtre de mots en 24h"
        if LANG == "fr"
        else f"Automated moderation: {WORDFILTER_SANCTION_THRESHOLD} messages removed by the word filter in 24h"
    )

    acted = False
    try:
        if sanction_type == "ban":
            await guild.ban(member, reason=reason, delete_message_seconds=0)
            acted = True
        elif sanction_type == "kick":
            await member.kick(reason=reason)
            acted = True
        else:
            await member.timeout(timedelta(minutes=mute_minutes), reason=reason)
            acted = True
    except discord.Forbidden:
        log.warning(f"Filtre de mots : permission insuffisante pour sanctionner {member} sur {guild.name}.")
    except Exception:
        log.exception(f"Filtre de mots : erreur en tentant de sanctionner {member} sur {guild.name}.")

    await _post_modlog_entry(
        guild, sanction_type if acted else "warn", member, str(bot.user), reason,
        duration_minutes=mute_minutes if (sanction_type == "mute" and acted) else None,
    )

    if acted:
        sanction_label = WORDFILTER_SANCTION_CHOICES.get(sanction_type, WORDFILTER_SANCTION_CHOICES["mute"])
        await _log_security_event(
            guild,
            t(
                "automod_wordfilter_sanction",
                author=str(member), channel=message.channel.name,
                sanction=sanction_label["fr" if LANG == "fr" else "en"],
            ),
        )
    else:
        await _log_security_event(
            guild,
            t("automod_wordfilter_sanction_failed", author=str(member), channel=message.channel.name),
        )


CONTENT_AUTOMOD_CHECKS = [
    check_phishing,
    check_scam_text,
    check_mass_mentions,
    check_invite,
    check_links,
]


async def _check_content_automod(message: discord.Message) -> bool:
    if not _module_enabled(message.guild.id, "automod"):
        return False
    for check in CONTENT_AUTOMOD_CHECKS:
        if await check(message):
            return True
    return False


def _webhook_message_kind(message: discord.Message) -> typing.Optional[str]:
    """Classe un message posté « par un webhook » selon les 3 types d'intégrations
    de Discord, pour que chacun soit réglable séparément :
      - "follower"    : suivi de salon (message publié depuis un salon d'annonces
                        d'un autre serveur, flag IS_CROSSPOSTED) ;
      - "application" : réponse d'une application à une commande/interaction ;
      - "incoming"    : webhook classique (URL de webhook).
    Renvoie None si le message ne vient pas d'un webhook."""
    if message.webhook_id is None:
        return None
    if message.flags.is_crossposted:
        return "follower"
    if message.interaction_metadata is not None:
        return "application"
    return "incoming"


async def _integration_message_blocked(message: discord.Message, kind: typing.Optional[str]) -> bool:
    """True si ce message doit être supprimé d'après les réglages du serveur."""
    if kind == "incoming":
        return not await get_webhooks_allowed(message.guild)
    if kind == "follower":
        return not await get_followers_allowed(message.guild)
    if kind == "application":
        if await get_apps_allowed(message.guild):
            return False
        app_id = getattr(message, "application_id", None) or message.author.id
        return message.guild.get_member(app_id) is None
    return False


def _integration_block_notice(message: discord.Message, kind: str) -> str:
    fr = {
        "incoming": ("un webhook", "webhooks-serveur"),
        "follower": ("un suivi de salon", "suivis-serveur"),
        "application": ("une application externe non installée sur ce serveur", "application-externe-serveur"),
    }
    en = {
        "incoming": ("a webhook", "server-webhooks"),
        "follower": ("a channel follow", "server-followers"),
        "application": ("an external application not installed on this server", "server-external-app"),
    }
    if LANG == "fr":
        what, cmd = fr[kind]
        return (
            f"⚠️ Message supprimé : {what} (`{message.webhook_id}`, pas un membre réel du serveur) "
            f"a posté dans #{message.channel.name} sur **{message.guild.name}**, alors que ce type "
            f"d'intégration est réglé sur **interdit** (`/{cmd}`).\n"
            "Je ne peux pas signaler ceci à Discord automatiquement (aucune API bot publique pour ça) : "
            "faites-le vous-même via **Signaler** si c'est malveillant. Vérifiez aussi les intégrations "
            "du salon (Paramètres du salon > Intégrations)."
        )
    what, cmd = en[kind]
    return (
        f"⚠️ Message deleted: {what} (`{message.webhook_id}`, not a real server member) posted in "
        f"#{message.channel.name} on **{message.guild.name}**, while this integration type is set "
        f"to **disallowed** (`/{cmd}`).\n"
        "I can't report this to Discord automatically (no public bot API for that): please do it "
        "yourself via **Report** if it's malicious. Also check the channel's integrations "
        "(Channel Settings > Integrations)."
    )


_active_purge_targets: set[tuple[int, int]] = set()
"""Ensemble de (guild_id, user_id) actuellement en cours de purge par
_purge_recent_messages_everywhere. Sert à ce que on_message_delete ne poste
PAS une entrée de log complet pour chaque suppression individuelle : quand
la personne piégée a posté dans beaucoup de salons, la purge peut supprimer
un message à la fois dans chacun (Discord ne permet le bulk-delete groupé
qu'à partir de 2 messages par salon), et logguer chacune de ces suppressions
individuellement peut envoyer des dizaines de messages en quelques secondes
vers le même salon de logs -> déclenche des rate limits Discord à répétition
(risque réel pour le compte du bot). L'action de sanction elle-même reste
tracée normalement via _post_modlog_entry : aucune perte d'information."""


async def _purge_recent_messages_everywhere(guild: discord.Guild, user_id: int, hours: int) -> int:
    """Supprime tous les messages envoyés par `user_id` sur TOUT le serveur
    (tous les salons textuels) durant les `hours` dernières heures. Utilisé
    par le salon piège pour effacer l'historique récent d'un compte qui
    vient de se faire sanctionner. Le bulk-delete de Discord ne fonctionne
    que sur les messages de moins de 14 jours ; discord.py bascule alors
    automatiquement en suppression une par une, donc rien à gérer ici.

    Le passage par _active_purge_targets évite en plus une rafale de posts de
    log individuels (voir sa docstring), et une petite pause entre chaque
    salon évite de marteler l'API Discord d'un coup sur un serveur qui en a
    beaucoup."""
    cutoff = discord.utils.utcnow() - timedelta(hours=hours)
    deleted = 0
    key = (guild.id, user_id)
    _active_purge_targets.add(key)
    try:
        for channel in guild.text_channels:
            try:
                removed = await channel.purge(
                    limit=MODLOG_HISTORY_SCAN_LIMIT,
                    after=cutoff,
                    check=lambda m: m.author.id == user_id,
                    reason="Salon piège : purge des messages récents de l'auteur",
                )
                deleted += len(removed)
            except discord.Forbidden:
                continue
            except Exception:
                log.exception(f"Salon piège : échec de la purge dans #{channel.name} sur {guild.name}.")
                continue
            await asyncio.sleep(0.3)
    finally:
        _active_purge_targets.discard(key)
    return deleted


async def _handle_honeypot_message(message: discord.Message) -> bool:
    """Si le message a été posté dans le salon piège : le supprime, applique
    la sanction configurée (mute/kick/ban, mute 1 semaine par défaut) et
    purge tous les messages de l'auteur sur le serveur entier durant la
    fenêtre configurée (1 semaine par défaut). Renvoie True si le message a
    déclenché le piège (et a donc déjà été traité)."""
    guild = message.guild
    if message.author.bot:
        return False
    if not _module_enabled(guild.id, "honeypot"):
        return False
    channel_id = _get_setting(guild.id, "honeypot_channel_id")
    if not channel_id or message.channel.id != channel_id:
        return False

    try:
        await message.delete()
    except Exception:
        pass

    sanction_type = _get_setting(guild.id, "honeypot_sanction_type")
    mute_minutes = _get_setting(guild.id, "honeypot_mute_minutes")
    lookback_hours = _get_setting(guild.id, "honeypot_delete_lookback_hours")
    reason = (
        f"Salon piège : message écrit dans #{message.channel.name}" if LANG == "fr"
        else f"Honeypot: message posted in #{message.channel.name}"
    )

    member = message.author if isinstance(message.author, discord.Member) else None
    acted = False
    try:
        if sanction_type == "ban":
            await guild.ban(message.author, reason=reason, delete_message_seconds=0)
            acted = True
        elif sanction_type == "kick":
            if member is not None:
                await member.kick(reason=reason)
                acted = True
        else:
            if member is not None:
                await member.timeout(timedelta(minutes=mute_minutes), reason=reason)
                acted = True
    except discord.Forbidden:
        log.warning(f"Salon piège : permission insuffisante pour sanctionner {message.author} sur {guild.name}.")
    except Exception:
        log.exception(f"Salon piège : erreur en sanctionnant {message.author} sur {guild.name}.")

    deleted_count = await _purge_recent_messages_everywhere(guild, message.author.id, lookback_hours)

    global_catch_count = _increment_honeypot_global_catch_count()
    asyncio.create_task(_refresh_all_honeypot_counters())

    known_ip = _ip_lookup_member(message.author.id)
    if known_ip:
        _ip_flag_honeypot(known_ip)

    await _post_modlog_entry(
        guild, sanction_type if acted else "warn", message.author, str(bot.user), reason,
        duration_minutes=mute_minutes if (sanction_type == "mute" and acted) else None,
    )
    sanction_label = HONEYPOT_SANCTION_CHOICES.get(sanction_type, HONEYPOT_SANCTION_CHOICES["mute"])
    await _log_security_event(
        guild,
        (
            f"🍯 Salon piège déclenché par **{message.author}** (`{message.author.id}`) — sanction : "
            f"{sanction_label['fr']}{'' if acted else ' (échec — permission manquante ?)'}. "
            f"{deleted_count} message(s) supprimé(s) sur tout le serveur (dernières {lookback_hours}h).\n"
            f"📊 Total de personnes piégées sur TOUS les serveurs (depuis toujours) : **{global_catch_count}**"
        ) if LANG == "fr" else (
            f"🍯 Honeypot triggered by **{message.author}** (`{message.author.id}`) — sanction: "
            f"{sanction_label['en']}{'' if acted else ' (failed — missing permission?)'}. "
            f"{deleted_count} message(s) deleted server-wide (past {lookback_hours}h).\n"
            f"📊 Total people caught across ALL servers (all-time): **{global_catch_count}**"
        ),
    )
    return True


@bot.event
async def on_thread_create(thread: discord.Thread):
    """Sans rejoindre explicitement un fil (public OU privé), le bot ne
    reçoit pas forcément ses messages via le websocket selon ses permissions
    (notamment pour les fils PRIVÉS, où l'appartenance est requise) — ce qui
    faisait échapper certains fils/posts de forum au filtre de mots
    interdits et au reste de l'auto-modération. On rejoint donc
    systématiquement tout nouveau fil dès sa création."""
    try:
        await thread.join()
    except (discord.Forbidden, discord.HTTPException):
        log.warning(f"Impossible de rejoindre le nouveau fil #{thread.name} sur {thread.guild.name} (permission manquante).")
    except Exception:
        log.exception(f"Erreur en tentant de rejoindre le nouveau fil #{thread.name}.")


async def _join_all_existing_threads() -> None:
    """Au démarrage : rejoint tout fil déjà existant (actif) auquel le bot
    n'appartient pas encore, sur tous les serveurs — comble les trous pour
    les fils/posts de forum créés avant ce correctif ou pendant que le bot
    était hors ligne. Les fils archivés n'ont pas besoin d'être rejoints
    (ils ne reçoivent plus de nouveaux messages tant qu'ils ne sont pas
    ré-ouverts, ce qui redéclenche alors un thread_update, pas thread_create
    — cas marginal, non couvert ici pour ne pas surcharger l'API au démarrage)."""
    joined = 0
    for guild in bot.guilds:
        try:
            for thread in guild.threads:
                if thread.me is None:
                    try:
                        await thread.join()
                        joined += 1
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    except Exception:
                        log.exception(f"Erreur en rejoignant le fil existant #{thread.name} sur {guild.name}.")
        except Exception:
            log.exception(f"Impossible de lister les fils existants sur {guild.name}.")
    if joined:
        log.info(f"{joined} fil(s) existant(s) rejoint(s) au démarrage (couverture complète de l'auto-modération).")


@bot.event
async def on_message(message: discord.Message):
    if message.guild is None or message.author.id == bot.user.id:
        return

    if message.channel.name == CONFIG_CHANNEL_NAME:
        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass
        except Exception:
            log.exception("Impossible de supprimer un message dans le salon de configuration.")
        return

    if message.webhook_id is not None:
        kind = _webhook_message_kind(message)
        if await _integration_message_blocked(message, kind):
            try:
                await message.delete()
            except Exception:
                pass
            await _log_security_event(message.guild, _integration_block_notice(message, kind))
            return

    if not message.author.bot:
        asyncio.create_task(_post_full_log_entry(message, "message"))

    if isinstance(message.author, discord.Member) and _is_whitelisted(message.guild.id, message.author, message.channel):
        await bot.process_commands(message)
        return

    if await _handle_honeypot_message(message):
        return

    if message.content:
        handled = await _check_content_automod(message)
        if handled:
            return
        handled = await check_banned_words(message)
        if handled:
            return

    spam_window = _get_setting(message.guild.id, "spam_window_seconds")
    spam_key = (message.guild.id, message.author.id)
    count = _prune_and_push(_message_hits[spam_key], spam_window)
    if _module_enabled(message.guild.id, "antispam") and count >= _get_setting(message.guild.id, "spam_message_count"):
        _message_hits[spam_key].clear()
        reason = (
            f"Anti-spam automatique : {count} messages en {spam_window}s" if LANG == "fr"
            else f"Automatic anti-spam: {count} messages in {spam_window}s"
        )

        acted = False
        if isinstance(message.author, discord.Member):
            acted = await _contain_member(
                message.guild, message.author, reason,
                minutes=_get_setting(message.guild.id, "spam_timeout_minutes"),
            )

        try:
            cutoff_secs = spam_window * 3
            recent = [
                m async for m in message.channel.history(limit=50)
                if m.author.id == message.author.id
                and (discord.utils.utcnow() - m.created_at).total_seconds() <= cutoff_secs
            ]
            if recent:
                await message.channel.delete_messages(recent)
        except Exception:
            pass

        status = _containment_status_text(message.guild, message.author, acted)
        await _log_security_event(
            message.guild,
            (
                f"🚨 Spam détecté : **{message.author}** a envoyé {count} messages en "
                f"{spam_window}s dans #{message.channel.name}. Il/elle a été {status}."
            ) if LANG == "fr" else (
                f"🚨 Spam detected: **{message.author}** sent {count} messages in "
                f"{spam_window}s in #{message.channel.name}. They were {status}."
            ),
        )

    await bot.process_commands(message)


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if after.guild is None or after.author.id == bot.user.id:
        return

    if not after.author.bot and before.content != after.content:
        asyncio.create_task(_post_full_log_entry(after, "edition", before_content=before.content))


@bot.event
async def on_message_delete(message: discord.Message):
    if message.guild is None or message.author is None or message.author.id == bot.user.id:
        return
    if message.author.bot:
        return
    if message.channel.id in _honeypot_purging_channels:
        return  # purge quotidienne du salon piège : pas de log message par message
    if (message.guild.id, message.author.id) in _active_purge_targets:
        # Fait partie d'une purge en masse du salon piège (voir
        # _active_purge_targets) : déjà couvert par l'entrée modlog de la
        # sanction, pas besoin (et surtout pas sûr, côté rate limit) de
        # logguer chaque suppression individuellement.
        return
    asyncio.create_task(_post_full_log_entry(message, "suppression"))


def _antinuke_thresholds_for(guild_id: int, actor) -> tuple[int, int]:
    """Renvoie (seuil, fenêtre en secondes) à appliquer pour cet auteur,
    selon qu'il s'agit d'un humain, d'un bot certifié Discord (badge
    "Vérifié"), ou d'un bot non certifié — chaque catégorie ayant son
    propre niveau de confiance par défaut, réglable séparément dans le
    panel."""
    if getattr(actor, "bot", False):
        is_verified = bool(getattr(getattr(actor, "public_flags", None), "verified_bot", False))
        if is_verified:
            return (
                _get_setting(guild_id, "antinuke_action_count_bot_verified"),
                _get_setting(guild_id, "antinuke_window_seconds_bot_verified"),
            )
        return (
            _get_setting(guild_id, "antinuke_action_count_bot_unverified"),
            _get_setting(guild_id, "antinuke_window_seconds_bot_unverified"),
        )
    return (
        _get_setting(guild_id, "antinuke_action_count_human"),
        _get_setting(guild_id, "antinuke_window_seconds_human"),
    )


async def _handle_structural_action(guild: discord.Guild, action, label: str, match_entry=None):
    if not _module_enabled(guild.id, "antinuke"):
        return
    if guild.id == STORAGE_GUILD_ID:
        return
    for attempt in range(10):
        found_recent_entry = False
        async for probe_entry in guild.audit_logs(limit=1, action=action):
            if (discord.utils.utcnow() - probe_entry.created_at).total_seconds() <= 5:
                found_recent_entry = True
            break
        if found_recent_entry:
            break
        await asyncio.sleep(0.4)
    try:
        async for entry in guild.audit_logs(limit=5, action=action):
            if (discord.utils.utcnow() - entry.created_at).total_seconds() > 5:
                break
            if match_entry is not None and not match_entry(entry):
                break
            actor = entry.user
            if actor is None or actor.id == guild.me.id:
                break

            member = actor if isinstance(actor, discord.Member) else guild.get_member(actor.id)
            if member is not None and _is_whitelisted(guild.id, member):
                break
            if _is_whitelisted(guild.id, actor):
                break

            key = (guild.id, actor.id)

            if _antinuke_lock_active(key):
                break

            antinuke_threshold, antinuke_window = _antinuke_thresholds_for(guild.id, actor)
            count = _prune_and_push(_channel_action_hits[key], antinuke_window)
            if count >= antinuke_threshold:
                _channel_action_hits[key].clear()
                reason = (
                    f"Anti-nuke automatique : {count} {label} en {antinuke_window}s" if LANG == "fr"
                    else f"Automatic anti-nuke: {count} {label} in {antinuke_window}s"
                )

                sanction_task = asyncio.create_task(_punish_antinuke_actor(guild, actor, reason))
                rollback_already_running = key in _antinuke_rollback_in_progress
                if not rollback_already_running:
                    asyncio.create_task(_run_antinuke_auto_rollback(guild, actor))

                acted, action_kind = await sanction_task
                human_timeout_minutes = _get_setting(guild.id, "antinuke_human_timeout_minutes")

                if action_kind == "timeout":
                    _antinuke_set_lock(key, human_timeout_minutes * 60)
                else:
                    _antinuke_set_lock(key, ANTINUKE_LOCK_MIN_SECONDS)

                if action_kind == "owner":
                    status = _containment_status_text(guild, actor, False)
                elif action_kind == "ban":
                    status = "banni(e)" if LANG == "fr" else "banned"
                elif action_kind == "ban_failed":
                    status = "PAS pu être banni(e) (permissions insuffisantes)" if LANG == "fr" else "could NOT be banned (insufficient permissions)"
                elif action_kind == "kick":
                    status = "expulsé(e)" if LANG == "fr" else "kicked"
                elif action_kind == "kick_failed":
                    status = "PAS pu être expulsé(e) (permissions insuffisantes)" if LANG == "fr" else "could NOT be kicked (insufficient permissions)"
                elif action_kind == "timeout":
                    status = (
                        f"mis(e) en sourdine {human_timeout_minutes} min et rôles dangereux retirés" if LANG == "fr"
                        else f"timed out for {human_timeout_minutes} min and stripped of dangerous roles"
                    )
                elif action_kind == "timeout_failed":
                    status = (
                        "PAS pu être bloqué(e) (permissions insuffisantes)" if LANG == "fr"
                        else "could NOT be contained (insufficient permissions)"
                    )
                else:
                    status = (
                        "introuvable sur le serveur (a peut-être déjà quitté)" if LANG == "fr"
                        else "not found on the server (may have already left)"
                    )

                if _antinuke_notification_allowed(guild.id):
                    await _log_security_event(
                        guild,
                        (
                            f"🚨 Raid probable : **{actor}** a fait {count} {label} en "
                            f"{antinuke_window}s. Il/elle a été {status}. "
                            f"Annulation automatique de ses actions des {ANTINUKE_ROLLBACK_MINUTES} "
                            "dernières minutes en cours..."
                        ) if LANG == "fr" else (
                            f"🚨 Likely raid: **{actor}** performed {count} {label} in "
                            f"{antinuke_window}s. They were {status}. Automatically reverting "
                            f"their actions from the last {ANTINUKE_ROLLBACK_MINUTES} minutes..."
                        ),
                    )
                    asyncio.create_task(_notify_guild_owner_antinuke_detected(guild, actor, count, label, status, antinuke_window))
                else:
                    log.info(
                        f"Alerte anti-nuke supprimée sur {guild.name} (cooldown de "
                        f"{ANTINUKE_NOTIFY_COOLDOWN_SECONDS}s) — sanction et rollback appliqués quand même."
                    )
            break
    except discord.Forbidden:
        pass
    except discord.NotFound:
        pass
    except Exception:
        log.exception("Erreur lors de la vérification du journal d'audit (anti-nuke salons/rôles).")


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    label = "créations de salon" if LANG == "fr" else "channel creations"
    await _handle_structural_action(channel.guild, discord.AuditLogAction.channel_create, label)

    freeze_role_id = _get_setting(channel.guild.id, "freeze_role_id")
    freeze_category_id = _get_setting(channel.guild.id, "freeze_category_id")
    freeze_channel_id = _get_setting(channel.guild.id, "freeze_channel_id")
    if (
        freeze_role_id and channel.id != freeze_category_id and channel.id != freeze_channel_id
        and getattr(channel, "category_id", None) != freeze_category_id
    ):
        freeze_role = channel.guild.get_role(freeze_role_id)
        if freeze_role is not None:
            await _hide_from_freeze_role(channel, freeze_role)


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    label = "suppressions de salon" if LANG == "fr" else "channel deletions"
    await _handle_structural_action(channel.guild, discord.AuditLogAction.channel_delete, label)


@bot.event
async def on_guild_role_create(role: discord.Role):
    label = "créations de rôle" if LANG == "fr" else "role creations"
    await _handle_structural_action(role.guild, discord.AuditLogAction.role_create, label)


@bot.event
async def on_guild_role_delete(role: discord.Role):
    label = "suppressions de rôle" if LANG == "fr" else "role deletions"
    await _handle_structural_action(role.guild, discord.AuditLogAction.role_delete, label)


@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role):
    dangerous_perm_added = any(
        getattr(after.permissions, p, False) and not getattr(before.permissions, p, False)
        for p in DANGEROUS_PERMS_TO_STRIP
    )
    moved_up = after.position > before.position
    if not dangerous_perm_added and not moved_up:
        return

    if dangerous_perm_added and moved_up:
        label = (
            "modifications dangereuses de rôle (permissions + hiérarchie)" if LANG == "fr"
            else "dangerous role changes (permissions + hierarchy)"
        )
    elif dangerous_perm_added:
        label = (
            "ajouts de permission sensible sur un rôle" if LANG == "fr"
            else "sensitive permission grants on a role"
        )
    else:
        label = (
            "remontées de rôle dans la hiérarchie" if LANG == "fr"
            else "role moves up the hierarchy"
        )

    def _match(entry) -> bool:
        if getattr(entry.target, "id", None) != after.id:
            return False
        return (
            getattr(entry.before, "permissions", None) is not None
            or getattr(entry.before, "position", None) is not None
        )

    await _handle_structural_action(
        after.guild, discord.AuditLogAction.role_update, label, match_entry=_match
    )


@bot.event
async def on_guild_update(before: discord.Guild, after: discord.Guild):
    """Verrouillage "nouveau bot" : indépendant du seuil anti-nuke habituel
    (X actions en Y secondes) — ici, un bot NON certifié qui change le nom ou
    l'icône du serveur moins de `unverified_bot_lockdown_minutes` minutes
    après son arrivée est sanctionné DÈS LA PREMIÈRE occurrence, sans laisser
    aucune marge : un bot fraîchement arrivé n'a strictement aucune raison
    légitime de toucher à ça tout de suite."""
    if before.name == after.name and before.icon == after.icon:
        return
    if not _module_enabled(after.id, "antinuke") or after.id == STORAGE_GUILD_ID:
        return
    lockdown_minutes = _get_setting(after.id, "unverified_bot_lockdown_minutes")
    if not lockdown_minutes:
        return

    actor = None
    try:
        for _ in range(5):
            async for entry in after.audit_logs(limit=3, action=discord.AuditLogAction.guild_update):
                if (discord.utils.utcnow() - entry.created_at).total_seconds() <= 5:
                    actor = entry.user
                break
            if actor is not None:
                break
            await asyncio.sleep(0.4)
    except (discord.Forbidden, discord.HTTPException):
        return

    if actor is None or actor.id == after.me.id:
        return

    member = actor if isinstance(actor, discord.Member) else after.get_member(actor.id)
    if member is None or not member.bot:
        return
    if bool(member.public_flags.verified_bot):
        return
    if _is_whitelisted(after.id, member):
        return
    if member.joined_at is None or (discord.utils.utcnow() - member.joined_at) > timedelta(minutes=lockdown_minutes):
        return

    key = (after.id, member.id)
    if _antinuke_lock_active(key):
        return
    _antinuke_set_lock(key, ANTINUKE_LOCK_MIN_SECONDS)

    changed = []
    if before.name != after.name:
        changed.append("le nom du serveur" if LANG == "fr" else "the server name")
    if before.icon != after.icon:
        changed.append("l'icône du serveur" if LANG == "fr" else "the server icon")
    changed_text = (" et " if LANG == "fr" else " and ").join(changed)

    reason = (
        f"Verrouillage anti-nuke \"nouveau bot\" : bot non certifié a changé {changed_text} "
        f"moins de {lockdown_minutes} min après son arrivée"
        if LANG == "fr"
        else f'Anti-nuke "new bot" lockdown: unverified bot changed {changed_text} '
        f"less than {lockdown_minutes} min after joining"
    )

    asyncio.create_task(_apply_antinuke_sanction(after, member, reason, "ban"))
    if key not in _antinuke_rollback_in_progress:
        asyncio.create_task(_run_antinuke_auto_rollback(after, member))

    await _log_security_event(
        after,
        (
            f"🚨 **{member}** (bot NON certifié, arrivé il y a moins de {lockdown_minutes} min) a changé "
            f"{changed_text} — banni immédiatement, rollback en cours."
        )
        if LANG == "fr"
        else (
            f"🚨 **{member}** (unverified bot, joined less than {lockdown_minutes} min ago) changed "
            f"{changed_text} — banned immediately, rollback in progress."
        ),
    )


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    label = "bannissements" if LANG == "fr" else "bans"
    await _handle_structural_action(guild, discord.AuditLogAction.ban, label)


@bot.event
async def on_member_remove(member: discord.Member):
    if member.guild.id != STORAGE_GUILD_ID:
        account_age_days = (discord.utils.utcnow() - member.joined_at).days if member.joined_at else None
        await _log_security_event(
            member.guild,
            (
                f"📤 **{member}** (`{member.id}`) a quitté **{member.guild.name}**."
                + (f" (membre depuis {account_age_days} j)" if account_age_days is not None else "")
            ) if LANG == "fr" else (
                f"📤 **{member}** (`{member.id}`) left **{member.guild.name}**."
                + (f" (member for {account_age_days}d)" if account_age_days is not None else "")
            ),
        )

    raid_state = _raid_state.get(member.guild.id)
    if raid_state and raid_state.get("active") and member.id in raid_state.get("member_ids", []):
        if member.id not in raid_state.setdefault("left_during_raid", []):
            raid_state["left_during_raid"].append(member.id)
            log.info(
                f"{member} ({member.id}) a quitté {member.guild.name} pendant le protocole anti-raid — "
                "rôle exclu de la restauration automatique."
            )
            if STORAGE_MODE == "file":
                g = _file_store_guild(member.guild.id)
                g["raid_state"] = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in raid_state.items()}
                _file_store_save()
            else:
                db_guild = get_db_guild()
                if db_guild is not None:
                    try:
                        await _save_raid_state(db_guild, member.guild, raid_state)
                    except Exception:
                        log.exception(
                            f"Impossible de sauvegarder le départ de {member.id} pendant le protocole anti-raid "
                            f"pour {member.guild.name}."
                        )

    def _match(entry) -> bool:
        return getattr(entry.target, "id", None) == member.id

    label = "expulsions" if LANG == "fr" else "kicks"
    await _handle_structural_action(
        member.guild, discord.AuditLogAction.kick, label, match_entry=_match
    )


WELCOME_CARD_WIDTH = 900
WELCOME_CARD_HEIGHT = 300
WELCOME_CARD_AVATAR_SIZE = 200


def _welcome_card_font(size: int):
    """Essaie une police nette classique, sinon la police par défaut de Pillow
    (toujours disponible, juste moins jolie). Inclut quelques chemins absolus
    courants (Linux) en plus des noms nus, car ImageFont.truetype ne fait pas
    de recherche système : un nom seul ne fonctionne que si le fichier est
    dans le dossier courant."""
    candidates = (
        "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf", "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
    )
    for name in candidates:
        try:
            return _WelcomeImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return _WelcomeImageFont.load_default(size=size)
    except TypeError:
        return _WelcomeImageFont.load_default()


async def _build_welcome_card(member: discord.Member):
    """Construit l'image de bienvenue (fond uni + PDP circulaire du membre +
    son pseudo) et renvoie un discord.File prêt à être attaché au message."""
    avatar_bytes = await member.display_avatar.replace(size=256, static_format="png").read()
    avatar_img = _WelcomeImage.open(_welcome_io.BytesIO(avatar_bytes)).convert("RGBA").resize(
        (WELCOME_CARD_AVATAR_SIZE, WELCOME_CARD_AVATAR_SIZE)
    )

    mask = _WelcomeImage.new("L", avatar_img.size, 0)
    _WelcomeImageDraw.Draw(mask).ellipse((0, 0) + avatar_img.size, fill=255)

    card = _WelcomeImage.new("RGBA", (WELCOME_CARD_WIDTH, WELCOME_CARD_HEIGHT), (35, 39, 42, 255))
    draw = _WelcomeImageDraw.Draw(card)
    draw.rectangle((0, 0, WELCOME_CARD_WIDTH, 8), fill=(88, 101, 242, 255))

    avatar_pos = (50, (WELCOME_CARD_HEIGHT - WELCOME_CARD_AVATAR_SIZE) // 2)
    ring_pad = 6
    draw.ellipse(
        (
            avatar_pos[0] - ring_pad, avatar_pos[1] - ring_pad,
            avatar_pos[0] + WELCOME_CARD_AVATAR_SIZE + ring_pad, avatar_pos[1] + WELCOME_CARD_AVATAR_SIZE + ring_pad,
        ),
        fill=(88, 101, 242, 255),
    )
    card.paste(avatar_img, avatar_pos, mask)

    text_x = avatar_pos[0] + WELCOME_CARD_AVATAR_SIZE + 45
    title_font = _welcome_card_font(46)
    sub_font = _welcome_card_font(26)
    draw.text((text_x, 95), member.display_name, font=title_font, fill=(255, 255, 255, 255))
    draw.text(
        (text_x, 155),
        "Bienvenue sur le serveur !" if LANG == "fr" else "Welcome to the server!",
        font=sub_font, fill=(185, 187, 190, 255),
    )

    buffer = _welcome_io.BytesIO()
    card.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(buffer, filename="bienvenue.png")


def _format_welcome_text(member: discord.Member, template: str) -> str:
    """Remplace les jetons (fr/en, les deux acceptés quel que soit LANG) dans
    le texte de bienvenue configuré à la main pour ce serveur."""
    return (
        template
        .replace("{membre}", member.display_name).replace("{member}", member.display_name)
        .replace("{mention}", member.mention)
        .replace("{serveur}", member.guild.name).replace("{server}", member.guild.name)
        .replace("{nombre}", str(member.guild.member_count)).replace("{count}", str(member.guild.member_count))
    )


async def _send_welcome_channel_message(member: discord.Member) -> None:
    """Message de bienvenue dans un salon (indépendant du MP) : image générée
    avec la PDP du membre + texte personnalisable + ping optionnel. Ne fait
    rien tant qu'aucun salon n'a été réglé via /bienvenue-salon."""
    channel_id = _get_setting(member.guild.id, "welcome_channel_id")
    if not channel_id:
        return
    channel = member.guild.get_channel(channel_id)
    if channel is None:
        return

    template = _get_setting(member.guild.id, "welcome_text") or WELCOME_TEXT_DEFAULT
    text = _format_welcome_text(member, template)
    content = member.mention if _get_setting(member.guild.id, "welcome_ping_enabled") else None

    if _WELCOME_CARD_AVAILABLE:
        try:
            file = await _build_welcome_card(member)
            embed = discord.Embed(description=text[:4096], color=0x5865F2)
            embed.set_image(url="attachment://bienvenue.png")
            await channel.send(content=content, embed=embed, file=file)
            return
        except Exception:
            log.exception(
                f"Impossible de générer la carte de bienvenue pour {member} sur {member.guild.name}, "
                "repli sur un embed simple."
            )

    embed = discord.Embed(description=text[:4096], color=0x5865F2)
    embed.set_thumbnail(url=member.display_avatar.url)
    try:
        await channel.send(content=content, embed=embed)
    except Exception:
        log.exception(f"Impossible d'envoyer le message de bienvenue dans le salon configuré sur {member.guild.name}.")



CAPTCHA_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CAPTCHA_CODE_LENGTH = 5
CAPTCHA_IMAGE_SIZE = (340, 130)

CAPTCHA_FONT_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTCHA_FONT_FILENAMES = ["PatrickHand-Regular.ttf", "Caveat-Regular.ttf", "ShadowsIntoLight.ttf"]

_captcha_font_cache: dict[int, list] = {}


def _generate_captcha_code() -> str:
    return "".join(random.choice(CAPTCHA_ALPHABET) for _ in range(CAPTCHA_CODE_LENGTH))


def _captcha_font_fallback(size: int):
    """Repli si aucune police manuscrite n'est trouvée dans fonts/ (dossier
    absent, fichiers manquants…) : police nette classique, sinon la police
    par défaut de Pillow."""
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return _WelcomeImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return _WelcomeImageFont.load_default(size=size)
    except TypeError:
        return _WelcomeImageFont.load_default()


def _captcha_fonts(size: int) -> list:
    """Renvoie la liste des polices manuscrites disponibles pour cette
    taille (chargées une fois puis mises en cache). Repli sur une police
    classique si le dossier fonts/ est absent ou incomplet."""
    if size in _captcha_font_cache:
        return _captcha_font_cache[size]
    fonts = []
    for filename in CAPTCHA_FONT_FILENAMES:
        path = os.path.join(CAPTCHA_FONT_DIR, filename)
        try:
            fonts.append(_WelcomeImageFont.truetype(path, size))
        except Exception:
            continue
    if not fonts:
        fonts = [_captcha_font_fallback(size)]
    _captcha_font_cache[size] = fonts
    return fonts


def _random_captcha_color(min_v: int = 40, max_v: int = 170) -> tuple[int, int, int]:
    return (random.randint(min_v, max_v), random.randint(min_v, max_v), random.randint(min_v, max_v))


def _draw_captcha_image(code: str, difficulty: str) -> discord.File:
    """Génère l'image CAPTCHA à recopier, avec un style manuscrit (police
    différente possible à chaque lettre, taille légèrement irrégulière) et
    un effet de perspective (comme une feuille regardée de travers, pas
    bien en face) pour gêner davantage une lecture automatisée qui
    s'attendrait à du texte bien droit.
    La difficulté du serveur pilote l'intensité de tout ça :
      - easy   : lettres juste un peu penchées, fond quasi propre, très
                 léger effet de perspective
      - medium : lettres plus penchées, tailles plus irrégulières, un peu
                 de bruit de fond, perspective plus marquée
      - hard   : lettres très penchées et de tailles très irrégulières +
                 traits qui passent PAR-DESSUS le texte + perspective
                 prononcée, comme une feuille vue nettement de travers
    """
    width, height = CAPTCHA_IMAGE_SIZE
    margin = int(min(width, height) * 0.22)
    canvas = _WelcomeImage.new("RGB", (width + 2 * margin, height + 2 * margin), (245, 246, 248))
    draw = _WelcomeImageDraw.Draw(canvas)

    dot_count = {"easy": 40, "medium": 90, "hard": 140}.get(difficulty, 40)
    for _ in range(dot_count):
        x = random.randint(margin, margin + width)
        y = random.randint(margin, margin + height)
        draw.point((x, y), fill=_random_captcha_color(150, 210))

    bg_line_count = {"easy": 0, "medium": 2, "hard": 3}.get(difficulty, 0)
    for _ in range(bg_line_count):
        y = margin + random.randint(10, height - 10)
        draw.line(
            [(margin, y + random.randint(-10, 10)), (margin + width, y + random.randint(-10, 10))],
            fill=_random_captcha_color(190, 220), width=2,
        )

    rotation_range = {"easy": 8, "medium": 18, "hard": 26}.get(difficulty, 8)
    size_choices = {
        "easy": [46, 50],
        "medium": [42, 48, 54],
        "hard": [40, 48, 56, 60],
    }.get(difficulty, [46, 50])
    char_w = width // (len(code) + 1)
    x_cursor = margin + 12

    for ch in code:
        angle = random.randint(-rotation_range, rotation_range)
        size = random.choice(size_choices)
        font = random.choice(_captcha_fonts(size))
        char_color = _random_captcha_color(15, 95)

        char_img = _WelcomeImage.new("RGBA", (100, 110), (0, 0, 0, 0))
        _WelcomeImageDraw.Draw(char_img).text((15, 15), ch, font=font, fill=char_color + (255,))
        char_img = char_img.rotate(angle, expand=True, resample=_WelcomeImage.BICUBIC)

        y_jitter = random.randint(-4, 4) if difficulty == "easy" else random.randint(-10, 10)
        y_pos = margin + (height - char_img.height) // 2 + y_jitter
        canvas.paste(char_img, (x_cursor, y_pos), char_img)
        x_cursor += char_w

    overlay_line_count = {"easy": 0, "medium": 1, "hard": 4}.get(difficulty, 0)
    for _ in range(overlay_line_count):
        y1 = margin + random.randint(0, height)
        y2 = margin + random.randint(0, height)
        draw.line([(margin, y1), (margin + width, y2)], fill=_random_captcha_color(30, 90), width=2)

    tilt_strength = {"easy": 0.35, "medium": 0.65, "hard": 1.0}.get(difficulty, 0.35)
    max_shift = margin * tilt_strength
    mode = random.choice(["left", "right", "top", "bottom", "corner"])

    tl = [margin, margin]
    bl = [margin, margin + height]
    br = [margin + width, margin + height]
    tr = [margin + width, margin]

    dx = random.uniform(0.5, 1.0) * max_shift
    dy = random.uniform(0.3, 0.7) * max_shift

    if mode == "left":
        tl[0] += dx; bl[0] += dx
        tl[1] += dy * 0.4; bl[1] -= dy * 0.4
    elif mode == "right":
        tr[0] -= dx; br[0] -= dx
        tr[1] += dy * 0.4; br[1] -= dy * 0.4
    elif mode == "top":
        tl[1] += dy; tr[1] += dy
        tl[0] += dx * 0.4; tr[0] -= dx * 0.4
    elif mode == "bottom":
        bl[1] -= dy; br[1] -= dy
        bl[0] += dx * 0.4; br[0] -= dx * 0.4
    else:
        tl[0] += dx * 0.8; tl[1] += dy * 0.8

    quad = [tl[0], tl[1], bl[0], bl[1], br[0], br[1], tr[0], tr[1]]
    img = canvas.transform((width, height), _WelcomeImage.QUAD, quad, resample=_WelcomeImage.BICUBIC)

    buffer = _welcome_io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(buffer, filename="captcha.png")


HONEYPOT_IMAGE_MAX_TEXT_WIDTH = 640
HONEYPOT_IMAGE_FONT_SIZE = 34
HONEYPOT_IMAGE_LINE_HEIGHT = 50
HONEYPOT_IMAGE_MARGIN = 40


HONEYPOT_WARNING_TEXTS_FR = [
    "Ce salon est un piège : n'écris rien ici, tu serais sanctionné(e) automatiquement.",
    "Merci de ne rien écrire dans ce salon — c'est un piège et la sanction est automatique.",
    "Attention, salon piège : le moindre message ici entraîne une sanction automatique.",
    "N'écris pas dans ce salon, c'est un piège de sécurité et la sanction tombe automatiquement.",
    "Ce salon sert uniquement à repérer les intrus : écrire ici déclenche une sanction immédiate.",
    "Salon piège — merci de ne pas y écrire, sous peine de sanction automatique.",
    "Il est interdit d'écrire ici : ce salon est un piège anti-intrusion.",
    "Ne poste rien ici, ce salon existe uniquement pour piéger les comptes indésirables.",
    "Ce canal est un piège de sécurité : toute personne qui y écrit est sanctionnée sans avertissement.",
    "Merci de laisser ce salon vide, il sert de piège et déclenche une sanction automatique.",
    "Écrire dans ce salon entraîne une sanction immédiate et automatique — évite d'y poster.",
    "Ce salon ne doit pas recevoir de message : c'est un piège de modération.",
    "Ne rien écrire ici, s'il te plaît : ce salon déclenche une sanction dès le premier message.",
    "Ce salon est réservé au système anti-intrusion : y écrire déclenche une sanction directe.",
    "Salon de sécurité : quiconque y écrit est automatiquement sanctionné.",
    "Merci d'ignorer ce salon, il sert de piège et sanctionne automatiquement celles et ceux qui y postent.",
    "Ce salon n'est pas destiné à être utilisé : écrire ici entraîne une sanction automatique.",
    "Éviter d'écrire ici : ce salon piège déclenche une sanction sans intervention humaine.",
    "Ce salon fait partie du système de sécurité du serveur : y poster entraîne une sanction automatique.",
    "N'importe quel message posté ici déclenche instantanément une sanction automatique.",
    "Ce salon existe pour surveiller les comptes suspects : écrire ici = sanction automatique.",
    "Merci de ne pas interagir avec ce salon, il déclenche une sanction automatique en cas de message.",
    "Ce salon est un leurre de sécurité : un seul message ici suffit pour être sanctionné.",
    "Restez à l'écart de ce salon, tout message y entraîne une sanction automatique.",
    "Ce salon sert de test de sécurité : y écrire provoque une sanction immédiate.",
    "Aucun message ne doit être posté ici, ce salon déclenche une sanction dès qu'on y écrit.",
    "Ce salon piège fait partie de la protection du serveur : y écrire est automatiquement sanctionné.",
    "Merci de ne jamais écrire dans ce salon : la sanction est automatique et immédiate.",
    "Ce canal sert uniquement de piège de modération, toute écriture y est sanctionnée automatiquement.",
    "N'écris rien dans ce salon, il est surveillé et sanctionne automatiquement chaque message.",
    "Ce salon est désactivé pour un usage normal : y écrire déclenche une sanction automatique.",
    "Un simple message dans ce salon suffit à déclencher une sanction automatique.",
    "Ce salon ne sert à rien d'autre qu'à piéger les comptes malveillants : n'y écris pas.",
    "Merci de rester silencieux ici, ce salon sanctionne automatiquement toute personne qui y écrit.",
    "Ce salon est un piège de sécurité invisible : écrire ici entraîne une sanction automatique.",
    "Évitez ce salon : il est configuré pour sanctionner automatiquement tout message posté.",
    "Ce salon ne doit jamais recevoir de message, la sanction est automatique et sans exception.",
    "Attention : ce salon fait partie du dispositif anti-raid, y écrire est automatiquement sanctionné.",
    "Merci de ne rien poster ici, ce salon repère et sanctionne automatiquement les intrus.",
    "Ce salon piège applique une sanction automatique dès le premier message écrit.",
    "N'écris surtout pas ici : ce salon est conçu pour sanctionner automatiquement quiconque y poste.",
    "Ce salon fait partie des mesures de sécurité du serveur, écrire ici entraîne une sanction directe.",
    "Merci de ne pas tester ce salon, tout message y est automatiquement sanctionné.",
    "Ce salon n'accepte aucun message : une sanction automatique s'applique immédiatement.",
    "Ce canal sert de piège discret : un message ici suffit à déclencher une sanction automatique.",
    "Merci de laisser ce salon tranquille, il sanctionne automatiquement toute personne qui y écrit.",
    "Ce salon est surveillé en continu : y écrire entraîne une sanction automatique et immédiate.",
    "Ne poste jamais dans ce salon, la sanction est automatique, sans intervention d'un modérateur.",
    "Ce salon piège protège le serveur : toute écriture y est immédiatement sanctionnée.",
    "Merci de ne pas écrire ici, ce salon applique une sanction automatique sans avertissement préalable.",
]

HONEYPOT_WARNING_TEXTS_EN = [
    "This channel is a trap: don't write here, you would be sanctioned automatically.",
    "Please don't post in this channel — it's a trap and the sanction is automatic.",
    "Warning, honeypot channel: any message here triggers an automatic sanction.",
    "Don't write in this channel, it's a security trap and the sanction applies automatically.",
    "This channel only exists to catch intruders: writing here triggers an immediate sanction.",
    "Honeypot channel — please don't post here, or you'll be sanctioned automatically.",
    "Writing here is not allowed: this channel is an anti-intrusion trap.",
    "Don't post anything here, this channel only exists to catch unwanted accounts.",
    "This channel is a security trap: anyone who writes here is sanctioned without warning.",
    "Please leave this channel empty, it acts as a trap and triggers an automatic sanction.",
    "Writing in this channel triggers an immediate, automatic sanction — avoid posting here.",
    "This channel should never receive a message: it's a moderation trap.",
    "Please don't write here: this channel triggers a sanction from the very first message.",
    "This channel is reserved for the anti-intrusion system: writing here triggers a direct sanction.",
    "Security channel: anyone who writes here is automatically sanctioned.",
    "Please ignore this channel, it's a trap that automatically sanctions anyone who posts.",
    "This channel isn't meant to be used: writing here causes an automatic sanction.",
    "Avoid writing here: this trap channel triggers a sanction with no human involved.",
    "This channel is part of the server's security system: posting here causes an automatic sanction.",
    "Any message posted here instantly triggers an automatic sanction.",
    "This channel exists to monitor suspicious accounts: writing here means an automatic sanction.",
    "Please don't interact with this channel, it triggers an automatic sanction if you post.",
    "This channel is a security decoy: a single message here is enough to be sanctioned.",
    "Stay away from this channel, any message here leads to an automatic sanction.",
    "This channel acts as a security test: writing here causes an immediate sanction.",
    "No message should ever be posted here, this channel sanctions as soon as someone writes in it.",
    "This trap channel is part of the server's protection: writing here is automatically sanctioned.",
    "Please never write in this channel: the sanction is automatic and immediate.",
    "This channel only serves as a moderation trap, any message here is automatically sanctioned.",
    "Don't write anything in this channel, it's monitored and automatically sanctions every message.",
    "This channel is disabled for normal use: writing here triggers an automatic sanction.",
    "A single message in this channel is enough to trigger an automatic sanction.",
    "This channel serves no purpose other than catching malicious accounts: don't write here.",
    "Please stay silent here, this channel automatically sanctions anyone who writes in it.",
    "This channel is an invisible security trap: writing here leads to an automatic sanction.",
    "Avoid this channel: it's configured to automatically sanction any message posted.",
    "This channel should never receive a message, the sanction is automatic and without exception.",
    "Warning: this channel is part of the anti-raid system, writing here is automatically sanctioned.",
    "Please don't post here, this channel detects and automatically sanctions intruders.",
    "This trap channel applies an automatic sanction from the very first message written.",
    "Definitely don't write here: this channel is designed to automatically sanction anyone who posts.",
    "This channel is part of the server's security measures, writing here causes a direct sanction.",
    "Please don't test this channel, any message here is automatically sanctioned.",
    "This channel accepts no messages: an automatic sanction applies immediately.",
    "This channel is a quiet trap: one message here is enough to trigger an automatic sanction.",
    "Please leave this channel alone, it automatically sanctions anyone who writes in it.",
    "This channel is monitored continuously: writing here causes an immediate, automatic sanction.",
    "Never post in this channel, the sanction is automatic, with no moderator involved.",
    "This trap channel protects the server: any writing here is immediately sanctioned.",
    "Please don't write here, this channel applies an automatic sanction with no prior warning.",
]


def _pick_honeypot_warning_text(guild_id: int) -> str:
    """Choisit le texte affiché sur l'image d'avertissement du salon piège.
    Si l'administrateur n'a jamais personnalisé le texte (réglage encore à sa
    valeur par défaut), un texte est tiré au hasard parmi 50 formulations
    différentes (voir HONEYPOT_WARNING_TEXTS_FR/EN) à chaque (ré)envoi de
    l'image, pour qu'elle ne soit jamais figée sur le même texte. Si
    l'administrateur a personnalisé le texte via /panel, ce choix est
    toujours respecté tel quel, sans tirage aléatoire."""
    configured = _get_setting(guild_id, "honeypot_warning_text")
    if configured != DEFAULT_SETTINGS["honeypot_warning_text"]:
        return configured
    pool = HONEYPOT_WARNING_TEXTS_FR if LANG == "fr" else HONEYPOT_WARNING_TEXTS_EN
    return random.choice(pool)


HONEYPOT_TEXT_COLOR_BASE = (206, 21, 21)


def _honeypot_warning_color() -> tuple:
    """Rouge vif avec une toute petite variation par lettre (pour garder un
    peu de texture), jamais assez pour perdre en lisibilité."""
    r, g, b = HONEYPOT_TEXT_COLOR_BASE
    return (
        min(255, max(0, r + random.randint(-10, 15))),
        max(0, g + random.randint(-8, 8)),
        max(0, b + random.randint(-8, 8)),
    )


def _draw_honeypot_warning_image(text: str, difficulty: str = "medium") -> discord.File:
    """Génère l'image d'avertissement du salon piège. Contrairement au CAPTCHA
    de vérification (_draw_captcha_image), qui doit rester difficile à lire,
    ce texte doit se voir IMMÉDIATEMENT : police d'écriture par défaut/classique
    (_welcome_card_font — pas la police manuscrite du CAPTCHA), grosses lettres
    (voir HONEYPOT_IMAGE_FONT_SIZE), rendu GRAS (contour épais), en ROUGE vif,
    rotation minime. Seul le bruit de fond (points + petites lettres
    décoratives) reprend le style du CAPTCHA, et suit toujours la difficulté
    réglée pour la vérification (`verification_difficulty`) — le texte
    principal, lui, ne varie plus avec la difficulté. Ajout : des traits
    rouges de fond (derrière le texte, jamais dessus) pour ralentir une
    lecture automatisée (OCR) de l'image, sans gêner la lecture humaine."""
    words = text.split() or ["⚠️"]
    font = _welcome_card_font(HONEYPOT_IMAGE_FONT_SIZE)

    probe = _WelcomeImage.new("RGB", (10, 10))
    probe_draw = _WelcomeImageDraw.Draw(probe)

    bold_stroke_width = max(1, HONEYPOT_IMAGE_FONT_SIZE // 32)

    def _text_width(s: str) -> int:
        bbox = probe_draw.textbbox((0, 0), s, font=font)
        return bbox[2] - bbox[0]

    def _rendered_width(s: str) -> int:
        """Largeur RÉELLEMENT dessinée pour `s`, lettre par lettre avec
        l'espacement du contour gras — doit rester identique à l'avancée du
        curseur dans la boucle de dessin plus bas."""
        total = 0
        for ch in s:
            if ch == " ":
                total += HONEYPOT_IMAGE_FONT_SIZE // 2
            else:
                total += _text_width(ch) + 4 + bold_stroke_width
        return total

    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and _rendered_width(candidate) > HONEYPOT_IMAGE_MAX_TEXT_WIDTH:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)

    margin = HONEYPOT_IMAGE_MARGIN
    content_width = max((_rendered_width(line) for line in lines), default=0)
    width = max(content_width, 1) + 2 * margin
    height = margin * 2 + HONEYPOT_IMAGE_LINE_HEIGHT * max(1, len(lines))
    canvas = _WelcomeImage.new("RGB", (width, height), (245, 246, 248))
    draw = _WelcomeImageDraw.Draw(canvas)

    dot_count = {"easy": 70, "medium": 150, "hard": 230}.get(difficulty, 150)
    for _ in range(dot_count):
        x, y = random.randint(0, width), random.randint(0, height)
        draw.point((x, y), fill=_random_captcha_color(150, 210))

    decoy_count = {"easy": 25, "medium": 55, "hard": 90}.get(difficulty, 55)
    decoy_font = random.choice(_captcha_fonts(16))
    for _ in range(decoy_count):
        ch = random.choice(CAPTCHA_ALPHABET)
        x, y = random.randint(0, max(1, width - 20)), random.randint(0, max(1, height - 20))
        draw.text((x, y), ch, font=decoy_font, fill=_random_captcha_color(180, 220))

    red_line_count = {"easy": 4, "medium": 8, "hard": 14}.get(difficulty, 8)
    for _ in range(red_line_count):
        y1 = random.randint(0, height)
        y2 = random.randint(0, height)
        draw.line(
            [(0, y1), (width, y2)],
            fill=(random.randint(170, 230), random.randint(30, 70), random.randint(30, 70)),
            width=random.randint(1, 3),
        )

    rotation_range = 2
    char_canvas_size = HONEYPOT_IMAGE_FONT_SIZE + 4 * bold_stroke_width + 20
    y_cursor = margin
    for line in lines:
        x_cursor = margin
        for ch in line:
            if ch == " ":
                x_cursor += HONEYPOT_IMAGE_FONT_SIZE // 2
                continue
            angle = random.randint(-rotation_range, rotation_range)
            char_color = _honeypot_warning_color()
            char_img = _WelcomeImage.new("RGBA", (char_canvas_size, char_canvas_size), (0, 0, 0, 0))
            char_draw = _WelcomeImageDraw.Draw(char_img)
            char_draw.text(
                (char_canvas_size // 2, char_canvas_size // 2), ch, font=font,
                fill=char_color + (255,), anchor="mm",
                stroke_width=bold_stroke_width, stroke_fill=char_color + (255,),
            )
            if ch == "I":
                ibbox = char_draw.textbbox(
                    (char_canvas_size // 2, char_canvas_size // 2), ch, font=font,
                    anchor="mm", stroke_width=bold_stroke_width,
                )
                dot_radius = max(3, bold_stroke_width + 3)
                dot_cx = (ibbox[0] + ibbox[2]) // 2
                dot_cy = max(dot_radius + 1, ibbox[1] - dot_radius * 2)
                char_draw.ellipse(
                    [dot_cx - dot_radius, dot_cy - dot_radius, dot_cx + dot_radius, dot_cy + dot_radius],
                    fill=char_color + (255,),
                )
            char_img = char_img.rotate(angle, expand=True, resample=_WelcomeImage.BICUBIC)
            paste_x = x_cursor - (char_img.width - char_canvas_size) // 2
            paste_y = y_cursor - (char_img.height - char_canvas_size) // 2
            canvas.paste(char_img, (paste_x, paste_y), char_img)
            x_cursor += _text_width(ch) + 4 + bold_stroke_width
        y_cursor += HONEYPOT_IMAGE_LINE_HEIGHT

    buffer = _welcome_io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    filename = "salon-piege.png" if LANG == "fr" else "honeypot-warning.png"
    return discord.File(buffer, filename=filename)


def _build_verification_embed(guild_name: str) -> discord.Embed:
    title = "🧩 Vérification" if LANG == "fr" else "🧩 Verification"
    desc = (
        f"Pour accéder à **{guild_name}**, recopie exactement le code affiché sur l'image ci-dessous, "
        "puis clique sur le bouton pour le saisir." if LANG == "fr"
        else f"To access **{guild_name}**, retype the exact code shown in the image below, then click "
        "the button to enter it."
    )
    embed = discord.Embed(title=title, description=desc, color=0x5865F2)
    embed.set_image(url="attachment://captcha.png")
    return embed


async def _verification_captcha_failed(member: discord.Member) -> None:
    """Nombre maximum d'essais CAPTCHA dépassé (réglage
    verification_captcha_max_attempts, méthodes MP/Serveur uniquement) :
    exclusion immédiate, sans attendre le délai normal. Même traitement que
    le délai expiré (kick simple, jamais de bannissement, suivi IP,
    nettoyage du salon privé s'il y en a un)."""
    guild = member.guild
    _cancel_verification_timeout(guild.id, member.id)
    reason = (
        "Vérification : nombre maximum d'essais CAPTCHA dépassé" if LANG == "fr"
        else "Verification: max CAPTCHA attempts exceeded"
    )
    ip = _ip_lookup_member(member.id)
    try:
        await member.kick(reason=reason)
    except discord.Forbidden:
        log.warning(f"Vérification : permission insuffisante pour exclure {member} sur {guild.name} (essais CAPTCHA dépassés).")
    except Exception:
        log.exception(f"Vérification : erreur en excluant {member} sur {guild.name} (essais CAPTCHA dépassés).")
    else:
        extra = ""
        if ip:
            count = _ip_register_exclusion(ip)
            extra = (
                f" (IP `{ip}` : {count} exclusion(s) au total — {'en liste noire dès 3' if count < 3 else 'DÉSORMAIS EN LISTE NOIRE'})"
                if LANG == "fr" else
                f" (IP `{ip}`: {count} total exclusion(s) — {'blacklisted at 3' if count < 3 else 'NOW BLACKLISTED'})"
            )
        await _log_security_event(
            guild,
            (
                f"🚫 **{member}** (`{member.id}`) exclu(e) : trop d'essais CAPTCHA échoués.{extra}"
                if LANG == "fr" else
                f"🚫 **{member}** (`{member.id}`) kicked: too many failed CAPTCHA attempts.{extra}"
            ),
        )
    finally:
        await _cleanup_verification_channel(guild, member.id)


class CaptchaModal(discord.ui.Modal):
    def __init__(self, captcha_view: "CaptchaView"):
        super().__init__(title="Vérification" if LANG == "fr" else "Verification")
        self.captcha_view = captcha_view
        self.code_input = discord.ui.TextInput(
            label="Code affiché sur l'image" if LANG == "fr" else "Code shown in the image",
            placeholder="Ex : 7K4PD" if LANG == "fr" else "E.g.: 7K4PD",
            min_length=CAPTCHA_CODE_LENGTH,
            max_length=CAPTCHA_CODE_LENGTH + 2,
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        view = self.captcha_view
        guild = bot.get_guild(view.guild_id)
        if guild is None:
            await interaction.response.edit_message(
                content=("❌ Ce serveur n'est plus accessible." if LANG == "fr" else "❌ That server is no longer reachable."),
                embed=None, attachments=[], view=None,
            )
            return
        member = guild.get_member(view.member_id)
        if member is None:
            await interaction.response.edit_message(
                content=("ℹ️ Tu ne sembles plus être sur ce serveur." if LANG == "fr" else "ℹ️ You don't seem to be on that server anymore."),
                embed=None, attachments=[], view=None,
            )
            return

        submitted = self.code_input.value.strip().upper().replace(" ", "")

        if submitted == view.code:
            view.stop()
            await _complete_verification(member, method="dm" if view.channel_id is None else "channel")

            text = (
                f"✅ Bonne réponse ! Tu es vérifié(e) sur **{guild.name}**." if LANG == "fr"
                else f"✅ Correct! You're verified on **{guild.name}**."
            )
            await interaction.response.edit_message(content=text, embed=None, attachments=[], view=None)

            if view.channel_id is not None:
                asyncio.create_task(_delayed_verification_channel_cleanup(guild, member.id))
        else:
            view.attempts_left -= 1
            if view.attempts_left <= 0:
                view.stop()
                await _verification_captcha_failed(member)
                text = (
                    "❌ Nombre maximum d'essais dépassé — tu as été exclu(e). Tu peux revenir sur le serveur "
                    "et retenter la vérification." if LANG == "fr" else
                    "❌ Max attempts exceeded — you've been kicked. You can come back to the server and try "
                    "verification again."
                )
                await interaction.response.edit_message(content=text, embed=None, attachments=[], view=None)
                return
            new_code = _generate_captcha_code()
            new_view = CaptchaView(
                view.guild_id, view.member_id, view.difficulty, view.minutes,
                code=new_code, channel_id=view.channel_id, attempts_left=view.attempts_left,
            )
            new_file = _draw_captcha_image(new_code, view.difficulty)
            wrong_text = (
                f"❌ Code incorrect — il te reste {view.attempts_left} essai(s). Nouvelle image ci-dessous :"
                if LANG == "fr" else
                f"❌ Wrong code — {view.attempts_left} attempt(s) left. New image below:"
            )
            await interaction.response.edit_message(
                content=wrong_text,
                embed=_build_verification_embed(guild.name),
                attachments=[new_file],
                view=new_view,
            )


class CaptchaVerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Entrer le code" if LANG == "fr" else "Enter code",
            emoji="🔑",
            custom_id=f"captcha_verify_{random.randint(0, 999999)}",
        )

    async def callback(self, interaction: discord.Interaction):
        view: CaptchaView = self.view
        await interaction.response.send_modal(CaptchaModal(view))


class CaptchaView(discord.ui.View):
    def __init__(
        self, guild_id: int, member_id: int, difficulty: str, minutes: typing.Optional[int],
        code: str | None = None, channel_id: int | None = None, attempts_left: int | None = None,
    ):
        super().__init__(timeout=(minutes * 60 if minutes else None))
        self.guild_id = guild_id
        self.member_id = member_id
        self.difficulty = difficulty
        self.minutes = minutes
        self.code = code or _generate_captcha_code()
        self.channel_id = channel_id
        self.attempts_left = (
            attempts_left if attempts_left is not None
            else _get_setting(guild_id, "verification_captcha_max_attempts")
        )
        self.add_item(CaptchaVerifyButton())

    async def on_timeout(self):
        guild = bot.get_guild(self.guild_id)
        member = guild.get_member(self.member_id) if guild else None
        if member is None:
            return
        try:
            await member.send(
                "⌛ Le temps pour répondre à la vérification est écoulé — tu vas être exclu(e) du serveur "
                "(tu pourras revenir et retenter)." if LANG == "fr"
                else "⌛ The verification timed out — you're about to be kicked from the server "
                "(you can come back and try again)."
            )
        except Exception:
            pass


async def _send_welcome_dm(member: discord.Member) -> None:
    """Envoie le MP de bienvenue, si activé sur ce serveur. Appelé soit
    directement à l'arrivée quand le module vérification est désactivé,
    soit juste après une vérification CAPTCHA réussie sinon — jamais avant."""
    if not _get_setting(member.guild.id, "welcome_dm_enabled"):
        return
    try:
        await member.send(t("welcome_dm", guild=member.guild.name, member=member.mention, bot_name="AVSD"))
    except discord.Forbidden:
        pass
    except Exception:
        log.exception(f"Impossible d'envoyer le MP de bienvenue à {member} sur {member.guild.name}.")



_pending_verification_tasks: dict[tuple[int, int], asyncio.Task] = {}
_pending_verification_channels: dict[tuple[int, int], int] = {}


def _cancel_verification_timeout(guild_id: int, member_id: int) -> None:
    task = _pending_verification_tasks.pop((guild_id, member_id), None)
    if task and not task.done():
        task.cancel()


async def _cleanup_verification_channel(guild: discord.Guild, member_id: int) -> None:
    channel_id = _pending_verification_channels.pop((guild.id, member_id), None)
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel is not None:
        try:
            await channel.delete(reason="Vérification terminée (réussie ou expirée)")
        except Exception:
            pass


async def _delayed_verification_channel_cleanup(guild: discord.Guild, member_id: int, delay: int = 5) -> None:
    await asyncio.sleep(delay)
    await _cleanup_verification_channel(guild, member_id)


async def _verification_timeout_kick(member: discord.Member, minutes: typing.Optional[int]) -> None:
    """Attend `minutes` puis exclut (kick, jamais bannissement) le membre
    s'il n'a toujours pas réussi la vérification. Annulé par
    _cancel_verification_timeout dès que la vérification réussit.
    `minutes` vaut None ou 0 pour un délai infini (choisi pour cette méthode
    de vérification) : dans ce cas, aucune exclusion automatique n'a lieu."""
    if not minutes:
        return
    try:
        await asyncio.sleep(minutes * 60)
    except asyncio.CancelledError:
        return

    guild = member.guild
    reason = (
        f"Vérification non complétée dans le délai imparti ({minutes} min)" if LANG == "fr"
        else f"Verification not completed within the time limit ({minutes} min)"
    )
    ip = _ip_lookup_member(member.id)
    try:
        await member.kick(reason=reason)
    except discord.Forbidden:
        log.warning(f"Vérification : permission insuffisante pour exclure {member} sur {guild.name} (délai dépassé).")
    except Exception:
        log.exception(f"Vérification : erreur en excluant {member} sur {guild.name} (délai dépassé).")
    else:
        extra = ""
        if ip:
            count = _ip_register_exclusion(ip)
            extra = (
                f" (IP `{ip}` : {count} exclusion(s) au total — {'en liste noire dès 3' if count < 3 else 'DÉSORMAIS EN LISTE NOIRE'})"
                if LANG == "fr" else
                f" (IP `{ip}`: {count} total exclusion(s) — {'blacklisted at 3' if count < 3 else 'NOW BLACKLISTED'})"
            )
        await _log_security_event(
            guild,
            (
                f"⌛ **{member}** (`{member.id}`) exclu(e) : vérification non complétée en {minutes} min.{extra}"
                if LANG == "fr" else
                f"⌛ **{member}** (`{member.id}`) kicked: verification not completed within {minutes} min.{extra}"
            ),
        )
    finally:
        _pending_verification_tasks.pop((guild.id, member.id), None)
        await _cleanup_verification_channel(guild, member.id)


def _schedule_verification_timeout(member: discord.Member, minutes: typing.Optional[int]) -> None:
    _cancel_verification_timeout(member.guild.id, member.id)
    if not minutes:
        return
    task = asyncio.create_task(_verification_timeout_kick(member, minutes))
    _pending_verification_tasks[(member.guild.id, member.id)] = task


async def _complete_verification(member: discord.Member, *, method: str) -> None:
    """Point d'entrée UNIQUE de réussite de vérification, quelle que soit la
    méthode (dm/channel/link) : annule le délai d'exclusion, applique le
    rôle donné/retiré, et envoie le MP de bienvenue. N'importe quelle méthode
    de vérification doit appeler cette fonction en cas de succès — jamais
    dupliquer cette logique ailleurs."""
    guild = member.guild
    _cancel_verification_timeout(guild.id, member.id)

    role_id = _get_setting(guild.id, "verification_role_id")
    remove_ids = _get_setting(guild.id, "verification_remove_role_ids")
    reason = f"Vérification réussie ({method})" if LANG == "fr" else f"Verification succeeded ({method})"
    try:
        role = guild.get_role(role_id) if role_id else None
        if role is not None:
            await member.add_roles(role, reason=reason)
        for rid in remove_ids:
            r = guild.get_role(rid)
            if r is not None and r in member.roles:
                await member.remove_roles(r, reason=reason)
    except discord.Forbidden:
        log.warning(f"Vérification : permissions insuffisantes pour ajuster les rôles de {member} sur {guild.name}.")
    except Exception:
        log.exception(f"Vérification : erreur en ajustant les rôles de {member} sur {guild.name}.")

    await _send_welcome_dm(member)


VERIFIED_ROLE_DEFAULT_NAME = "✅ Vérifié" if LANG == "fr" else "✅ Verified"
UNVERIFIED_ROLE_DEFAULT_NAME = "🔒 Non vérifié" if LANG == "fr" else "🔒 Unverified"


async def _ensure_verification_roles(guild: discord.Guild) -> tuple[discord.Role, discord.Role]:
    """Renvoie (rôle Vérifié, rôle Non vérifié) pour ce serveur, en les créant
    si besoin. N'écrase jamais un choix déjà fait par un(e) administrateur/
    administratrice dans le panel : si `verification_role_id` /
    `verification_unverified_role_id` pointent déjà vers un rôle existant, ce
    rôle est réutilisé tel quel. Le rôle Non vérifié est automatiquement
    ajouté à `verification_remove_role_ids` (retiré à la réussite du
    CAPTCHA)."""
    verified_id = _get_setting(guild.id, "verification_role_id")
    verified_role = guild.get_role(verified_id) if verified_id else None
    if verified_role is None:
        verified_role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_DEFAULT_NAME)
        if verified_role is None:
            verified_role = await guild.create_role(
                name=VERIFIED_ROLE_DEFAULT_NAME,
                reason="Auto-configuration de la vérification : création du rôle Vérifié",
            )
        _set_setting(guild.id, "verification_role_id", verified_role.id)

    unverified_id = _get_setting(guild.id, "verification_unverified_role_id")
    unverified_role = guild.get_role(unverified_id) if unverified_id else None
    if unverified_role is None:
        unverified_role = discord.utils.get(guild.roles, name=UNVERIFIED_ROLE_DEFAULT_NAME)
        if unverified_role is None:
            unverified_role = await guild.create_role(
                name=UNVERIFIED_ROLE_DEFAULT_NAME,
                reason="Auto-configuration de la vérification : création du rôle Non vérifié",
            )
        _set_setting(guild.id, "verification_unverified_role_id", unverified_role.id)

    remove_ids = list(_get_setting(guild.id, "verification_remove_role_ids") or [])
    if unverified_role.id not in remove_ids:
        remove_ids.append(unverified_role.id)
        _set_setting(guild.id, "verification_remove_role_ids", remove_ids)

    return verified_role, unverified_role


def _channel_is_private(channel: discord.abc.GuildChannel) -> bool:
    """Un salon est considéré privé si @everyone n'a pas la vue dessus
    (overwrite explicite `view_channel=False`). L'auto-configuration de la
    vérification ne touche jamais à ces salons-là — elle ne les rend pas
    publics et ne modifie pas leurs permissions."""
    try:
        overwrite = channel.overwrites_for(channel.guild.default_role)
    except Exception:
        return False
    return overwrite.view_channel is False


async def _apply_verification_channel_gating(
    guild: discord.Guild, verified_role: discord.Role, unverified_role: discord.Role,
    *, skip_channel_ids: frozenset = frozenset(),
) -> int:
    """Sur tous les salons textuels/vocaux non privés : le rôle Non vérifié
    ne peut pas voir le salon, le rôle Vérifié le peut (les autres
    permissions existantes de ces salons ne sont jamais touchées). Ne modifie
    jamais un salon déjà privé, ni un salon listé dans `skip_channel_ids`
    (le salon piège notamment : il doit rester visible/inscriptible par les
    non-vérifiés — voir _auto_setup_verification). Renvoie le nombre de
    salons mis à jour."""
    updated = 0
    channels = list(guild.text_channels) + list(guild.voice_channels)
    for channel in channels:
        if channel.id in skip_channel_ids:
            continue
        if _channel_is_private(channel):
            continue
        changed = False
        try:
            unverified_ow = channel.overwrites_for(unverified_role)
            if unverified_ow.view_channel is not False:
                unverified_ow.view_channel = False
                await channel.set_permissions(
                    unverified_role, overwrite=unverified_ow,
                    reason="Auto-configuration de la vérification : salon masqué tant que non vérifié",
                )
                changed = True
            verified_ow = channel.overwrites_for(verified_role)
            if verified_ow.view_channel is not True:
                verified_ow.view_channel = True
                await channel.set_permissions(
                    verified_role, overwrite=verified_ow,
                    reason="Auto-configuration de la vérification : salon visible une fois vérifié",
                )
                changed = True
        except discord.Forbidden:
            continue
        except Exception:
            log.exception(f"Vérification : échec de configuration des permissions du salon {channel} sur {guild.name}.")
            continue
        if changed:
            updated += 1
    return updated


async def _auto_setup_verification(guild: discord.Guild) -> tuple[discord.Role, discord.Role, int]:
    """Point d'entrée unique de l'auto-configuration : crée les rôles Vérifié/
    Non vérifié si besoin, puis applique le masquage sur tous les salons
    textuels/vocaux non privés — sauf le salon piège, qui doit rester
    accessible aux non-vérifiés (c'est tout son intérêt). Appelé
    automatiquement dès que le module vérification passe à l'état activé,
    quel que soit le moyen utilisé (bouton du panel ou /configuration-complete),
    et peut aussi être relancé manuellement (ex. après la création de
    nouveaux salons)."""
    verified_role, unverified_role = await _ensure_verification_roles(guild)
    skip_ids = set()
    if honeypot_id := _get_setting(guild.id, "honeypot_channel_id"):
        skip_ids.add(honeypot_id)
    if link_channel_id := _get_setting(guild.id, "verification_link_channel_id"):
        skip_ids.add(link_channel_id)
    updated = await _apply_verification_channel_gating(guild, verified_role, unverified_role, skip_channel_ids=frozenset(skip_ids))
    return verified_role, unverified_role, updated


HONEYPOT_CHANNEL_NAME = "🍯-ne-pas-écrire-ici" if LANG == "fr" else "🍯-do-not-post-here"

HONEYPOT_WATCHDOG_INTERVAL_SECONDS = 10 * 60          # fréquence de vérification (pas de renvoi !)
HONEYPOT_ROTATION_INTERVAL_SECONDS = 24 * 3600        # purge du salon + nouvelle image toutes les 24 h
HONEYPOT_MAX_MANUAL_DELETIONS = 3                     # suppressions manuelles avant de proposer de désactiver
HONEYPOT_MANUAL_DELETE_WINDOW_SECONDS = 7 * 24 * 3600 # fenêtre de comptage des suppressions manuelles
HONEYPOT_PROMPT_TIMEOUT_SECONDS = 24 * 3600

# IDs de messages que le BOT supprime lui-même (rotation, purge) : ne comptent pas
# comme une suppression manuelle et ne déclenchent pas de renvoi immédiat.
_honeypot_internal_deleted_ids: set[int] = set()
# Salons en cours de purge quotidienne (évite le spam de logs de suppression).
_honeypot_purging_channels: set[int] = set()
_honeypot_guild_locks: dict[int, asyncio.Lock] = {}
_honeypot_prompt_pending: set[int] = set()
_honeypot_last_audit_seen: dict[int, tuple] = {}


def _honeypot_lock(guild_id: int) -> asyncio.Lock:
    lock = _honeypot_guild_locks.get(guild_id)
    if lock is None:
        lock = _honeypot_guild_locks[guild_id] = asyncio.Lock()
    return lock


HONEYPOT_EMBED_COLOR = 0xCE1515


async def _send_honeypot_warning_image(guild: discord.Guild, channel: discord.TextChannel) -> "discord.Message | None":
    """Génère l'image d'avertissement du salon piège, l'envoie dans `channel`
    (dans un embed, avec le compteur global de personnes piégées en pied de
    l'embed — donc affiché juste EN DESSOUS de l'image), l'épingle, et
    retient son ID (honeypot_warning_message_id) pour pouvoir vérifier plus
    tard qu'elle est toujours là (voir _ensure_honeypot_warning_present /
    _honeypot_watchdog_loop). Utilisée à la création du salon, après
    modification du texte d'avertissement, par le bouton « Renvoyer l'image »
    du panel, et par le watchdog."""
    difficulty = _get_setting(guild.id, "verification_difficulty")
    warning_text = _pick_honeypot_warning_text(guild.id)

    # Supprime l'ancienne image avant d'en renvoyer une nouvelle : sans ça,
    # chaque (ré)envoi (bouton « Renvoyer l'image », modification du texte,
    # rotation périodique du watchdog...) laissait l'ancienne épinglée en
    # plus de la nouvelle, et l'image affichée au premier plan du salon
    # restait toujours la même tant que personne ne la supprimait à la main.
    old_message_id = _get_setting(guild.id, "honeypot_warning_message_id")
    if old_message_id:
        _honeypot_internal_deleted_ids.add(old_message_id)
        try:
            old_msg = await channel.fetch_message(old_message_id)
            await old_msg.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            _honeypot_internal_deleted_ids.discard(old_message_id)

    try:
        file = _draw_honeypot_warning_image(warning_text, difficulty)
        embed = discord.Embed(color=HONEYPOT_EMBED_COLOR)
        embed.set_image(url=f"attachment://{file.filename}")
        embed.set_footer(text=_honeypot_counter_footer_text())
        msg = await channel.send(file=file, embed=embed)
        _set_setting(guild.id, "honeypot_warning_message_id", msg.id)
        try:
            await msg.pin(reason="Salon piège : image d'avertissement")
            # Supprime le message système « AVSD a épinglé un message » qui,
            # sinon, s'accumulait dans le salon à chaque renvoi.
            async for sys_msg in channel.history(limit=5, after=msg):
                if sys_msg.type == discord.MessageType.pins_add and sys_msg.author.id == bot.user.id:
                    await sys_msg.delete()
                    break
        except Exception:
            pass
        return msg
    except discord.Forbidden:
        return None
    except Exception:
        log.exception(f"Salon piège : échec de l'envoi de l'image d'avertissement sur {guild.name}.")
        return None


async def _update_honeypot_message_counter(guild: discord.Guild) -> None:
    """Met à jour, sur CE serveur, le pied (footer) de l'embed de l'image
    d'avertissement avec la valeur actuelle du compteur global — sans
    retoucher l'image elle-même. Ne fait rien si le salon/message n'existe
    pas (le watchdog s'occupe déjà de renvoyer l'image si elle manque)."""
    if not _module_enabled(guild.id, "honeypot"):
        return
    channel_id = _get_setting(guild.id, "honeypot_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel is None or not isinstance(channel, discord.TextChannel):
        return
    message_id = _get_setting(guild.id, "honeypot_warning_message_id")
    if not message_id:
        return
    try:
        msg = await channel.fetch_message(message_id)
    except Exception:
        return
    embed = msg.embeds[0] if msg.embeds else discord.Embed(color=HONEYPOT_EMBED_COLOR)
    embed.set_footer(text=_honeypot_counter_footer_text())
    try:
        await msg.edit(embed=embed)
    except Exception:
        pass


async def _refresh_all_honeypot_counters() -> None:
    """Le compteur global est le même partout : dès qu'il change (une
    personne vient d'être piégée quelque part), on met à jour son affichage
    sous l'image sur TOUS les serveurs où le salon piège est actif."""
    for guild in list(bot.guilds):
        if guild.id == STORAGE_GUILD_ID:
            continue
        try:
            await _update_honeypot_message_counter(guild)
        except Exception:
            log.exception(f"Salon piège : échec de la mise à jour du compteur sur {guild.name}.")


async def _purge_honeypot_channel(channel: discord.TextChannel) -> int:
    """Supprime TOUS les messages du salon piège (purge quotidienne)."""
    guild_id = channel.guild.id
    _honeypot_purging_channels.add(channel.id)
    warning_id = _get_setting(guild_id, "honeypot_warning_message_id")
    if warning_id:
        _honeypot_internal_deleted_ids.add(warning_id)
    try:
        removed = await channel.purge(limit=None, reason="Salon piège : purge quotidienne (24 h)")
        _set_setting(guild_id, "honeypot_warning_message_id", 0)
        await asyncio.sleep(3)  # laisse passer les événements de suppression avant de lever le drapeau
        return len(removed)
    except discord.Forbidden:
        log.warning(f"Salon piège : permission manquante pour purger #{channel.name} sur {channel.guild.name}.")
        _honeypot_internal_deleted_ids.discard(warning_id)
        return 0
    except Exception:
        log.exception(f"Salon piège : échec de la purge de #{channel.name} sur {channel.guild.name}.")
        _honeypot_internal_deleted_ids.discard(warning_id)
        return 0
    finally:
        _honeypot_purging_channels.discard(channel.id)


async def _ensure_honeypot_warning_present(guild: discord.Guild, *, force_purge: bool = False) -> bool:
    """Garde l'image d'avertissement du salon piège en place, SANS la renvoyer
    en boucle :
      - si elle a moins de 24 h et existe encore -> ne fait RIEN ;
      - si elle a disparu (supprimée) -> la renvoie immédiatement (sans purge) ;
      - si elle a 24 h ou plus (ou force_purge) -> purge TOUS les messages du
        salon puis renvoie une nouvelle image.
    L'âge est déduit de l'ID du message (snowflake) : rien à stocker en plus, et
    ça survit aux redémarrages du bot. Renvoie True si l'image est présente."""
    if not _module_enabled(guild.id, "honeypot"):
        return False
    channel_id = _get_setting(guild.id, "honeypot_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel is None or not isinstance(channel, discord.TextChannel):
        return False

    async with _honeypot_lock(guild.id):
        message_id = _get_setting(guild.id, "honeypot_warning_message_id")
        purge = force_purge
        if message_id and not purge:
            age = (discord.utils.utcnow() - discord.utils.snowflake_time(message_id)).total_seconds()
            if age >= HONEYPOT_ROTATION_INTERVAL_SECONDS:
                purge = True
            else:
                try:
                    await channel.fetch_message(message_id)
                    return True
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    return False
                except Exception:
                    log.exception(f"Salon piège : échec de la vérification de l'image d'avertissement sur {guild.name}.")
                    return False

        if purge:
            removed = await _purge_honeypot_channel(channel)
            log.info(f"Salon piège : purge quotidienne sur {guild.name} — {removed} message(s) supprimé(s).")
        msg = await _send_honeypot_warning_image(guild, channel)

    if msg is not None:
        await save_guild_config(guild)
    return msg is not None


async def _honeypot_find_deleter(guild: discord.Guild, channel: discord.TextChannel):
    """Retrouve dans le journal d'audit QUI a supprimé l'image du bot dans le
    salon piège. Les entrées « message supprimé » sont regroupées par Discord
    (même id, `count` qui augmente) : on suit donc le couple (id, count) pour ne
    détecter que les nouvelles suppressions. Renvoie None si inconnu."""
    for _ in range(4):
        await asyncio.sleep(1.5)
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.message_delete):
                if getattr(entry.target, "id", None) != bot.user.id:
                    continue
                if getattr(getattr(entry.extra, "channel", None), "id", None) != channel.id:
                    continue
                key = (entry.id, getattr(entry.extra, "count", 1))
                prev = _honeypot_last_audit_seen.get(guild.id)
                if prev == key:
                    break  # pas encore d'entrée plus récente -> on réessaie
                age = (discord.utils.utcnow() - entry.created_at).total_seconds()
                if prev is None and age > 90:
                    _honeypot_last_audit_seen[guild.id] = key  # entrée ancienne : simple point de repère
                    break
                _honeypot_last_audit_seen[guild.id] = key
                return entry.user
        except discord.Forbidden:
            log.warning(f"Salon piège : « Voir le journal d'audit » manquant sur {guild.name} — auteur de la suppression inconnu.")
            return None
        except Exception:
            log.exception(f"Salon piège : lecture du journal d'audit impossible sur {guild.name}.")
            return None
    return None


def _honeypot_register_manual_deletion(guild_id: int) -> int:
    now = time.time()
    recent = [
        ts for ts in (_get_setting(guild_id, "honeypot_manual_delete_log") or [])
        if isinstance(ts, (int, float)) and now - ts < HONEYPOT_MANUAL_DELETE_WINDOW_SECONDS
    ]
    recent.append(now)
    _set_setting(guild_id, "honeypot_manual_delete_log", recent)
    return len(recent)


class HoneypotDisableProposalView(discord.ui.View):
    """Proposition affichée après plusieurs suppressions manuelles de l'image."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=HONEYPOT_PROMPT_TIMEOUT_SECONDS)
        self.guild_id = guild_id

    def _finish(self) -> None:
        _honeypot_prompt_pending.discard(self.guild_id)
        _set_setting(self.guild_id, "honeypot_manual_delete_log", [])
        self.stop()

    async def _check_admin(self, interaction: discord.Interaction):
        guild = bot.get_guild(self.guild_id)
        member = guild.get_member(interaction.user.id) if guild else None
        if guild is None or member is None or not _has_effective_administrator(member):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return None
        return guild

    @discord.ui.button(
        label="Désactiver le salon piège" if LANG == "fr" else "Disable the honeypot",
        style=discord.ButtonStyle.danger, emoji="🛑",
    )
    async def disable_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = await self._check_admin(interaction)
        if guild is None:
            return
        _set_setting(guild.id, "module_honeypot_enabled", False)
        self._finish()
        await save_guild_config(guild)
        await interaction.response.edit_message(
            content=(
                "✅ Salon piège **désactivé** : il ne sanctionne plus personne et l'image n'est plus renvoyée. "
                "Le salon existe toujours (tu peux le supprimer à la main) ; réactive-le via `/panel` > Salon piège."
                if LANG == "fr" else
                "✅ Honeypot **disabled**: it no longer sanctions anyone and the image is no longer resent. "
                "The channel still exists (you can delete it manually); re-enable it via `/panel` > Honeypot."
            ),
            view=None,
        )
        await _log_security_event(
            guild,
            f"🍯 Salon piège désactivé par **{interaction.user}** (`{interaction.user.id}`)." if LANG == "fr"
            else f"🍯 Honeypot disabled by **{interaction.user}** (`{interaction.user.id}`).",
        )

    @discord.ui.button(
        label="Garder le salon piège" if LANG == "fr" else "Keep the honeypot",
        style=discord.ButtonStyle.success, emoji="🍯",
    )
    async def keep_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = await self._check_admin(interaction)
        if guild is None:
            return
        self._finish()
        await save_guild_config(guild)
        await interaction.response.edit_message(
            content=(
                "👍 Le salon piège est conservé. L'image continuera d'être restaurée automatiquement."
                if LANG == "fr" else
                "👍 Honeypot kept. The image will keep being restored automatically."
            ),
            view=None,
        )

    async def on_timeout(self):
        _honeypot_prompt_pending.discard(self.guild_id)
        _set_setting(self.guild_id, "honeypot_manual_delete_log", [])


async def _propose_honeypot_disable(guild: discord.Guild, deleter, count: int) -> None:
    """Propose de désactiver le salon piège : en MP à l'administrateur qui a
    supprimé l'image (si on le connaît), sinon dans le salon d'audit."""
    _honeypot_prompt_pending.add(guild.id)
    view = HoneypotDisableProposalView(guild.id)
    days = HONEYPOT_MANUAL_DELETE_WINDOW_SECONDS // 86400
    text = (
        f"🍯 L'image d'avertissement du salon piège de **{guild.name}** a été supprimée **{count} fois** "
        f"en {days} jours. Je la remets à chaque fois, mais si ce salon vous gêne, "
        "veux-tu que je le **désactive** ?"
        if LANG == "fr" else
        f"🍯 The honeypot warning image on **{guild.name}** was deleted **{count} times** in {days} days. "
        "I restore it every time, but if this channel is a nuisance, do you want me to **disable** it?"
    )

    sent = False
    member = guild.get_member(deleter.id) if deleter is not None else None
    if member is not None and not member.bot and _has_effective_administrator(member):
        try:
            await member.send(text, view=view)
            sent = True
        except Exception:
            log.info(f"Salon piège : MP de proposition impossible à {member} — repli sur le salon d'audit.")
    if not sent:
        try:
            audit_channel = await get_or_create_audit_channel(guild)
            await audit_channel.send(text, view=view)
            sent = True
        except Exception:
            log.exception(f"Salon piège : impossible d'envoyer la proposition de désactivation sur {guild.name}.")
    if not sent:
        _honeypot_prompt_pending.discard(guild.id)


async def _on_honeypot_warning_deleted(guild_id: int, message_id: int) -> None:
    """Auto-réparation : l'image d'avertissement vient d'être supprimée par
    quelqu'un d'autre que le bot -> on la remet tout de suite, on compte la
    suppression, et au bout de HONEYPOT_MAX_MANUAL_DELETIONS on propose de
    désactiver le salon piège."""
    if guild_id == STORAGE_GUILD_ID:
        return
    if message_id in _honeypot_internal_deleted_ids:
        _honeypot_internal_deleted_ids.discard(message_id)
        return
    if message_id != _get_setting(guild_id, "honeypot_warning_message_id"):
        return
    guild = bot.get_guild(guild_id)
    if guild is None or not _module_enabled(guild_id, "honeypot"):
        return
    channel_id = _get_setting(guild_id, "honeypot_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel is None or not isinstance(channel, discord.TextChannel):
        return

    async with _honeypot_lock(guild_id):
        if _get_setting(guild_id, "honeypot_warning_message_id") == message_id:
            msg = await _send_honeypot_warning_image(guild, channel)
        else:
            msg = True  # déjà remplacée entre-temps
    if msg is None:
        log.warning(f"Salon piège : impossible de restaurer l'image sur {guild.name} (permissions ?).")

    deleter = await _honeypot_find_deleter(guild, channel)
    if deleter is not None and deleter.id == bot.user.id:
        await save_guild_config(guild)
        return

    count = _honeypot_register_manual_deletion(guild_id)
    await save_guild_config(guild)
    who = f"**{deleter}** (`{deleter.id}`)" if deleter is not None else ("quelqu'un" if LANG == "fr" else "someone")
    await _log_security_event(
        guild,
        (f"🍯 L'image du salon piège a été supprimée par {who} — restaurée automatiquement "
         f"({count}/{HONEYPOT_MAX_MANUAL_DELETIONS} avant proposition de désactivation).") if LANG == "fr"
        else (f"🍯 The honeypot image was deleted by {who} — automatically restored "
              f"({count}/{HONEYPOT_MAX_MANUAL_DELETIONS} before offering to disable)."),
    )
    if count >= HONEYPOT_MAX_MANUAL_DELETIONS and guild_id not in _honeypot_prompt_pending:
        await _propose_honeypot_disable(guild, deleter, count)


@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    if payload.guild_id is None:
        return
    try:
        await _on_honeypot_warning_deleted(payload.guild_id, payload.message_id)
    except Exception:
        log.exception("Salon piège : erreur dans la réparation automatique de l'image.")


@bot.event
async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
    if payload.guild_id is None or payload.guild_id == STORAGE_GUILD_ID:
        return
    warning_id = _get_setting(payload.guild_id, "honeypot_warning_message_id")
    if warning_id and warning_id in payload.message_ids:
        try:
            await _on_honeypot_warning_deleted(payload.guild_id, warning_id)
        except Exception:
            log.exception("Salon piège : erreur dans la réparation automatique de l'image (suppression groupée).")


async def _log_file_limit_loop() -> None:
    """Boucle de fond active uniquement si LOG_FILE_LIMIT_ENABLED (choix fait
    une fois pour toutes au démarrage, voir log_limit_setup_wizard) : toutes
    les LOG_FILE_LIMIT_CHECK_SECONDS, vide TOTALEMENT le fichier de log
    (LOG_FILE) dès qu'il dépasse LOG_FILE_LIMIT_MAX_BYTES. Objectif : sur un
    bot présent sur beaucoup de serveurs, éviter qu'un fichier de log énorme
    et inutile ne s'accumule sur le disque. N'affecte jamais le
    fonctionnement du bot en cas d'erreur (fichier verrouillé, permissions...),
    l'erreur est seulement journalisée."""
    while True:
        try:
            await asyncio.sleep(LOG_FILE_LIMIT_CHECK_SECONDS)
            if os.path.isfile(LOG_FILE) and os.path.getsize(LOG_FILE) > LOG_FILE_LIMIT_MAX_BYTES:
                with open(LOG_FILE, "w", encoding="utf-8"):
                    pass
                log.warning(
                    f"🧹 Fichier de log ({LOG_FILE}) vidé automatiquement "
                    f"(dépassait {LOG_FILE_LIMIT_MAX_BYTES} octets — limitation activée au démarrage)."
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Erreur dans la boucle de limitation du fichier de log.")


async def _honeypot_watchdog_loop() -> None:
    """Boucle de fond : toutes les HONEYPOT_WATCHDOG_INTERVAL_SECONDS (10 min),
    vérifie chaque serveur où le salon piège est actif. Elle ne renvoie plus
    l'image en boucle : _ensure_honeypot_warning_present ne fait quelque chose
    que si l'image a disparu (renvoi) ou a 24 h (purge du salon + nouvelle image)."""
    await asyncio.sleep(30)
    while True:
        try:
            for guild in list(bot.guilds):
                if guild.id == STORAGE_GUILD_ID:
                    continue
                try:
                    await _ensure_honeypot_warning_present(guild)
                except Exception:
                    log.exception(f"Salon piège : erreur du watchdog sur {guild.name}.")
                await asyncio.sleep(0.5)
            await asyncio.sleep(HONEYPOT_WATCHDOG_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Erreur dans la boucle de surveillance du salon piège.")
            await asyncio.sleep(60)


async def _setup_honeypot_channel(guild: discord.Guild) -> discord.TextChannel:
    """Crée (ou retrouve/resynchronise) le salon piège : visible ET
    inscriptible par TOUT LE MONDE, y compris les membres non vérifiés (le
    rôle Non vérifié est explicitement autorisé s'il existe déjà) — liens,
    images et textes autorisés par défaut. Poste et épingle l'image
    d'avertissement générée avec le même style que le CAPTCHA de
    vérification. N'écrase jamais un salon existant : si
    `honeypot_channel_id` pointe déjà vers un salon valide, il est réutilisé
    (permissions et sujet resynchronisés, nouvelle image postée)."""
    channel_id = _get_setting(guild.id, "honeypot_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel is not None and not isinstance(channel, discord.TextChannel):
        channel = None

    everyone = guild.default_role
    overwrites = {
        everyone: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            embed_links=True, attach_files=True,
        ),
    }
    if guild.me is not None:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_messages=True,
            embed_links=True, attach_files=True, read_message_history=True, manage_channels=True,
        )
    unverified_id = _get_setting(guild.id, "verification_unverified_role_id")
    unverified_role = guild.get_role(unverified_id) if unverified_id else None
    if unverified_role is not None:
        overwrites[unverified_role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            embed_links=True, attach_files=True,
        )

    topic = (
        "⚠️ Ne rien écrire ici — salon piège : tout message posté ici entraîne une sanction automatique."
        if LANG == "fr"
        else "⚠️ Do not post here — honeypot channel: any message posted here triggers an automatic sanction."
    )

    if channel is None:
        channel = await guild.create_text_channel(
            name=HONEYPOT_CHANNEL_NAME, overwrites=overwrites, topic=topic,
            reason="Création du salon piège (/salon-piege)",
        )
        _set_setting(guild.id, "honeypot_channel_id", channel.id)
    else:
        for target, overwrite in overwrites.items():
            try:
                await channel.set_permissions(
                    target, overwrite=overwrite, reason="Salon piège : resynchronisation des permissions",
                )
            except discord.Forbidden:
                pass
        try:
            await channel.edit(topic=topic)
        except Exception:
            pass

    _set_setting(guild.id, "module_honeypot_enabled", True)

    await _send_honeypot_warning_image(guild, channel)

    return channel


async def _start_channel_verification(member: discord.Member, difficulty: str, minutes: int) -> None:
    """Méthode « Salon privé » : crée, dans la catégorie choisie par les
    modérateurs, un salon textuel visible UNIQUEMENT par ce membre, où le
    CAPTCHA est posté directement (pas besoin d'avoir les MP ouverts)."""
    guild = member.guild
    category_id = _get_setting(guild.id, "verification_channel_category_id")
    category = guild.get_channel(category_id) if category_id else None
    if not isinstance(category, discord.CategoryChannel):
        await _log_security_event(
            guild,
            (
                f"⚠️ Vérification par salon privé activée mais aucune catégorie valide n'est configurée — "
                f"**{member}** n'a pas pu recevoir de salon de vérification (configurer via `/panel` > "
                "Vérification > Méthode/délai/salon)."
            ) if LANG == "fr" else (
                f"⚠️ In-server verification is enabled but no valid category is configured — **{member}** "
                "couldn't get a verification channel (configure it via `/panel` > Verification > "
                "Method/timeout/channel)."
            ),
        )
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, attach_files=True,
        ),
    }
    if guild.me is not None:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True, manage_messages=True,
            attach_files=True, read_message_history=True,
        )

    base_name = "vérification" if LANG == "fr" else "verify"
    channel_name = f"{base_name}-{member.name}"[:90]
    try:
        channel = await guild.create_text_channel(
            name=channel_name, category=category, overwrites=overwrites,
            reason="Vérification : salon privé créé pour ce membre",
        )
    except discord.Forbidden:
        await _log_security_event(
            guild,
            (f"⚠️ Permission insuffisante pour créer le salon de vérification de **{member}**." if LANG == "fr"
             else f"⚠️ Missing permission to create the verification channel for **{member}**."),
        )
        return
    except Exception:
        log.exception(f"Vérification : échec de la création du salon privé pour {member} sur {guild.name}.")
        return

    _pending_verification_channels[(guild.id, member.id)] = channel.id
    view = CaptchaView(guild.id, member.id, difficulty, minutes, channel_id=channel.id)
    embed = _build_verification_embed(guild.name)
    file = _draw_captcha_image(view.code, difficulty)
    try:
        await channel.send(content=member.mention, embed=embed, file=file, view=view)
    except Exception:
        log.exception(f"Vérification : échec de l'envoi du CAPTCHA dans le salon privé de {member} sur {guild.name}.")


_pending_link_tokens: dict[str, dict] = {}


def _new_verification_link_token(guild_id: int, member_id: int, minutes: int) -> str:
    token = secrets.token_urlsafe(24)
    _pending_link_tokens[token] = {
        "guild_id": guild_id,
        "member_id": member_id,
        "expires_at": time.time() + minutes * 60,
    }
    return token


async def _start_dm_verification(member: discord.Member, difficulty: str, minutes: typing.Optional[int]) -> None:
    view = CaptchaView(member.guild.id, member.id, difficulty, minutes)
    embed = _build_verification_embed(member.guild.name)
    try:
        try:
            file = _draw_captcha_image(view.code, difficulty)
            await member.send(embed=embed, file=file, view=view)
        except discord.HTTPException as e:
            if e.code == 40003:
                await asyncio.sleep(5)
                file = _draw_captcha_image(view.code, difficulty)
                await member.send(embed=embed, file=file, view=view)
            else:
                raise
    except discord.Forbidden:
        await _log_security_event(
            member.guild,
            (
                f"⚠️ Impossible d'envoyer le CAPTCHA de vérification en MP à **{member}** (MP fermés). "
                "Iel devra être vérifié(e) manuellement par un(e) modérateur/modératrice, sinon exclusion "
                "automatique au délai configuré."
            ) if LANG == "fr" else (
                f"⚠️ Couldn't DM the verification CAPTCHA to **{member}** (DMs closed). "
                "They'll need to be manually verified by a moderator, otherwise they'll be kicked "
                "automatically at the configured timeout."
            ),
        )
    except discord.HTTPException as e:
        await _log_security_event(
            member.guild,
            (
                f"⚠️ Impossible d'envoyer le CAPTCHA de vérification en MP à **{member}** "
                f"(Discord a limité l'ouverture de MP : {e})."
            ) if LANG == "fr" else (
                f"⚠️ Couldn't DM the verification CAPTCHA to **{member}** "
                f"(Discord rate-limited DM opening: {e})."
            ),
        )
    except Exception:
        log.exception(f"Erreur lors de l'envoi de la vérification CAPTCHA en MP à {member}.")


async def _start_link_verification(member: discord.Member, minutes: int) -> None:
    """Méthode « Lien de vérification » : ne fait RIEN envoyer en MP. Le rôle
    Non vérifié (déjà donné avant l'appel) rend automatiquement visible le
    salon unique configuré (verification_link_channel_id), où un message
    persistant avec un bouton « Se vérifier » a été publié une fois pour
    toutes par un(e) administrateur/administratrice (voir
    ConfigPublishVerificationLinkButton). Cette fonction se contente de
    prévenir en logs si ce salon n'est pas (ou plus) configuré."""
    guild = member.guild
    channel_id = _get_setting(guild.id, "verification_link_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    if not VERIFY_PUBLIC_BASE_URL:
        await _log_security_event(
            guild,
            (
                f"⚠️ Vérification par lien activée mais `VERIFY_PUBLIC_BASE_URL` n'est pas configuré dans "
                f"`bot_config.json` côté hébergeur du bot — **{member}** ne pourra pas se vérifier."
            ) if LANG == "fr" else (
                f"⚠️ Link verification is enabled but `VERIFY_PUBLIC_BASE_URL` isn't set in "
                f"`bot_config.json` on the bot host — **{member}** won't be able to verify."
            ),
        )
        return
    if channel is None:
        await _log_security_event(
            guild,
            (
                f"⚠️ Vérification par lien activée mais aucun salon valide n'est configuré — **{member}** "
                "ne voit aucun endroit où se vérifier (configurer via `/panel` > Vérification > "
                "Méthode & salon > Salon du lien, puis cliquer sur « Publier le message »)."
            ) if LANG == "fr" else (
                f"⚠️ Link verification is enabled but no valid channel is configured — **{member}** has "
                "nowhere to verify (configure it via `/panel` > Verification > Method & channel > "
                "Link channel, then click \"Publish message\")."
            ),
        )


def _verify_link_page_html(message: str, success: bool = False) -> str:
    color = "#43b581" if success else "#ed4245"
    safe_message = message.replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Vérification</title></head>"
        "<body style=\"font-family:sans-serif;background:#23272a;color:#fff;display:flex;"
        "align-items:center;justify-content:center;height:100vh;margin:0;\">"
        "<div style=\"text-align:center;padding:2rem 3rem;border-radius:12px;background:#2c2f33;"
        "max-width:90vw;\">"
        f"<h1 style=\"color:{color};font-size:1.4rem;\">{safe_message}</h1></div></body></html>"
    )


async def _verify_handle_request(request):
    from aiohttp import web

    token = request.match_info.get("token", "")
    data = _pending_link_tokens.get(token)
    if not data or data["expires_at"] < time.time():
        _pending_link_tokens.pop(token, None)
        msg = "❌ Lien invalide ou expiré." if LANG == "fr" else "❌ Invalid or expired link."
        return web.Response(text=_verify_link_page_html(msg), content_type="text/html", status=410)

    guild = bot.get_guild(data["guild_id"])
    member = guild.get_member(data["member_id"]) if guild else None
    if guild is None or member is None:
        _pending_link_tokens.pop(token, None)
        msg = "❌ Membre ou serveur introuvable." if LANG == "fr" else "❌ Member or server not found."
        return web.Response(text=_verify_link_page_html(msg), content_type="text/html", status=404)

    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.remote or "0.0.0.0")
    _ip_remember_member(member.id, ip)

    if _ip_is_blacklisted(ip):
        _pending_link_tokens.pop(token, None)
        await _log_security_event(
            guild,
            (f"⛔ **{member}** (`{member.id}`) — vérification par lien refusée : IP en liste noire." if LANG == "fr"
             else f"⛔ **{member}** (`{member.id}`) — link verification denied: IP is blacklisted."),
        )
        msg = (
            "⛔ Accès refusé : cette adresse IP est en liste noire (exclusions répétées ou salon piège)."
            if LANG == "fr" else
            "⛔ Access denied: this IP address is blacklisted (repeated exclusions or honeypot trigger)."
        )
        return web.Response(text=_verify_link_page_html(msg), content_type="text/html", status=403)

    info = await _proxycheck_lookup(ip)
    if info and info.get("is_vpn_or_proxy"):
        _pending_link_tokens.pop(token, None)
        await _log_security_event(
            guild,
            (f"⛔ **{member}** (`{member.id}`) — vérification par lien refusée : VPN/proxy détecté." if LANG == "fr"
             else f"⛔ **{member}** (`{member.id}`) — link verification denied: VPN/proxy detected."),
        )
        msg = (
            "⛔ Accès refusé : VPN ou proxy détecté. Désactive-le puis redemande une vérification." if LANG == "fr"
            else "⛔ Access denied: VPN or proxy detected. Turn it off then ask for a new verification link."
        )
        return web.Response(text=_verify_link_page_html(msg), content_type="text/html", status=403)

    _pending_link_tokens.pop(token, None)
    await _complete_verification(member, method="link")
    msg = (
        f"✅ Vérifié(e) ! Tu peux retourner sur {guild.name}." if LANG == "fr"
        else f"✅ Verified! You can head back to {guild.name}."
    )
    return web.Response(text=_verify_link_page_html(msg, success=True), content_type="text/html")


_verify_web_started = False


async def _start_verify_web_server() -> None:
    """Démarre le petit serveur web intégré au bot pour la méthode de
    vérification « Lien ». Sans effet si VERIFY_PUBLIC_BASE_URL n'est pas
    configuré (aucun serveur n'écoute alors, la méthode "link" restera
    simplement indisponible et le signale à chaque tentative)."""
    global _verify_web_started
    if _verify_web_started or not VERIFY_PUBLIC_BASE_URL:
        return
    _verify_web_started = True
    try:
        from aiohttp import web
        app = web.Application()
        app.router.add_get("/verify/{token}", _verify_handle_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", VERIFY_WEB_PORT)
        await site.start()
        log.info(f"Vérification par lien : serveur web démarré sur le port {VERIFY_WEB_PORT}.")
    except Exception:
        log.exception("Vérification par lien : échec du démarrage du serveur web.")


async def _start_verification(member: discord.Member) -> None:
    if member.bot:
        return
    if not _module_enabled(member.guild.id, "verification"):
        return

    guild = member.guild
    difficulty = _get_setting(guild.id, "verification_difficulty")
    method = _get_setting(guild.id, "verification_method")
    minutes = _get_setting(
        guild.id,
        {
            "dm": "verification_dm_timeout_minutes",
            "link": "verification_link_timeout_minutes",
        }.get(method, "verification_channel_timeout_minutes"),
    )

    _schedule_verification_timeout(member, minutes)

    if method == "link":
        await _start_link_verification(member, minutes)
    elif method == "dm":
        await _start_dm_verification(member, difficulty, minutes)
    else:
        await _start_channel_verification(member, difficulty, minutes)



async def _enforce_apps_policy(member: discord.Member) -> None:
    """Réglage « Application externe » sur interdit : un bot qui vient d'être ajouté
    au serveur est expulsé, sauf s'il est en liste blanche ou si la personne
    qui l'a ajouté est le/la propriétaire ou est en liste blanche."""
    guild = member.guild
    if member.id == bot.user.id or guild.id == STORAGE_GUILD_ID:
        return
    try:
        if await get_apps_allowed(guild):
            return
        if _is_whitelisted(guild.id, member):
            return

        adder = None
        for _ in range(6):
            try:
                async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                    if getattr(entry.target, "id", None) == member.id:
                        adder = entry.user
                        break
            except (discord.Forbidden, discord.HTTPException):
                break
            if adder is not None:
                break
            await asyncio.sleep(0.5)

        if adder is not None:
            if adder.id == guild.owner_id or _is_whitelisted(guild.id, adder):
                return
            adder_member = guild.get_member(adder.id)
            if adder_member is not None and _is_whitelisted(guild.id, adder_member):
                return

        reason = "Application externe interdite sur ce serveur (/application-externe-serveur)"
        await member.kick(reason=reason)
        who = f"{adder} (`{adder.id}`)" if adder is not None else ("inconnu" if LANG == "fr" else "unknown")
        await _log_security_event(
            guild,
            (
                f"🤖 Application **{member}** (`{member.id}`) expulsée à son arrivée : les applications sont "
                f"réglées sur **interdites** (`/application-externe-serveur`). Ajoutée par : {who}."
            ) if LANG == "fr" else (
                f"🤖 Application **{member}** (`{member.id}`) kicked on arrival: applications are set to "
                f"**disallowed** (`/server-external-app`). Added by: {who}."
            ),
        )
    except discord.Forbidden:
        log.warning(f"Impossible d'expulser l'application {member} sur {guild.name} (permission manquante).")
    except Exception:
        log.exception(f"Erreur lors de l'application de la règle « applications interdites » sur {guild.name}.")


@bot.event
async def on_member_join(member: discord.Member):
    if member.guild.id != STORAGE_GUILD_ID:
        account_age_days = (discord.utils.utcnow() - member.created_at).days
        await _log_security_event(
            member.guild,
            (
                f"📥 **{member}** (`{member.id}`) a rejoint **{member.guild.name}** "
                f"(compte créé il y a {account_age_days} j)."
            ) if LANG == "fr" else (
                f"📥 **{member}** (`{member.id}`) joined **{member.guild.name}** "
                f"(account created {account_age_days}d ago)."
            ),
        )

    if not member.bot and _account_too_young(member):
        min_hours = _get_setting(member.guild.id, "min_account_age_hours")
        try:
            await member.send(
                f"👋 Ton compte est trop récent pour rejoindre **{member.guild.name}** "
                f"(minimum {min_hours} heure(s) requise(s))." if LANG == "fr"
                else f"👋 Your account is too young to join **{member.guild.name}** "
                f"(minimum {min_hours} hour(s) required)."
            )
        except Exception:
            pass
        try:
            await member.kick(reason="Compte trop récent (âge minimum configuré)")
            log.info(
                f"{member} ({member.id}) expulsé automatiquement à l'arrivée sur {member.guild.name} "
                f"(compte de moins de {min_hours} heure(s), réglage min_account_age_hours)."
            )
        except Exception:
            log.exception(f"Impossible d'expulser {member} (âge minimum de compte).")
        return

    raid_state = _raid_state.get(member.guild.id)
    if raid_state and raid_state.get("active") and not member.bot:
        kick_until = raid_state.get("new_account_kick_until")
        if kick_until and discord.utils.utcnow() < kick_until and _is_new_account(member):
            try:
                await member.send(
                    RAID_DM_NEW_ACCOUNT_KICK_EN.format(
                        guild=member.guild.name, days=RAID_NEW_ACCOUNT_MAX_AGE_DAYS
                    )
                )
            except Exception:
                pass
            try:
                await member.kick(reason="Protocole anti-raid : compte trop récent")
                log.info(
                    f"{member} ({member.id}) expulsé automatiquement à l'arrivée (compte de moins de "
                    f"{RAID_NEW_ACCOUNT_MAX_AGE_DAYS} jours, protocole anti-raid actif sur {member.guild.name})."
                )
            except Exception:
                log.exception(f"Impossible d'expulser {member} (protocole anti-raid, compte récent).")
            return

    if member.bot:
        asyncio.create_task(_enforce_apps_policy(member))
        return

    verification_on = _module_enabled(member.guild.id, "verification")
    if verification_on:
        try:
            role_id = _get_setting(member.guild.id, "verification_unverified_role_id")
            unverified_role = member.guild.get_role(role_id) if role_id else None
            if unverified_role is None:
                _, unverified_role, _ = await _auto_setup_verification(member.guild)
            if unverified_role is not None:
                await member.add_roles(unverified_role, reason="Arrivée sur le serveur : en attente de vérification")
        except discord.Forbidden:
            log.warning(f"Vérification : impossible de donner le rôle Non vérifié à {member} sur {member.guild.name} (permission manquante).")
        except Exception:
            log.exception(f"Vérification : erreur en donnant le rôle Non vérifié à {member} sur {member.guild.name}.")
        asyncio.create_task(_start_verification(member))

    await _send_welcome_channel_message(member)

    if not verification_on:
        await _send_welcome_dm(member)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    raid_state = _raid_state.get(after.guild.id)
    if not raid_state or not raid_state.get("active"):
        return
    if raid_state.get("restoring"):
        return
    role_id = raid_state.get("role_id")
    if role_id is None:
        return

    before_role_ids = {r.id for r in before.roles}
    after_role_ids = {r.id for r in after.roles}
    if role_id not in after_role_ids or role_id in before_role_ids:
        return

    role = after.guild.get_role(role_id)
    if role is None:
        return
    try:
        await after.remove_roles(role, reason="Protocole anti-raid actif : rôle bloqué pendant la procédure")
        log.info(
            f"Rôle {role.name} retiré à {after} ({after.id}) sur {after.guild.name} — "
            "ajouté par une autre source pendant que le protocole anti-raid était actif."
        )
    except Exception:
        log.exception(
            f"Impossible de retirer le rôle {role_id} à {after} (protocole anti-raid, ajout externe)."
        )


@bot.event
async def on_webhooks_update(channel: discord.abc.GuildChannel):
    label = "créations de webhook" if LANG == "fr" else "webhook creations"
    await _handle_structural_action(channel.guild, discord.AuditLogAction.webhook_create, label)

    incoming_ok = await get_webhooks_allowed(channel.guild)
    followers_ok = await get_followers_allowed(channel.guild)
    if incoming_ok and followers_ok:
        return

    try:
        webhooks = await channel.webhooks()
    except discord.Forbidden:
        log.error(f"Permission manquante pour lister les webhooks de #{channel.name} ({channel.guild.name}).")
        return
    except Exception:
        log.exception(f"Impossible de lister les webhooks sur {channel.guild.name}.")
        return
    for webhook in webhooks:
        if webhook.type == discord.WebhookType.channel_follower:
            if followers_ok:
                continue
            reason = "Suivis de salon interdits sur ce serveur (/suivis-serveur)"
        elif webhook.type == discord.WebhookType.incoming:
            if incoming_ok:
                continue
            reason = "Webhooks interdits sur ce serveur (/webhooks-serveur)"
        else:
            continue
        try:
            await webhook.delete(reason=reason)
            log.info(f"Webhook supprimé sur {channel.guild.name} (#{channel.name}) — {reason}.")
        except Exception:
            log.exception(f"Impossible de supprimer un webhook sur {channel.guild.name}.")



import enum as _enum

SERVER_LOG_CATEGORIES = {
    "ban": ("Bannissements", "Bans"),
    "kick": ("Expulsions", "Kicks"),
    "members": ("Membres (pseudo, sourdine, rôles)", "Members (nickname, timeout, roles)"),
    "channels": ("Salons et fils", "Channels and threads"),
    "roles": ("Rôles", "Roles"),
    "server": ("Paramètres du serveur", "Server settings"),
    "webhooks": ("Webhooks", "Webhooks"),
    "apps": ("Applications et intégrations", "Applications and integrations"),
    "invites": ("Invitations", "Invites"),
    "messages": ("Messages (actions de modération)", "Messages (moderation actions)"),
    "automod": ("Auto-modération Discord", "Discord AutoMod"),
}

SERVER_LOG_ACTION_LABELS = {
    "kick": ("🥾", "Expulsion", "Member kicked"),
    "ban": ("🔨", "Bannissement", "Member banned"),
    "unban": ("🕊️", "Débannissement", "Member unbanned"),
    "member_prune": ("🧹", "Purge de membres inactifs", "Members pruned"),
    "member_update": ("👤", "Membre modifié (pseudo/sourdine...)", "Member updated (nickname/timeout...)"),
    "member_role_update": ("🏷️", "Rôles d'un membre modifiés", "Member roles updated"),
    "member_move": ("🔀", "Membres déplacés en vocal", "Members moved in voice"),
    "member_disconnect": ("🔇", "Membres déconnectés du vocal", "Members disconnected from voice"),
    "bot_add": ("🤖", "Application ajoutée", "Application added"),
    "channel_create": ("➕", "Salon créé", "Channel created"),
    "channel_update": ("✏️", "Salon modifié", "Channel updated"),
    "channel_delete": ("🗑️", "Salon supprimé", "Channel deleted"),
    "overwrite_create": ("🔐", "Permission de salon ajoutée", "Channel permission added"),
    "overwrite_update": ("🔐", "Permission de salon modifiée", "Channel permission updated"),
    "overwrite_delete": ("🔐", "Permission de salon retirée", "Channel permission removed"),
    "thread_create": ("🧵", "Fil créé", "Thread created"),
    "thread_update": ("🧵", "Fil modifié", "Thread updated"),
    "thread_delete": ("🧵", "Fil supprimé", "Thread deleted"),
    "role_create": ("➕", "Rôle créé", "Role created"),
    "role_update": ("✏️", "Rôle modifié", "Role updated"),
    "role_delete": ("🗑️", "Rôle supprimé", "Role deleted"),
    "guild_update": ("⚙️", "Serveur modifié", "Server updated"),
    "invite_create": ("📨", "Invitation créée", "Invite created"),
    "invite_update": ("📨", "Invitation modifiée", "Invite updated"),
    "invite_delete": ("📨", "Invitation supprimée", "Invite deleted"),
    "webhook_create": ("🪝", "Webhook créé", "Webhook created"),
    "webhook_update": ("🪝", "Webhook modifié", "Webhook updated"),
    "webhook_delete": ("🪝", "Webhook supprimé", "Webhook deleted"),
    "integration_create": ("🔌", "Intégration ajoutée", "Integration added"),
    "integration_update": ("🔌", "Intégration modifiée", "Integration updated"),
    "integration_delete": ("🔌", "Intégration retirée", "Integration removed"),
    "emoji_create": ("😀", "Émoji ajouté", "Emoji added"),
    "emoji_update": ("😀", "Émoji modifié", "Emoji updated"),
    "emoji_delete": ("😀", "Émoji supprimé", "Emoji deleted"),
    "message_delete": ("🗑️", "Message supprimé par un modérateur", "Message deleted by a moderator"),
    "message_bulk_delete": ("🗑️", "Suppression de messages en masse", "Bulk message deletion"),
    "message_pin": ("📌", "Message épinglé", "Message pinned"),
    "message_unpin": ("📌", "Message désépinglé", "Message unpinned"),
    "app_command_permission_update": ("🔐", "Permissions d'une commande d'application modifiées", "Application command permissions updated"),
    "automod_rule_create": ("🛡️", "Règle AutoMod créée", "AutoMod rule created"),
    "automod_rule_update": ("🛡️", "Règle AutoMod modifiée", "AutoMod rule updated"),
    "automod_rule_delete": ("🛡️", "Règle AutoMod supprimée", "AutoMod rule deleted"),
    "automod_block_message": ("🛡️", "AutoMod : message bloqué", "AutoMod: message blocked"),
    "automod_flag_message": ("🛡️", "AutoMod : message signalé", "AutoMod: message flagged"),
    "automod_timeout_member": ("🛡️", "AutoMod : membre mis en sourdine", "AutoMod: member timed out"),
}

_AUDIT_MISSING = object()
_SERVER_LOG_FOOTER_RE = re.compile(r"ACT:(\S+) • BY:(\d+) • TO:(\d+)(?: • E:(\d+))?")


def _audit_category(action_name: str) -> str:
    """Rattache une action de l'audit log à une catégorie de SERVER_LOG_CATEGORIES."""
    if action_name in ("ban", "unban"):
        return "ban"
    if action_name in ("kick", "member_prune"):
        return "kick"
    if action_name == "bot_add" or action_name.startswith("integration_") or action_name == "app_command_permission_update":
        return "apps"
    if action_name.startswith("webhook_"):
        return "webhooks"
    if action_name.startswith("invite_"):
        return "invites"
    if action_name.startswith("role_"):
        return "roles"
    if action_name.startswith(("channel_", "overwrite_", "thread_", "stage_instance_")):
        return "channels"
    if action_name.startswith("member_"):
        return "members"
    if action_name.startswith("message_"):
        return "messages"
    if action_name.startswith("automod_"):
        return "automod"
    return "server"


def _audit_fmt_value(value, limit: int = 120) -> str:
    """Rend une valeur de l'audit log lisible (jamais d'exception)."""
    try:
        if value is None:
            text = "∅"
        elif isinstance(value, bool):
            text = ("oui" if value else "non") if LANG == "fr" else ("yes" if value else "no")
        elif isinstance(value, discord.Asset):
            text = "(image)"
        elif isinstance(value, (_enum.Enum, discord.enums.Enum)):
            text = str(value.name)
        elif isinstance(value, (discord.Role, discord.abc.GuildChannel, discord.Thread, discord.Member, discord.User)):
            text = value.mention
        elif isinstance(value, discord.Object):
            text = f"`{value.id}`"
        elif isinstance(value, datetime):
            text = f"<t:{int(value.timestamp())}:f>"
        elif isinstance(value, timedelta):
            text = f"{int(value.total_seconds())}s"
        elif isinstance(value, (list, tuple, set)):
            text = ", ".join(_audit_fmt_value(v, 60) for v in list(value)[:10]) or "∅"
        else:
            text = str(value)
    except Exception:
        text = "?"
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _audit_perm_names(perms) -> set:
    if isinstance(perms, discord.Permissions):
        return {("view_channel" if name == "read_messages" else name) for name, value in perms if value}
    return set()


def _audit_changes_lines(entry) -> list:
    """Liste des changements (avant → après) d'une entrée d'audit log."""
    try:
        before = dict(iter(entry.before))
        after = dict(iter(entry.after))
    except Exception:
        return []

    category = getattr(entry.action, "category", None)
    is_create = category == discord.AuditLogActionCategory.create
    is_delete = category == discord.AuditLogActionCategory.delete
    lines = []
    for key in dict.fromkeys([*before.keys(), *after.keys()]):
        bv = before.get(key, _AUDIT_MISSING)
        av = after.get(key, _AUDIT_MISSING)

        if key in ("permissions", "allow", "deny"):
            if is_delete:
                continue
            added = sorted(_audit_perm_names(av) - _audit_perm_names(bv))
            removed = sorted(_audit_perm_names(bv) - _audit_perm_names(av)) if not is_create else []
            if added:
                lines.append(f"**{key}** + `{', '.join(added)}`")
            if removed:
                lines.append(f"**{key}** − `{', '.join(removed)}`")
            continue
        if key == "roles":
            removed = bv if bv is not _AUDIT_MISSING else []
            added = av if av is not _AUDIT_MISSING else []
            if added:
                lines.append(("**Rôles ajoutés** : " if LANG == "fr" else "**Roles added**: ") + _audit_fmt_value(added, 300))
            if removed:
                lines.append(("**Rôles retirés** : " if LANG == "fr" else "**Roles removed**: ") + _audit_fmt_value(removed, 300))
            continue
        if key == "overwrites":
            continue
        if (is_create or is_delete) and key not in ("name", "type", "code", "channel", "max_uses", "max_age", "temporary"):
            continue

        if bv is _AUDIT_MISSING:
            lines.append(f"**{key}** : {_audit_fmt_value(av)}")
        elif av is _AUDIT_MISSING:
            lines.append(f"**{key}** : {_audit_fmt_value(bv)}")
        elif bv != av:
            lines.append(f"**{key}** : {_audit_fmt_value(bv)} → {_audit_fmt_value(av)}")
    return lines[:15]


def _audit_extra_text(entry) -> str:
    try:
        extra = entry.extra
        if extra is None:
            return ""
        if isinstance(extra, (discord.Member, discord.User, discord.Role, discord.Object, discord.abc.GuildChannel)):
            return _audit_fmt_value(extra)
        return ", ".join(f"{k}: {_audit_fmt_value(v, 80)}" for k, v in vars(extra).items() if v is not None)
    except Exception:
        return ""


def _audit_actor_text(entry) -> tuple:
    user = entry.user
    uid = getattr(entry, "user_id", None) or getattr(user, "id", None)
    if user is not None:
        return f"{user.mention} (`{user.id}`)", uid
    if uid:
        return f"<@{uid}> (`{uid}`)", uid
    return ("inconnu" if LANG == "fr" else "unknown"), None


def _audit_target_text(entry) -> tuple:
    target = entry.target
    tid = getattr(target, "id", None) or getattr(entry, "_target_id", None)
    name = None
    for diff in (entry.before, entry.after):
        try:
            name = getattr(diff, "name", None) or name
        except Exception:
            pass

    if target is None and tid is None:
        return "", None
    if isinstance(target, (discord.Member, discord.User)):
        return f"{target.mention} (`{target.id}`)", tid
    if isinstance(target, (discord.Role, discord.abc.GuildChannel, discord.Thread)):
        return f"{target.mention} (`{target.id}`)", tid
    if isinstance(target, discord.Guild):
        return target.name, tid
    if isinstance(target, discord.Invite):
        return f"`{target.code}`", tid
    if isinstance(target, discord.Object):
        kind = getattr(entry.action, "target_type", None)
        if kind == "user" and tid:
            return f"<@{tid}> (`{tid}`)", tid
        label = f"**{name}** " if name else ""
        return f"{label}(`{tid}`)", tid
    label = getattr(target, "name", None) or name
    return (f"**{label}** (`{tid}`)" if label and tid else str(label or tid or "")), tid


def _build_server_log_embed(entry) -> discord.Embed:
    action_name = entry.action.name
    emoji, label_fr, label_en = SERVER_LOG_ACTION_LABELS.get(
        action_name, ("📋", action_name.replace("_", " ").capitalize(), action_name.replace("_", " ").capitalize())
    )
    category = getattr(entry.action, "category", None)
    if action_name in ("ban", "kick", "member_prune") or category == discord.AuditLogActionCategory.delete:
        color = 0xE74C3C
    elif category == discord.AuditLogActionCategory.create:
        color = 0x2ECC71
    elif category == discord.AuditLogActionCategory.update:
        color = 0xF39C12
    else:
        color = 0x5865F2

    actor_text, actor_id = _audit_actor_text(entry)
    target_text, target_id = _audit_target_text(entry)

    embed = discord.Embed(
        title=f"{emoji} {label_fr if LANG == 'fr' else label_en}",
        description=f"{actor_text} → {target_text}" if target_text else actor_text,
        color=color,
        timestamp=entry.created_at,
    )
    changes = _audit_changes_lines(entry)
    if changes:
        embed.add_field(name="Détails" if LANG == "fr" else "Details", value="\n".join(changes)[:1024], inline=False)
    extra = _audit_extra_text(entry)
    if extra:
        embed.add_field(name="Infos" if LANG == "fr" else "Info", value=extra[:1024], inline=False)
    if entry.reason:
        embed.add_field(name="Raison" if LANG == "fr" else "Reason", value=str(entry.reason)[:1024], inline=False)
    embed.set_footer(text=f"ACT:{action_name} • BY:{actor_id or 0} • TO:{target_id or 0} • E:{getattr(entry, 'id', 0)}")
    return embed


_server_log_thread_cache: dict = {}
_server_log_thread_locks: dict = {}


async def _get_or_create_server_log_thread(channel: discord.TextChannel, user_id: int, user=None):
    """Retourne (en le créant si besoin) le fil de logs d'actions d'un membre dans
    le salon de logs serveur. Un verrou par membre évite de créer deux fils
    identiques quand plusieurs actions arrivent en rafale (raid).
    user_id == 0 : fil « système » pour les actions sans membre identifiable."""
    key = (channel.guild.id, user_id)
    thread_name = str(user_id) if user_id else ("système" if LANG == "fr" else "system")
    lock = _server_log_thread_locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached_id = _server_log_thread_cache.get(key)
        if cached_id:
            thread = channel.get_thread(cached_id)
            if thread is not None:
                if thread.archived:
                    try:
                        await thread.edit(archived=False)
                    except Exception:
                        pass
                return thread

        thread = await _find_log_thread_by_name(channel, thread_name)
        if thread is None:
            thread = await channel.create_thread(
                name=thread_name,
                auto_archive_duration=FULL_LOG_THREAD_AUTO_ARCHIVE_MINUTES,
                type=discord.ChannelType.public_thread,
                reason="Nouveau fil de logs d'actions du serveur pour ce membre",
            )
            try:
                if user_id:
                    intro = discord.Embed(
                        title=str(user) if user is not None else f"ID {user_id}",
                        description=f"<@{user_id}> — `{user_id}`",
                        color=0x5865F2,
                    )
                    avatar = getattr(user, "display_avatar", None)
                    if avatar:
                        intro.set_thumbnail(url=avatar.url)
                else:
                    intro = discord.Embed(
                        title="Système" if LANG == "fr" else "System",
                        description=(
                            "Actions sans membre identifiable (auteur inconnu)."
                            if LANG == "fr" else "Actions with no identifiable member (unknown author)."
                        ),
                        color=0x5865F2,
                    )
                await thread.send(embed=intro)
            except Exception:
                pass
        elif thread.archived:
            try:
                await thread.edit(archived=False)
            except Exception:
                pass

        _server_log_thread_cache[key] = thread.id
        return thread


async def _post_server_log_entry(entry) -> None:
    guild = entry.guild
    if guild is None or guild.id == STORAGE_GUILD_ID:
        return
    if not _module_enabled(guild.id, "serverlog"):
        return
    channel_id = _get_setting(guild.id, "server_log_channel_id")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel is None:
        return
    if entry.action.name.startswith("thread_") and entry.user_id == bot.user.id:
        return

    try:
        embed = _build_server_log_embed(entry)
    except Exception:
        log.exception(f"Impossible de construire l'embed de log serveur ({entry.action}) sur {guild.name}.")
        return

    recipients = []
    actor_id = getattr(entry, "user_id", None) or getattr(entry.user, "id", None)
    if actor_id:
        recipients.append((actor_id, entry.user))
    if getattr(entry.action, "target_type", None) == "user":
        _, target_id = _audit_target_text(entry)
        if target_id and target_id != actor_id:
            target_obj = entry.target if isinstance(entry.target, (discord.Member, discord.User)) else None
            recipients.append((target_id, target_obj))

    if not recipients:
        recipients.append((0, None))

    for user_id, user in recipients:
        try:
            thread = await _get_or_create_server_log_thread(channel, user_id, user)
            await thread.send(embed=embed)
        except discord.Forbidden:
            log.warning(
                f"Log serveur non posté sur {guild.name} (fil {user_id}) : permission manquante dans "
                f"#{channel.name} — le bot a besoin de « Créer des fils publics » et "
                f"« Envoyer des messages dans les fils »."
            )
        except Exception as e:
            _log_send_failure(f"Log serveur (fil {user_id}) sur {guild.name}", e)


@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
    await _post_server_log_entry(entry)


@bot.event
async def on_invite_create(invite: discord.Invite):
    if invite.guild is None:
        return
    raid_state = _raid_state.get(invite.guild.id)
    if not (raid_state and raid_state.get("active")):
        return
    reason = "Protocole anti-raid actif : aucune nouvelle invitation autorisée"
    try:
        await invite.delete(reason=reason)
        log.info(f"Invitation supprimée sur {invite.guild.name} ({invite.code}) — {reason}.")
    except Exception:
        log.exception(f"Impossible de supprimer une invitation sur {invite.guild.name}.")


def _status_line(ok: bool, label: str, detail: str = "", pending: bool = False) -> str:
    icon = "⏳" if pending else ("✅" if ok else "❌")
    padded_label = (label + " ").ljust(38, ".")
    return f"{icon} {padded_label} {detail}".rstrip()


_console_thread_started = False


def _start_terminal_console_once():
    global _console_thread_started
    if _console_thread_started:
        return
    _console_thread_started = True
    threading.Thread(target=_terminal_console_loop, daemon=True).start()


def _print_startup_constants_check():
    tenant_guilds = [g for g in bot.guilds if g.id != STORAGE_GUILD_ID]
    configured = sum(
        1 for g in tenant_guilds if _get_setting(g.id, "mod_request_channel_id")
    )
    storage_lines = [
        _status_line(True, "Mode de stockage", f"fichier local ({STORAGE_FILE_PATH})"),
    ] if STORAGE_MODE == "file" else [
        _status_line(
            bool(STORAGE_GUILD_ID) and bot.get_guild(STORAGE_GUILD_ID) is not None, "Serveur de stockage",
            f"trouvé ({STORAGE_GUILD_ID})" if bool(STORAGE_GUILD_ID) and bot.get_guild(STORAGE_GUILD_ID) is not None
            else "ℹ️ non configuré — /serveur-stockage pour le régler",
        ),
    ]
    lines = [
        "=" * 62,
        "📋 VÉRIFICATION DES CONSTANTES DE CONFIGURATION",
        "=" * 62,
        *storage_lines,
        _status_line(
            True,
            "Staff (permission Discord, mute minimum)",
            "automatique sur tous les serveurs — aucune configuration requise",
        ),
        _status_line(
            not tenant_guilds or configured > 0,
            "Salon des demandes par serveur",
            f"{configured}/{len(tenant_guilds)} serveur(s) configuré(s) via /roles-staff"
            if tenant_guilds else "aucun serveur client pour le moment",
        ),
        "=" * 62,
    ]
    dashboard = "\n".join(lines)
    print(dashboard)
    log.info("Vérification des constantes affichée dans le terminal.")


async def _delayed_startup_constants_check():
    await asyncio.sleep(60)
    _print_startup_constants_check()


_startup_constants_check_task = None


_bot_ready_initialized = False


STATUS_ROTATE_SECONDS = 10
_honeypot_watchdog_task = None
_frozen_watchdog_task = None

_status_rotate_task = None

_log_file_limit_task = None


def _server_count_label(total_guilds: int) -> str:
    return (
        f"Sur {total_guilds} serveur{'s' if total_guilds > 1 else ''}"
        if LANG == "fr"
        else f"On {total_guilds} server{'s' if total_guilds > 1 else ''}"
    )


def _version_label() -> str:
    return f"Version {BOT_VERSION}" if LANG == "fr" else f"Version {BOT_VERSION}"


async def _update_server_count_presence() -> None:
    """Compte le nombre de serveurs où le bot est présent et sauvegarde ce
    nombre localement dans bot_config.json (SERVER_COUNT). Le statut affiché
    sous le nom du bot alterne ensuite automatiquement entre ce nombre et la
    version du bot via _status_rotate_loop() (appelée au démarrage, à chaque
    fois que le bot rejoint un serveur, et à chaque fois qu'il en quitte un)."""
    total_guilds = len(bot.guilds)

    try:
        _write_config_values({"SERVER_COUNT": total_guilds})
    except Exception:
        log.exception("Impossible de sauvegarder le nombre de serveurs dans bot_config.json.")

    label = _server_count_label(total_guilds)
    try:
        await bot.change_presence(activity=discord.CustomActivity(name=label))
        log.info(f"Statut du bot mis à jour : {label}")
    except Exception:
        log.exception("Impossible de définir le statut personnalisé du bot.")


async def _status_rotate_loop() -> None:
    """Boucle de fond qui fait alterner le statut du bot toutes les
    STATUS_ROTATE_SECONDS secondes entre le nombre de serveurs et la version
    du bot (BOT_VERSION)."""
    showing_version = False
    while True:
        try:
            await asyncio.sleep(STATUS_ROTATE_SECONDS)
            showing_version = not showing_version
            if showing_version:
                label = _version_label()
            else:
                label = _server_count_label(len(bot.guilds))
            await bot.change_presence(activity=discord.CustomActivity(name=label))
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Erreur dans la boucle de rotation du statut du bot.")


def _copy_global_to_guild(guild: discord.Guild) -> None:
    """Équivalent de bot.tree.copy_global_to(guild=guild) : copie toutes les
    commandes déclarées globalement (en mémoire) vers ce serveur précis."""
    for c in bot.tree.get_commands():
        bot.tree.add_command(c, guild=guild, override=True)


@bot.event
async def on_ready():
    global _bot_ready_initialized
    if _bot_ready_initialized:
        log.info(f"on_ready redéclenché (reconnexion Discord) — {bot.user} déjà initialisé, rien à refaire.")
        return
    _bot_ready_initialized = True

    await _refresh_bot_owner_ids()

    for guild in bot.guilds:
        if guild.id == STORAGE_GUILD_ID:
            continue
        await load_guild_config(guild)
        await _load_frozen_members(guild)
    await _migrate_legacy_whitelist_file()
    bot.add_view(ModRequestView())
    bot.add_view(VerificationLinkPublicView())
    bot.add_view(FreezeView())
    bot.add_view(FreezeTicketView())
    bot.add_view(FreezeTicketOpenView())
    await _restore_frozen_schedules_on_ready()
    await _join_all_existing_threads()

    await _start_verify_web_server()

    await _update_server_count_presence()

    global _status_rotate_task
    if _status_rotate_task is None or _status_rotate_task.done():
        _status_rotate_task = asyncio.create_task(_status_rotate_loop())

    global _honeypot_watchdog_task
    if _honeypot_watchdog_task is None or _honeypot_watchdog_task.done():
        _honeypot_watchdog_task = asyncio.create_task(_honeypot_watchdog_loop())

    global _frozen_watchdog_task
    if _frozen_watchdog_task is None or _frozen_watchdog_task.done():
        _frozen_watchdog_task = asyncio.create_task(_frozen_watchdog_loop())

    global _log_file_limit_task
    if LOG_FILE_LIMIT_ENABLED and (_log_file_limit_task is None or _log_file_limit_task.done()):
        _log_file_limit_task = asyncio.create_task(_log_file_limit_loop())
        log.info(
            f"🧹 Limitation du fichier de log ACTIVÉE (vidage auto au-delà de "
            f"{LOG_FILE_LIMIT_MAX_BYTES} octets, vérifié toutes les {LOG_FILE_LIMIT_CHECK_SECONDS}s)."
        )

    log.info(f"Connecté en tant que {bot.user} (id: {bot.user.id})")
    try:
        if not _CONFIG.get("GLOBAL_COMMANDS_CLEARED"):
            await bot.http.bulk_upsert_global_commands(bot.application_id, payload=[])
            log.info("Anciennes commandes slash globales effacées côté Discord (reset, pas de réenregistrement global).")
            _write_config_values({"GLOBAL_COMMANDS_CLEARED": True})
        else:
            log.info("Nettoyage des commandes globales déjà effectué précédemment — ignoré (évite le rate limit Discord).")

        guild_sync_ok = 0
        guild_sync_fail = 0
        total_guilds = len(bot.guilds)
        log.info(
            f"⏳ Synchronisation des commandes sur {total_guilds} serveur(s) en cours "
            "(les commandes slash ne seront pas disponibles avant la fin de cette étape)…"
        )
        for i, guild in enumerate(bot.guilds, start=1):
            try:
                _copy_global_to_guild(guild)
                synced = await bot.tree.sync(guild=guild)
                guild_sync_ok += 1
            except Exception as e:
                guild_sync_fail += 1
                log.warning(
                    f"Échec de la synchronisation des commandes sur le serveur {guild.name} ({guild.id}) : "
                    f"{type(e).__name__}: {e}"
                )
            if total_guilds > 5 and i % 5 == 0:
                log.info(f"⏳ Synchronisation en cours : {i}/{total_guilds} serveur(s) traité(s)…")
            await asyncio.sleep(0.3)
        log.info(
            f"✅ Commandes synchronisées directement sur {guild_sync_ok} serveur(s)"
            + (f" ({guild_sync_fail} échec(s))." if guild_sync_fail else ".")
            + " Les commandes slash sont maintenant disponibles."
        )
    except Exception as e:
        log.warning(f"Erreur de synchronisation des commandes : {e}")

    global _startup_constants_check_task
    _startup_constants_check_task = asyncio.create_task(_delayed_startup_constants_check())
    _start_terminal_console_once()


async def _sync_commands_for_guild(guild: discord.Guild, *, attempts: int = 3) -> bool:
    """Synchronise les commandes slash sur UN serveur, avec plusieurs essais
    (un simple échec réseau/rate-limit ponctuel ne doit pas laisser le
    serveur sans commandes). Retourne True si un essai a réussi. En dernier
    recours, un admin peut toujours relancer manuellement avec
    /synchroniser-commandes."""
    for i in range(1, attempts + 1):
        try:
            _copy_global_to_guild(guild)
            await bot.tree.sync(guild=guild)
            log.info(f"Commandes synchronisées sur {guild.name} ({guild.id}) (essai {i}/{attempts}).")
            return True
        except discord.HTTPException as e:
            log.warning(
                f"Échec de synchronisation des commandes sur {guild.name} ({guild.id}), "
                f"essai {i}/{attempts} : {e}"
            )
            if i < attempts:
                await asyncio.sleep(3 * i)
        except Exception:
            log.exception(f"Erreur inattendue de synchronisation des commandes sur {guild.name} ({guild.id}).")
            break
    log.warning(
        f"Commandes toujours pas synchronisées sur {guild.name} ({guild.id}) après {attempts} essai(s) — "
        "un administrateur du serveur peut utiliser /synchroniser-commandes pour réessayer manuellement."
    )
    return False


@bot.event
async def on_guild_join(guild: discord.Guild):
    log.info(f"Bot ajouté au serveur : {guild.name} ({guild.id})")

    asyncio.create_task(_sync_commands_for_guild(guild))

    asyncio.create_task(_notify_guild_owner_welcome(guild))
    await _update_server_count_presence()

    if guild.id == STORAGE_GUILD_ID:
        log.info(f"Serveur de stockage rejoint ({guild.name}, {guild.id}) — aucune configuration à faire dessus.")
        return

    await asyncio.sleep(2)
    try:
        await load_guild_config(guild)
        await run_audit_and_post(guild)
    except discord.Forbidden:
        log.error(
            f"Permissions insuffisantes pour auditer/créer le salon sur {guild.name}. "
            f"Le bot a-t-il bien 'Gérer les salons' et 'Gérer les rôles' ?"
        )
    except Exception:
        log.exception(f"Erreur lors de l'audit du serveur {guild.name}")

    db_guild = get_db_guild()
    if db_guild is not None:
        try:
            await get_or_create_db_category(db_guild, guild)
        except Exception:
            log.exception(f"Impossible de préparer la catégorie base de données pour {guild.name}.")


@bot.event
async def on_guild_remove(guild: discord.Guild):
    log.info(f"Bot retiré du serveur : {guild.name} ({guild.id})")
    await _update_server_count_presence()


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CheckFailure):
        return
    log.warning(f"Erreur de commande préfixée '{ctx.command}': {error}")


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: discord.app_commands.AppCommandError
):
    if interaction.type == discord.InteractionType.autocomplete:
        try:
            if not interaction.response.is_done():
                await interaction.response.autocomplete([])
        except Exception:
            pass
        if not isinstance(error, discord.app_commands.CheckFailure):
            log.exception("Erreur non gérée dans l'autocomplétion d'une commande :", exc_info=error)
        return

    if isinstance(error, discord.app_commands.MissingPermissions):
        msg = (
            "❌ Tu n'as pas la permission nécessaire pour cette commande."
            if LANG == "fr"
            else "❌ You don't have the required permission for this command."
        )
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        msg = (
            f"⏳ Commande en cooldown, réessaie dans {error.retry_after:.0f}s."
            if LANG == "fr"
            else f"⏳ Command on cooldown, try again in {error.retry_after:.0f}s."
        )
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        perms = ", ".join(error.missing_permissions)
        msg = (
            f"❌ Il me manque une permission pour faire ça : {perms}."
            if LANG == "fr"
            else f"❌ I'm missing a permission to do this: {perms}."
        )
    elif isinstance(error, discord.app_commands.CheckFailure):
        msg = str(error) or (
            "❌ Tu n'as pas accès à cette commande."
            if LANG == "fr"
            else "❌ You don't have access to this command."
        )
    else:
        original = getattr(error, "original", error)
        if isinstance(original, discord.Forbidden):
            msg = (
                "❌ Action refusée par Discord (permissions insuffisantes ou hiérarchie de rôles)."
                if LANG == "fr"
                else "❌ Action refused by Discord (insufficient permissions or role hierarchy)."
            )
            log.warning(f"Forbidden dans la commande '{interaction.command}': {original}")
        elif isinstance(original, discord.NotFound):
            msg = (
                "❌ Élément introuvable (membre, message ou salon déjà supprimé)."
                if LANG == "fr"
                else "❌ Item not found (member, message, or channel already deleted)."
            )
            log.warning(f"NotFound dans la commande '{interaction.command}': {original}")
        elif isinstance(error, discord.app_commands.TransformerError):
            msg = (
                "❌ Je n'ai pas réussi à identifier ce membre. Utilise le menu Discord "
                "(commence à taper son pseudo et clique dessus, ou @mentionne-le) au lieu "
                "d'écrire `pseudo#1234` à la main — ce format n'existe quasiment plus."
                if LANG == "fr"
                else "❌ I couldn't identify that member. Use Discord's picker (start typing "
                "their name and select them, or @mention them) instead of typing "
                "`name#1234` by hand — that format barely exists anymore."
            )
            log.info(f"Saisie de membre invalide dans '{interaction.command}': {error}")
        elif isinstance(original, discord.HTTPException) and original.status == 429:
            msg = (
                "⏳ Discord/Cloudflare limite temporairement les requêtes du bot. "
                "Réessaie dans une minute ou deux."
                if LANG == "fr"
                else "⏳ Discord/Cloudflare is temporarily rate-limiting the bot. "
                "Try again in a minute or two."
            )
            _log_send_failure(f"Rate limit (429) dans la commande '{interaction.command}'", original)
        else:
            msg = (
                "❌ Une erreur inattendue s'est produite. L'équipe technique a été notifiée."
                if LANG == "fr"
                else "❌ An unexpected error occurred. The tech team has been notified."
            )
            log.exception(f"Erreur non gérée dans la commande '{interaction.command}':", exc_info=error)

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception as e:
        _log_send_failure("Impossible d'envoyer le message d'erreur à l'utilisateur", e)


@bot.tree.command(
    name="audit-securite" if LANG == "fr" else "security-audit",
    description=(
        "Relance l'analyse de sécurité du serveur" if LANG == "fr"
        else "Re-run the server's security audit"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def audit_command(interaction: discord.Interaction):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    channel = await run_audit_and_post(interaction.guild, requester=str(interaction.user))
    await interaction.followup.send(
        f"✅ {channel.mention}" if LANG == "fr" else f"✅ {channel.mention}",
        ephemeral=True,
    )


@bot.tree.command(
    name="webhooks-serveur" if LANG == "fr" else "server-webhooks",
    description=(
        "Consulte ou change si les webhooks (hors suivis de salon et applications externes) sont autorisés" if LANG == "fr"
        else "View or change whether webhooks (excl. channel follows and external apps) are allowed"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    autoriser="True pour autoriser, False pour interdire (omettre pour juste consulter)" if LANG == "fr"
    else "True to allow, False to disallow (omit to just check the current setting)",
)
async def server_webhooks_command(interaction: discord.Interaction, autoriser: bool = None):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if autoriser is None:
        current = await get_webhooks_allowed(guild)
        await interaction.followup.send(
            (
                f"ℹ️ Les webhooks sont actuellement **{'autorisés' if current else 'interdits'}** sur ce serveur. "
                "Utilise `autoriser:True` ou `autoriser:False` pour changer ce réglage."
            )
            if LANG == "fr"
            else (
                f"ℹ️ Webhooks are currently **{'allowed' if current else 'disallowed'}** on this server. "
                "Use `autoriser:True` or `autoriser:False` to change this setting."
            ),
            ephemeral=True,
        )
        return

    saved = await set_webhooks_allowed(guild, autoriser)
    if saved:
        await interaction.followup.send(
            (
                f"✅ Webhooks désormais **{'autorisés' if autoriser else 'interdits'}** sur ce serveur "
                "(enregistré sur le serveur base de données)."
            )
            if LANG == "fr"
            else (
                f"✅ Webhooks are now **{'allowed' if autoriser else 'disallowed'}** on this server "
                "(saved on the database server)."
            ),
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            (
                f"⚠️ Réglage appliqué (**{'autorisés' if autoriser else 'interdits'}**) pour cette session, "
                "mais PAS enregistré (serveur base de données indisponible) : il sera perdu au redémarrage du bot."
            )
            if LANG == "fr"
            else (
                f"⚠️ Setting applied (**{'allowed' if autoriser else 'disallowed'}**) for this session, "
                "but NOT saved (database server unavailable): it will be lost when the bot restarts."
            ),
            ephemeral=True,
        )


async def _run_toggle_command(
    interaction: discord.Interaction,
    autoriser,
    get_fn,
    set_fn,
    *,
    subject_fr: str,
    subject_en: str,
    ok_fr: str,
    ko_fr: str,
    note_fr: str = "",
    note_en: str = "",
) -> None:
    """Corps commun des commandes « consulter / changer un réglage autoriser-interdire »."""
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if autoriser is None:
        current = await get_fn(guild)
        await interaction.followup.send(
            (
                f"ℹ️ {subject_fr} : actuellement **{ok_fr if current else ko_fr}** sur ce serveur. {note_fr}"
                "Utilise `autoriser:True` ou `autoriser:False` pour changer ce réglage."
            )
            if LANG == "fr"
            else (
                f"ℹ️ {subject_en}: currently **{'allowed' if current else 'disallowed'}** on this server. {note_en}"
                "Use `autoriser:True` or `autoriser:False` to change this setting."
            ),
            ephemeral=True,
        )
        return

    saved = await set_fn(guild, autoriser)
    if saved:
        await interaction.followup.send(
            f"✅ {subject_fr} : désormais **{ok_fr if autoriser else ko_fr}** sur ce serveur."
            if LANG == "fr"
            else f"✅ {subject_en}: now **{'allowed' if autoriser else 'disallowed'}** on this server.",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            f"⚠️ Réglage appliqué (**{ok_fr if autoriser else ko_fr}**) pour cette session, mais PAS enregistré "
            "(stockage indisponible) : il sera perdu au redémarrage du bot."
            if LANG == "fr"
            else f"⚠️ Setting applied (**{'allowed' if autoriser else 'disallowed'}**) for this session, but NOT saved "
            "(storage unavailable): it will be lost when the bot restarts.",
            ephemeral=True,
        )


@bot.tree.command(
    name="suivis-serveur" if LANG == "fr" else "server-followers",
    description=(
        "Consulte ou change si les suivis de salon (annonces d'autres serveurs) sont autorisés" if LANG == "fr"
        else "View or change whether channel follows (other servers' announcements) are allowed"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    autoriser="True pour autoriser, False pour interdire (omettre pour juste consulter)" if LANG == "fr"
    else "True to allow, False to disallow (omit to just check the current setting)",
)
async def server_followers_command(interaction: discord.Interaction, autoriser: bool = None):
    await _run_toggle_command(
        interaction, autoriser, get_followers_allowed, set_followers_allowed,
        subject_fr="Suivis de salon", subject_en="Channel follows",
        ok_fr="autorisés", ko_fr="interdits",
        note_fr="(Réglage indépendant des webhooks classiques.) ",
        note_en="(Independent from regular webhooks.) ",
    )


@bot.tree.command(
    name="application-externe-serveur" if LANG == "fr" else "server-external-app",
    description=(
        "Consulte ou change si les applications externes (et bots ajoutés) sont autorisées" if LANG == "fr"
        else "View or change whether external applications (and added bots) are allowed"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    autoriser="True pour autoriser, False pour interdire (omettre pour juste consulter)" if LANG == "fr"
    else "True to allow, False to disallow (omit to just check the current setting)",
)
async def server_apps_command(interaction: discord.Interaction, autoriser: bool = None):
    await _run_toggle_command(
        interaction, autoriser, get_apps_allowed, set_apps_allowed,
        subject_fr="Application externe", subject_en="External application",
        ok_fr="autorisée", ko_fr="interdite",
        note_fr=(
            "Interdites = un bot qui vient d'être ajouté est expulsé (sauf liste blanche / ajout par le "
            "propriétaire) et les messages d'applications externes sont supprimés. "
        ),
        note_en=(
            "Disallowed = a newly added bot is kicked (unless whitelisted / added by the owner) and "
            "messages from external applications are deleted. "
        ),
    )


@bot.tree.command(
    name="liens-serveur" if LANG == "fr" else "server-links",
    description=(
        "Consulte ou change si les liens sont autorisés sur ce serveur" if LANG == "fr"
        else "View or change whether links are allowed on this server"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    autoriser="True pour autoriser, False pour interdire (omettre pour juste consulter)" if LANG == "fr"
    else "True to allow, False to disallow (omit to just check the current setting)",
)
async def server_links_command(interaction: discord.Interaction, autoriser: bool = None):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if autoriser is None:
        current = await get_links_allowed(guild)
        await interaction.followup.send(
            (
                f"ℹ️ Les liens sont actuellement **{'autorisés' if current else 'interdits'}** sur ce serveur. "
                "Utilise `autoriser:True` ou `autoriser:False` pour changer ce réglage."
            )
            if LANG == "fr"
            else (
                f"ℹ️ Links are currently **{'allowed' if current else 'disallowed'}** on this server. "
                "Use `autoriser:True` or `autoriser:False` to change this setting."
            ),
            ephemeral=True,
        )
        return

    saved = await set_links_allowed(guild, autoriser)
    if saved:
        await interaction.followup.send(
            (
                f"✅ Liens désormais **{'autorisés' if autoriser else 'interdits'}** sur ce serveur "
                "(enregistré sur le serveur base de données)."
            )
            if LANG == "fr"
            else (
                f"✅ Links are now **{'allowed' if autoriser else 'disallowed'}** on this server "
                "(saved on the database server)."
            ),
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            (
                f"⚠️ Réglage appliqué (**{'autorisés' if autoriser else 'interdits'}**) pour cette session, "
                "mais PAS enregistré (serveur base de données indisponible) : il sera perdu au redémarrage du bot."
            )
            if LANG == "fr"
            else (
                f"⚠️ Setting applied (**{'allowed' if autoriser else 'disallowed'}**) for this session, "
                "but NOT saved (database server unavailable): it will be lost when the bot restarts."
            ),
            ephemeral=True,
        )


@bot.tree.command(
    name="age-minimum-comptes" if LANG == "fr" else "min-account-age",
    description=(
        "Consulte ou change l'âge minimum (en heures) requis pour rejoindre ce serveur"
        if LANG == "fr"
        else "View or change the minimum account age (in hours) required to join this server"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    heures="Âge minimum en heures, 0 pour désactiver (omettre pour juste consulter)" if LANG == "fr"
    else "Minimum age in hours, 0 to disable (omit to just check the current setting)",
)
async def min_account_age_command(interaction: discord.Interaction, heures: int = None):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if heures is None:
        current = _get_setting(guild.id, "min_account_age_hours")
        if current:
            msg = (
                f"ℹ️ Âge minimum actuel : **{current} heure(s)**. Les comptes plus récents sont "
                "expulsés automatiquement à l'arrivée. Utilise `heures:0` pour désactiver."
                if LANG == "fr"
                else f"ℹ️ Current minimum age: **{current} hour(s)**. Younger accounts are "
                "auto-kicked on join. Use `heures:0` to disable."
            )
        else:
            msg = (
                "ℹ️ Aucun âge minimum n'est configuré (vérification désactivée). "
                "Utilise `heures:<nombre>` pour l'activer."
                if LANG == "fr"
                else "ℹ️ No minimum age is configured (check disabled). "
                "Use `heures:<number>` to enable it."
            )
        await interaction.followup.send(msg, ephemeral=True)
        return

    if heures < 0:
        await interaction.followup.send(
            "❌ La valeur ne peut pas être négative." if LANG == "fr"
            else "❌ The value can't be negative.",
            ephemeral=True,
        )
        return

    _set_setting(guild.id, "min_account_age_hours", heures)
    saved = await save_guild_config(guild)

    if heures:
        base = (
            f"✅ Âge minimum désormais réglé à **{heures} heure(s)** : les comptes plus récents "
            "seront expulsés automatiquement à l'arrivée sur ce serveur."
            if LANG == "fr"
            else f"✅ Minimum age is now set to **{heures} hour(s)**: younger accounts will be "
            "auto-kicked on join to this server."
        )
    else:
        base = (
            "✅ Vérification désactivée : plus aucune expulsion liée à l'âge du compte."
            if LANG == "fr"
            else "✅ Check disabled: no more kicks based on account age."
        )

    if not saved:
        base += "\n\n⚠️ " + (
            "Non enregistré (serveur base de données indisponible) : perdu au redémarrage du bot."
            if LANG == "fr"
            else "Not saved (database server unavailable): lost when the bot restarts."
        )
    await interaction.followup.send(base, ephemeral=True)


@bot.tree.command(
    name="bienvenue-salon" if LANG == "fr" else "welcome-channel",
    description=(
        "Choisit le salon où envoyer le message de bienvenue (image + texte), ou le désactive"
        if LANG == "fr"
        else "Pick the channel for the welcome message (image + text), or disable it"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    salon="Salon où poster la bienvenue (omettre pour juste consulter)" if LANG == "fr"
    else "Channel to post the welcome message in (omit to just check the current setting)",
    desactiver="True pour couper le système de bienvenue en salon" if LANG == "fr"
    else "True to turn off the channel welcome system",
)
async def welcome_channel_command(
    interaction: discord.Interaction,
    salon: discord.TextChannel = None,
    desactiver: bool = False,
):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if desactiver:
        _set_setting(guild.id, "welcome_channel_id", 0)
        saved = await save_guild_config(guild)
        msg = "✅ Bienvenue en salon désactivée." if LANG == "fr" else "✅ Channel welcome disabled."
        if not saved:
            msg += "\n\n⚠️ " + (
                "Non enregistré (serveur base de données indisponible)." if LANG == "fr"
                else "Not saved (database server unavailable)."
            )
        await interaction.followup.send(msg, ephemeral=True)
        return

    if salon is None:
        current_id = _get_setting(guild.id, "welcome_channel_id")
        if current_id:
            await interaction.followup.send(
                f"ℹ️ Salon de bienvenue actuel : <#{current_id}>." if LANG == "fr"
                else f"ℹ️ Current welcome channel: <#{current_id}>.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "ℹ️ Aucun salon de bienvenue configuré. Utilise `salon:<salon>` pour en régler un."
                if LANG == "fr"
                else "ℹ️ No welcome channel configured. Use `salon:<channel>` to set one.",
                ephemeral=True,
            )
        return

    _set_setting(guild.id, "welcome_channel_id", salon.id)
    saved = await save_guild_config(guild)
    msg = (
        f"✅ Les nouveaux membres seront accueillis dans {salon.mention} (image + texte)." if LANG == "fr"
        else f"✅ New members will be welcomed in {salon.mention} (image + text)."
    )
    if not saved:
        msg += "\n\n⚠️ " + (
            "Non enregistré (serveur base de données indisponible) : perdu au redémarrage du bot."
            if LANG == "fr"
            else "Not saved (database server unavailable): lost when the bot restarts."
        )
    await interaction.followup.send(msg, ephemeral=True)


@bot.tree.command(
    name="bienvenue-texte" if LANG == "fr" else "welcome-text",
    description=(
        "Change le texte du message de bienvenue en salon (jetons: {mention} {serveur} {nombre})"
        if LANG == "fr"
        else "Change the channel welcome message text (tokens: {mention} {server} {count})"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    texte=(
        "Nouveau texte. Jetons : {mention}, {membre}, {serveur}, {nombre} (vide = texte actuel)"
        if LANG == "fr"
        else "New text. Usable tokens: {mention}, {member}, {server}, {count} "
        "(omit to see the current text)"
    ),
)
async def welcome_text_command(interaction: discord.Interaction, texte: str = None):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if texte is None:
        current = _get_setting(guild.id, "welcome_text") or WELCOME_TEXT_DEFAULT
        await interaction.followup.send(
            f"ℹ️ Texte de bienvenue actuel :\n```\n{current[:1900]}\n```" if LANG == "fr"
            else f"ℹ️ Current welcome text:\n```\n{current[:1900]}\n```",
            ephemeral=True,
        )
        return

    _set_setting(guild.id, "welcome_text", texte)
    saved = await save_guild_config(guild)
    msg = "✅ Texte de bienvenue mis à jour." if LANG == "fr" else "✅ Welcome text updated."
    if not saved:
        msg += "\n\n⚠️ " + (
            "Non enregistré (serveur base de données indisponible) : perdu au redémarrage du bot."
            if LANG == "fr"
            else "Not saved (database server unavailable): lost when the bot restarts."
        )
    await interaction.followup.send(msg, ephemeral=True)


@bot.tree.command(
    name="bienvenue-ping" if LANG == "fr" else "welcome-ping",
    description=(
        "Active ou désactive le ping du membre dans le message de bienvenue en salon"
        if LANG == "fr"
        else "Turn the member ping on or off in the channel welcome message"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    actif="True pour ping le membre, False pour ne pas le ping (omettre pour consulter)" if LANG == "fr"
    else "True to ping the member, False to not ping (omit to check the current setting)",
)
async def welcome_ping_command(interaction: discord.Interaction, actif: bool = None):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if actif is None:
        current = bool(_get_setting(guild.id, "welcome_ping_enabled"))
        await interaction.followup.send(
            f"ℹ️ Ping à l'arrivée : **{'activé' if current else 'désactivé'}**." if LANG == "fr"
            else f"ℹ️ Join ping: **{'enabled' if current else 'disabled'}**.",
            ephemeral=True,
        )
        return

    _set_setting(guild.id, "welcome_ping_enabled", actif)
    saved = await save_guild_config(guild)
    msg = (
        f"✅ Ping à l'arrivée désormais **{'activé' if actif else 'désactivé'}**." if LANG == "fr"
        else f"✅ Join ping is now **{'enabled' if actif else 'disabled'}**."
    )
    if not saved:
        msg += "\n\n⚠️ " + (
            "Non enregistré (serveur base de données indisponible) : perdu au redémarrage du bot."
            if LANG == "fr"
            else "Not saved (database server unavailable): lost when the bot restarts."
        )
    await interaction.followup.send(msg, ephemeral=True)


@bot.tree.command(
    name="roles-staff" if LANG == "fr" else "staff-roles",
    description=(
        "Configure le rôle Fondateur et le salon des demandes de sanction"
        if LANG == "fr"
        else "Configure the Founder role, the requests channel, and the request system"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    fondateur="Rôle Fondateur (accès total aux commandes du bot)" if LANG == "fr" else "Founder role (full access to bot commands)",
    salon_demandes="Salon où les demandes (mute/kick/ban) sont envoyées aux personnes habilitées à les valider" if LANG == "fr" else "Channel where requests (mute/kick/ban) are sent to the people allowed to approve them",
    activer_demandes="Active/désactive le système de demande quand la permission manque (sinon refus direct)" if LANG == "fr" else "Enable/disable the request system when the permission is missing (otherwise a direct refusal)",
)
async def roles_staff_command(
    interaction: discord.Interaction,
    fondateur: discord.Role = None,
    salon_demandes: discord.TextChannel = None,
    activer_demandes: bool = None,
):
    guild = interaction.guild
    is_allowed = _has_effective_administrator(interaction.user) if isinstance(interaction.user, discord.Member) else False
    if not is_allowed:
        await interaction.response.send_message(
            "❌ Seul·e le/la propriétaire du serveur ou un membre Administrateur peut configurer les rôles staff."
            if LANG == "fr"
            else "❌ Only the server owner or an Administrator member can configure staff roles.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    if fondateur is not None:
        _set_setting(guild.id, "owner_role_id", fondateur.id)
    if salon_demandes is not None:
        _set_setting(guild.id, "mod_request_channel_id", salon_demandes.id)
    if activer_demandes is not None:
        _set_setting(guild.id, "mod_request_enabled", activer_demandes)

    saved = await save_guild_config(guild)

    def _fmt_role(key: str) -> str:
        rid = _get_setting(guild.id, key)
        return f"<@&{rid}>" if rid else ("*non défini*" if LANG == "fr" else "*not set*")

    summary = (
        (
            "⚙️ **Configuration staff de ce serveur**\n"
            f"• Fondateur : {_fmt_role('owner_role_id')}\n"
            f"{_fmt_mod_request_status_line(guild)}\n\n"
            "*Le staff est déterminé par les permissions Discord réelles (mute minimum) "
            "— plus aucun rôle à assigner niveau par niveau.*\n\n"
            + ("✅ Enregistré." if saved else "⚠️ Appliqué pour cette session, mais PAS enregistré (serveur base de données indisponible) — sera perdu au redémarrage.")
        )
        if LANG == "fr"
        else (
            "⚙️ **This server's staff settings**\n"
            f"• Founder: {_fmt_role('owner_role_id')}\n"
            f"{_fmt_mod_request_status_line(guild)}\n\n"
            "*Staff is now determined by real Discord permissions (mute minimum) — no "
            "more per-level roles to assign.*\n\n"
            + ("✅ Saved." if saved else "⚠️ Applied for this session, but NOT saved (database server unavailable) — will be lost on restart.")
        )
    )
    await interaction.followup.send(summary, ephemeral=True)


@bot.tree.command(
    name="invitations-serveur" if LANG == "fr" else "server-invites",
    description=(
        "Consulte ou change si les invitations Discord sont autorisées sur ce serveur" if LANG == "fr"
        else "View or change whether Discord invite links are allowed on this server"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    autoriser="True pour autoriser, False pour interdire (omettre pour juste consulter)" if LANG == "fr"
    else "True to allow, False to disallow (omit to just check the current setting)",
)
async def server_invites_command(interaction: discord.Interaction, autoriser: bool = None):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if autoriser is None:
        current = await get_invites_allowed(guild)
        await interaction.followup.send(
            (
                f"ℹ️ Les invitations Discord sont actuellement **{'autorisées' if current else 'interdites'}** "
                "sur ce serveur (les invitations vers un AUTRE serveur restent, elles, toujours supprimées). "
                "Utilise `autoriser:True` ou `autoriser:False` pour changer ce réglage."
            )
            if LANG == "fr"
            else (
                f"ℹ️ Discord invite links are currently **{'allowed' if current else 'disallowed'}** on this "
                "server (invites to ANOTHER server are always removed regardless). "
                "Use `autoriser:True` or `autoriser:False` to change this setting."
            ),
            ephemeral=True,
        )
        return

    saved = await set_invites_allowed(guild, autoriser)
    if saved:
        await interaction.followup.send(
            (
                f"✅ Invitations Discord désormais **{'autorisées' if autoriser else 'interdites'}** sur ce "
                "serveur (enregistré sur le serveur base de données)."
            )
            if LANG == "fr"
            else (
                f"✅ Discord invite links are now **{'allowed' if autoriser else 'disallowed'}** on this "
                "server (saved on the database server)."
            ),
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            (
                f"⚠️ Réglage appliqué (**{'autorisées' if autoriser else 'interdites'}**) pour cette session, "
                "mais PAS enregistré (serveur base de données indisponible) : il sera perdu au redémarrage du bot."
            )
            if LANG == "fr"
            else (
                f"⚠️ Setting applied (**{'allowed' if autoriser else 'disallowed'}**) for this session, "
                "but NOT saved (database server unavailable): it will be lost when the bot restarts."
            ),
            ephemeral=True,
        )


@bot.tree.command(
    name="protocole-anti-raid" if LANG == "fr" else "anti-raid-protocol",
    description=(
        "Active le protocole anti-raid : retire un rôle, coupe webhooks/invitations/vocal, "
        "verrouille salons" if LANG == "fr"
        else "Activates the anti-raid protocol: strips a role, cuts webhooks/invites/voice, "
        "locks channels"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    role="Rôle à retirer à tous les membres qui l'ont pendant le protocole" if LANG == "fr"
    else "Role to strip from every member who has it during the protocol",
)
async def anti_raid_protocol_command(interaction: discord.Interaction, role: discord.Role):
    if not _raid_command_allowed(interaction):
        await interaction.response.send_message(
            "❌ Seul le propriétaire du serveur ou un administrateur peut utiliser cette commande."
            if LANG == "fr"
            else "❌ Only the server owner or an administrator can use this command.",
            ephemeral=True,
        )
        return

    guild = interaction.guild
    if _raid_state.get(guild.id, {}).get("active"):
        await interaction.response.send_message(
            "⚠️ Le protocole anti-raid est déjà actif sur ce serveur." if LANG == "fr"
            else "⚠️ The anti-raid protocol is already active on this server.",
            ephemeral=True,
        )
        return
    if role.is_default():
        await interaction.response.send_message(
            "❌ Impossible de retirer @everyone — choisis un vrai rôle." if LANG == "fr"
            else "❌ Can't strip @everyone — pick an actual role.",
            ephemeral=True,
        )
        return
    if role >= guild.me.top_role:
        await interaction.response.send_message(
            (
                "❌ Je ne peux pas gérer ce rôle (il est au-dessus ou au même niveau que mon "
                "rôle le plus haut) — remonte mon rôle dans la hiérarchie."
            )
            if LANG == "fr"
            else (
                "❌ I can't manage that role (it's above or equal to my highest role) — move "
                "my role higher in the role list."
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)
    now = discord.utils.utcnow()

    everyone = guild.default_role
    locked_channels = []
    for channel in guild.text_channels:
        try:
            prev_overwrite = channel.overwrites_for(everyone)
            if prev_overwrite.send_messages is False:
                continue
            locked_channels.append({"id": channel.id, "prev_send_messages": prev_overwrite.send_messages})
            new_overwrite = prev_overwrite
            new_overwrite.send_messages = False
            await channel.set_permissions(
                everyone, overwrite=new_overwrite, reason="Protocole anti-raid activé (verrouillage)"
            )
        except Exception:
            log.exception(f"Impossible de verrouiller #{channel.name} (protocole anti-raid).")

    for vc in guild.voice_channels:
        for vc_member in list(vc.members):
            try:
                await vc_member.move_to(None, reason="Protocole anti-raid activé")
            except Exception:
                log.exception(f"Impossible de déconnecter {vc_member} du vocal (protocole anti-raid).")

    previous_webhooks_allowed = await get_webhooks_allowed(guild)
    await set_webhooks_allowed(guild, False)

    previous_invites_allowed = await get_invites_allowed(guild)
    await set_invites_allowed(guild, False)

    try:
        await guild.edit(
            invites_disabled_until=now + timedelta(hours=24),
            reason="Protocole anti-raid activé (invitations suspendues)",
        )
    except Exception:
        log.exception(f"Impossible de suspendre nativement les invitations sur {guild.name} (protocole anti-raid).")

    targeted_members = list(role.members)
    member_ids = [m.id for m in targeted_members]
    for member in targeted_members:
        try:
            await member.remove_roles(role, reason="Protocole anti-raid activé")
        except Exception:
            log.exception(f"Impossible de retirer le rôle {role} à {member} (protocole anti-raid).")
        await asyncio.sleep(0.25)

    state = {
        "active": True,
        "role_id": role.id,
        "member_ids": member_ids,
        "left_during_raid": [],
        "started_at": now,
        "started_by": interaction.user.id,
        "previous_webhooks_allowed": previous_webhooks_allowed,
        "previous_invites_allowed": previous_invites_allowed,
        "locked_channels": locked_channels,
        "new_account_kick_until": now + timedelta(hours=RAID_NEW_ACCOUNT_KICK_WINDOW_HOURS),
    }
    _raid_state[guild.id] = state
    if STORAGE_MODE == "file":
        g = _file_store_guild(guild.id)
        g["raid_state"] = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in state.items()}
        _file_store_save()
    else:
        db_guild = get_db_guild()
        if db_guild is not None:
            try:
                await _save_raid_state(db_guild, guild, state)
            except Exception:
                log.exception(
                    f"Impossible d'enregistrer l'état du protocole anti-raid sur le serveur base de données "
                    f"pour {guild.name}."
                )

    log.info(
        f"Protocole anti-raid activé sur {guild.name} par {interaction.user} ({interaction.user.id}) — "
        f"rôle {role.name}, {len(member_ids)} membre(s) concerné(s), {len(locked_channels)} salon(s) verrouillé(s)."
    )
    await interaction.followup.send(
        (
            f"🚨 **Protocole anti-raid activé sur {guild.name}.**\n"
            f"• **{len(locked_channels)}** salon(s) textuel(s) verrouillé(s).\n"
            f"• Tout le monde déconnecté du vocal.\n"
            f"• Webhooks suspendus (aucun nouveau autorisé, existants conservés).\n"
            f"• Invitations suspendues nativement (liens existants ET nouveaux inutilisables, rien supprimé).\n"
            f"• Rôle `{role.name}` retiré à **{len(member_ids)}** membre(s) (sauvegardé pour restauration).\n"
            f"• Comptes de moins de {RAID_NEW_ACCOUNT_MAX_AGE_DAYS} jours automatiquement expulsés à "
            f"l'arrivée pendant {RAID_NEW_ACCOUNT_KICK_WINDOW_HOURS}h.\n"
            f"• MP en cours d'envoi à tous les membres en arrière-plan.\n\n"
            f"Utilise `/fin-protocole-anti-raid` pour tout restaurer."
        )
        if LANG == "fr"
        else (
            f"🚨 **Anti-raid protocol activated on {guild.name}.**\n"
            f"• **{len(locked_channels)}** text channel(s) locked.\n"
            f"• Everyone disconnected from voice.\n"
            f"• Webhooks suspended (no new ones allowed, existing ones kept).\n"
            f"• Invites natively paused (existing AND new links unusable, nothing deleted).\n"
            f"• Role `{role.name}` removed from **{len(member_ids)}** member(s) (saved for restore).\n"
            f"• Accounts younger than {RAID_NEW_ACCOUNT_MAX_AGE_DAYS} days will be auto-kicked on join for "
            f"{RAID_NEW_ACCOUNT_KICK_WINDOW_HOURS}h.\n"
            f"• DM being sent to all members in the background.\n\n"
            f"Use `/end-anti-raid-protocol` to restore everything."
        ),
        ephemeral=True,
    )

    asyncio.create_task(
        _send_raid_dm_broadcast(guild, RAID_DM_START_EN.format(guild=guild.name), "de début de protocole anti-raid")
    )
    asyncio.create_task(_keep_invites_paused(guild))


@bot.tree.command(
    name="fin-protocole-anti-raid" if LANG == "fr" else "end-anti-raid-protocol",
    description=(
        "Désactive le protocole anti-raid et restaure tout ce qu'il avait changé" if LANG == "fr"
        else "Deactivates the anti-raid protocol and restores everything it changed"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def end_anti_raid_protocol_command(interaction: discord.Interaction):
    if not _raid_command_allowed(interaction):
        await interaction.response.send_message(
            "❌ Seul le propriétaire du serveur ou un administrateur peut utiliser cette commande."
            if LANG == "fr"
            else "❌ Only the server owner or an administrator can use this command.",
            ephemeral=True,
        )
        return

    guild = interaction.guild
    state = _raid_state.get(guild.id)
    if state is None:
        if STORAGE_MODE == "file":
            state = _load_file_raid_state(guild)
        else:
            db_guild = get_db_guild()
            if db_guild is not None:
                try:
                    state = await _load_raid_state(db_guild, guild)
                except Exception:
                    log.exception(f"Impossible de relire l'état du protocole anti-raid pour {guild.name}.")
        if state is not None:
            _raid_state[guild.id] = state

    if not state or not state.get("active"):
        await interaction.response.send_message(
            "ℹ️ Aucun protocole anti-raid actif sur ce serveur." if LANG == "fr"
            else "ℹ️ No anti-raid protocol is currently active on this server.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    state["restoring"] = True

    role = guild.get_role(state["role_id"])
    left_during_raid = set(state.get("left_during_raid", []))
    restored = 0
    flagged_members = []
    if role is not None:
        for member_id in state.get("member_ids", []):
            if member_id in left_during_raid:
                target = guild.get_member(member_id)
                if target is not None:
                    flagged_members.append(target)
                continue
            target = guild.get_member(member_id)
            if target is None:
                continue
            try:
                await target.add_roles(role, reason="Fin du protocole anti-raid")
                restored += 1
            except Exception:
                log.exception(f"Impossible de restaurer le rôle pour {member_id} (fin protocole anti-raid).")
            await asyncio.sleep(0.25)

    await set_webhooks_allowed(guild, state.get("previous_webhooks_allowed", True))
    await set_invites_allowed(guild, state.get("previous_invites_allowed", True))
    try:
        await guild.edit(invites_disabled_until=None, reason="Fin du protocole anti-raid (invitations réactivées)")
    except Exception:
        log.exception(f"Impossible de réactiver nativement les invitations sur {guild.name} (fin protocole anti-raid).")

    everyone = guild.default_role
    unlocked = 0
    for entry in state.get("locked_channels", []):
        channel = guild.get_channel(entry["id"])
        if channel is None:
            continue
        try:
            overwrite = channel.overwrites_for(everyone)
            overwrite.send_messages = entry.get("prev_send_messages")
            if overwrite.is_empty():
                await channel.set_permissions(
                    everyone, overwrite=None, reason="Fin du protocole anti-raid (déverrouillage)"
                )
            else:
                await channel.set_permissions(
                    everyone, overwrite=overwrite, reason="Fin du protocole anti-raid (déverrouillage)"
                )
            unlocked += 1
        except Exception:
            log.exception(f"Impossible de déverrouiller #{channel} (fin protocole anti-raid).")

    state["active"] = False
    _raid_state.pop(guild.id, None)
    if STORAGE_MODE == "file":
        g = _file_store_guild(guild.id)
        g["raid_state"] = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in state.items()}
        _file_store_save()
    else:
        db_guild = get_db_guild()
        if db_guild is not None:
            try:
                await _save_raid_state(db_guild, guild, state)
            except Exception:
                log.exception(
                    f"Impossible de mettre à jour l'état du protocole anti-raid sur le serveur base de données "
                    f"pour {guild.name}."
                )

    log.info(
        f"Protocole anti-raid désactivé sur {guild.name} par {interaction.user} ({interaction.user.id}) — "
        f"{restored} rôle(s) restauré(s), {unlocked} salon(s) déverrouillé(s), "
        f"{len(flagged_members)} compte(s) exclu(s) de la restauration (parti(s) pendant le protocole)."
    )
    flagged_line_fr = ""
    flagged_line_en = ""
    if flagged_members:
        mentions = ", ".join(m.mention for m in flagged_members)
        flagged_line_fr = (
            f"• ⚠️ **{len(flagged_members)}** compte(s) ont quitté le serveur PENDANT le protocole puis "
            f"sont revenus : rôle **PAS** restauré automatiquement, à vérifier toi-même avant de le "
            f"redonner à la main : {mentions}\n"
        )
        flagged_line_en = (
            f"• ⚠️ **{len(flagged_members)}** account(s) left the server DURING the protocol and came "
            f"back: role **NOT** auto-restored, review manually before re-granting it: {mentions}\n"
        )
    await interaction.followup.send(
        (
            f"✅ **Protocole anti-raid terminé sur {guild.name}.**\n"
            f"• {restored} rôle(s) restauré(s).\n"
            f"{flagged_line_fr}"
            f"• Webhooks/invitations remis à leur réglage précédent, invitations réactivées nativement.\n"
            f"• {unlocked} salon(s) déverrouillé(s).\n"
            f"• MP de fin en cours d'envoi à tous les membres en arrière-plan."
        )
        if LANG == "fr"
        else (
            f"✅ **Anti-raid protocol ended on {guild.name}.**\n"
            f"• {restored} role(s) restored.\n"
            f"{flagged_line_en}"
            f"• Webhooks/invites reset to their previous setting, invites natively re-enabled.\n"
            f"• {unlocked} channel(s) unlocked.\n"
            f"• Closing DM being sent to all members in the background."
        ),
        ephemeral=True,
    )

    asyncio.create_task(
        _send_raid_dm_broadcast(guild, RAID_DM_END_EN.format(guild=guild.name), "de fin de protocole anti-raid")
    )


def _build_whitelist_embed(guild: discord.Guild) -> discord.Embed:
    entries = _guild_store.get(guild.id, {}).get("whitelist", {})
    if not entries:
        description = "La liste blanche est vide." if LANG == "fr" else "The whitelist is empty."
    else:
        lines = []
        for entity_id, kind in entries.items():
            if kind == "role":
                mention = f"<@&{entity_id}>"
            elif kind == "channel":
                mention = f"<#{entity_id}>"
            else:
                mention = f"<@{entity_id}>"
            lines.append(f"• {mention} ({kind})")
        description = "\n".join(lines)[:4000]

    embed = discord.Embed(
        title="📋 Liste blanche" if LANG == "fr" else "📋 Whitelist",
        description=description,
        color=0x5865F2,
    )
    embed.set_footer(
        text=(
            "Exempte de l'anti-spam et de l'anti-nuke." if LANG == "fr"
            else "Exempts from anti-spam and anti-nuke."
        )
    )
    return embed


async def _whitelist_not_saved_notice(interaction: discord.Interaction) -> None:
    await interaction.followup.send(
        "⚠️ Non enregistré (serveur base de données indisponible) : perdu au redémarrage du bot." if LANG == "fr"
        else "⚠️ Not saved (database server unavailable): lost when the bot restarts.",
        ephemeral=True,
    )


class WhitelistAddRoleSelect(discord.ui.RoleSelect):
    """Liste blanche : rôles uniquement, plus de membre individuel possible.
    Whitelister un membre précis est risqué (compte compromis, aucune trace
    de qui a été exempté et pourquoi) — mieux vaut passer par un rôle dédié."""

    def __init__(self):
        super().__init__(
            placeholder="➕ Ajouter un rôle…" if LANG == "fr" else "➕ Add a role…",
            min_values=1,
            max_values=1,
            custom_id="whitelist_add_role_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        role = self.values[0]
        _guild_store[interaction.guild.id]["whitelist"][role.id] = "role"
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            embed=_build_whitelist_embed(interaction.guild),
            view=await _build_whitelist_panel_view(interaction.guild),
        )
        if not saved:
            await _whitelist_not_saved_notice(interaction)


class WhitelistAddChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="➕ Ajouter un salon…" if LANG == "fr" else "➕ Add a channel…",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            custom_id="whitelist_add_channel_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        channel = self.values[0]
        _guild_store[interaction.guild.id]["whitelist"][channel.id] = "channel"
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            embed=_build_whitelist_embed(interaction.guild),
            view=await _build_whitelist_panel_view(interaction.guild),
        )
        if not saved:
            await _whitelist_not_saved_notice(interaction)


def _describe_whitelist_entry(
    guild: typing.Optional[discord.Guild],
    entity_id: int,
    kind: str,
    member_cache: typing.Optional[dict] = None,
) -> str:
    """Transforme une entrée de liste blanche (id + type) en libellé lisible pour
    l'humain (nom du rôle/salon/membre), avec repli sur l'id si l'entité a
    vraiment disparu du serveur (rôle supprimé, salon supprimé, membre parti…)
    ou si le serveur n'est pas en cache. `member_cache` (optionnel) est un dict
    {id: discord.Member|None} pré-résolu via l'API pour les membres absents du
    cache Discord.py (voir _resolve_whitelist_member_cache), pour éviter de dire
    à tort « introuvable » à un membre bien réel mais juste pas en cache."""
    kind_fr = {"role": "rôle", "channel": "salon", "member": "membre"}.get(kind, kind)
    kind_label = kind_fr if LANG == "fr" else kind

    if guild is not None:
        if kind == "role":
            role = guild.get_role(entity_id)
            if role is not None:
                return f"@{role.name} ({kind_label})"
        elif kind == "channel":
            channel = guild.get_channel(entity_id)
            if channel is not None:
                return f"#{channel.name} ({kind_label})"
        else:
            member = guild.get_member(entity_id)
            if member is None and member_cache is not None:
                member = member_cache.get(entity_id)
            if member is not None:
                return f"{member.display_name} ({kind_label})"

    introuvable = "introuvable" if LANG == "fr" else "not found"
    return f"{kind_label} {entity_id} ({introuvable})"


async def _resolve_whitelist_member_cache(guild: typing.Optional[discord.Guild], entries: dict) -> dict:
    """Va chercher via l'API Discord (fetch_member) les membres de la liste
    blanche qui ne sont pas dans le cache local (le bot tourne sans l'intent
    privilégié 'membres', donc son cache de membres est partiel). Renvoie un
    dict {id: discord.Member|None} — None si le membre a réellement quitté le
    serveur ou n'existe plus."""
    cache: dict = {}
    if guild is None:
        return cache
    for entity_id, kind in entries.items():
        if kind != "member" or guild.get_member(entity_id) is not None:
            continue
        try:
            cache[entity_id] = await guild.fetch_member(entity_id)
        except discord.NotFound:
            cache[entity_id] = None
        except discord.HTTPException:
            cache[entity_id] = None
    return cache


class WhitelistRemoveSelect(discord.ui.Select):
    def __init__(self, guild_id: int, member_cache: typing.Optional[dict] = None):
        entries = _guild_store.get(guild_id, {}).get("whitelist", {})
        guild = bot.get_guild(guild_id)
        options = []
        for entity_id, kind in list(entries.items())[:25]:
            label = _describe_whitelist_entry(guild, entity_id, kind, member_cache)
            options.append(discord.SelectOption(label=label[:100], value=f"{kind}:{entity_id}"))
        empty = not options
        if empty:
            options = [
                discord.SelectOption(
                    label="Liste blanche vide" if LANG == "fr" else "Whitelist empty",
                    value="none",
                )
            ]
        super().__init__(
            placeholder="➖ Retirer une entrée…" if LANG == "fr" else "➖ Remove an entry…",
            min_values=1,
            max_values=1,
            options=options,
            disabled=empty,
            custom_id="whitelist_remove_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        kind, _, entity_id_str = self.values[0].partition(":")
        entity_id = int(entity_id_str)
        removed = _guild_store[interaction.guild.id]["whitelist"].pop(entity_id, None)
        saved = True
        if removed is not None:
            saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            embed=_build_whitelist_embed(interaction.guild),
            view=await _build_whitelist_panel_view(interaction.guild),
        )
        if removed is not None and not saved:
            await _whitelist_not_saved_notice(interaction)


class WhitelistPanelView(discord.ui.View):
    def __init__(self, guild_id: int, member_cache: typing.Optional[dict] = None):
        super().__init__(timeout=180)
        self.add_item(WhitelistAddRoleSelect())
        self.add_item(WhitelistAddChannelSelect())
        self.add_item(WhitelistRemoveSelect(guild_id, member_cache))
        self.add_item(BackToMainPanelButton(row=3))


async def _build_whitelist_panel_view(guild: discord.Guild) -> "WhitelistPanelView":
    """Construit le panel liste blanche en résolvant d'abord (via l'API si besoin)
    les membres absents du cache local, pour que le menu « Retirer » affiche de
    vrais pseudos plutôt que des identifiants ou un « introuvable » erroné."""
    entries = _guild_store.get(guild.id, {}).get("whitelist", {})
    member_cache = await _resolve_whitelist_member_cache(guild, entries)
    return WhitelistPanelView(guild.id, member_cache)


@bot.tree.command(
    name="liste-blanche" if LANG == "fr" else "whitelist",
    description=(
        "Ouvre le panel de gestion de la liste blanche (voir/ajouter/retirer)" if LANG == "fr"
        else "Opens the whitelist management panel (view/add/remove)"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def whitelist_panel_command(interaction: discord.Interaction):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    await interaction.response.send_message(
        embed=_build_whitelist_embed(interaction.guild),
        view=await _build_whitelist_panel_view(interaction.guild),
        ephemeral=True,
    )


def _build_wordfilter_embed(guild: discord.Guild) -> discord.Embed:
    enabled = _module_enabled(guild.id, "wordfilter")
    words = _get_setting(guild.id, "banned_words_list") or []
    if not words:
        description = "Aucun mot interdit configuré." if LANG == "fr" else "No banned word configured."
    else:
        description = "\n".join(f"• `{w}`" for w in words)[:4000]

    sanction_type = _get_setting(guild.id, "wordfilter_sanction_type") or "mute"
    sanction_label = WORDFILTER_SANCTION_CHOICES.get(sanction_type, WORDFILTER_SANCTION_CHOICES["mute"])
    mute_minutes = _get_setting(guild.id, "wordfilter_mute_minutes") or 60

    embed = discord.Embed(
        title="🚯 Mots interdits" if LANG == "fr" else "🚯 Banned words",
        description=description,
        color=0x5865F2,
    )
    embed.add_field(
        name="⛔ Anti-spam" if LANG == "fr" else "⛔ Anti-spam",
        value=(
            f"Au {WORDFILTER_SANCTION_THRESHOLD}ᵉ message supprimé en 24h par ce filtre (même membre), "
            f"sanction automatique : **{sanction_label['fr']}**"
            f"{f' ({mute_minutes} min)' if sanction_type == 'mute' else ''}.\n"
            "Cette sanction ne peut pas être désactivée tant que le filtre est actif, pour éviter de "
            "faire enchaîner trop de suppressions de messages au bot (risque de rate limit Discord / "
            "ban IP du bot)."
            if LANG == "fr"
            else
            f"At the {WORDFILTER_SANCTION_THRESHOLD}th message removed in 24h by this filter (same member), "
            f"automatic sanction: **{sanction_label['en']}**"
            f"{f' ({mute_minutes} min)' if sanction_type == 'mute' else ''}.\n"
            "This sanction can't be disabled while the filter is active, to avoid the bot chaining too "
            "many message deletions (Discord rate limit / bot IP ban risk)."
        ),
        inline=False,
    )
    embed.set_footer(
        text=(
            f"État : {'✅ Activé' if enabled else '❌ Désactivé'} — liste 100% manuelle, vide par défaut."
            if LANG == "fr"
            else f"Status: {'✅ Enabled' if enabled else '❌ Disabled'} — fully manual list, empty by default."
        )
    )
    return embed


async def _wordfilter_not_saved_notice(interaction: discord.Interaction) -> None:
    await interaction.followup.send(
        "⚠️ Non enregistré (serveur base de données indisponible) : perdu au redémarrage du bot." if LANG == "fr"
        else "⚠️ Not saved (database server unavailable): lost when the bot restarts.",
        ephemeral=True,
    )


class WordFilterAddModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Ajouter des mots interdits" if LANG == "fr" else "Add banned words")
        self.words_input = discord.ui.TextInput(
            label="Mot(s), séparés par des virgules" if LANG == "fr" else "Word(s), comma-separated",
            style=discord.TextStyle.paragraph,
            placeholder="motA, motB, motC" if LANG == "fr" else "wordA, wordB, wordC",
            max_length=500,
            required=True,
        )
        self.add_item(self.words_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        current = list(_get_setting(guild.id, "banned_words_list") or [])
        added = []
        for raw in self.words_input.value.split(","):
            word = raw.strip().lower()
            if word and word not in current:
                current.append(word)
                added.append(word)
        _set_setting(guild.id, "banned_words_list", current)
        saved = True
        if added:
            saved = await save_guild_config(guild)
        await interaction.response.edit_message(
            embed=_build_wordfilter_embed(guild),
            view=WordFilterPanelView(guild.id),
        )
        if added and not saved:
            await _wordfilter_not_saved_notice(interaction)


class WordFilterRemoveSelect(discord.ui.Select):
    def __init__(self, guild_id: int, row: int = 1):
        words = _get_setting(guild_id, "banned_words_list") or []
        options = [discord.SelectOption(label=w[:100], value=w) for w in words[:25]]
        empty = not options
        if empty:
            options = [
                discord.SelectOption(
                    label="Aucun mot interdit" if LANG == "fr" else "No banned word",
                    value="none",
                )
            ]
        super().__init__(
            placeholder="➖ Retirer un mot…" if LANG == "fr" else "➖ Remove a word…",
            min_values=1,
            max_values=1,
            options=options,
            disabled=empty,
            row=row,
            custom_id="wordfilter_remove_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        current = list(_get_setting(guild.id, "banned_words_list") or [])
        word = self.values[0]
        removed = word in current
        if removed:
            current.remove(word)
            _set_setting(guild.id, "banned_words_list", current)
        saved = True
        if removed:
            saved = await save_guild_config(guild)
        await interaction.response.edit_message(
            embed=_build_wordfilter_embed(guild),
            view=WordFilterPanelView(guild.id),
        )
        if removed and not saved:
            await _wordfilter_not_saved_notice(interaction)


class WordFilterAddButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Ajouter des mots" if LANG == "fr" else "Add words",
            emoji="➕",
            row=row,
            custom_id="wordfilter_add",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.send_modal(WordFilterAddModal())


class WordFilterClearButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Tout vider" if LANG == "fr" else "Clear all",
            emoji="🗑️",
            row=row,
            custom_id="wordfilter_clear",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        had_words = bool(_get_setting(guild.id, "banned_words_list"))
        _set_setting(guild.id, "banned_words_list", [])
        saved = True
        if had_words:
            saved = await save_guild_config(guild)
        await interaction.response.edit_message(
            embed=_build_wordfilter_embed(guild),
            view=WordFilterPanelView(guild.id),
        )
        if had_words and not saved:
            await _wordfilter_not_saved_notice(interaction)


class WordFilterSanctionSelect(discord.ui.Select):
    """Choix de la sanction automatique appliquée au {WORDFILTER_SANCTION_THRESHOLD}e
    message supprimé par le filtre en 24h (mute/kick/ban). Pas d'option
    « aucune sanction » : volontaire, voir _handle_wordfilter_repeat_offender."""

    def __init__(self, guild: discord.Guild):
        current = _get_setting(guild.id, "wordfilter_sanction_type") or "mute"
        options = [
            discord.SelectOption(
                label=(choice["fr"] if LANG == "fr" else choice["en"])[:100],
                value=key,
                default=(key == current),
            )
            for key, choice in WORDFILTER_SANCTION_CHOICES.items()
        ]
        super().__init__(
            placeholder="Sanction automatique (anti-spam)" if LANG == "fr" else "Automatic sanction (anti-spam)",
            options=options, min_values=1, max_values=1, row=2,
            custom_id="config_wordfilter_sanction",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        _set_setting(guild.id, "wordfilter_sanction_type", self.values[0])
        saved = await save_guild_config(guild)
        await interaction.response.edit_message(
            embed=_build_wordfilter_embed(guild),
            view=WordFilterPanelView(guild.id),
        )
        if not saved:
            await _wordfilter_not_saved_notice(interaction)


class WordFilterMuteModal(discord.ui.Modal):
    """Durée de la sourdine infligée par la sanction anti-spam du filtre de
    mots — seule valeur personnalisable par les serveurs, entre 5 min et
    24h (voir CONFIG_META['wordfilter_mute_minutes'])."""

    def __init__(self, guild: discord.Guild):
        super().__init__(
            title="Durée de la sourdine (filtre de mots)" if LANG == "fr" else "Timeout duration (word filter)",
            timeout=300,
        )
        self.guild_id = guild.id
        self.mute_input = discord.ui.TextInput(
            label=(CONFIG_META["wordfilter_mute_minutes"]["fr"] if LANG == "fr" else CONFIG_META["wordfilter_mute_minutes"]["en"])[:45],
            default=str(_get_setting(guild.id, "wordfilter_mute_minutes")),
            required=True, max_length=5,
        )
        self.add_item(self.mute_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        mute_val, err = _validate_setting_input("wordfilter_mute_minutes", self.mute_input.value)
        if err:
            await interaction.response.send_message(
                f"**{'Durée de sourdine' if LANG == 'fr' else 'Timeout duration'}** : {err}"[:2000],
                ephemeral=True,
            )
            return
        _set_setting(guild.id, "wordfilter_mute_minutes", mute_val)
        saved = await save_guild_config(guild)
        text = "✅ Réglage mis à jour." if LANG == "fr" else "✅ Setting updated."
        if not saved:
            text += "\n\n⚠️ " + (
                "Non enregistré (serveur base de données indisponible) : perdu au redémarrage."
                if LANG == "fr" else "Not saved (database server unavailable): lost on restart."
            )
        await interaction.response.send_message(text, ephemeral=True)


class WordFilterOpenMuteModalButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Durée de la sourdine" if LANG == "fr" else "Timeout duration",
            emoji="⏱️",
            row=row,
            custom_id="config_wordfilter_open_mute_modal",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.send_modal(WordFilterMuteModal(interaction.guild))


class WordFilterPanelView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        guild = bot.get_guild(guild_id)
        self.add_item(ConfigModuleToggleButton(module_key="wordfilter", row=0, refresh=_refresh_wordfilter_panel))
        self.add_item(WordFilterAddButton(row=0))
        self.add_item(WordFilterClearButton(row=0))
        self.add_item(WordFilterOpenMuteModalButton(row=0))
        self.add_item(WordFilterRemoveSelect(guild_id, row=1))
        if guild is not None:
            self.add_item(WordFilterSanctionSelect(guild))
        self.add_item(BackToMainPanelButton(row=3))


@bot.tree.command(
    name="mots-interdits" if LANG == "fr" else "banned-words",
    description=(
        "Ouvre le panel du filtre de mots interdits (voir/ajouter/retirer, activer/désactiver)" if LANG == "fr"
        else "Opens the banned-words filter panel (view/add/remove, enable/disable)"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def wordfilter_panel_command(interaction: discord.Interaction):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    await interaction.response.send_message(
        embed=_build_wordfilter_embed(interaction.guild),
        view=WordFilterPanelView(interaction.guild.id),
        ephemeral=True,
    )


@bot.tree.command(
    name="salon-piege" if LANG == "fr" else "honeypot-channel",
    description=(
        "Crée (ou resynchronise) le salon piège : quiconque y écrit est sanctionné"
        if LANG == "fr"
        else "Creates (or resyncs) the honeypot channel: anyone who writes there gets sanctioned"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def honeypot_channel_command(interaction: discord.Interaction):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    guild = interaction.guild
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        channel = await _setup_honeypot_channel(guild)
        saved = await save_guild_config(guild)
        summary = (
            f"✅ Salon piège prêt : {channel.mention}. Réglable (sanction, durée, texte) via `/panel` > "
            "Configuration serveur > Salon piège." if LANG == "fr"
            else f"✅ Honeypot channel ready: {channel.mention}. Configurable (sanction, duration, text) "
            "via `/panel` > Server configuration > Honeypot channel."
        )
        await interaction.followup.send(summary, ephemeral=True)
        if not saved:
            await _toggle_not_saved_notice(interaction)
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Permissions insuffisantes (il faut Gérer les salons)." if LANG == "fr"
            else "❌ Missing permissions (needs Manage Channels).",
            ephemeral=True,
        )
    except Exception:
        log.exception(f"Salon piège : échec de la création/resynchronisation sur {guild.name}.")
        await interaction.followup.send(
            "❌ Une erreur est survenue pendant la création du salon." if LANG == "fr"
            else "❌ An error occurred while creating the channel.",
            ephemeral=True,
        )



def _on_off_label(value: bool, label_fr: str, label_en: str) -> str:
    label = label_fr if LANG == "fr" else label_en
    state = ("Autorisés" if LANG == "fr" else "Allowed") if value else ("Interdits" if LANG == "fr" else "Disallowed")
    emoji = "✅" if value else "⛔"
    return f"{emoji} {label} : {state}" if LANG == "fr" else f"{emoji} {label}: {state}"


def _enabled_label(value: bool) -> str:
    state = ("Activé" if LANG == "fr" else "Enabled") if value else ("Désactivé" if LANG == "fr" else "Disabled")
    emoji = "✅" if value else "⛔"
    return f"{emoji} Module : {state}" if LANG == "fr" else f"{emoji} Module: {state}"


def _fmt_mod_request_status_line(guild: discord.Guild) -> str:
    """Ligne de statut du système de demande, affichée dans les embeds du
    panel : Activé/Désactivé, et le salon des demandes s'il est réglé.
    Depuis la suppression des niveaux, le staff (et donc qui peut exécuter ou
    valider quoi) découle uniquement des permissions Discord réelles du
    membre (voir _member_is_staff / _can_member_direct_sanction)."""
    enabled = bool(_get_setting(guild.id, "mod_request_enabled"))
    channel_id = _get_setting(guild.id, "mod_request_channel_id")
    channel_txt = f"<#{channel_id}>" if channel_id else ("*non défini*" if LANG == "fr" else "*not set*")
    if LANG == "fr":
        state = "✅ Activé" if enabled else "⛔ Désactivé"
        return f"• Système de demande : {state}\n• Salon des demandes : {channel_txt}"
    state = "✅ Enabled" if enabled else "⛔ Disabled"
    return f"• Request system: {state}\n• Requests channel: {channel_txt}"


async def _build_server_settings_embed(guild: discord.Guild) -> discord.Embed:
    """Embed du sous-menu « Configuration serveur » (webhooks/liens/invitations,
    anti-nuke temps réel, anti-spam), regroupé derrière le bouton du même nom
    pour ne plus tout afficher d'un coup sur le panel principal."""
    webhooks = await get_webhooks_allowed(guild)
    links = await get_links_allowed(guild)
    invites = await get_invites_allowed(guild)
    apps = await get_apps_allowed(guild)
    followers = await get_followers_allowed(guild)
    antinuke_on = _module_enabled(guild.id, "antinuke")
    antispam_on = _module_enabled(guild.id, "antispam")
    messagelog_on = _module_enabled(guild.id, "messagelog")
    serverlog_on = _module_enabled(guild.id, "serverlog")

    def _fmt_channel_local(key: str) -> str:
        cid = _get_setting(guild.id, key)
        return f"<#{cid}>" if cid else ("*non défini*" if LANG == "fr" else "*not set*")

    if LANG == "fr":
        embed = discord.Embed(
            title="🛠️ Configuration serveur",
            description="Choisis un réglage ci-dessous pour l'activer, le désactiver ou en changer les valeurs.",
            color=0x5865F2,
        )
        embed.add_field(
            name="Sécurité",
            value=(
                f"{_on_off_label(webhooks, 'Webhooks', 'Webhooks')}\n"
                f"{_on_off_label(apps, 'Application externe', 'External application')}\n"
                f"{_on_off_label(followers, 'Suivis de salon', 'Channel follows')}\n"
                f"{_on_off_label(links, 'Liens', 'Links')}\n"
                f"{_on_off_label(invites, 'Invitations', 'Invites')}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Anti-nuke — temps réel (rôles/salons/webhooks)",
            value=(
                f"{_enabled_label(antinuke_on)}\n"
                f"• Seuil humain : {_get_setting(guild.id, 'antinuke_action_count_human')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_human')}s\n"
                f"• Seuil bot non certifié : {_get_setting(guild.id, 'antinuke_action_count_bot_unverified')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_unverified')}s\n"
                f"• Seuil bot certifié : {_get_setting(guild.id, 'antinuke_action_count_bot_verified')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_verified')}s\n"
                f"• Sourdine humain : {_get_setting(guild.id, 'antinuke_human_timeout_minutes')} min\n"
                f"• Sanction bot : {ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, 'antinuke_bot_sanction')]['fr']}\n"
                f"• Sanction humain : {ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, 'antinuke_human_sanction')]['fr']}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Anti-spam",
            value=(
                f"{_enabled_label(antispam_on)}\n"
                f"• Seuil : {_get_setting(guild.id, 'spam_message_count')} messages / "
                f"{_get_setting(guild.id, 'spam_window_seconds')}s\n"
                f"• Sourdine : {_get_setting(guild.id, 'spam_timeout_minutes')} min"
            ),
            inline=False,
        )
        embed.add_field(
            name="Logs messages",
            value=(
                f"{_enabled_label(messagelog_on)}\n"
                f"• Salon : {_fmt_channel_local('message_log_channel_id')}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Logs serveur (bans, expulsions, salons, rôles...)",
            value=(
                f"{_enabled_label(serverlog_on)}\n"
                f"• Salon : {_fmt_channel_local('server_log_channel_id')}"
            ),
            inline=False,
        )
        min_age = _get_setting(guild.id, "min_account_age_hours")
        embed.add_field(
            name="Âge minimum des comptes",
            value=(
                f"{_enabled_label(bool(min_age))}\n"
                f"• Seuil : {min_age} heure(s)" if min_age else f"{_enabled_label(False)}"
            ),
            inline=False,
        )
    else:
        embed = discord.Embed(
            title="🛠️ Server settings",
            description="Pick a setting below to enable it, disable it, or change its values.",
            color=0x5865F2,
        )
        embed.add_field(
            name="Security",
            value=(
                f"{_on_off_label(webhooks, 'Webhooks', 'Webhooks')}\n"
                f"{_on_off_label(apps, 'Application externe', 'External application')}\n"
                f"{_on_off_label(followers, 'Suivis de salon', 'Channel follows')}\n"
                f"{_on_off_label(links, 'Links', 'Links')}\n"
                f"{_on_off_label(invites, 'Invites', 'Invites')}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Anti-nuke — real-time (roles/channels/webhooks)",
            value=(
                f"{_enabled_label(antinuke_on)}\n"
                f"• Human threshold: {_get_setting(guild.id, 'antinuke_action_count_human')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_human')}s\n"
                f"• Unverified bot threshold: {_get_setting(guild.id, 'antinuke_action_count_bot_unverified')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_unverified')}s\n"
                f"• Verified bot threshold: {_get_setting(guild.id, 'antinuke_action_count_bot_verified')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_verified')}s\n"
                f"• Human timeout: {_get_setting(guild.id, 'antinuke_human_timeout_minutes')} min\n"
                f"• Bot sanction: {ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, 'antinuke_bot_sanction')]['en']}\n"
                f"• Human sanction: {ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, 'antinuke_human_sanction')]['en']}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Anti-spam",
            value=(
                f"{_enabled_label(antispam_on)}\n"
                f"• Threshold: {_get_setting(guild.id, 'spam_message_count')} messages / "
                f"{_get_setting(guild.id, 'spam_window_seconds')}s\n"
                f"• Timeout: {_get_setting(guild.id, 'spam_timeout_minutes')} min"
            ),
            inline=False,
        )
        embed.add_field(
            name="Message logs",
            value=(
                f"{_enabled_label(messagelog_on)}\n"
                f"• Channel: {_fmt_channel_local('message_log_channel_id')}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Server logs (bans, kicks, channels, roles...)",
            value=(
                f"{_enabled_label(serverlog_on)}\n"
                f"• Channel: {_fmt_channel_local('server_log_channel_id')}"
            ),
            inline=False,
        )
        min_age = _get_setting(guild.id, "min_account_age_hours")
        embed.add_field(
            name="Minimum account age",
            value=(
                f"{_enabled_label(bool(min_age))}\n"
                f"• Threshold: {min_age} hour(s)" if min_age else f"{_enabled_label(False)}"
            ),
            inline=False,
        )
    return embed


def _build_staff_settings_embed(guild: discord.Guild) -> discord.Embed:
    """Embed du sous-menu « Configuration staff » (rôles staff + salon des
    demandes), regroupé derrière le bouton du même nom pour ne plus tout
    afficher d'un coup sur le panel principal."""

    def _fmt_role(key: str) -> str:
        rid = _get_setting(guild.id, key)
        return f"<@&{rid}>" if rid else ("*non défini*" if LANG == "fr" else "*not set*")

    def _fmt_channel(key: str) -> str:
        cid = _get_setting(guild.id, key)
        return f"<#{cid}>" if cid else ("*non défini*" if LANG == "fr" else "*not set*")

    if LANG == "fr":
        embed = discord.Embed(
            title="👮 Configuration staff",
            description=(
                "Le staff est désormais déterminé par les permissions Discord réelles : "
                "avoir au moins **Modérer les membres** (mute) suffit à utiliser les "
                "commandes du bot. Ici, tu peux juste régler un rôle Fondateur optionnel "
                "(accès total, même sans permission Discord), le salon des demandes, et "
                "activer/désactiver le système de demande."
            ),
            color=0x5865F2,
        )
        embed.add_field(
            name="Rôle Fondateur",
            value=_fmt_role('owner_role_id'),
            inline=False,
        )
        embed.add_field(
            name="Système de demande",
            value=_fmt_mod_request_status_line(guild),
            inline=False,
        )
        embed.add_field(name="Tickets de gel", value=_freeze_tickets_status_text(guild), inline=False)
        embed.add_field(name="Accès aux commandes de gel", value=_freeze_access_status_text(guild), inline=False)
    else:
        embed = discord.Embed(
            title="👮 Staff settings",
            description=(
                "Staff is now determined by real Discord permissions: having at least "
                "**Moderate Members** (mute) is enough to use the bot's commands. Here "
                "you can just set an optional Founder role (full access even without "
                "the Discord permission), the requests channel, and toggle the request "
                "system on/off."
            ),
            color=0x5865F2,
        )
        embed.add_field(
            name="Founder role",
            value=_fmt_role('owner_role_id'),
            inline=False,
        )
        embed.add_field(
            name="Request system",
            value=_fmt_mod_request_status_line(guild),
            inline=False,
        )
        embed.add_field(name="Freeze tickets", value=_freeze_tickets_status_text(guild), inline=False)
        embed.add_field(name="Freeze command access", value=_freeze_access_status_text(guild), inline=False)
    return embed


async def _build_config_panel_embed(guild: discord.Guild) -> discord.Embed:
    webhooks = await get_webhooks_allowed(guild)
    links = await get_links_allowed(guild)
    invites = await get_invites_allowed(guild)
    apps = await get_apps_allowed(guild)
    followers = await get_followers_allowed(guild)
    whitelist_count = len(_guild_store.get(guild.id, {}).get("whitelist", {}))

    def _fmt_role(key: str) -> str:
        rid = _get_setting(guild.id, key)
        return f"<@&{rid}>" if rid else ("*non défini*" if LANG == "fr" else "*not set*")

    def _fmt_channel(key: str) -> str:
        cid = _get_setting(guild.id, key)
        return f"<#{cid}>" if cid else ("*non défini*" if LANG == "fr" else "*not set*")

    if LANG == "fr":
        embed = discord.Embed(
            title="⚙️ Panel de configuration",
            description="Utilise les boutons ci-dessous pour régler le bot sur ce serveur.",
            color=0x5865F2,
        )
        embed.add_field(
            name="Sécurité",
            value=(
                f"{_on_off_label(webhooks, 'Webhooks', 'Webhooks')}\n"
                f"{_on_off_label(apps, 'Application externe', 'External application')}\n"
                f"{_on_off_label(followers, 'Suivis de salon', 'Channel follows')}\n"
                f"{_on_off_label(links, 'Liens', 'Links')}\n"
                f"{_on_off_label(invites, 'Invitations', 'Invites')}\n"
                f"📋 Liste blanche : {whitelist_count} entrée(s)"
            ),
            inline=False,
        )
        embed.add_field(
            name="Staff",
            value=(
                f"• Fondateur : {_fmt_role('owner_role_id')}\n"
                + _fmt_mod_request_status_line(guild)
            ),
            inline=False,
        )
        embed.add_field(
            name="Anti-nuke — temps réel (rôles/salons/webhooks)",
            value=(
                f"• Humain : {_get_setting(guild.id, 'antinuke_action_count_human')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_human')}s\n"
                f"• Bot non certifié : {_get_setting(guild.id, 'antinuke_action_count_bot_unverified')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_unverified')}s\n"
                f"• Bot certifié : {_get_setting(guild.id, 'antinuke_action_count_bot_verified')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_verified')}s\n"
                f"• Sourdine humain : {_get_setting(guild.id, 'antinuke_human_timeout_minutes')} min\n"
                f"• Sanction bot : {ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, 'antinuke_bot_sanction')]['fr']}\n"
                f"• Sanction humain : {ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, 'antinuke_human_sanction')]['fr']}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Anti-spam",
            value=(
                f"• Seuil : {_get_setting(guild.id, 'spam_message_count')} messages / "
                f"{_get_setting(guild.id, 'spam_window_seconds')}s\n"
                f"• Sourdine : {_get_setting(guild.id, 'spam_timeout_minutes')} min"
            ),
            inline=True,
        )
    else:
        embed = discord.Embed(
            title="⚙️ Configuration panel",
            description="Use the buttons below to configure the bot on this server.",
            color=0x5865F2,
        )
        embed.add_field(
            name="Security",
            value=(
                f"{_on_off_label(webhooks, 'Webhooks', 'Webhooks')}\n"
                f"{_on_off_label(apps, 'Application externe', 'External application')}\n"
                f"{_on_off_label(followers, 'Suivis de salon', 'Channel follows')}\n"
                f"{_on_off_label(links, 'Links', 'Links')}\n"
                f"{_on_off_label(invites, 'Invites', 'Invites')}\n"
                f"📋 Whitelist: {whitelist_count} entry(ies)"
            ),
            inline=False,
        )
        embed.add_field(
            name="Staff",
            value=(
                f"• Founder: {_fmt_role('owner_role_id')}\n"
                + _fmt_mod_request_status_line(guild)
            ),
            inline=False,
        )
        embed.add_field(
            name="Anti-nuke — real-time (roles/channels/webhooks)",
            value=(
                f"• Human: {_get_setting(guild.id, 'antinuke_action_count_human')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_human')}s\n"
                f"• Unverified bot: {_get_setting(guild.id, 'antinuke_action_count_bot_unverified')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_unverified')}s\n"
                f"• Verified bot: {_get_setting(guild.id, 'antinuke_action_count_bot_verified')} actions / "
                f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_verified')}s\n"
                f"• Human timeout: {_get_setting(guild.id, 'antinuke_human_timeout_minutes')} min\n"
                f"• Bot sanction: {ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, 'antinuke_bot_sanction')]['en']}\n"
                f"• Human sanction: {ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, 'antinuke_human_sanction')]['en']}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Anti-spam",
            value=(
                f"• Threshold: {_get_setting(guild.id, 'spam_message_count')} messages / "
                f"{_get_setting(guild.id, 'spam_window_seconds')}s\n"
                f"• Timeout: {_get_setting(guild.id, 'spam_timeout_minutes')} min"
            ),
            inline=True,
        )
    return embed


async def _refresh_config_panel(interaction: discord.Interaction) -> None:
    await interaction.response.edit_message(
        content=None,
        embed=await _build_config_panel_embed(interaction.guild),
        view=ConfigPanelView(),
    )


async def _refresh_server_settings_panel(interaction: discord.Interaction) -> None:
    """Comme _refresh_config_panel, mais reste dans le sous-menu « Configuration
    serveur » après un toggle, au lieu de sauter au menu principal."""
    await interaction.response.edit_message(
        content=None,
        embed=await _build_server_settings_embed(interaction.guild),
        view=ConfigServerSettingsView(),
    )


async def _refresh_wordfilter_panel(interaction: discord.Interaction) -> None:
    """Refresh dédié pour le toggle du module 'wordfilter' : reste sur le
    panel Mots interdits (WordFilterPanelView), au lieu de sauter ailleurs."""
    await interaction.response.edit_message(
        embed=_build_wordfilter_embed(interaction.guild),
        view=WordFilterPanelView(interaction.guild.id),
    )


async def _refresh_honeypot_settings_panel(interaction: discord.Interaction) -> None:
    """Refresh dédié pour le toggle du module 'honeypot' (salon piège) : reste
    sur le panel Salon piège (ConfigHoneypotSettingsView) — c'est l'absence de
    ce refresh dédié qui empêchait le salon piège de s'activer/désactiver
    correctement depuis son propre sous-menu."""
    await interaction.response.edit_message(
        content=_build_honeypot_settings_text(interaction.guild),
        embed=None,
        view=ConfigHoneypotSettingsView(interaction.guild),
    )


async def _toggle_not_saved_notice(interaction: discord.Interaction) -> None:
    await interaction.followup.send(
        "⚠️ Non enregistré (serveur base de données indisponible) : perdu au redémarrage du bot." if LANG == "fr"
        else "⚠️ Not saved (database server unavailable): lost when the bot restarts.",
        ephemeral=True,
    )



MODULE_TOGGLE_LABELS_FR = {
    "antinuke": ("Anti-nuke", "🛡️"),
    "automod": ("Auto-mod", "🧹"),
    "antispam": ("Anti-spam", "🚫"),
    "messagelog": ("Logs messages", "📝"),
    "serverlog": ("Logs serveur", "🗂️"),
    "verification": ("Vérification", "🧩"),
    "wordfilter": ("Mots interdits", "🚯"),
    "honeypot": ("Salon piège", "🍯"),
}
MODULE_TOGGLE_LABELS_EN = {
    "antinuke": ("Anti-nuke", "🛡️"),
    "automod": ("Auto-mod", "🧹"),
    "antispam": ("Anti-spam", "🚫"),
    "messagelog": ("Message logs", "📝"),
    "serverlog": ("Server logs", "🗂️"),
    "verification": ("Verification", "🧩"),
    "wordfilter": ("Banned words", "🚯"),
    "honeypot": ("Honeypot channel", "🍯"),
}


class ConfigModuleToggleButton(discord.ui.Button):
    """Active/désactive un module (antinuke/automod/antispam/...) pour CE
    serveur uniquement — réglage stocké dans DEFAULT_SETTINGS via
    'module_<key>_enabled' et lu par _module_enabled()."""

    def __init__(self, *, module_key: str, row: int, refresh=None):
        self.module_key = module_key
        self._refresh = refresh
        labels = MODULE_TOGGLE_LABELS_FR if LANG == "fr" else MODULE_TOGGLE_LABELS_EN
        label, emoji = labels[module_key]
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            emoji=emoji,
            row=row,
            custom_id=f"config_module_toggle_{module_key}",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        setting_key = MODULE_SETTING_KEY[self.module_key]
        current = bool(_get_setting(guild.id, setting_key))
        turning_on = not current
        _set_setting(guild.id, setting_key, not current)

        setup_summary = None
        if self.module_key == "verification" and turning_on:
            try:
                verified_role, unverified_role, updated = await _auto_setup_verification(guild)
                setup_summary = (
                    f"🧩 Auto-configuration : rôles {verified_role.mention} / {unverified_role.mention} "
                    f"prêts, {updated} salon(s) masqué(s) au rôle non vérifié."
                    if LANG == "fr"
                    else f"🧩 Auto-setup: {verified_role.mention} / {unverified_role.mention} roles ready, "
                    f"{updated} channel(s) hidden from the unverified role."
                )
            except discord.Forbidden:
                setup_summary = (
                    "⚠️ Vérification activée, mais permissions insuffisantes pour créer les rôles/paramétrer "
                    "les salons automatiquement (il faut Gérer les rôles + Gérer les salons)." if LANG == "fr"
                    else "⚠️ Verification enabled, but missing permissions to auto-create roles/configure "
                    "channels (needs Manage Roles + Manage Channels)."
                )
            except Exception:
                log.exception(f"Vérification : échec de l'auto-configuration sur {guild.name}.")
                setup_summary = (
                    "⚠️ Vérification activée, mais l'auto-configuration des rôles/salons a échoué." if LANG == "fr"
                    else "⚠️ Verification enabled, but auto-setup of roles/channels failed."
                )

        saved = await save_guild_config(guild)
        if self._refresh is not None:
            await self._refresh(interaction)
        else:
            await _refresh_server_settings_panel(interaction)
        if setup_summary:
            await interaction.followup.send(setup_summary, ephemeral=True)
        if not saved:
            await _toggle_not_saved_notice(interaction)



def _validate_setting_input(key: str, raw: str):
    """Retourne (valeur, None) si valide, ou (None, message_erreur) sinon."""
    meta = CONFIG_META[key]
    raw = raw.strip().replace(",", ".") if meta.get("float") else raw.strip()
    try:
        value = float(raw) if meta.get("float") else int(raw)
    except ValueError:
        return None, (
            f"❌ « {raw} » n'est pas un nombre valide pour ce champ." if LANG == "fr"
            else f"❌ « {raw} » is not a valid number for this field."
        )
    lo, hi = meta.get("min"), meta.get("max")
    if lo is not None and value < lo:
        return None, (
            f"❌ Valeur trop basse (minimum {lo})." if LANG == "fr" else f"❌ Value too low (minimum {lo})."
        )
    if hi is not None and value > hi:
        return None, (
            f"❌ Valeur trop haute (maximum {hi})." if LANG == "fr" else f"❌ Value too high (maximum {hi})."
        )
    return value, None


class SettingsGroupModal(discord.ui.Modal):
    """Modal générique : jusqu'à 5 réglages numériques de CONFIG_META, avec la
    valeur actuelle du serveur pré-remplie (pas de valeur par défaut imposée
    à l'aveugle). Utilisé pour anti-spam, anti-nuke, sécurité admin, etc."""

    def __init__(self, *, guild: discord.Guild, title_fr: str, title_en: str, keys: list[str]):
        super().__init__(title=title_fr if LANG == "fr" else title_en, timeout=300)
        self.guild_id = guild.id
        self.keys = keys
        self.inputs: dict[str, discord.ui.TextInput] = {}
        for key in keys:
            meta = CONFIG_META[key]
            label = (meta["fr"] if LANG == "fr" else meta["en"])[:45]
            current = _get_setting(guild.id, key)
            text_input = discord.ui.TextInput(
                label=label,
                default=str(current),
                required=True,
                max_length=10,
            )
            self.inputs[key] = text_input
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        errors = []
        applied = []
        for key, text_input in self.inputs.items():
            value, error = _validate_setting_input(key, text_input.value)
            if error:
                meta = CONFIG_META[key]
                label = meta["fr"] if LANG == "fr" else meta["en"]
                errors.append(f"**{label}** : {error}")
                continue
            _set_setting(self.guild_id, key, value)
            meta = CONFIG_META[key]
            label = meta["fr"] if LANG == "fr" else meta["en"]
            applied.append(f"✅ **{label}** → `{value}`")
        saved = True
        if applied:
            saved = await save_guild_config(interaction.guild)
        lines = applied + errors
        text = "\n".join(lines) if lines else ("Aucun changement." if LANG == "fr" else "No changes.")
        if not saved:
            text += "\n\n⚠️ " + (
                "Non enregistré (serveur base de données indisponible) : perdu au redémarrage."
                if LANG == "fr"
                else "Not saved (database server unavailable): lost on restart."
            )
        await interaction.response.send_message(text[:2000], ephemeral=True)


class ConfigOpenSettingsModalButton(discord.ui.Button):
    """Bouton du panel qui ouvre un SettingsGroupModal pour un sous-ensemble
    de réglages (max 5 par modal — limite Discord)."""

    def __init__(self, *, keys: list[str], title_fr: str, title_en: str, label_fr: str, label_en: str, emoji: str, row: int):
        self.keys = keys
        self.title_fr = title_fr
        self.title_en = title_en
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label_fr if LANG == "fr" else label_en,
            emoji=emoji,
            row=row,
            custom_id=f"config_open_modal_{'_'.join(keys)}"[:100],
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        modal = SettingsGroupModal(
            guild=interaction.guild, title_fr=self.title_fr, title_en=self.title_en, keys=self.keys,
        )
        await interaction.response.send_modal(modal)



ANTINUKE_SANCTION_VALID_VALUES = tuple(ANTINUKE_SANCTION_CHOICES.keys())


def _validate_sanction_input(raw_value: str) -> tuple[str | None, str | None]:
    value = raw_value.strip().lower()
    if value not in ANTINUKE_SANCTION_VALID_VALUES:
        valid_list = ", ".join(ANTINUKE_SANCTION_VALID_VALUES)
        return None, (
            f"❌ Valeur invalide : `{value}`. Valeurs possibles : {valid_list}." if LANG == "fr"
            else f"❌ Invalid value: `{value}`. Allowed values: {valid_list}."
        )
    return value, None


class AntinukeCategoryModal(discord.ui.Modal):
    """Formulaire pour UNE catégorie anti-nuke (bots non certifiés / bots
    certifiés / humain) : seuils numériques (CONFIG_META) + sanction en
    texte libre, préremplis avec les valeurs actuelles du serveur. La
    sanction « bot » (antinuke_bot_sanction) est partagée entre les deux
    catégories de bots — un seul réglage en base, modifiable depuis l'un ou
    l'autre bouton, ça reste cohérent puisque c'est la même action."""

    def __init__(
        self, *, guild: discord.Guild, title_fr: str, title_en: str, keys: list[str],
        sanction_key: str, sanction_label_fr: str, sanction_label_en: str, sanction_default: str,
    ):
        super().__init__(title=title_fr if LANG == "fr" else title_en, timeout=300)
        self.guild_id = guild.id
        self.keys = keys
        self.sanction_key = sanction_key
        self.inputs: dict[str, discord.ui.TextInput] = {}
        for key in keys:
            meta = CONFIG_META[key]
            label = (meta["fr"] if LANG == "fr" else meta["en"])[:45]
            current = _get_setting(guild.id, key)
            text_input = discord.ui.TextInput(label=label, default=str(current), required=True, max_length=10)
            self.inputs[key] = text_input
            self.add_item(text_input)
        valid_list = ", ".join(ANTINUKE_SANCTION_VALID_VALUES)
        sanction_label = ((sanction_label_fr if LANG == "fr" else sanction_label_en) + f" ({valid_list})")[:45]
        self.sanction_input = discord.ui.TextInput(
            label=sanction_label,
            default=str(_get_setting(guild.id, sanction_key) or sanction_default),
            required=True,
            max_length=20,
        )
        self.add_item(self.sanction_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return

        errors = []
        applied = []
        for key, text_input in self.inputs.items():
            value, error = _validate_setting_input(key, text_input.value)
            meta = CONFIG_META[key]
            label = meta["fr"] if LANG == "fr" else meta["en"]
            if error:
                errors.append(f"**{label}** : {error}")
                continue
            _set_setting(self.guild_id, key, value)
            applied.append(f"✅ **{label}** → `{value}`")

        sanction_value, sanction_error = _validate_sanction_input(self.sanction_input.value)
        if sanction_error:
            errors.append(sanction_error)
        else:
            _set_setting(self.guild_id, self.sanction_key, sanction_value)
            applied.append(f"✅ Sanction → `{sanction_value}`")

        saved = True
        if applied:
            saved = await save_guild_config(interaction.guild)

        lines = applied + errors
        text = "\n".join(lines) if lines else ("Aucun changement." if LANG == "fr" else "No changes.")
        if not saved:
            text += "\n\n⚠️ " + (
                "Non enregistré (serveur base de données indisponible) : perdu au redémarrage."
                if LANG == "fr"
                else "Not saved (database server unavailable): lost on restart."
            )
        await interaction.response.send_message(text[:2000], ephemeral=True)


class ConfigOpenAntinukeCategoryButton(discord.ui.Button):
    """Un bouton = une catégorie anti-nuke (bots non certifiés / bots
    certifiés / humain), qui ouvre son propre AntinukeCategoryModal."""

    def __init__(
        self, *, category: str, label_fr: str, label_en: str, emoji: str, row: int, keys: list[str],
        sanction_key: str, sanction_label_fr: str, sanction_label_en: str, sanction_default: str,
    ):
        self.keys = keys
        self.sanction_key = sanction_key
        self.sanction_label_fr = sanction_label_fr
        self.sanction_label_en = sanction_label_en
        self.sanction_default = sanction_default
        self._title_fr = label_fr
        self._title_en = label_en
        super().__init__(
            style=discord.ButtonStyle.danger,
            label=label_fr if LANG == "fr" else label_en,
            emoji=emoji,
            row=row,
            custom_id=f"config_open_antinuke_{category}",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        modal = AntinukeCategoryModal(
            guild=interaction.guild,
            title_fr=self._title_fr, title_en=self._title_en,
            keys=self.keys,
            sanction_key=self.sanction_key,
            sanction_label_fr=self.sanction_label_fr, sanction_label_en=self.sanction_label_en,
            sanction_default=self.sanction_default,
        )
        await interaction.response.send_modal(modal)


class ConfigAntinukeSettingsView(discord.ui.View):
    """Sous-menu « Anti-nuke » : un bouton dédié par catégorie surveillée,
    chacun ouvrant son propre formulaire (seuils + sanction)."""

    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ConfigModuleToggleButton(module_key="antinuke", row=0))
        self.add_item(ConfigOpenAntinukeCategoryButton(
            category="bot_unverified",
            label_fr="Anti-nuke bots non certifiés" if LANG == "fr" else "Anti-nuke unverified bots",
            label_en="Anti-nuke unverified bots",
            emoji="🤖", row=1,
            keys=["antinuke_action_count_bot_unverified", "antinuke_window_seconds_bot_unverified", "unverified_bot_lockdown_minutes"],
            sanction_key="antinuke_bot_sanction",
            sanction_label_fr="Sanction BOT", sanction_label_en="BOT sanction",
            sanction_default="ban",
        ))
        self.add_item(ConfigOpenAntinukeCategoryButton(
            category="bot_verified",
            label_fr="Anti-nuke bots certifiés" if LANG == "fr" else "Anti-nuke verified bots",
            label_en="Anti-nuke verified bots",
            emoji="✅", row=1,
            keys=["antinuke_action_count_bot_verified", "antinuke_window_seconds_bot_verified"],
            sanction_key="antinuke_bot_sanction",
            sanction_label_fr="Sanction BOT", sanction_label_en="BOT sanction",
            sanction_default="ban",
        ))
        self.add_item(ConfigOpenAntinukeCategoryButton(
            category="human",
            label_fr="Anti-nuke humain" if LANG == "fr" else "Anti-nuke human",
            label_en="Anti-nuke human",
            emoji="🧑", row=1,
            keys=["antinuke_action_count_human", "antinuke_window_seconds_human", "antinuke_human_timeout_minutes"],
            sanction_key="antinuke_human_sanction",
            sanction_label_fr="Sanction HUMAIN", sanction_label_en="HUMAN sanction",
            sanction_default="timeout",
        ))
        self.add_item(BackToMainPanelButton(row=2, target="server"))


def _build_antinuke_settings_text(guild: discord.Guild) -> str:
    """Petit résumé texte affiché en ouvrant le sous-menu Anti-nuke, avant
    de choisir la catégorie à régler."""
    bot_sanction = ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, "antinuke_bot_sanction")]
    human_sanction = ANTINUKE_SANCTION_CHOICES[_get_setting(guild.id, "antinuke_human_sanction")]
    if LANG == "fr":
        return (
            "🛡️ **Anti-nuke** — choisis une catégorie à régler ci-dessous.\n"
            f"• Bots non certifiés : {_get_setting(guild.id, 'antinuke_action_count_bot_unverified')} actions / "
            f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_unverified')}s\n"
            f"• Verrouillage nom/icône serveur (bots non certifiés) : "
            f"{_get_setting(guild.id, 'unverified_bot_lockdown_minutes')} min après leur arrivée\n"
            f"• Bots certifiés : {_get_setting(guild.id, 'antinuke_action_count_bot_verified')} actions / "
            f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_verified')}s\n"
            f"• Humain : {_get_setting(guild.id, 'antinuke_action_count_human')} actions / "
            f"{_get_setting(guild.id, 'antinuke_window_seconds_human')}s "
            f"(sourdine {_get_setting(guild.id, 'antinuke_human_timeout_minutes')} min)\n"
            f"• Sanction bot (les deux catégories) : {bot_sanction['fr']}\n"
            f"• Sanction humain : {human_sanction['fr']}"
        )
    return (
        "🛡️ **Anti-nuke** — pick a category to configure below.\n"
        f"• Unverified bots: {_get_setting(guild.id, 'antinuke_action_count_bot_unverified')} actions / "
        f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_unverified')}s\n"
        f"• Server name/icon lockdown (unverified bots): "
        f"{_get_setting(guild.id, 'unverified_bot_lockdown_minutes')} min after joining\n"
        f"• Verified bots: {_get_setting(guild.id, 'antinuke_action_count_bot_verified')} actions / "
        f"{_get_setting(guild.id, 'antinuke_window_seconds_bot_verified')}s\n"
        f"• Human: {_get_setting(guild.id, 'antinuke_action_count_human')} actions / "
        f"{_get_setting(guild.id, 'antinuke_window_seconds_human')}s "
        f"(timeout {_get_setting(guild.id, 'antinuke_human_timeout_minutes')} min)\n"
        f"• Bot sanction (both categories): {bot_sanction['en']}\n"
        f"• Human sanction: {human_sanction['en']}"
    )


class ConfigOpenAntinukeSettingsButton(discord.ui.Button):
    """Bouton principal « Anti-nuke » sur le panel Configuration serveur,
    qui ouvre le sous-menu à 3 catégories ci-dessus."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Anti-nuke" if LANG == "fr" else "Anti-nuke",
            emoji="🛡️",
            row=row,
            custom_id="config_open_antinuke_settings",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=_build_antinuke_settings_text(interaction.guild),
            embed=None,
            view=ConfigAntinukeSettingsView(),
        )


class ConfigToggleButton(discord.ui.Button):
    def __init__(self, *, key: str, get_fn, set_fn, label_fr: str, label_en: str, emoji: str, row: int):
        self.key = key
        self.get_fn = get_fn
        self.set_fn = set_fn
        self.label_fr = label_fr
        self.label_en = label_en
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=(label_fr if LANG == "fr" else label_en),
            emoji=emoji,
            row=row,
            custom_id=f"config_toggle_{key}",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        current = await self.get_fn(interaction.guild)
        saved = await self.set_fn(interaction.guild, not current)
        await _refresh_server_settings_panel(interaction)
        if not saved:
            await _toggle_not_saved_notice(interaction)


class ConfigStaffRoleSelect(discord.ui.RoleSelect):
    def __init__(self, *, key: str, placeholder_fr: str, placeholder_en: str, row: int):
        self.key = key
        super().__init__(
            placeholder=placeholder_fr if LANG == "fr" else placeholder_en,
            min_values=1,
            max_values=1,
            row=row,
            custom_id=f"config_staffrole_{key}",
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(
                "❌ Seul·e le/la propriétaire du serveur ou un membre Administrateur peut configurer les rôles staff."
                if LANG == "fr"
                else "❌ Only the server owner or an Administrator member can configure staff roles.",
                ephemeral=True,
            )
            return
        role = self.values[0]
        _set_setting(guild.id, self.key, role.id)
        saved = await save_guild_config(guild)
        text = (
            f"✅ Rôle Fondateur réglé sur {role.mention}." if LANG == "fr"
            else f"✅ Founder role set to {role.mention}."
        )
        await interaction.response.edit_message(content=text, embed=None, view=FounderRolePanelView())
        if not saved:
            await _toggle_not_saved_notice(interaction)


class FounderRolePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ConfigStaffRoleSelect(
            key="owner_role_id",
            placeholder_fr="👑 Choisir le rôle Fondateur…",
            placeholder_en="👑 Choose the Founder role…",
            row=0,
        ))
        self.add_item(BackToMainPanelButton(row=1, target="staff"))




class ConfigSanctionChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="📨 Choisir le salon des demandes…" if LANG == "fr" else "📨 Choose the requests channel…",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            row=0,
            custom_id="config_sanction_channel_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        channel = self.values[0]
        _set_setting(interaction.guild.id, "mod_request_channel_id", channel.id)
        saved = await save_guild_config(interaction.guild)
        cid = _get_setting(interaction.guild.id, "mod_request_channel_id")
        text = (
            f"✅ Salon des demandes de sanction réglé sur <#{cid}>." if LANG == "fr"
            else f"✅ Sanction-request channel set to <#{cid}>."
        )
        await interaction.response.edit_message(content=text, embed=None, view=SanctionChannelPanelView())
        if not saved:
            await _toggle_not_saved_notice(interaction)


class SanctionChannelPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ConfigSanctionChannelSelect())
        self.add_item(BackToMainPanelButton(row=1, target="staff"))



class MessageLogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="📝 Choisir le salon de logs de messages…" if LANG == "fr" else "📝 Choose the message log channel…",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            row=0,
            custom_id="config_message_log_channel_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        channel = self.values[0]
        _set_setting(interaction.guild.id, "message_log_channel_id", channel.id)
        saved = await save_guild_config(interaction.guild)
        cid = _get_setting(interaction.guild.id, "message_log_channel_id")
        text = (
            f"✅ Salon de logs de messages réglé sur <#{cid}> (sur CE serveur — pas de serveur de stockage requis).\n"
            "N'oublie pas d'activer le module « 📝 Logs messages » si ce n'est pas déjà fait." if LANG == "fr"
            else f"✅ Message log channel set to <#{cid}> (on THIS server — no storage server needed).\n"
            "Don't forget to enable the « 📝 Message logs » module if it isn't already."
        )
        await interaction.response.edit_message(content=text, embed=None, view=MessageLogChannelPanelView())
        if not saved:
            await _toggle_not_saved_notice(interaction)


class MessageLogChannelPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(MessageLogChannelSelect())
        self.add_item(BackToMainPanelButton(row=1, target="server"))


class ConfigOpenMessageLogChannelButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Salon de logs messages" if LANG == "fr" else "Message log channel",
            emoji="📝",
            row=row,
            custom_id="config_open_message_log_channel",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        current = _get_setting(interaction.guild.id, "message_log_channel_id")
        text = (
            (f"📝 Salon actuel : <#{current}>." if current else "📝 Aucun salon défini pour l'instant.")
            + "\nChoisis le salon (sur CE serveur) où seront postés les messages envoyés/édités/supprimés."
            if LANG == "fr"
            else (f"📝 Current channel: <#{current}>." if current else "📝 No channel set yet.")
            + "\nChoose the channel (on THIS server) where sent/edited/deleted messages will be posted."
        )
        await interaction.response.edit_message(content=text, embed=None, view=MessageLogChannelPanelView())


class ServerLogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="🗂️ Choisir le salon de logs du serveur…" if LANG == "fr" else "🗂️ Choose the server log channel…",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            row=0,
            custom_id="config_server_log_channel_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        channel = self.values[0]
        _set_setting(interaction.guild.id, "server_log_channel_id", channel.id)
        saved = await save_guild_config(interaction.guild)
        cid = _get_setting(interaction.guild.id, "server_log_channel_id")
        text = (
            f"✅ Salon de logs du serveur réglé sur <#{cid}>.\n"
            "N'oublie pas d'activer le module « 🗂️ Logs serveur » si ce n'est pas déjà fait. "
            "Le bot doit avoir « Voir les logs du serveur », « Créer des fils publics » et « Envoyer des messages dans les fils »."
            if LANG == "fr"
            else f"✅ Server log channel set to <#{cid}>.\n"
            "Don't forget to enable the « 🗂️ Server logs » module if it isn't already. "
            "The bot needs « View Audit Log », « Create Public Threads » and « Send Messages in Threads »."
        )
        await interaction.response.edit_message(content=text, embed=None, view=ServerLogChannelPanelView())
        if not saved:
            await _toggle_not_saved_notice(interaction)


class ServerLogChannelPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ServerLogChannelSelect())
        self.add_item(BackToMainPanelButton(row=1, target="server"))


class ConfigOpenServerLogChannelButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Salon de logs serveur" if LANG == "fr" else "Server log channel",
            emoji="🗂️",
            row=row,
            custom_id="config_open_server_log_channel",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        current = _get_setting(interaction.guild.id, "server_log_channel_id")
        text = (
            (f"🗂️ Salon actuel : <#{current}>." if current else "🗂️ Aucun salon défini pour l'instant.")
            + "\nChoisis le salon où seront postées les actions du serveur (bans, expulsions, salons, rôles, webhooks...). Un fil par membre y sera créé."
            if LANG == "fr"
            else (f"🗂️ Current channel: <#{current}>." if current else "🗂️ No channel set yet.")
            + "\nChoose the channel where server actions will be posted (bans, kicks, channels, roles, webhooks...). One thread per member will be created there."
        )
        await interaction.response.edit_message(content=text, embed=None, view=ServerLogChannelPanelView())


class RefreshPanelButton(discord.ui.Button):
    """Recharge l'embed du sous-panel actuel (valeurs fraîches depuis
    _get_setting / les fonctions get_*), sans changer de vue ni de message."""

    def __init__(self, row: int = 4, target: str = "main"):
        self.target = target
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="🔄 Rafraîchir" if LANG == "fr" else "🔄 Refresh",
            row=row,
            custom_id=f"config_refresh_{target}",
        )

    async def callback(self, interaction: discord.Interaction):
        if self.target == "server":
            await interaction.response.edit_message(
                content=None,
                embed=await _build_server_settings_embed(interaction.guild),
                view=ConfigServerSettingsView(),
            )
        elif self.target == "staff":
            await interaction.response.edit_message(
                content=None,
                embed=_build_staff_settings_embed(interaction.guild),
                view=ConfigStaffSettingsView(),
            )
        else:
            await interaction.response.edit_message(
                content=None,
                embed=await _build_config_panel_embed(interaction.guild),
                view=ConfigPanelView(),
            )


class BackToMainPanelButton(discord.ui.Button):
    """Bouton retour générique, DANS le même message (edit_message), pour ne
    jamais laisser de message fantôme. `target` choisit où revenir :
    - "main"   -> le menu principal de /panel
    - "server" -> le sous-menu « Configuration serveur » (webhooks/liens/invitations)
    - "staff"  -> le sous-menu « Configuration staff » (rôles staff/salon des demandes)
    Ça évite de sauter directement au menu principal quand on est descendu
    depuis un sous-menu de catégorie."""

    _LABELS = {
        "main": ("⬅ Menu principal", "⬅ Main menu"),
        "server": ("⬅ Configuration serveur", "⬅ Server settings"),
        "staff": ("⬅ Configuration staff", "⬅ Staff settings"),
    }

    def __init__(self, row: int = 4, target: str = "main"):
        self.target = target
        label_fr, label_en = self._LABELS[target]
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label_fr if LANG == "fr" else label_en,
            row=row,
            custom_id=f"config_back_to_{target}",
        )

    async def callback(self, interaction: discord.Interaction):
        if self.target == "server":
            await interaction.response.edit_message(
                content=None,
                embed=await _build_server_settings_embed(interaction.guild),
                view=ConfigServerSettingsView(),
            )
        elif self.target == "staff":
            await interaction.response.edit_message(
                content=None,
                embed=_build_staff_settings_embed(interaction.guild),
                view=ConfigStaffSettingsView(),
            )
        else:
            await interaction.response.edit_message(
                content=None,
                embed=await _build_config_panel_embed(interaction.guild),
                view=ConfigPanelView(),
            )


class ConfigOpenFounderRoleButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Rôle Fondateur" if LANG == "fr" else "Founder role",
            emoji="👑",
            row=row,
            custom_id="config_open_founder_role",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=FounderRolePanelView(),
        )


class ConfigModRequestToggleButton(discord.ui.Button):
    """Active/désactive le système de demande (envoi + ping des personnes
    habilitées quand une action dépasse la permission réelle de quelqu'un).
    Désactivé, l'action est simplement refusée ("Tu n'as aucune permission.")
    au lieu de partir en demande."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Système de demande" if LANG == "fr" else "Request system",
            emoji="📨",
            row=row,
            custom_id="config_toggle_mod_request_enabled",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        current = bool(_get_setting(guild.id, "mod_request_enabled"))
        _set_setting(guild.id, "mod_request_enabled", not current)
        saved = await save_guild_config(guild)
        await interaction.response.edit_message(
            content=None,
            embed=_build_staff_settings_embed(guild),
            view=ConfigStaffSettingsView(),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class ConfigOpenSanctionChannelButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Salon des demandes" if LANG == "fr" else "Requests channel",
            emoji="📨",
            row=row,
            custom_id="config_open_sanction_channel",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=(
                "📨 Choisis le salon où les demandes (mute/kick/ban) seront envoyées aux personnes habilitées à les valider."
                if LANG == "fr"
                else "📨 Choose the channel where requests (mute/kick/ban) will be sent to the people allowed to approve them."
            ),
            embed=None,
            view=SanctionChannelPanelView(),
        )


class ConfigOpenWhitelistButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Liste blanche" if LANG == "fr" else "Whitelist",
            emoji="📋",
            row=row,
            custom_id="config_open_whitelist",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=None,
            embed=_build_whitelist_embed(interaction.guild),
            view=await _build_whitelist_panel_view(interaction.guild),
        )


class ConfigOpenWordFilterButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Mots interdits" if LANG == "fr" else "Banned words",
            emoji="🚯",
            row=row,
            custom_id="config_open_wordfilter",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=None,
            embed=_build_wordfilter_embed(interaction.guild),
            view=WordFilterPanelView(interaction.guild.id),
        )


class ConfigAuditButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Relancer l'audit sécurité" if LANG == "fr" else "Re-run security audit",
            emoji="🔍",
            row=row,
            custom_id="config_run_audit",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        channel = await run_audit_and_post(interaction.guild, requester=str(interaction.user))
        await interaction.followup.send(
            f"✅ Audit relancé, résultat détaillé (avec note) dans {channel.mention}." if LANG == "fr"
            else f"✅ Audit re-run, detailed graded result in {channel.mention}.",
            ephemeral=True,
        )


class BackToMainPanelOnlyView(discord.ui.View):
    """Petite vue jetable : juste un bouton retour, utilisée quand il n'y a
    rien d'autre à afficher (ex : rien à corriger)."""

    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(BackToMainPanelButton(row=0))


class ConfigOpenServerSettingsButton(discord.ui.Button):
    """Regroupe Webhooks/Liens/Invitations derrière un seul bouton, au lieu de
    les afficher tous les trois directement sur le panel principal."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Configuration serveur" if LANG == "fr" else "Server settings",
            emoji="🛠️",
            row=row,
            custom_id="config_open_server_settings",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=None,
            embed=await _build_server_settings_embed(interaction.guild),
            view=ConfigServerSettingsView(),
        )


class ConfigServerSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ConfigToggleButton(
            key="webhooks", get_fn=get_webhooks_allowed, set_fn=set_webhooks_allowed,
            label_fr="Webhooks", label_en="Webhooks", emoji="🪝", row=0,
        ))
        self.add_item(ConfigToggleButton(
            key="apps", get_fn=get_apps_allowed, set_fn=set_apps_allowed,
            label_fr="Application externe", label_en="External app", emoji="🤖", row=0,
        ))
        self.add_item(ConfigToggleButton(
            key="followers", get_fn=get_followers_allowed, set_fn=set_followers_allowed,
            label_fr="Suivis de salon", label_en="Channel follows", emoji="📡", row=0,
        ))
        self.add_item(ConfigToggleButton(
            key="links", get_fn=get_links_allowed, set_fn=set_links_allowed,
            label_fr="Liens", label_en="Links", emoji="🔗", row=0,
        ))
        self.add_item(ConfigToggleButton(
            key="invites", get_fn=get_invites_allowed, set_fn=set_invites_allowed,
            label_fr="Invitations", label_en="Invites", emoji="📨", row=0,
        ))
        self.add_item(ConfigModuleToggleButton(module_key="antispam", row=1))
        self.add_item(ConfigModuleToggleButton(module_key="messagelog", row=1))
        self.add_item(ConfigModuleToggleButton(module_key="serverlog", row=1))
        self.add_item(ConfigOpenAntinukeSettingsButton(row=2))
        self.add_item(ConfigOpenSettingsModalButton(
            keys=["spam_message_count", "spam_window_seconds", "spam_timeout_minutes"],
            title_fr="Réglages anti-spam", title_en="Anti-spam settings",
            label_fr="Régler l'anti-spam", label_en="Configure anti-spam",
            emoji="🚫", row=2,
        ))
        self.add_item(ConfigOpenMessageLogChannelButton(row=2))
        self.add_item(ConfigOpenServerLogChannelButton(row=2))
        self.add_item(ConfigOpenSettingsModalButton(
            keys=["min_account_age_hours"],
            title_fr="Âge minimum des comptes", title_en="Minimum account age",
            label_fr="Âge minimum des comptes", label_en="Min. account age",
            emoji="🐣", row=3,
        ))
        self.add_item(ConfigOpenVerificationSettingsButton(row=3))
        self.add_item(ConfigOpenHoneypotSettingsButton(row=3))
        self.add_item(RefreshPanelButton(row=3, target="server"))
        self.add_item(BackToMainPanelButton(row=3, target="main"))


VERIFICATION_METHOD_CHOICES = {
    "dm": {"fr": "Vérification MP CAPTCHA", "en": "DM CAPTCHA verification"},
    "channel": {"fr": "Vérification serveur CAPTCHA", "en": "Server CAPTCHA verification"},
    "link": {"fr": "Vérification lien (IP/VPN)", "en": "Link verification (IP/VPN)"},
}

VERIFICATION_TIMEOUT_CHOICES_MINUTES = (5, 10, 15)
VERIFICATION_CAPTCHA_ATTEMPTS_CHOICES = (2, 3, 5)
VERIFICATION_DIFFICULTY_LABELS_FR = {"easy": "Facile 🟢", "medium": "Moyen 🟡", "hard": "Difficile 🔴"}
VERIFICATION_DIFFICULTY_LABELS_EN = {"easy": "Easy 🟢", "medium": "Medium 🟡", "hard": "Hard 🔴"}


def _format_verification_timeout(minutes) -> str:
    if not minutes:
        return "infini" if LANG == "fr" else "infinite"
    return f"{minutes} minutes"


def _build_verification_method_text(guild: discord.Guild) -> str:
    """Texte du sous-panel de la méthode ACTUELLEMENT configurée (MP / Serveur
    / Lien) — voir _build_verification_method_view() pour la vue associée."""
    method = _get_setting(guild.id, "verification_method")
    enabled = _module_enabled(guild.id, "verification")
    status = (
        ("✅ Activé" if enabled else "❌ Désactivé") if LANG == "fr"
        else ("✅ Enabled" if enabled else "❌ Disabled")
    )
    method_label = VERIFICATION_METHOD_CHOICES.get(method, VERIFICATION_METHOD_CHOICES["channel"])
    header = (
        f"🧩 **{method_label['fr']}**\n\n• État : {status}\n" if LANG == "fr"
        else f"🧩 **{method_label['en']}**\n\n• Status: {status}\n"
    )

    if method == "link":
        channel_id = _get_setting(guild.id, "verification_link_channel_id")
        channel = guild.get_channel(channel_id) if channel_id else None
        timeout = _get_setting(guild.id, "verification_link_timeout_minutes")
        provider_label_fr = {
            "free": "ip-api.com + liste de fournisseurs connus (gratuit)",
            "paid": "proxycheck.io (fournisseur choisi)",
            "cloudflare": "Cloudflare — API Intelligence IP (fournisseur choisi)",
        }.get(VPN_PROVIDER_MODE, "ip-api.com + liste de fournisseurs connus (gratuit)")
        provider_label_en = {
            "free": "ip-api.com + known-provider list (free)",
            "paid": "proxycheck.io (chosen provider)",
            "cloudflare": "Cloudflare — IP Intelligence API (chosen provider)",
        }.get(VPN_PROVIDER_MODE, "ip-api.com + known-provider list (free)")
        if LANG == "fr":
            body = (
                f"• Salon unique de vérification : {channel.mention if channel else '*non défini*'}\n"
                f"• Délai avant exclusion : **{_format_verification_timeout(timeout)}**\n\n"
                "Ce salon est visible UNIQUEMENT par les membres non vérifiés. Utilise « Publier le message "
                "de vérification » ci-dessous après avoir choisi/changé le salon (ou pour republier si le "
                "message a été supprimé par erreur).\n\n"
                "🔗 Nécessite `VERIFY_PUBLIC_BASE_URL` dans `bot_config.json`, côté hébergeur du bot. "
                f"Détection VPN/proxy : {provider_label_fr}."
            )
        else:
            body = (
                f"• Single verification channel: {channel.mention if channel else '*not set*'}\n"
                f"• Timeout before exclusion: **{_format_verification_timeout(timeout)}**\n\n"
                "This channel is visible ONLY to unverified members. Use \"Publish verification message\" "
                "below after choosing/changing the channel (or to republish if the message was deleted by "
                "mistake).\n\n"
                "🔗 Needs `VERIFY_PUBLIC_BASE_URL` in `bot_config.json` on the bot host. "
                f"VPN/proxy detection: {provider_label_en}."
            )
    else:
        difficulty = _get_setting(guild.id, "verification_difficulty")
        diff_label = (VERIFICATION_DIFFICULTY_LABELS_FR if LANG == "fr" else VERIFICATION_DIFFICULTY_LABELS_EN).get(difficulty, difficulty)
        attempts = _get_setting(guild.id, "verification_captcha_max_attempts")
        if method == "channel":
            category_id = _get_setting(guild.id, "verification_channel_category_id")
            category = guild.get_channel(category_id) if category_id else None
            timeout = _get_setting(guild.id, "verification_channel_timeout_minutes")
            place_line = (
                f"• Catégorie des salons privés (un salon créé par personne, supprimé à la réussite, au "
                f"délai ou après {attempts} essais ratés) : {category.mention if category else '*non définie*'}\n"
                if LANG == "fr" else
                f"• Private channels category (one channel per person, deleted on success, timeout, or "
                f"after {attempts} failed attempts): {category.mention if category else '*not set*'}\n"
            )
        else:
            timeout = _get_setting(guild.id, "verification_dm_timeout_minutes")
            place_line = ""
        if LANG == "fr":
            body = (
                place_line +
                f"• Difficulté : {diff_label}\n"
                f"• Essais CAPTCHA max avant exclusion immédiate : **{attempts}**\n"
                f"• Délai avant exclusion : **{_format_verification_timeout(timeout)}**"
            )
        else:
            body = (
                place_line +
                f"• Difficulty: {diff_label}\n"
                f"• Max CAPTCHA attempts before immediate exclusion: **{attempts}**\n"
                f"• Timeout before exclusion: **{_format_verification_timeout(timeout)}**"
            )

    role_id = _get_setting(guild.id, "verification_role_id")
    role = guild.get_role(role_id) if role_id else None
    remove_ids = _get_setting(guild.id, "verification_remove_role_ids")
    remove_mentions = [r.mention for rid in remove_ids if (r := guild.get_role(rid))]
    if LANG == "fr":
        roles_line = (
            f"\n\n• Rôle donné à la réussite : {role.mention if role else '*aucun*'}\n"
            f"• Rôle(s) retiré(s) à la réussite : {', '.join(remove_mentions) if remove_mentions else '*aucun*'}\n"
            "(réglable via le bouton « Rôles » ci-dessous)"
        )
    else:
        roles_line = (
            f"\n\n• Role granted on success: {role.mention if role else '*none*'}\n"
            f"• Role(s) removed on success: {', '.join(remove_mentions) if remove_mentions else '*none*'}\n"
            "(set via the \"Roles\" button below)"
        )
    return header + body + roles_line


def _build_verification_method_picker_text(guild: discord.Guild) -> str:
    return "🧩 **Choisis une méthode de vérification**" if LANG == "fr" else "🧩 **Pick a verification method**"


def _build_verification_roles_text(guild: discord.Guild) -> str:
    role_id = _get_setting(guild.id, "verification_role_id")
    role = guild.get_role(role_id) if role_id else None
    unverified_id = _get_setting(guild.id, "verification_unverified_role_id")
    unverified_role = guild.get_role(unverified_id) if unverified_id else None
    remove_ids = _get_setting(guild.id, "verification_remove_role_ids")
    remove_mentions = [r.mention for rid in remove_ids if (r := guild.get_role(rid))]
    if LANG == "fr":
        return (
            "🎭 **Rôles de vérification**\n\n"
            f"• Rôle Non vérifié (auto, masque les salons non privés) : "
            f"{unverified_role.mention if unverified_role else '*sera créé à l’activation*'}\n"
            f"• Rôle donné à la réussite : {role.mention if role else '*aucun*'}\n"
            f"• Rôle(s) retiré(s) à la réussite : {', '.join(remove_mentions) if remove_mentions else '*aucun*'}\n\n"
            "À l'activation, le bot crée automatiquement ces rôles s'ils n'existent pas et masque tous les "
            "salons textuels/vocaux non privés au rôle Non vérifié. Le bouton 🔄 relance ce paramétrage "
            "manuellement (utile après avoir créé de nouveaux salons)."
        )
    return (
        "🎭 **Verification roles**\n\n"
        f"• Unverified role (auto, hides non-private channels): "
        f"{unverified_role.mention if unverified_role else '*created on activation*'}\n"
        f"• Role granted on success: {role.mention if role else '*none*'}\n"
        f"• Role(s) removed on success: {', '.join(remove_mentions) if remove_mentions else '*none*'}\n\n"
        "On activation, the bot auto-creates these roles if missing and hides every non-private text/voice "
        "channel from the unverified role. The 🔄 button re-runs this setup manually (useful after creating "
        "new channels)."
    )


def _build_verification_method_view(guild: discord.Guild) -> discord.ui.View:
    method = _get_setting(guild.id, "verification_method")
    if method == "link":
        return ConfigVerificationLinkView(guild)
    elif method == "dm":
        return ConfigVerificationDmView(guild)
    else:
        return ConfigVerificationServerView(guild)


async def _refresh_verification_method_panel(interaction: discord.Interaction) -> None:
    """Refresh dédié pour le toggle du module 'verification' : reste sur le
    sous-panel de la méthode actuellement configurée (MP / Serveur / Lien)."""
    await interaction.response.edit_message(
        content=_build_verification_method_text(interaction.guild),
        embed=None,
        view=_build_verification_method_view(interaction.guild),
    )


class VerificationMethodSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        current = _get_setting(guild.id, "verification_method")
        options = [
            discord.SelectOption(
                label=(choice["fr"] if LANG == "fr" else choice["en"])[:100],
                value=key, default=(key == current),
            )
            for key, choice in VERIFICATION_METHOD_CHOICES.items()
        ]
        super().__init__(
            placeholder="Méthode de vérification" if LANG == "fr" else "Verification method",
            options=options, min_values=1, max_values=1, row=0,
            custom_id="config_verification_method",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        _set_setting(interaction.guild.id, "verification_method", self.values[0])
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            content=_build_verification_method_text(interaction.guild),
            embed=None,
            view=_build_verification_method_view(interaction.guild),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class ConfigVerificationMethodPickerView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.add_item(VerificationMethodSelect(guild))


class CancelVerificationMethodButton(discord.ui.Button):
    """« Annuler » : ramène au sélecteur de méthode pour en choisir une autre.
    DÉSACTIVÉ tant que le module vérification est activé (il faut d'abord le
    désactiver, via le bouton juste à côté, pour changer de méthode — évite
    de casser une vérification en cours pour quelqu'un)."""

    def __init__(self, row: int, guild: discord.Guild):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Annuler" if LANG == "fr" else "Cancel",
            emoji="🔁", row=row,
            custom_id="config_verification_cancel",
            disabled=_module_enabled(guild.id, "verification"),
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=_build_verification_method_picker_text(interaction.guild),
            embed=None,
            view=ConfigVerificationMethodPickerView(interaction.guild),
        )


class VerificationDifficultySelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild, row: int):
        current = _get_setting(guild.id, "verification_difficulty")
        options = [
            discord.SelectOption(label="Facile" if LANG == "fr" else "Easy", value="easy", emoji="🟢", default=(current == "easy")),
            discord.SelectOption(label="Moyen" if LANG == "fr" else "Medium", value="medium", emoji="🟡", default=(current == "medium")),
            discord.SelectOption(label="Difficile" if LANG == "fr" else "Hard", value="hard", emoji="🔴", default=(current == "hard")),
        ]
        super().__init__(
            placeholder="Niveau de difficulté" if LANG == "fr" else "Difficulty level",
            options=options, min_values=1, max_values=1, row=row,
            custom_id="config_verification_difficulty",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        _set_setting(interaction.guild.id, "verification_difficulty", self.values[0])
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            content=_build_verification_method_text(interaction.guild),
            embed=None,
            view=_build_verification_method_view(interaction.guild),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class VerificationCaptchaAttemptsSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild, row: int):
        current = _get_setting(guild.id, "verification_captcha_max_attempts")
        options = [
            discord.SelectOption(
                label=(f"{n} essais" if LANG == "fr" else f"{n} attempts"),
                value=str(n), default=(n == current),
            )
            for n in VERIFICATION_CAPTCHA_ATTEMPTS_CHOICES
        ]
        super().__init__(
            placeholder="Essais CAPTCHA max avant exclusion" if LANG == "fr" else "Max CAPTCHA attempts before exclusion",
            options=options, min_values=1, max_values=1, row=row,
            custom_id="config_verification_captcha_attempts",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        _set_setting(interaction.guild.id, "verification_captcha_max_attempts", int(self.values[0]))
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            content=_build_verification_method_text(interaction.guild),
            embed=None,
            view=_build_verification_method_view(interaction.guild),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class _VerificationTimeoutSelectBase(discord.ui.Select):
    """Base commune aux 3 sélecteurs de délai (MP / serveur / lien) : mêmes
    options (5/10/15 minutes ou infini), seuls le réglage stocké, le
    placeholder et la ligne changent."""

    setting_key: str = ""
    placeholder_fr: str = ""
    placeholder_en: str = ""

    def __init__(self, guild: discord.Guild, row: int):
        current = _get_setting(guild.id, self.setting_key)
        options = [
            discord.SelectOption(label=f"{m} minutes", value=str(m), default=(m == current))
            for m in VERIFICATION_TIMEOUT_CHOICES_MINUTES
        ] + [
            discord.SelectOption(
                label="Infini (pas d'exclusion auto)" if LANG == "fr" else "Infinite (no auto-exclusion)",
                value="infinite",
                default=(not current),
            )
        ]
        super().__init__(
            placeholder=(self.placeholder_fr if LANG == "fr" else self.placeholder_en),
            options=options, min_values=1, max_values=1, row=row,
            custom_id=f"config_{self.setting_key}",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        raw = self.values[0]
        value = 0 if raw == "infinite" else int(raw)
        _set_setting(interaction.guild.id, self.setting_key, value)
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            content=_build_verification_method_text(interaction.guild),
            embed=None,
            view=_build_verification_method_view(interaction.guild),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class VerificationDmTimeoutSelect(_VerificationTimeoutSelectBase):
    setting_key = "verification_dm_timeout_minutes"
    placeholder_fr = "Délai avant exclusion"
    placeholder_en = "Timeout before exclusion"

    def __init__(self, guild: discord.Guild):
        super().__init__(guild, row=2)


class VerificationChannelTimeoutSelect(_VerificationTimeoutSelectBase):
    setting_key = "verification_channel_timeout_minutes"
    placeholder_fr = "Délai avant exclusion"
    placeholder_en = "Timeout before exclusion"

    def __init__(self, guild: discord.Guild):
        super().__init__(guild, row=3)


class VerificationLinkTimeoutSelect(_VerificationTimeoutSelectBase):
    setting_key = "verification_link_timeout_minutes"
    placeholder_fr = "Délai avant exclusion"
    placeholder_en = "Timeout before exclusion"

    def __init__(self, guild: discord.Guild):
        super().__init__(guild, row=1)


class VerificationCategorySelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder=(
                "Catégorie des salons privés" if LANG == "fr" else "Private channels category"
            ),
            min_values=1, max_values=1, channel_types=[discord.ChannelType.category], row=0,
            custom_id="config_verification_category_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        category = self.values[0]
        _set_setting(interaction.guild.id, "verification_channel_category_id", category.id)
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            content=_build_verification_method_text(interaction.guild),
            embed=None,
            view=_build_verification_method_view(interaction.guild),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class VerificationLinkChannelSelect(discord.ui.ChannelSelect):
    """UN SEUL salon (pas une catégorie) — méthode « Lien » uniquement : c'est
    le salon unique que TOUS les membres non vérifiés voient, où le bouton
    « Se vérifier » est publié (voir ConfigPublishVerificationLinkButton)."""

    def __init__(self):
        super().__init__(
            placeholder=(
                "Salon visible par tout le monde pour la vérification" if LANG == "fr"
                else "Channel visible to everyone for verification"
            ),
            min_values=1, max_values=1, channel_types=[discord.ChannelType.text], row=0,
            custom_id="config_verification_link_channel_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        channel = self.values[0]
        _set_setting(interaction.guild.id, "verification_link_channel_id", channel.id)
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            content=_build_verification_method_text(interaction.guild),
            embed=None,
            view=_build_verification_method_view(interaction.guild),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


VERIFY_LINK_PUBLIC_BUTTON_CUSTOM_ID = "verify_link_public_request_button"


def _build_verification_link_public_embed(guild: discord.Guild) -> discord.Embed:
    if LANG == "fr":
        embed = discord.Embed(
            title="🔗 Vérification requise",
            description=(
                "Clique sur le bouton ci-dessous : tu recevras un lien personnel (visible de toi "
                "seul(e)) qui contrôle rapidement ton adresse IP avant de débloquer ton accès au reste "
                "du serveur."
            ),
            color=discord.Color.blurple(),
        )
    else:
        embed = discord.Embed(
            title="🔗 Verification required",
            description=(
                "Click the button below: you'll get a personal link (visible to you only) that quickly "
                "checks your IP address before unlocking the rest of the server for you."
            ),
            color=discord.Color.blurple(),
        )
    return embed


class VerificationLinkPublicButton(discord.ui.Button):
    """Bouton PERSISTANT (même custom_id pour tout le monde, sur tous les
    serveurs) posté une fois dans le salon unique de vérification par lien.
    Chaque clic ne concerne QUE la personne qui clique (réponse éphémère) :
    pas besoin d'avoir les MP ouverts."""

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Se vérifier" if LANG == "fr" else "Verify",
            emoji="🔗",
            custom_id=VERIFY_LINK_PUBLIC_BUTTON_CUSTOM_ID,
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            return
        if not _module_enabled(guild.id, "verification") or _get_setting(guild.id, "verification_method") != "link":
            await interaction.response.send_message(
                "❌ La vérification par lien n'est pas active sur ce serveur." if LANG == "fr"
                else "❌ Link verification isn't active on this server.",
                ephemeral=True,
            )
            return
        role_id = _get_setting(guild.id, "verification_role_id")
        role = guild.get_role(role_id) if role_id else None
        if role is not None and role in member.roles:
            await interaction.response.send_message(
                "✅ Tu es déjà vérifié(e) !" if LANG == "fr" else "✅ You're already verified!",
                ephemeral=True,
            )
            return
        if not VERIFY_PUBLIC_BASE_URL:
            await interaction.response.send_message(
                "❌ Vérification indisponible pour le moment (configuration serveur incomplète, "
                "contacte un(e) administrateur/administratrice)." if LANG == "fr" else
                "❌ Verification unavailable right now (incomplete server-side setup, contact an admin).",
                ephemeral=True,
            )
            return
        minutes = _get_setting(guild.id, "verification_link_timeout_minutes")
        token = _new_verification_link_token(guild.id, member.id, minutes or 15)
        url = f"{VERIFY_PUBLIC_BASE_URL}/verify/{token}"
        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link, url=url,
            label="Cliquer ici pour se vérifier" if LANG == "fr" else "Click here to verify",
        ))
        text = (
            "🔗 Voici ton lien personnel — il contrôle que ton adresse IP n'est pas déjà connue pour poser "
            "problème (VPN, exclusions répétées) avant de débloquer ton accès." if LANG == "fr" else
            "🔗 Here's your personal link — it checks that your IP address isn't already known to be an "
            "issue (VPN, repeated exclusions) before unlocking your access."
        )
        await interaction.response.send_message(text, view=link_view, ephemeral=True)


class VerificationLinkPublicView(discord.ui.View):
    """Vue persistante (timeout=None) enregistrée UNE FOIS au démarrage du bot
    (voir on_ready). Fonctionne pour tous les serveurs à la fois grâce au
    custom_id fixe du bouton."""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerificationLinkPublicButton())


class ConfigPublishVerificationLinkButton(discord.ui.Button):
    """Action manuelle admin : publie (poste un nouveau message) le panneau
    « Se vérifier » dans le salon configuré, et (re)verrouille ses
    permissions (visible uniquement par le rôle Non vérifié). À utiliser
    après avoir choisi/changé le salon, ou pour republier si le message a
    été supprimé par erreur."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Envoyer le message" if LANG == "fr" else "Send the message",
            emoji="📨", row=row,
            custom_id="config_verification_publish_link",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        channel_id = _get_setting(guild.id, "verification_link_channel_id")
        channel = guild.get_channel(channel_id) if channel_id else None
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Choisis d'abord un salon (menu déroulant juste au-dessus)." if LANG == "fr"
                else "❌ Pick a channel first (dropdown right above).",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            verified_role, unverified_role = await _ensure_verification_roles(guild)
            await channel.set_permissions(
                guild.default_role, view_channel=False, send_messages=False,
                reason="Vérification par lien : salon réservé aux membres non vérifiés",
            )
            await channel.set_permissions(
                unverified_role, view_channel=True, send_messages=False, read_message_history=True,
                reason="Vérification par lien : salon visible tant que non vérifié",
            )
            if guild.me is not None:
                await channel.set_permissions(
                    guild.me, view_channel=True, send_messages=True, manage_messages=True,
                    reason="Vérification par lien : accès du bot au salon",
                )
            await channel.send(
                embed=_build_verification_link_public_embed(guild),
                view=VerificationLinkPublicView(),
            )
            saved = await save_guild_config(guild)
            await interaction.followup.send(
                f"✅ Message publié dans {channel.mention}." if LANG == "fr"
                else f"✅ Message published in {channel.mention}.",
                ephemeral=True,
            )
            if not saved:
                await _toggle_not_saved_notice(interaction)
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Permissions insuffisantes (Gérer les salons + Gérer les rôles + Envoyer des messages)."
                if LANG == "fr" else
                "❌ Missing permissions (Manage Channels + Manage Roles + Send Messages).",
                ephemeral=True,
            )
        except Exception:
            log.exception(f"Vérification par lien : échec de la publication sur {guild.name}.")
            await interaction.followup.send(
                "❌ Une erreur est survenue pendant la publication." if LANG == "fr"
                else "❌ An error occurred while publishing.",
                ephemeral=True,
            )


class VerificationRoleGrantSelect(discord.ui.RoleSelect):
    def __init__(self, guild: discord.Guild):
        current_id = _get_setting(guild.id, "verification_role_id")
        current_role = guild.get_role(current_id) if current_id else None
        super().__init__(
            placeholder="Rôle donné à la réussite (vide = aucun)" if LANG == "fr" else "Role granted on success (empty = none)",
            min_values=0, max_values=1, row=0,
            custom_id="config_verification_role_grant",
            default_values=[current_role] if current_role else [],
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        role = self.values[0] if self.values else None
        _set_setting(interaction.guild.id, "verification_role_id", role.id if role else 0)
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            content=_build_verification_roles_text(interaction.guild),
            embed=None,
            view=ConfigVerificationRolesView(interaction.guild),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class VerificationRolesRemoveSelect(discord.ui.RoleSelect):
    def __init__(self, guild: discord.Guild):
        current_ids = _get_setting(guild.id, "verification_remove_role_ids")
        current_roles = [r for rid in current_ids if (r := guild.get_role(rid))]
        super().__init__(
            placeholder="Rôle(s) retiré(s) à la réussite (optionnel)" if LANG == "fr" else "Role(s) removed on success (optional)",
            min_values=0, max_values=25, row=1,
            custom_id="config_verification_roles_remove",
            default_values=current_roles,
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        _set_setting(interaction.guild.id, "verification_remove_role_ids", [r.id for r in self.values])
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            content=_build_verification_roles_text(interaction.guild),
            embed=None,
            view=ConfigVerificationRolesView(interaction.guild),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class VerificationResyncButton(discord.ui.Button):
    """Relance manuellement l'auto-configuration (rôles + permissions des
    salons) — utile après la création de nouveaux salons, ou si les rôles ont
    été supprimés/renommés entre-temps. Ne fait rien sur les salons déjà
    privés (ni sur le salon unique du lien, configuré à part)."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Configurer rapidement les salons" if LANG == "fr" else "Quickly configure channels",
            emoji="🔄",
            row=row,
            custom_id="config_verification_resync",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            verified_role, unverified_role, updated = await _auto_setup_verification(guild)
            saved = await save_guild_config(guild)
            summary = (
                f"✅ {updated} salon(s) mis à jour. Rôles : {verified_role.mention} / {unverified_role.mention}."
                if LANG == "fr"
                else f"✅ {updated} channel(s) updated. Roles: {verified_role.mention} / {unverified_role.mention}."
            )
            await interaction.followup.send(summary, ephemeral=True)
            if not saved:
                await _toggle_not_saved_notice(interaction)
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Permissions insuffisantes (il faut Gérer les rôles + Gérer les salons)." if LANG == "fr"
                else "❌ Missing permissions (needs Manage Roles + Manage Channels).",
                ephemeral=True,
            )
        except Exception:
            log.exception(f"Vérification : échec du resync manuel sur {guild.name}.")
            await interaction.followup.send(
                "❌ Une erreur est survenue pendant le paramétrage." if LANG == "fr" else "❌ An error occurred during setup.",
                ephemeral=True,
            )


class BackFromVerificationRolesButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Retour" if LANG == "fr" else "Back",
            emoji="↩️", row=row,
            custom_id="config_verification_roles_back",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=_build_verification_method_text(interaction.guild),
            embed=None,
            view=_build_verification_method_view(interaction.guild),
        )


class ConfigVerificationRolesView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.add_item(VerificationRoleGrantSelect(guild))
        self.add_item(VerificationRolesRemoveSelect(guild))
        self.add_item(VerificationResyncButton(row=2))
        self.add_item(BackFromVerificationRolesButton(row=2))


class ConfigOpenVerificationRolesButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Rôles" if LANG == "fr" else "Roles",
            emoji="🎭", row=row,
            custom_id="config_verification_open_roles",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=_build_verification_roles_text(interaction.guild),
            embed=None,
            view=ConfigVerificationRolesView(interaction.guild),
        )


class ConfigVerificationDmView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.add_item(VerificationDifficultySelect(guild, row=0))
        self.add_item(VerificationCaptchaAttemptsSelect(guild, row=1))
        self.add_item(VerificationDmTimeoutSelect(guild))
        self.add_item(ConfigModuleToggleButton(module_key="verification", row=3, refresh=_refresh_verification_method_panel))
        self.add_item(ConfigOpenVerificationRolesButton(row=3))
        self.add_item(CancelVerificationMethodButton(row=3, guild=guild))
        self.add_item(BackToMainPanelButton(row=3, target="server"))


class ConfigVerificationServerView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.add_item(VerificationCategorySelect())
        self.add_item(VerificationDifficultySelect(guild, row=1))
        self.add_item(VerificationCaptchaAttemptsSelect(guild, row=2))
        self.add_item(VerificationChannelTimeoutSelect(guild))
        self.add_item(ConfigModuleToggleButton(module_key="verification", row=4, refresh=_refresh_verification_method_panel))
        self.add_item(ConfigOpenVerificationRolesButton(row=4))
        self.add_item(CancelVerificationMethodButton(row=4, guild=guild))
        self.add_item(BackToMainPanelButton(row=4, target="server"))


class ConfigVerificationLinkView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.add_item(VerificationLinkChannelSelect())
        self.add_item(VerificationLinkTimeoutSelect(guild))
        self.add_item(ConfigPublishVerificationLinkButton(row=2))
        self.add_item(ConfigModuleToggleButton(module_key="verification", row=2, refresh=_refresh_verification_method_panel))
        self.add_item(ConfigOpenVerificationRolesButton(row=2))
        self.add_item(CancelVerificationMethodButton(row=2, guild=guild))
        self.add_item(BackToMainPanelButton(row=2, target="server"))


class ConfigOpenVerificationSettingsButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Vérification" if LANG == "fr" else "Verification",
            emoji="🧩",
            row=row,
            custom_id="config_open_verification_settings",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=_build_verification_method_text(interaction.guild),
            embed=None,
            view=_build_verification_method_view(interaction.guild),
        )


def _build_honeypot_settings_text(guild: discord.Guild) -> str:
    enabled = _module_enabled(guild.id, "honeypot")
    channel_id = _get_setting(guild.id, "honeypot_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    sanction_type = _get_setting(guild.id, "honeypot_sanction_type")
    sanction_label = HONEYPOT_SANCTION_CHOICES.get(sanction_type, HONEYPOT_SANCTION_CHOICES["mute"])
    mute_minutes = _get_setting(guild.id, "honeypot_mute_minutes")
    lookback_hours = _get_setting(guild.id, "honeypot_delete_lookback_hours")
    warning_text = _get_setting(guild.id, "honeypot_warning_text")
    global_catch_count = _get_honeypot_global_catch_count()

    if LANG == "fr":
        return (
            "🍯 **Salon piège** — accessible et inscriptible par TOUT LE MONDE, y compris les membres "
            "non vérifiés. Liens, images et textes autorisés par défaut. Toute personne qui y écrit est "
            "automatiquement sanctionnée, et tous ses messages récents sur le serveur sont supprimés.\n\n"
            f"• État : {'✅ Activé' if enabled else '❌ Désactivé'}\n"
            f"• Salon : {channel.mention if channel else '*aucun — clique sur Créer/recréer le salon*'}\n"
            f"• Sanction : {sanction_label['fr']}"
            f"{f' ({mute_minutes} min)' if sanction_type == 'mute' else ''}\n"
            f"• Purge des messages de l'auteur : dernières {lookback_hours}h, sur tout le serveur\n"
            f"• Texte de l'image d'avertissement : « {warning_text} »\n\n"
            f"📊 **{global_catch_count}** personne(s) piégée(s) au total, sur TOUS les serveurs où ce bot "
            "est (ou a été) présent — compteur global, jamais remis à zéro."
        )
    return (
        "🍯 **Honeypot channel** — visible and writable by EVERYONE, including unverified members. "
        "Links, images and text are allowed by default. Anyone who writes there is automatically "
        "sanctioned, and all their recent messages on the server are deleted.\n\n"
        f"• Status: {'✅ Enabled' if enabled else '❌ Disabled'}\n"
        f"• Channel: {channel.mention if channel else '*none — click Create/recreate channel*'}\n"
        f"• Sanction: {sanction_label['en']}"
        f"{f' ({mute_minutes} min)' if sanction_type == 'mute' else ''}\n"
        f"• Author's message purge: last {lookback_hours}h, server-wide\n"
        f"• Warning image text: \"{warning_text}\"\n\n"
        f"📊 **{global_catch_count}** total people caught across ALL servers this bot is (or has been) "
        "in — global counter, never reset."
    )


class HoneypotSanctionSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        current = _get_setting(guild.id, "honeypot_sanction_type")
        options = [
            discord.SelectOption(
                label=(choice["fr"] if LANG == "fr" else choice["en"])[:100],
                value=key,
                default=(key == current),
            )
            for key, choice in HONEYPOT_SANCTION_CHOICES.items()
        ]
        super().__init__(
            placeholder="Sanction appliquée" if LANG == "fr" else "Sanction applied",
            options=options, min_values=1, max_values=1, row=1,
            custom_id="config_honeypot_sanction",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        _set_setting(interaction.guild.id, "honeypot_sanction_type", self.values[0])
        saved = await save_guild_config(interaction.guild)
        await interaction.response.edit_message(
            content=_build_honeypot_settings_text(interaction.guild),
            view=ConfigHoneypotSettingsView(interaction.guild),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class HoneypotSettingsModal(discord.ui.Modal):
    """Durée de la sourdine, fenêtre de purge et texte de l'image
    d'avertissement — 3 réglages qui ne rentrent pas dans SettingsGroupModal
    (celui-ci ne gère que du numérique) à cause du champ texte libre."""

    def __init__(self, guild: discord.Guild):
        super().__init__(title="Réglages du salon piège" if LANG == "fr" else "Honeypot channel settings", timeout=300)
        self.guild_id = guild.id
        self.mute_input = discord.ui.TextInput(
            label=(CONFIG_META["honeypot_mute_minutes"]["fr"] if LANG == "fr" else CONFIG_META["honeypot_mute_minutes"]["en"])[:45],
            default=str(_get_setting(guild.id, "honeypot_mute_minutes")),
            required=True, max_length=6,
        )
        self.lookback_input = discord.ui.TextInput(
            label=(CONFIG_META["honeypot_delete_lookback_hours"]["fr"] if LANG == "fr" else CONFIG_META["honeypot_delete_lookback_hours"]["en"])[:45],
            default=str(_get_setting(guild.id, "honeypot_delete_lookback_hours")),
            required=True, max_length=4,
        )
        self.warning_input = discord.ui.TextInput(
            label="Texte de l'image d'avertissement" if LANG == "fr" else "Warning image text",
            default=_get_setting(guild.id, "honeypot_warning_text"),
            style=discord.TextStyle.paragraph, required=True, max_length=200,
        )
        self.add_item(self.mute_input)
        self.add_item(self.lookback_input)
        self.add_item(self.warning_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        errors = []
        mute_val, err = _validate_setting_input("honeypot_mute_minutes", self.mute_input.value)
        if err:
            errors.append(f"**{'Durée de sourdine' if LANG == 'fr' else 'Timeout duration'}** : {err}")
        lookback_val, err = _validate_setting_input("honeypot_delete_lookback_hours", self.lookback_input.value)
        if err:
            errors.append(f"**{'Fenêtre de purge' if LANG == 'fr' else 'Purge window'}** : {err}")
        warning_text = self.warning_input.value.strip()
        if not warning_text:
            errors.append(
                "❌ Le texte de l'avertissement ne peut pas être vide." if LANG == "fr"
                else "❌ The warning text can't be empty."
            )

        if errors:
            await interaction.response.send_message("\n".join(errors)[:2000], ephemeral=True)
            return

        if mute_val is not None:
            _set_setting(guild.id, "honeypot_mute_minutes", mute_val)
        if lookback_val is not None:
            _set_setting(guild.id, "honeypot_delete_lookback_hours", lookback_val)
        _set_setting(guild.id, "honeypot_warning_text", warning_text)
        saved = await save_guild_config(guild)

        channel_id = _get_setting(guild.id, "honeypot_channel_id")
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is not None and isinstance(channel, discord.TextChannel):
            await _send_honeypot_warning_image(guild, channel)

        text = "✅ Réglages mis à jour." if LANG == "fr" else "✅ Settings updated."
        if not saved:
            text += "\n\n⚠️ " + (
                "Non enregistré (serveur base de données indisponible) : perdu au redémarrage."
                if LANG == "fr" else "Not saved (database server unavailable): lost on restart."
            )
        await interaction.response.send_message(text, ephemeral=True)


class HoneypotOpenSettingsModalButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Durée / fenêtre / texte" if LANG == "fr" else "Duration / window / text",
            emoji="⚙️",
            row=row,
            custom_id="config_honeypot_open_modal",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.send_modal(HoneypotSettingsModal(interaction.guild))


class HoneypotCreateChannelButton(discord.ui.Button):
    """Crée le salon piège s'il n'existe pas encore, ou le resynchronise
    (permissions + nouvelle image) s'il existe déjà."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Créer / recréer le salon" if LANG == "fr" else "Create / recreate channel",
            emoji="🍯",
            row=row,
            custom_id="config_honeypot_create_channel",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            channel = await _setup_honeypot_channel(guild)
            saved = await save_guild_config(guild)
            summary = (
                f"✅ Salon piège prêt : {channel.mention}." if LANG == "fr"
                else f"✅ Honeypot channel ready: {channel.mention}."
            )
            await interaction.followup.send(summary, ephemeral=True)
            if not saved:
                await _toggle_not_saved_notice(interaction)
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Permissions insuffisantes (il faut Gérer les salons)." if LANG == "fr"
                else "❌ Missing permissions (needs Manage Channels).",
                ephemeral=True,
            )
        except Exception:
            log.exception(f"Salon piège : échec de la création/resynchronisation sur {guild.name}.")
            await interaction.followup.send(
                "❌ Une erreur est survenue pendant la création du salon." if LANG == "fr"
                else "❌ An error occurred while creating the channel.",
                ephemeral=True,
            )


class HoneypotResendImageButton(discord.ui.Button):
    """Renvoie (et épingle) l'image d'avertissement du salon piège à la
    demande — utile si elle a été supprimée par erreur (ou volontairement),
    sans avoir à recréer tout le salon. Le bot vérifie aussi automatiquement,
    en tâche de fond, qu'elle est toujours présente, et la renvoie tout seul
    si elle a disparu (voir _honeypot_watchdog_loop)."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Renvoyer l'image" if LANG == "fr" else "Resend image",
            emoji="🔁",
            row=row,
            custom_id="config_honeypot_resend_image",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        channel_id = _get_setting(guild.id, "honeypot_channel_id")
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Aucun salon piège n'existe encore — clique d'abord sur « Créer / recréer le salon »."
                if LANG == "fr"
                else "❌ No honeypot channel exists yet — click « Create / recreate channel » first.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        msg = await _send_honeypot_warning_image(guild, channel)
        saved = await save_guild_config(guild)
        if msg is not None:
            await interaction.followup.send(
                f"✅ Image renvoyée et épinglée dans {channel.mention}." if LANG == "fr"
                else f"✅ Image resent and pinned in {channel.mention}.",
                ephemeral=True,
            )
            if not saved:
                await _toggle_not_saved_notice(interaction)
        else:
            await interaction.followup.send(
                "❌ Échec de l'envoi de l'image (permissions insuffisantes ?)." if LANG == "fr"
                else "❌ Failed to send the image (missing permissions?).",
                ephemeral=True,
            )


class ConfigHoneypotSettingsView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.add_item(ConfigModuleToggleButton(module_key="honeypot", row=0, refresh=_refresh_honeypot_settings_panel))
        self.add_item(HoneypotCreateChannelButton(row=0))
        self.add_item(HoneypotOpenSettingsModalButton(row=0))
        self.add_item(HoneypotResendImageButton(row=0))
        self.add_item(HoneypotSanctionSelect(guild))
        self.add_item(BackToMainPanelButton(row=4, target="server"))


class ConfigOpenHoneypotSettingsButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Salon piège" if LANG == "fr" else "Honeypot channel",
            emoji="🍯",
            row=row,
            custom_id="config_open_honeypot_settings",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=_build_honeypot_settings_text(interaction.guild),
            embed=None,
            view=ConfigHoneypotSettingsView(interaction.guild),
        )


class ConfigOpenStaffSettingsButton(discord.ui.Button):
    """Regroupe Rôles staff/Salon des demandes derrière un seul bouton, au lieu
    de les afficher tous les deux directement sur le panel principal."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Configuration staff" if LANG == "fr" else "Staff settings",
            emoji="👮",
            row=row,
            custom_id="config_open_staff_settings",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=None,
            embed=_build_staff_settings_embed(interaction.guild),
            view=ConfigStaffSettingsView(),
        )


class ConfigFreezeTicketsToggleButton(discord.ui.Button):
    """Bouton on/off des tickets de gel (ajoute/retire le bouton du salon des gelés)."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Tickets de gel" if LANG == "fr" else "Freeze tickets",
            emoji="🎫", row=row, custom_id="config_toggle_freeze_tickets",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        await interaction.response.defer()
        current = bool(_get_setting(guild.id, "freeze_tickets_enabled"))
        saved = await _set_freeze_tickets_enabled(guild, not current)
        await interaction.edit_original_response(
            content=None, embed=_build_staff_settings_embed(guild), view=ConfigStaffSettingsView(),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class FreezePingRolesSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="🎫 Rôles mentionnés dans les tickets de gel…" if LANG == "fr" else "🎫 Roles pinged in freeze tickets…",
            min_values=0, max_values=10, row=0, custom_id="config_freeze_ping_roles",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        _set_setting(guild.id, "freeze_ticket_ping_role_ids", [r.id for r in self.values])
        saved = await save_guild_config(guild)
        await interaction.response.edit_message(
            content=_freeze_tickets_status_text(guild), embed=None, view=FreezePingRolesPanelView(),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class FreezePingRolesPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(FreezePingRolesSelect())
        self.add_item(BackToMainPanelButton(row=1, target="staff"))


class ConfigOpenFreezePingRolesButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Rôles mentionnés (tickets de gel)" if LANG == "fr" else "Pinged roles (freeze tickets)",
            emoji="🔔", row=row, custom_id="config_open_freeze_ping_roles",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=_freeze_tickets_status_text(interaction.guild), embed=None, view=FreezePingRolesPanelView(),
        )


def _freeze_access_status_text(guild: discord.Guild) -> str:
    roles = " ".join(
        f"<@&{rid}>" for rid in (_get_setting(guild.id, "freeze_allowed_role_ids") or []) if guild.get_role(rid)
    ) or ("*aucun*" if LANG == "fr" else "*none*")
    users = " ".join(f"<@{uid}>" for uid in (_get_setting(guild.id, "freeze_allowed_user_ids") or [])) \
        or ("*aucun*" if LANG == "fr" else "*none*")
    if LANG == "fr":
        return f"Administrateurs + rôles : {roles}\nMembres : {users}"
    return f"Administrators + roles: {roles}\nMembers: {users}"


class FreezeAccessRolesSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="🥶 Rôles autorisés à utiliser /gel…" if LANG == "fr" else "🥶 Roles allowed to use /freeze…",
            min_values=0, max_values=10, row=0, custom_id="config_freeze_access_roles",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        _set_setting(guild.id, "freeze_allowed_role_ids", [r.id for r in self.values])
        saved = await save_guild_config(guild)
        await interaction.response.edit_message(
            content=_freeze_access_status_text(guild), embed=None, view=FreezeAccessPanelView(),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class FreezeAccessUsersSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(
            placeholder="👤 Membres autorisés à utiliser /gel…" if LANG == "fr" else "👤 Members allowed to use /freeze…",
            min_values=0, max_values=10, row=1, custom_id="config_freeze_access_users",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        _set_setting(guild.id, "freeze_allowed_user_ids", [u.id for u in self.values if not u.bot])
        saved = await save_guild_config(guild)
        await interaction.response.edit_message(
            content=_freeze_access_status_text(guild), embed=None, view=FreezeAccessPanelView(),
        )
        if not saved:
            await _toggle_not_saved_notice(interaction)


class FreezeAccessPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(FreezeAccessRolesSelect())
        self.add_item(FreezeAccessUsersSelect())
        self.add_item(BackToMainPanelButton(row=2, target="staff"))


class ConfigOpenFreezeAccessButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Accès /gel" if LANG == "fr" else "/freeze access",
            emoji="🥶", row=row, custom_id="config_open_freeze_access",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=_freeze_access_status_text(interaction.guild), embed=None, view=FreezeAccessPanelView(),
        )


class ConfigStaffSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ConfigOpenFounderRoleButton(row=0))
        self.add_item(ConfigOpenSanctionChannelButton(row=0))
        self.add_item(ConfigModRequestToggleButton(row=0))
        self.add_item(ConfigFreezeTicketsToggleButton(row=1))
        self.add_item(ConfigOpenFreezePingRolesButton(row=1))
        self.add_item(ConfigOpenFreezeAccessButton(row=1))
        self.add_item(BackToMainPanelButton(row=2, target="main"))



import unicodedata

HB_GHOST_MAX_GUILD_SIZE = 20000
HB_RECENT_DAYS = 7
HB_MAX_SELECT = 25
HB_MAX_LISTED = 10

_HB_INVISIBLE_CHARS = frozenset("\u2800\u3164\u115f\u1160\uffa0\u180e\u034f\u17b4\u17b5")

_HB_FLAG_WEIGHTS = {
    "invisible_name": 2,
    "no_channel": 2,
    "ghost": 3,
    "commands_only": 1,
    "orphan_role": 1,
}

_HB_FLAG_LABELS = {
    "invisible_name": ("nom affiché invisible", "invisible display name"),
    "no_channel": (
        "ne voit aucun salon (absent de la liste des membres)",
        "sees no channel (missing from the member list)",
    ),
    "ghost": (
        "présent côté API mais absent du cache du bot",
        "present via the API but missing from the bot's cache",
    ),
    "commands_only": (
        "application installée sans membre bot (commandes seulement)",
        "app installed without a bot member (commands only)",
    ),
    "orphan_role": (
        "rôle de bot orphelin (bot introuvable)",
        "orphan bot role (bot not found)",
    ),
}


def _hb(fr: str, en: str) -> str:
    return fr if LANG == "fr" else en


def _is_invisible_text(text) -> bool:
    """True si le texte est vide ou ne contient que des caractères invisibles
    (espaces, contrôle/format, marques sans caractère de base, Braille vide,
    Hangul filler...)."""
    if text is None:
        return True
    text = str(text)
    if not text.strip():
        return True
    for ch in text:
        if ch in _HB_INVISIBLE_CHARS:
            continue
        if unicodedata.category(ch) in ("Cf", "Cc", "Zs", "Zl", "Zp", "Mn", "Me"):
            continue
        return False
    return True


def _hb_risk(score: int) -> tuple[str, str]:
    if score >= 5:
        return "🔴", _hb("Risque élevé", "High risk")
    if score >= 3:
        return "🟠", _hb("Risque moyen", "Medium risk")
    return "🟡", _hb("Risque faible", "Low risk")


def _hb_display_name(s: dict) -> str:
    name = s.get("name")
    if _is_invisible_text(name):
        return _hb("[nom invisible]", "[invisible name]")
    return discord.utils.escape_markdown(str(name))[:60]


def _hb_dangerous_perms(member: discord.Member) -> list[str]:
    perms = member.guild_permissions
    if perms.administrator:
        return ["administrator"]
    return [k for k in DANGEROUS_BOT_PERM_KEYS if getattr(perms, k, False)]


def _hb_can_see_any_channel(guild: discord.Guild, member: discord.Member) -> bool:
    for ch in guild.channels:
        if isinstance(ch, discord.CategoryChannel):
            continue
        try:
            if ch.permissions_for(member).view_channel:
                return True
        except Exception:
            continue
    return False


def _hb_kick_blocker(guild: discord.Guild, member: discord.Member, actor=None):
    """Retourne None si le membre peut être expulsé, sinon la raison du blocage."""
    if member.id == guild.owner_id:
        return _hb("propriétaire du serveur", "server owner")
    if actor is not None and member.id == actor.id:
        return _hb("toi-même", "yourself")
    if not guild.me.guild_permissions.kick_members:
        return _hb("permission « Expulser des membres » manquante pour le bot", "bot lacks “Kick Members”")
    if member.top_role >= guild.me.top_role:
        return _hb("rôle supérieur ou égal à celui du bot", "role equal to or above the bot's")
    if actor is not None and actor.id != guild.owner_id and member.top_role >= actor.top_role:
        return _hb("rôle supérieur ou égal au tien", "role equal to or above yours")
    return None


async def _scan_hidden_accounts(guild: discord.Guild, actor: discord.Member = None) -> tuple[list[dict], dict]:
    """Analyse le serveur et retourne (suspects triés par risque, statistiques).
    Ne modifie rien sur le serveur."""
    now = discord.utils.utcnow()
    notes: list[str] = []

    bot_add_info: dict[int, tuple] = {}
    try:
        async for entry in guild.audit_logs(limit=100, action=discord.AuditLogAction.bot_add):
            target_id = getattr(entry.target, "id", None)
            if target_id is not None and target_id not in bot_add_info:
                bot_add_info[target_id] = (entry.user, entry.created_at)
    except discord.Forbidden:
        notes.append(_hb(
            "Permission « Voir les logs d'audit » manquante : impossible de savoir qui a ajouté chaque bot.",
            "Missing “View Audit Log” permission: can't tell who added each bot.",
        ))
    except Exception:
        log.exception(f"Lecture de l'audit log impossible (analyse bots invisibles) sur {guild.name}.")

    integrations: dict[int, object] = {}
    commands_only: dict[int, object] = {}
    bot_integration_cls = getattr(discord, "BotIntegration", None)
    try:
        for integ in await guild.integrations():
            if bot_integration_cls is None or not isinstance(integ, bot_integration_cls):
                continue
            app = integ.application
            bot_user = getattr(app, "user", None)
            bid = bot_user.id if bot_user is not None else app.id
            integrations[bid] = integ
            if "bot" not in (getattr(integ, "scopes", None) or []):
                commands_only[bid] = integ
    except discord.Forbidden:
        notes.append(_hb(
            "Permission « Gérer le serveur » manquante : intégrations non analysées.",
            "Missing “Manage Server” permission: integrations were not analysed.",
        ))
    except Exception:
        log.exception(f"Lecture des intégrations impossible (analyse bots invisibles) sur {guild.name}.")

    role_of_bot: dict[int, discord.Role] = {}
    for role in guild.roles:
        tags = getattr(role, "tags", None)
        if role.managed and tags is not None and getattr(tags, "bot_id", None):
            role_of_bot[tags.bot_id] = role

    members: dict[int, discord.Member] = {m.id: m for m in guild.members}
    ghost_ids: set[int] = set()
    not_found_ids: set[int] = set()

    candidate_bot_ids = set(role_of_bot) | set(integrations) | set(bot_add_info)
    for bid in candidate_bot_ids:
        if bid in members:
            continue
        try:
            members[bid] = await guild.fetch_member(bid)
            ghost_ids.add(bid)
        except discord.NotFound:
            not_found_ids.add(bid)
        except discord.HTTPException:
            continue

    if guild.member_count and guild.member_count > len(guild.members):
        if guild.member_count <= HB_GHOST_MAX_GUILD_SIZE:
            try:
                async for m in guild.fetch_members(limit=None):
                    if m.id not in members:
                        members[m.id] = m
                        ghost_ids.add(m.id)
            except Exception:
                log.exception(f"Recoupement REST des membres impossible sur {guild.name}.")
        else:
            notes.append(_hb(
                f"Serveur trop grand (> {HB_GHOST_MAX_GUILD_SIZE} membres) : recoupement complet du cache ignoré.",
                f"Server too large (> {HB_GHOST_MAX_GUILD_SIZE} members): full cache cross-check skipped.",
            ))

    suspects: dict[int, dict] = {}
    me_id = guild.me.id if guild.me else None

    def _new(user_id: int, name, is_bot: bool) -> dict:
        s = {
            "id": user_id, "name": name, "is_bot": is_bot, "verified": False,
            "member": None, "flags": [], "perms": [], "added_by": None, "added_at": None,
            "integration": integrations.get(user_id), "blocker": None,
            "actionable": False, "score": 0,
        }
        suspects[user_id] = s
        return s

    for m in members.values():
        if m.id == me_id:
            continue
        flags = []
        if _is_invisible_text(m.display_name):
            flags.append("invisible_name")
        if m.bot and not _hb_can_see_any_channel(guild, m):
            flags.append("no_channel")
        if m.id in ghost_ids:
            flags.append("ghost")
        if not flags:
            continue
        if _is_whitelisted(guild.id, m):
            continue

        s = _new(m.id, m.display_name, m.bot)
        s["member"] = m
        s["flags"] = flags
        s["verified"] = bool(m.bot and m.public_flags.verified_bot)
        s["perms"] = _hb_dangerous_perms(m) if m.bot else []

    for bid, integ in commands_only.items():
        if bid in members or bid in suspects:
            continue
        s = _new(bid, getattr(integ.application, "name", None), True)
        s["flags"] = ["commands_only"]
    for bid, role in role_of_bot.items():
        if bid in members or bid in suspects or bid in commands_only:
            continue
        if bid in not_found_ids:
            s = _new(bid, role.name, True)
            s["flags"] = ["orphan_role"]

    for s in suspects.values():
        info = bot_add_info.get(s["id"])
        if info is not None:
            adder, added_at = info
            s["added_by"] = str(adder) if adder is not None else None
            s["added_at"] = added_at
        elif s["member"] is not None and s["member"].joined_at is not None:
            s["added_at"] = s["member"].joined_at

        score = sum(_HB_FLAG_WEIGHTS[f] for f in s["flags"])
        if "administrator" in s["perms"]:
            score += 3
        elif s["perms"]:
            score += 2
        if s["added_at"] is not None and (now - s["added_at"]) <= timedelta(days=HB_RECENT_DAYS):
            score += 1
        s["score"] = score

        if s["member"] is not None:
            s["blocker"] = _hb_kick_blocker(guild, s["member"], actor)
        s["actionable"] = (s["member"] is not None and s["blocker"] is None) or s["integration"] is not None

    result = sorted(suspects.values(), key=lambda x: (-x["score"], str(x["name"] or "")))
    stats = {
        "members": len(members),
        "bots": sum(1 for m in members.values() if m.bot),
        "notes": notes,
    }
    return result, stats


async def _hb_remove_account(guild: discord.Guild, actor: discord.Member, s: dict, reason: str) -> tuple[bool, str]:
    """Expulse le compte ; si l'expulsion directe est impossible et qu'une
    intégration existe, tente de supprimer l'intégration (Discord expulse alors
    le bot associé). Retourne (succès, détail)."""
    reason = reason[:480]
    member = s.get("member")
    blocker = None

    if member is not None:
        blocker = _hb_kick_blocker(guild, member, actor)
        if blocker is None:
            try:
                await guild.kick(member, reason=reason)
                return True, _hb("expulsé", "kicked")
            except discord.Forbidden:
                blocker = _hb("refusé par Discord (permissions/hiérarchie)", "refused by Discord (permissions/hierarchy)")
            except Exception as e:
                blocker = _hb(f"erreur Discord ({e})", f"Discord error ({e})")

    integ = s.get("integration")
    if integ is not None:
        try:
            await integ.delete(reason=reason)
            return True, _hb("intégration supprimée (bot retiré)", "integration deleted (bot removed)")
        except discord.Forbidden:
            return False, blocker or _hb("suppression de l'intégration refusée", "integration deletion refused")
        except Exception as e:
            return False, blocker or _hb(f"erreur Discord ({e})", f"Discord error ({e})")

    return False, blocker or _hb("compte introuvable sur le serveur", "account not found on the server")


def _build_hidden_scan_embed(guild: discord.Guild, suspects: list[dict], stats: dict) -> discord.Embed:
    if not suspects:
        embed = discord.Embed(
            title=_hb("✅ Aucun compte ou bot invisible détecté", "✅ No hidden account or bot detected"),
            description=_hb(
                "Aucun nom invisible, aucun bot sans accès aux salons, aucun membre fantôme, "
                "aucune application ou rôle de bot orphelin.",
                "No invisible name, no bot without channel access, no ghost member, "
                "no orphan app or bot role.",
            ),
            color=0x57F287,
        )
    else:
        high = sum(1 for s in suspects if s["score"] >= 5)
        embed = discord.Embed(
            title=_hb(
                f"🕵️ {len(suspects)} compte(s)/bot(s) suspect(s)",
                f"🕵️ {len(suspects)} suspicious account(s)/bot(s)",
            ),
            color=0xED4245 if high else 0xFEE75C,
        )
        blocks = []
        for s in suspects[:HB_MAX_LISTED]:
            emoji, label = _hb_risk(s["score"])
            kind = "🤖" if s["is_bot"] else "👤"
            reasons = ", ".join(_hb(*_HB_FLAG_LABELS[f]) for f in s["flags"])
            block = f"{emoji} {kind} **{_hb_display_name(s)}** (`{s['id']}`) — {label}\n↳ {reasons}"
            if s["is_bot"] and s["verified"]:
                block += _hb("\n↳ ✅ Bot certifié (peut quand même être compromis)", "\n↳ ✅ Verified bot (can still be compromised)")
            if s["perms"]:
                block += _hb("\n↳ Permissions sensibles : ", "\n↳ Sensitive permissions: ") + ", ".join(
                    f"`{p}`" for p in s["perms"][:6]
                )
            if s["added_at"]:
                when = discord.utils.format_dt(s["added_at"], "R")
                if s["added_by"]:
                    block += _hb(f"\n↳ Ajouté par {s['added_by']} — {when}", f"\n↳ Added by {s['added_by']} — {when}")
                else:
                    block += _hb(f"\n↳ Arrivé sur le serveur {when}", f"\n↳ Joined the server {when}")
            if not s["actionable"]:
                block += "\n↳ ⚠️ " + (
                    _hb(f"Action manuelle nécessaire ({s['blocker']})", f"Manual action needed ({s['blocker']})")
                    if s["blocker"]
                    else _hb(
                        "Aucune action automatique possible — à vérifier à la main (Paramètres du serveur > Intégrations / Rôles)",
                        "No automatic action possible — check manually (Server Settings > Integrations / Roles)",
                    )
                )
            elif s["blocker"] and s["integration"] is not None:
                block += _hb(
                    f"\n↳ Expulsion directe impossible ({s['blocker']}) : suppression via l'intégration tentée.",
                    f"\n↳ Direct kick impossible ({s['blocker']}): integration removal will be tried.",
                )
            blocks.append(block)
        if len(suspects) > HB_MAX_LISTED:
            blocks.append(_hb(
                f"… et {len(suspects) - HB_MAX_LISTED} autre(s) suspect(s) moins prioritaire(s).",
                f"… and {len(suspects) - HB_MAX_LISTED} more lower-priority suspect(s).",
            ))
        embed.description = "\n\n".join(blocks)[:4000]

    if stats["notes"]:
        embed.add_field(
            name=_hb("Limites de l'analyse", "Scan limits"),
            value="\n".join(f"• {n}" for n in stats["notes"])[:1000],
            inline=False,
        )
    embed.set_footer(text=_hb(
        f"{stats['members']} comptes analysés dont {stats['bots']} bot(s)",
        f"{stats['members']} accounts analysed, {stats['bots']} bot(s)",
    ))
    return embed


def _hb_build_scan_message(author_id: int, guild: discord.Guild, suspects: list[dict], stats: dict) -> dict:
    kwargs = {"embed": _build_hidden_scan_embed(guild, suspects, stats)}
    if suspects:
        kwargs["view"] = HiddenScanResultView(author_id, suspects)
    return kwargs


async def _hb_send_scan(interaction: discord.Interaction) -> None:
    """Lance l'analyse et répond en message éphémère (interaction déjà différée)."""
    suspects, stats = await _scan_hidden_accounts(interaction.guild, interaction.user)
    await interaction.followup.send(
        ephemeral=True,
        **_hb_build_scan_message(interaction.user.id, interaction.guild, suspects, stats),
    )


class HiddenScanSelect(discord.ui.Select):
    def __init__(self, suspects: list[dict]):
        options = []
        for s in suspects[:HB_MAX_SELECT]:
            reasons = ", ".join(_hb(*_HB_FLAG_LABELS[f]) for f in s["flags"])
            options.append(discord.SelectOption(
                label=f"{_hb_display_name(s)} ({s['id']})"[:100],
                value=str(s["id"]),
                description=f"{_hb_risk(s['score'])[0]} {reasons}"[:100],
                emoji="🤖" if s["is_bot"] else "👤",
            ))
        super().__init__(
            placeholder=_hb("Choisis les comptes à expulser…", "Choose the accounts to remove…"),
            min_values=1,
            max_values=len(options),
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected = [int(v) for v in self.values]
        await interaction.response.defer()


class HiddenScanConfirmView(discord.ui.View):
    def __init__(self, author_id: int, chosen: list[dict]):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.chosen = chosen

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id or not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return False
        return True

    @discord.ui.button(label=_hb("Confirmer l'expulsion", "Confirm removal"), style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=_hb("⏳ Expulsion en cours…", "⏳ Removing…"), view=None)
        guild = interaction.guild
        reason = f"[{interaction.user}] " + _hb(
            "Compte/bot invisible détecté par l'analyse de sécurité",
            "Hidden account/bot flagged by the security scan",
        )
        lines = []
        for s in self.chosen:
            ok, detail = await _hb_remove_account(guild, interaction.user, s, reason)
            lines.append(f"{'✅' if ok else '❌'} **{_hb_display_name(s)}** (`{s['id']}`) — {detail}")
            if ok:
                log.info(f"[bots invisibles] {s['id']} retiré de {guild.name} par {interaction.user} ({detail}).")
            else:
                log.warning(f"[bots invisibles] échec pour {s['id']} sur {guild.name} : {detail}")

        summary = "\n".join(lines)
        if len(summary) > 1900:
            summary = summary[:1899] + "…"
        await interaction.edit_original_response(content=summary, view=None)

        await _log_security_event(
            guild,
            (
                f"🕵️ {interaction.user.mention} a lancé l'expulsion de comptes/bots invisibles :\n"
                if LANG == "fr"
                else f"🕵️ {interaction.user.mention} removed hidden accounts/bots:\n"
            ) + summary[:1500],
        )

    @discord.ui.button(label=_hb("Annuler", "Cancel"), style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=_hb("Annulé.", "Cancelled."), view=None)


class HiddenScanResultView(discord.ui.View):
    def __init__(self, author_id: int, suspects: list[dict]):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.suspects = {s["id"]: s for s in suspects}
        self.selected: list[int] = []
        actionable = [s for s in suspects if s["actionable"]]
        if actionable:
            self.add_item(HiddenScanSelect(actionable))
        else:
            self.kick_selection.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id or not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return False
        return True

    @discord.ui.button(label=_hb("Expulser la sélection", "Remove selection"), style=discord.ButtonStyle.danger, emoji="🥾", row=1)
    async def kick_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        chosen = [self.suspects[i] for i in self.selected if i in self.suspects]
        if not chosen:
            await interaction.response.send_message(
                _hb("Sélectionne d'abord au moins un compte dans le menu.", "Select at least one account in the menu first."),
                ephemeral=True,
            )
            return
        names = ", ".join(f"**{_hb_display_name(s)}**" for s in chosen[:10])
        extra = f" (+{len(chosen) - 10})" if len(chosen) > 10 else ""
        await interaction.response.send_message(
            _hb(
                f"⚠️ Confirmer l'expulsion de {len(chosen)} compte(s) : {names}{extra} ?",
                f"⚠️ Confirm removal of {len(chosen)} account(s): {names}{extra}?",
            ),
            view=HiddenScanConfirmView(self.author_id, chosen),
            ephemeral=True,
        )

    @discord.ui.button(label=_hb("Relancer l'analyse", "Re-scan"), style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def rescan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        suspects, stats = await _scan_hidden_accounts(interaction.guild, interaction.user)
        message = _hb_build_scan_message(interaction.user.id, interaction.guild, suspects, stats)
        await interaction.edit_original_response(embed=message["embed"], view=message.get("view"))


class ConfigHiddenBotsButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label=_hb("Détecter les bots invisibles", "Detect hidden bots"),
            emoji="🕵️",
            row=row,
            custom_id="config_scan_hidden_bots",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        await _hb_send_scan(interaction)


@bot.tree.command(
    name="bots-invisibles" if LANG == "fr" else "hidden-bots",
    description=(
        "Détecte (et permet d'expulser) les comptes/bots invisibles ou cachés de la liste des membres"
        if LANG == "fr"
        else "Detect (and remove) accounts/bots hidden from the member list"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def hidden_bots_command(interaction: discord.Interaction):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    await _hb_send_scan(interaction)


class ConfigPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ConfigOpenServerSettingsButton(row=0))
        self.add_item(ConfigOpenStaffSettingsButton(row=0))
        self.add_item(ConfigOpenWhitelistButton(row=0))
        self.add_item(ConfigOpenWordFilterButton(row=0))
        self.add_item(ConfigAuditButton(row=1))
        self.add_item(ConfigHiddenBotsButton(row=1))
        self.add_item(ConfigQuickSetupButton(row=1))


@bot.tree.command(
    name="panel",
    description=(
        "Panel unique de configuration du bot sur ce serveur (webhooks, liens, rôles, liste blanche...)"
        if LANG == "fr"
        else "Single config panel for this server (webhooks, links, roles, whitelist...)"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def configuration_panel_command(interaction: discord.Interaction):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    await interaction.response.send_message(
        embed=await _build_config_panel_embed(interaction.guild),
        view=ConfigPanelView(),
        ephemeral=True,
    )


def _role_hierarchy_ok(actor: discord.Member, bot_member: discord.Member, target: discord.Member) -> bool:
    if target.id == actor.guild.owner_id:
        return False
    if actor.id != actor.guild.owner_id and target.top_role >= actor.top_role:
        return False
    if target.top_role >= bot_member.top_role:
        return False
    return True


async def _get_or_create_warning_role(guild: discord.Guild, level: int) -> discord.Role:
    name = WARNING_ROLE_NAMES[level - 1]
    role = discord.utils.get(guild.roles, name=name)
    if role is not None:
        return role
    role = await guild.create_role(
        name=name, reason="Création automatique du rôle de palier d'avertissement",
    )
    try:
        await role.edit(position=1)
    except Exception:
        log.exception(f"Impossible de placer le rôle {name} tout en bas de la hiérarchie sur {guild}.")
    return role


async def _apply_warning_role(guild: discord.Guild, member: discord.Member, level: int):
    level = max(1, min(level, len(WARNING_ROLE_NAMES)))
    target_name = WARNING_ROLE_NAMES[level - 1]
    to_remove = [r for r in member.roles if r.name in WARNING_ROLE_NAMES and r.name != target_name]
    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason="Passage au palier d'avertissement suivant")
        new_role = await _get_or_create_warning_role(guild, level)
        if new_role not in member.roles:
            await member.add_roles(new_role, reason="Nouveau palier d'avertissement atteint")
    except Exception:
        log.exception(f"Impossible d'appliquer le rôle de palier d'avertissement à {member} sur {guild}.")


@bot.tree.command(
    name="avertir" if LANG == "fr" else "warn",
    description=(
        "Envoie un avertissement à un membre (conservé dans son historique)" if LANG == "fr"
        else "Sends a warning to a member (kept in their history)"
    ),
)
@discord.app_commands.describe(
    membre="Le membre à avertir" if LANG == "fr" else "The member to warn",
    raison="Raison de l'avertissement" if LANG == "fr" else "Reason for the warning",
)
async def warn_command(interaction: discord.Interaction, membre: discord.Member, raison: str = None):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(t("no_perm_moderate"), ephemeral=True)
        return
    if not _role_hierarchy_ok(interaction.user, interaction.guild.me, membre):
        await interaction.response.send_message(t("target_too_high"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    prior_entries = await get_member_history(interaction.guild, membre)
    prior_warns_here = sum(
        1 for e in prior_entries
        if e["type"] == "warn" and e.get("guild_id") == interaction.guild.id
    )
    if prior_warns_here >= MAX_WARNINGS_BEFORE_SANCTION:
        await interaction.followup.send(WARN_LIMIT_MESSAGE, ephemeral=True)
        return

    reason = raison or t("no_reason")
    n = await _post_modlog_entry(interaction.guild, "warn", membre, str(interaction.user), reason)

    await _apply_warning_role(interaction.guild, membre, prior_warns_here + 1)

    await interaction.followup.send(t("warn_done", target=membre.mention, n=n), ephemeral=True)
    await _start_target_response_flow(interaction.guild, membre, "warn", str(interaction.user), reason)


_mod_request_last_use: dict[int, float] = {}

_MOD_REQUEST_ACTION_LABELS = {
    "mute": "🔇 Sourdine (mute)",
    "kick": "👢 Expulsion (kick)",
    "ban": "🔨 Bannissement (ban)",
    "autre": "❓ Autre sanction",
    "unmute": "🔈 Retrait de sourdine (unmute)",
    "unban": "🔓 Retrait de bannissement (unban)",
}


def _format_request_datetime() -> str:
    return discord.utils.utcnow().strftime("%d/%m/%Y %H:%M:%S UTC")


def _member_is_configured_staff(member: discord.Member) -> bool:
    """True si `member` est reconnu comme staff par le bot. Recharge d'abord
    le membre (rôles/permissions à jour) quand c'est possible — utile dans
    les commandes de modération où le cache d'objet Member peut être
    légèrement périmé. Voir _member_is_staff pour la définition exacte
    (permission Discord réelle, mute minimum)."""
    if member.guild is None:
        return False
    fresh = member.guild.get_member(member.id)
    if fresh is not None:
        member = fresh
    return _member_is_staff(member)


SANCTION_ACTION_DISCORD_PERMISSION = {
    "mute": "moderate_members",
    "kick": "kick_members",
    "ban": "ban_members",
    "unmute": "moderate_members",
    "unban": "ban_members",
}


def _print_sanction_diagnostic(member: discord.Member, action: str, context: str = "") -> None:
    """Affiche dans le terminal (et dans audit_bot.log) TOUT ce qui entre en
    compte dans la décision _can_member_direct_sanction pour `member` et
    `action`, AVANT que la décision ne soit prise. Purement informatif :
    ne change aucun comportement. Objectif : voir immédiatement, sans deviner,
    LEQUEL des critères (bot owner / server owner / administrator / rôle
    Fondateur / permission Discord précise) fait basculer le résultat."""
    fresh = member.guild.get_member(member.id) if member.guild else None
    check_member = fresh if fresh is not None else member

    is_bot_owner = _is_bot_owner(check_member.id)
    is_guild_owner = member.guild is not None and check_member.id == member.guild.owner_id
    is_admin = bool(check_member.guild_permissions.administrator)
    owner_role_id = _get_setting(member.guild.id, "owner_role_id") if member.guild else None
    owner_role = member.guild.get_role(owner_role_id) if (member.guild and owner_role_id) else None
    has_owner_role = bool(owner_role and owner_role in check_member.roles)
    perm_name = SANCTION_ACTION_DISCORD_PERMISSION.get(action)
    has_precise_perm = bool(perm_name) and getattr(check_member.guild_permissions, perm_name, False)

    role_names = ", ".join(r.name for r in check_member.roles if not r.is_default()) or "aucun"

    # Le statut "propriétaire du bot" est affiché pour information mais
    # n'entre PLUS dans le calcul du bypass de sanction (voir correctif dans
    # _can_member_direct_sanction) : il ne doit jamais, à lui seul, rendre
    # would_be_direct vrai.
    would_be_direct = is_admin or is_guild_owner or has_owner_role or has_precise_perm

    lines = [
        "=" * 70,
        f"[DIAGNOSTIC SANCTION] action='{action}' contexte='{context}'",
        f"  Membre analysé      : {check_member} (id={check_member.id})",
        f"  Rôles               : {role_names}",
        f"  1) Propriétaire du BOT (Dev Portal)     : {is_bot_owner} "
        f"(ⓘ n'accorde plus de bypass sanction depuis le correctif)",
        f"  2) Propriétaire du SERVEUR              : {is_guild_owner}",
        f"  3) Permission Administrateur (cumulée)  : {is_admin}",
        f"  4) Rôle Fondateur configuré (owner_role_id={owner_role_id}) : "
        f"{'présent -> ' + owner_role.name if owner_role else 'aucun rôle configuré'} "
        f"| membre l'a : {has_owner_role}",
        f"  5) Permission précise requise pour '{action}' : {perm_name} = {has_precise_perm}",
        f"  -> RÉSULTAT ATTENDU (_can_member_direct_sanction) : {would_be_direct}",
        "=" * 70,
    ]
    for line in lines:
        print(line, flush=True)
        log.warning(line)


def _can_member_direct_sanction(member: discord.Member, action: str) -> bool:
    """Détermine si `member` peut exécuter `action` directement, sans passer
    par le système de demande : propriétaire DU SERVEUR concerné, Administrateur
    réel sur CE serveur, ou rôle Fondateur explicitement configuré par CE
    serveur -> toujours direct, ce sont les « chefs » de ce serveur précis.
    Sinon, direct uniquement si le membre a réellement, sur ce serveur, la
    permission Discord correspondant précisément à cette action (ex : Bannir
    des membres pour /ban). Sans cette permission précise, l'action passe par
    le système de demande (si activé) ou est simplement refusée (si
    désactivé) — voir mod_request_enabled.

    IMPORTANT (correctif sécurité) : le statut « propriétaire/copropriétaire
    DU BOT » (Discord Developer Portal > Team) n'accorde PLUS de bypass ici,
    volontairement. Ce bot est installé sur des serveurs tiers indépendants
    (communautés qui ne sont pas gérées par l'équipe du bot) ; leur accorder
    automatiquement le droit de mute/kick/ban sur CHAQUE serveur où le bot est
    présent, sans la moindre permission Discord réelle là-bas, serait une
    faille de sécurité pour ces serveurs. Ce statut continue en revanche de
    donner accès aux commandes de configuration/support du bot lui-même
    (voir _has_effective_administrator), ce qui reste légitime."""
    if member.guild is None:
        return False
    fresh = member.guild.get_member(member.id)
    if fresh is not None:
        member = fresh
    if member.guild_permissions.administrator or member.id == member.guild.owner_id:
        return True
    owner_role_id = _get_setting(member.guild.id, "owner_role_id")
    if owner_role_id and any(r.id == owner_role_id for r in member.roles):
        return True
    perm_name = SANCTION_ACTION_DISCORD_PERMISSION.get(action)
    return bool(perm_name) and getattr(member.guild_permissions, perm_name, False)


def _mod_request_approver_role_ids(guild_id: int, action: str) -> set[int]:
    """Rôles à mentionner dans le salon des demandes pour une `action`
    donnée : tous les rôles du serveur qui ont réellement, eux-mêmes, la
    permission Discord correspondant précisément à cette action (ou
    Administrateur) — ce sont, concrètement, les rôles dont les membres
    pourront directement accepter cette demande (voir
    _can_member_direct_sanction). Le rôle Fondateur, s'il est configuré, est
    toujours inclus : il peut tout valider."""
    guild = bot.get_guild(guild_id)
    if guild is None:
        return set()
    perm_name = SANCTION_ACTION_DISCORD_PERMISSION.get(action)
    role_ids: set[int] = set()
    for role in guild.roles:
        if role.permissions.administrator:
            role_ids.add(role.id)
            continue
        if perm_name and getattr(role.permissions, perm_name, False):
            role_ids.add(role.id)
    owner_role_id = _get_setting(guild_id, "owner_role_id")
    if owner_role_id:
        role_ids.add(owner_role_id)
    return role_ids


async def _execute_sanction_direct(
    guild: discord.Guild,
    actor: discord.Member,
    target: discord.Member,
    action: str,
    reason: str,
    duration_minutes: int = None,
    check_actor_hierarchy: bool = True,
) -> tuple[bool, str]:
    if target.id == guild.owner_id:
        return False, "impossible d'agir sur le propriétaire du serveur"
    if target.top_role >= guild.me.top_role:
        return False, "hiérarchie de rôles insuffisante pour le bot"
    if check_actor_hierarchy and actor.id != guild.owner_id and target.top_role >= actor.top_role:
        return False, "la cible a un rôle égal ou supérieur au tien"

    try:
        full_reason = f"[{actor}] {reason}"
        if action == "mute":
            minutes = max(1, min(duration_minutes or 60, 40320))
            await target.timeout(timedelta(minutes=minutes), reason=full_reason)
        elif action == "kick":
            await target.kick(reason=full_reason)
        elif action == "ban":
            await target.ban(reason=full_reason)
    except Exception as e:
        return False, f"erreur Discord ({e})"
    return True, ""


class _StubUser:
    def __init__(self, user_id: int):
        self.id = user_id
        self.mention = f"<@{user_id}>"

    def __str__(self):
        return f"ID {self.id}"


async def _resolve_user_for_modlog(guild: discord.Guild, target_id: int):
    member = guild.get_member(target_id)
    if member is not None:
        return member
    try:
        return await bot.fetch_user(target_id)
    except Exception:
        return _StubUser(target_id)


async def _execute_unsanction_direct(
    guild: discord.Guild,
    actor: discord.Member,
    target_id: int,
    action: str,
    reason: str,
) -> tuple[bool, str]:
    full_reason = f"[{actor}] {reason}"
    if action == "unmute":
        member = guild.get_member(target_id)
        if member is None:
            try:
                member = await guild.fetch_member(target_id)
            except Exception:
                return False, "membre introuvable sur le serveur"
        try:
            await member.timeout(None, reason=full_reason)
        except Exception as e:
            return False, f"erreur Discord ({e})"
        return True, ""
    elif action == "unban":
        try:
            await guild.unban(discord.Object(id=target_id), reason=full_reason)
        except discord.NotFound:
            return False, "ce membre n'est pas banni sur ce serveur"
        except Exception as e:
            return False, f"erreur Discord ({e})"
        return True, ""
    return False, "action inconnue"


def _build_mod_request_embed(
    action: str,
    target: discord.Member,
    requester: discord.abc.User,
    reason: str,
    duration_minutes: int = None,
    status: str = None,
) -> discord.Embed:
    embed = discord.Embed(title="📋 Demande de sanction", color=discord.Color.orange())
    embed.add_field(name="Cible", value=f"{target.mention} (`{target.id}`)", inline=False)
    embed.add_field(name="Type", value=_MOD_REQUEST_ACTION_LABELS.get(action, action), inline=True)
    if action == "mute":
        embed.add_field(name="Durée", value=f"{duration_minutes} min", inline=True)
    embed.add_field(name="Raison", value=reason, inline=False)
    embed.add_field(name="Demandé par", value=f"{requester.mention} (`{requester.id}`)", inline=False)
    embed.add_field(name="Date de la demande", value=_format_request_datetime(), inline=False)
    embed.add_field(name="Statut", value=status or "⏳ En attente de validation", inline=False)
    embed.set_footer(
        text=f"action={action}|target={target.id}|requester={requester.id}|duration={duration_minutes or 0}"
    )
    return embed


def _parse_mod_request_embed(embed: discord.Embed) -> typing.Optional[dict]:
    footer = embed.footer.text if embed.footer else None
    if not footer or "action=" not in footer:
        return None
    data = {}
    for part in footer.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            data[k] = v
    try:
        return {
            "action": data.get("action"),
            "target_id": int(data.get("target", 0)),
            "requester_id": int(data.get("requester", 0)),
            "duration_minutes": int(data.get("duration", 0)) or None,
        }
    except (ValueError, TypeError):
        return None


def _mod_request_reason(embed: discord.Embed) -> str:
    for field in embed.fields:
        if field.name == "Raison":
            return field.value
    return t("no_reason")


def _mod_request_is_pending(embed: discord.Embed) -> bool:
    for field in embed.fields:
        if field.name == "Statut":
            return "En attente" in field.value
    return False


class ModRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _handle(self, interaction: discord.Interaction, approve: bool):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Action indisponible hors serveur.", ephemeral=True)
            return

        message = interaction.message
        if not message.embeds:
            await interaction.response.send_message("❌ Demande invalide (embed manquant).", ephemeral=True)
            return
        embed = message.embeds[0]

        if not _mod_request_is_pending(embed):
            await interaction.response.send_message("ℹ️ Cette demande a déjà été traitée.", ephemeral=True)
            return

        data = _parse_mod_request_embed(embed)
        if data is None:
            await interaction.response.send_message("❌ Demande invalide (données illisibles).", ephemeral=True)
            return

        action = data["action"]
        _print_sanction_diagnostic(interaction.user, action, context="validation-demande")
        if not _can_member_direct_sanction(interaction.user, action):
            await interaction.response.send_message(
                "❌ Il te faut, pour ce type de sanction précisément, la permission "
                "Discord correspondante (ou un réglage « sanction directe » sur "
                "toujours) pour valider ou refuser cette demande."
                if LANG == "fr"
                else "❌ You need, specifically for this sanction type, the matching "
                "Discord permission (or a « direct sanction » setting of always) to "
                "approve or reject this request.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        reason = _mod_request_reason(embed)
        target_id = data["target_id"]
        requester_id = data["requester_id"]
        duration_minutes = data["duration_minutes"]

        requester_member = guild.get_member(requester_id)
        requester_label = str(requester_member) if requester_member else f"ID {requester_id}"

        def _set_status_and_save(new_status: str, color: discord.Color):
            new_embed = embed.copy()
            for i, field in enumerate(new_embed.fields):
                if field.name == "Statut":
                    new_embed.set_field_at(i, name="Statut", value=new_status, inline=False)
            new_embed.color = color
            return new_embed

        if not approve:
            new_status = f"❌ Refusé par {interaction.user.mention}"
            new_embed = _set_status_and_save(new_status, discord.Color.red())
            for item in self.children:
                item.disabled = True
            await message.edit(embed=new_embed, view=self)
            log.info(
                f"Demande de sanction refusée par {interaction.user} ({interaction.user.id}) — "
                f"cible {target_id}, action {action}."
            )
            await interaction.followup.send("❌ Demande refusée.", ephemeral=True)
            return

        target = None
        if action in ("mute", "kick", "ban"):
            target = guild.get_member(target_id)
            if target is None:
                try:
                    target = await guild.fetch_member(target_id)
                except Exception:
                    target = None

        if action == "autre":
            success, failure_reason = True, ""
        elif action in ("unmute", "unban"):
            success, failure_reason = await _execute_unsanction_direct(
                guild, interaction.user, target_id, action, reason
            )
        elif target is None:
            success, failure_reason = False, "membre introuvable sur le serveur"
        else:
            success, failure_reason = await _execute_sanction_direct(
                guild, interaction.user, target, action, reason, duration_minutes,
                check_actor_hierarchy=False,
            )

        if success:
            if action in ("mute", "kick", "ban") and target is not None:
                await _post_modlog_entry(
                    guild,
                    action,
                    target,
                    requester_label,
                    reason,
                    duration_minutes=duration_minutes if action == "mute" else None,
                )
                await _start_target_response_flow(guild, target, action, requester_label, reason)
            elif action in ("unmute", "unban"):
                display_target = await _resolve_user_for_modlog(guild, target_id)
                await _post_modlog_entry(guild, action, display_target, requester_label, reason)
            new_status = f"✅ Approuvé par {interaction.user.mention} — action exécutée"
            color = discord.Color.green()
            log.info(
                f"Demande de sanction approuvée par {interaction.user} ({interaction.user.id}) — "
                f"cible {target_id}, action {action}."
            )
        else:
            new_status = f"⚠️ Approuvé par {interaction.user.mention} mais échec de l'exécution ({failure_reason})"
            color = discord.Color.gold()
            log.warning(
                f"Échec d'exécution de la demande de sanction approuvée par {interaction.user} — "
                f"cible {target_id}, action {action} : {failure_reason}"
            )

        new_embed = _set_status_and_save(new_status, color)
        for item in self.children:
            item.disabled = True
        await message.edit(embed=new_embed, view=self)
        await interaction.followup.send(
            "✅ Demande approuvée et exécutée." if success else f"⚠️ Approuvé mais échec : {failure_reason}",
            ephemeral=True,
        )

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success, custom_id="modreq_accept")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle(interaction, approve=True)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger, custom_id="modreq_refuse")
    async def refuse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle(interaction, approve=False)


async def _run_sanction_flow(
    interaction: discord.Interaction,
    membre: discord.Member,
    action: str,
    raison: str,
    duration: int | None = None,
):
    """Logique commune à /mute, /kick, /ban : exécute directement si le membre
    a la permission Discord précise pour cette action précise (ou est un
    « chef » : owner/admin/fondateur/propriétaire du bot), sinon passe par le
    système de demande (si activé, voir mod_request_enabled) ou refuse
    directement (si désactivé)."""
    _print_sanction_diagnostic(interaction.user, action, context=f"/{action}")
    can_direct = _can_member_direct_sanction(interaction.user, action)
    if not (_member_is_configured_staff(interaction.user) or can_direct):
        await interaction.response.send_message(
            "❌ Tu n'as aucune permission." if LANG == "fr" else "❌ You have no permission.",
            ephemeral=True,
        )
        return

    if membre.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Tu ne peux pas viser toi-même." if LANG == "fr" else "❌ You can't target yourself.",
            ephemeral=True,
        )
        return
    if membre.bot:
        await interaction.response.send_message(
            "❌ Impossible de viser un bot." if LANG == "fr" else "❌ You can't target a bot.",
            ephemeral=True,
        )
        return
    if membre.id == interaction.guild.owner_id:
        await interaction.response.send_message(
            "❌ Impossible de viser le propriétaire du serveur." if LANG == "fr"
            else "❌ You can't target the server owner.",
            ephemeral=True,
        )
        return

    if can_direct:
        await interaction.response.defer(ephemeral=True)
        success, failure_reason = await _execute_sanction_direct(
            interaction.guild, interaction.user, membre, action, raison, duration
        )
        if not success:
            await interaction.followup.send(
                f"❌ Action impossible : {failure_reason}" if LANG == "fr"
                else f"❌ Action failed: {failure_reason}",
                ephemeral=True,
            )
            return

        await _post_modlog_entry(
            interaction.guild, action, membre, str(interaction.user), raison,
            duration_minutes=duration if action == "mute" else None,
        )
        await interaction.followup.send(
            f"✅ Sanction « {action} » appliquée à {membre.mention}." if LANG == "fr"
            else f"✅ Sanction \"{action}\" applied to {membre.mention}.",
            ephemeral=True,
        )
        await _start_target_response_flow(interaction.guild, membre, action, str(interaction.user), raison)
        return

    mod_request_enabled = bool(_get_setting(interaction.guild.id, "mod_request_enabled"))
    if not mod_request_enabled:
        await interaction.response.send_message(
            "❌ Tu n'as aucune permission." if LANG == "fr" else "❌ You have no permission.",
            ephemeral=True,
        )
        return

    mod_request_channel_id = _get_setting(interaction.guild.id, "mod_request_channel_id")
    if not mod_request_channel_id:
        await interaction.response.send_message(
            "❌ Le système de demande de sanction n'est pas encore configuré sur ce serveur "
            "(salon des demandes à définir avec `/roles-staff`)."
            if LANG == "fr"
            else "❌ The sanction-request system isn't configured on this server yet "
            "(request channel needs to be set with `/staff-roles`).",
            ephemeral=True,
        )
        return
    approver_role_ids = _mod_request_approver_role_ids(interaction.guild.id, action)

    now = time.time()
    last_use = _mod_request_last_use.get(interaction.user.id, 0)
    if now - last_use < MOD_REQUEST_COOLDOWN_SECONDS:
        wait = int(MOD_REQUEST_COOLDOWN_SECONDS - (now - last_use))
        await interaction.response.send_message(
            f"⏱️ Attends encore {wait}s avant de faire une nouvelle demande." if LANG == "fr"
            else f"⏱️ Wait {wait}s more before making a new request.",
            ephemeral=True,
        )
        return
    _mod_request_last_use[interaction.user.id] = now

    channel = interaction.guild.get_channel(mod_request_channel_id)
    if channel is None:
        await interaction.response.send_message(
            "❌ Salon de demandes introuvable (réglage `mod_request_channel_id` invalide, "
            "reconfigure-le avec `/roles-staff`)." if LANG == "fr"
            else "❌ Request channel not found (invalid `mod_request_channel_id` setting, "
            "reconfigure it with `/staff-roles`).",
            ephemeral=True,
        )
        return

    embed = _build_mod_request_embed(action, membre, interaction.user, raison, duration_minutes=duration)
    mentions = " ".join(f"<@&{rid}>" for rid in approver_role_ids)

    try:
        await channel.send(content=mentions or None, embed=embed, view=ModRequestView())
    except Exception:
        log.exception("Échec de l'envoi de la demande de sanction dans le salon dédié.")
        await interaction.response.send_message(
            "❌ Échec de l'envoi de la demande." if LANG == "fr" else "❌ Failed to send the request.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"✅ Demande envoyée dans {channel.mention} pour validation." if LANG == "fr"
        else f"✅ Request sent to {channel.mention} for approval.",
        ephemeral=True,
    )


FREEZE_ROLE_NAME = "🥶 Gelé" if LANG == "fr" else "🥶 Frozen"
FREEZE_CATEGORY_NAME = "🥶 Zone de gel" if LANG == "fr" else "🥶 Freeze zone"
FREEZE_MESSAGE_MARKER = "AUDITBOT_FREEZE_V1"

_frozen_unfreeze_tasks: dict[tuple[int, int], "asyncio.Task"] = {}


def _frozen_members_store(guild_id: int) -> dict:
    """Retourne (et crée si besoin) le dict {str(member_id): record} des
    membres actuellement gelés pour ce serveur. Persisté comme n'importe
    quel autre réglage via save_guild_config (fichier local ou serveur de
    stockage selon STORAGE_MODE) — aucune plomberie de stockage dédiée."""
    data = _get_setting(guild_id, "frozen_members")
    if not isinstance(data, dict):
        data = {}
        _set_setting(guild_id, "frozen_members", data)
    return data


FROZEN_STORE_MESSAGE_MARKER = "AUDITBOT_FROZEN_MEMBERS_V1"


async def _get_frozen_storage_channel(guild: discord.Guild) -> "discord.TextChannel | None":
    """Renvoie le salon qui sert de stockage pour l'état de gel de CE serveur :
    le salon de configuration local en mode fichier, ou le salon de
    configuration dédié sur le serveur de stockage en mode « serveur Discord »
    (même salon que save_guild_config_db, mais un message séparé — voir
    _build_frozen_store_embed — pour ne jamais risquer de corrompre ou de
    tronquer le reste de la configuration si la liste des membres gelés
    grossit)."""
    try:
        if STORAGE_MODE == "file":
            return await get_or_create_config_channel(guild)
        db_guild = get_db_guild()
        if db_guild is None:
            return None
        return await get_or_create_db_channel(db_guild, guild, "config")
    except Exception:
        log.exception(f"Gel : impossible d'accéder/créer le salon de stockage pour {guild.name}.")
        return None


async def _find_frozen_store_message(channel: discord.TextChannel):
    try:
        async for msg in channel.history(limit=50):
            if msg.embeds and msg.embeds[0].footer and msg.embeds[0].footer.text == FROZEN_STORE_MESSAGE_MARKER:
                return msg
    except Exception:
        log.exception("Gel : impossible de relire le salon de stockage pour l'état de gel.")
    return None


def _build_frozen_store_embed(store: dict) -> discord.Embed:
    """Contrairement à la configuration générale (_build_config_embed), les
    données ne sont JAMAIS mises dans le texte de l'embed (limite de 4096
    caractères imposée par Discord, qui finirait par tronquer — et donc
    corrompre silencieusement — le JSON dès que plusieurs membres sont gelés
    en même temps). Elles sont jointes en fichier .json, sans limite de
    taille réaliste pour ce cas d'usage : c'est directement ce qui causait le
    bug où le bot « oubliait » un gel et refusait de dégeler."""
    title = "🥶 État du gel — NE PAS MODIFIER (voir fichier joint)" if LANG == "fr" else "🥶 Freeze state — DO NOT EDIT (see attached file)"
    desc = (
        f"{len(store)} membre(s) actuellement gelé(s) sur ce serveur. Les données vivent dans le "
        "fichier JSON ci-dessous — ne modifie pas ce message et ne supprime pas le fichier joint."
        if LANG == "fr" else
        f"{len(store)} member(s) currently frozen on this server. Data lives in the attached JSON "
        "file below — don't edit this message or remove the attached file."
    )
    embed = discord.Embed(title=title, description=desc, color=0x3498DB, timestamp=discord.utils.utcnow())
    embed.set_footer(text=FROZEN_STORE_MESSAGE_MARKER)
    return embed


async def _save_frozen_members(guild: discord.Guild) -> None:
    """Point d'entrée UNIQUE pour persister l'état de gel — volontairement à
    part de save_guild_config (voir _build_frozen_store_embed) pour ne
    jamais être perdu ou corrompu si la configuration générale grossit ou si
    son message est tronqué par Discord. N'échoue jamais bruyamment : au pire
    l'état reste correct en mémoire pour cette exécution, et une nouvelle
    tentative aura lieu au prochain gel/dégel."""
    store = _frozen_members_store(guild.id)
    channel = await _get_frozen_storage_channel(guild)
    if channel is None:
        log.warning(f"Gel : aucun salon de stockage disponible pour sauvegarder l'état de gel de {guild.name}.")
        return
    try:
        payload = json.dumps(store, ensure_ascii=False, indent=2).encode("utf-8")
        file = discord.File(io.BytesIO(payload), filename="frozen_members.json")
        embed = _build_frozen_store_embed(store)
        existing = await _find_frozen_store_message(channel)
        if existing is not None:
            try:
                await existing.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
        await channel.send(embed=embed, file=file)
    except Exception:
        log.exception(f"Gel : impossible d'enregistrer l'état de gel pour {guild.name}.")


async def _load_frozen_members(guild: discord.Guild) -> None:
    """Recharge l'état de gel depuis le salon de stockage en le relisant
    directement (fichier joint, jamais tronqué) plutôt qu'en se fiant
    seulement à la mémoire. Appelé au démarrage (on_ready) pour CHAQUE
    serveur, avant de reprogrammer les dégels automatiques (voir
    _restore_frozen_schedules_on_ready), pour que le bot sache toujours qui
    est gelé et depuis combien de temps — même après un redémarrage."""
    channel = await _get_frozen_storage_channel(guild)
    if channel is None:
        return
    try:
        msg = await _find_frozen_store_message(channel)
        if msg is None or not msg.attachments:
            return
        raw = await msg.attachments[0].read()
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return
        _set_setting(guild.id, "frozen_members", data)
        if data:
            log.info(f"Gel : {len(data)} membre(s) gelé(s) rechargé(s) depuis le salon de stockage pour {guild.name}.")
    except Exception:
        log.exception(
            f"Gel : impossible de relire l'état de gel pour {guild.name} — l'état déjà en mémoire "
            "(éventuellement vide) est conservé pour cette exécution."
        )


def _freeze_staff_role_ids(guild: discord.Guild) -> list[int]:
    """Rôles considérés comme staff pour l'accès au salon de gel : rôle
    Fondateur configuré + tout rôle ayant réellement la permission Discord
    Administrateur ou Modérer les membres (même logique que _member_is_staff,
    mais au niveau du rôle plutôt que du membre)."""
    owner_role_id = _get_setting(guild.id, "owner_role_id")
    role_ids = set()
    if owner_role_id:
        role_ids.add(owner_role_id)
    for role in guild.roles:
        if role.is_default():
            continue
        if role.permissions.administrator or role.permissions.moderate_members:
            role_ids.add(role.id)
    return list(role_ids)


async def get_or_create_freeze_role(guild: discord.Guild) -> discord.Role:
    """Rôle unique et réutilisé d'un gel à l'autre : aucune permission propre
    (son seul rôle est d'être visé par les surcharges de permission « caché
    partout sauf le salon dédié », posées ci-dessous)."""
    role_id = _get_setting(guild.id, "freeze_role_id")
    role = guild.get_role(role_id) if role_id else None
    if role is not None:
        return role

    role = discord.utils.get(guild.roles, name=FREEZE_ROLE_NAME)
    if role is None:
        role = await guild.create_role(
            name=FREEZE_ROLE_NAME,
            permissions=discord.Permissions.none(),
            hoist=False,
            mentionable=False,
            reason="Création automatique du rôle de gel (commande /gel)",
        )
    _set_setting(guild.id, "freeze_role_id", role.id)
    await save_guild_config(guild)
    return role


FREEZE_CHANNEL_NAME = "🥶-gelés" if LANG == "fr" else "🥶-frozen"
FREEZE_TICKET_PREFIX = "ticket-gel-" if LANG == "fr" else "freeze-ticket-"
FREEZE_GENERAL_MESSAGE_MARKER = "AUDITBOT_FREEZE_GENERAL_V1"
FREEZE_ROLE_OP_DELAY = 0.5  # 2 opérations de rôle par seconde (évite le warning/rate-limit Discord)


def _deny_all_overwrite() -> discord.PermissionOverwrite:
    """Surcharge qui REFUSE explicitement chaque permission existante (voir
    le salon, écrire, applications externes, réactions, fils, vocal…), pas
    seulement « voir le salon », pour ne dépendre d'aucun bug/héritage."""
    return discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.all())


async def _hide_from_freeze_role(channel, freeze_role: discord.Role) -> None:
    """Pose (si besoin seulement, pour éviter les appels API inutiles) une
    surcharge qui refuse TOUTES les permissions au rôle de gel sur ce salon."""
    all_bits = discord.Permissions.all().value
    allow, deny = channel.overwrites_for(freeze_role).pair()
    if allow.value == 0 and (deny.value & all_bits) == all_bits:
        return
    try:
        await channel.set_permissions(
            freeze_role, overwrite=_deny_all_overwrite(),
            reason="Gel : toutes les permissions refusées au rôle de gel",
        )
    except (discord.Forbidden, discord.HTTPException):
        log.warning(f"Gel : impossible de verrouiller {getattr(channel, 'name', channel.id)} pour le rôle de gel sur {channel.guild.name}.")


async def _apply_freeze_role_hidden_everywhere(guild: discord.Guild, freeze_role: discord.Role, skip_channel_ids: "set[int] | None" = None) -> None:
    """Refuse toutes les permissions au rôle de gel sur L'INTÉGRALITÉ des
    salons (catégories, textuels, vocaux, forums, stages…), explicitement salon
    par salon — sans compter sur l'héritage de catégorie — sauf le(s) salon(s)
    indiqué(s) (le salon général des gelés)."""
    skip = skip_channel_ids or set()
    for channel in guild.channels:
        if channel.id in skip:
            continue
        await _hide_from_freeze_role(channel, freeze_role)


def _freeze_ping_role_ids(guild: discord.Guild) -> list[int]:
    ids = _get_setting(guild.id, "freeze_ticket_ping_role_ids")
    if not isinstance(ids, list):
        return []
    return [rid for rid in ids if guild.get_role(rid) is not None]


async def get_or_create_freeze_category(guild: discord.Guild) -> discord.CategoryChannel:
    category_id = _get_setting(guild.id, "freeze_category_id")
    category = guild.get_channel(category_id) if category_id else None
    if isinstance(category, discord.CategoryChannel):
        return category

    category = discord.utils.get(guild.categories, name=FREEZE_CATEGORY_NAME)
    if category is None:
        category = await guild.create_category(
            name=FREEZE_CATEGORY_NAME,
            overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=False)},
            reason="Création automatique de la catégorie de gel",
        )
    _set_setting(guild.id, "freeze_category_id", category.id)
    await save_guild_config(guild)
    return category


def _freeze_general_overwrites(guild: discord.Guild, freeze_role: discord.Role) -> dict:
    """Salon général des gelés : visible et lisible par les gelés, mais rien
    d'autre (pas d'écriture, pas de réaction, pas d'application externe…)."""
    frozen_ow = _deny_all_overwrite()
    frozen_ow.view_channel = True
    frozen_ow.read_message_history = True
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        freeze_role: frozen_ow,
    }
    if guild.me is not None:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, embed_links=True, manage_channels=True,
            manage_messages=True, read_message_history=True,
        )
    # Salon général : visible UNIQUEMENT par les administrateurs (rôles avec la
    # permission Administrateur + rôle Fondateur) et par les gelés. Les simples
    # modérateurs n'y ont pas accès (ils passent par les tickets).
    admin_ids = {r.id for r in guild.roles if not r.is_default() and r.permissions.administrator}
    owner_role_id = _get_setting(guild.id, "owner_role_id")
    if owner_role_id:
        admin_ids.add(owner_role_id)
    for role_id in admin_ids:
        role = guild.get_role(role_id)
        if role is not None:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
            )
    return overwrites


async def get_or_create_freeze_channel(guild: discord.Guild, freeze_role: discord.Role) -> discord.TextChannel:
    """Salon UNIQUE et commun à tous les gelés (plus aucun salon par personne)."""
    channel_id = _get_setting(guild.id, "freeze_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    overwrites = _freeze_general_overwrites(guild, freeze_role)
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.edit(overwrites=overwrites, reason="Gel : resynchronisation des permissions du salon des gelés")
        except (discord.Forbidden, discord.HTTPException):
            log.warning(f"Gel : impossible de resynchroniser les permissions du salon des gelés sur {guild.name}.")
        return channel

    category = await get_or_create_freeze_category(guild)
    channel = await guild.create_text_channel(
        name=FREEZE_CHANNEL_NAME, category=category, overwrites=overwrites,
        topic="Salon commun des membres gelés." if LANG == "fr" else "Shared channel for frozen members.",
        reason="Création automatique du salon général des gelés",
    )
    _set_setting(guild.id, "freeze_channel_id", channel.id)
    await save_guild_config(guild)
    return channel


def _build_freeze_general_embed(tickets_enabled: bool) -> discord.Embed:
    if LANG == "fr":
        desc = "**Vous avez été gelé(e), vous n'avez plus accès au serveur.**"
        if tickets_enabled:
            desc += "\n\nSi besoin, ouvrez un ticket avec le bouton ci-dessous pour discuter avec la modération."
        title = "🥶 Vous êtes gelé(e)"
    else:
        desc = "**You have been frozen, you no longer have access to the server.**"
        if tickets_enabled:
            desc += "\n\nIf needed, open a ticket with the button below to talk to the moderation team."
        title = "🥶 You are frozen"
    embed = discord.Embed(title=title, description=desc, color=0x3498DB)
    embed.set_footer(text=FREEZE_GENERAL_MESSAGE_MARKER)
    return embed


async def _refresh_freeze_general_message(guild: discord.Guild) -> None:
    """Crée ou met à jour le message du salon général : avec le bouton
    « Ouvrir un ticket » si les tickets de gel sont activés, sans sinon."""
    channel_id = _get_setting(guild.id, "freeze_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    if not isinstance(channel, discord.TextChannel):
        return
    enabled = bool(_get_setting(guild.id, "freeze_tickets_enabled"))
    embed = _build_freeze_general_embed(enabled)
    view = FreezeTicketOpenView() if enabled else None
    try:
        existing = None
        async for msg in channel.history(limit=50):
            if msg.author.id == bot.user.id and msg.embeds and msg.embeds[0].footer \
                    and msg.embeds[0].footer.text == FREEZE_GENERAL_MESSAGE_MARKER:
                existing = msg
                break
        if existing is not None:
            await existing.edit(embed=embed, view=view)
        else:
            await channel.send(embed=embed, view=view)
    except (discord.Forbidden, discord.HTTPException):
        log.warning(f"Gel : impossible de mettre à jour le message du salon des gelés sur {guild.name}.")


async def _set_freeze_tickets_enabled(guild: discord.Guild, enabled: bool) -> bool:
    _set_setting(guild.id, "freeze_tickets_enabled", bool(enabled))
    saved = await save_guild_config(guild)
    await _refresh_freeze_general_message(guild)
    return saved


async def create_freeze_ticket_channel(
    guild: discord.Guild, member: discord.Member, freeze_role: discord.Role, record: dict,
) -> discord.TextChannel:
    category = await get_or_create_freeze_category(guild)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        freeze_role: _deny_all_overwrite(),
        member: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, attach_files=True,
        ),
    }
    if guild.me is not None:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, embed_links=True, manage_channels=True,
            manage_messages=True, read_message_history=True,
        )
    staff_ids = set(_freeze_staff_role_ids(guild)) | set(_freeze_ping_role_ids(guild))
    for role_id in staff_ids:
        role = guild.get_role(role_id)
        if role is not None:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
            )
    channel = await guild.create_text_channel(
        name=f"{FREEZE_TICKET_PREFIX}{member.name}"[:90], category=category, overwrites=overwrites,
        reason=f"Ticket de gel de {member}",
    )
    expires_at = datetime.fromisoformat(record["expires_at"])
    minutes = max(1, int((expires_at - datetime.fromisoformat(record["started_at"])).total_seconds() // 60))
    mod_label = f"<@{record.get('moderator_id')}>" if record.get("moderator_id") else "?"
    embed = _build_freeze_embed(guild, member.id, member.mention, mod_label, record.get("reason", ""), minutes, expires_at)
    ping_roles = [guild.get_role(rid) for rid in _freeze_ping_role_ids(guild)]
    content = member.mention + "".join(f" {r.mention}" for r in ping_roles if r is not None)
    await channel.send(
        content=content, embed=embed, view=FreezeTicketView(),
        allowed_mentions=discord.AllowedMentions(users=True, roles=True),
    )
    return channel


async def _verify_freeze_isolation(
    guild: discord.Guild, member_id: int, freeze_role: discord.Role, allowed_channel_ids: set,
) -> tuple[list[int], bool]:
    """Vérifie réellement (permissions calculées par Discord/discord.py) que le
    membre ne voit plus aucun salon hors du salon général. Si un salon reste
    visible (rôle géré non retirable, bug d'héritage…), pose une surcharge
    directe sur le MEMBRE (prioritaire sur tous les rôles) qui refuse tout.
    Retourne (ids des salons à nettoyer au dégel, isolation complète ?)."""
    await asyncio.sleep(2)  # laisse le cache refléter les changements de permissions/rôles
    try:
        member = await guild.fetch_member(member_id)
    except (discord.NotFound, discord.HTTPException):
        return [], True
    if member.guild_permissions.administrator or member.id == guild.owner_id:
        return [], False  # un rôle géré/protégé donne Administrateur : impossible à masquer
    fixed: list[int] = []
    for channel in guild.channels:
        if channel.id in allowed_channel_ids:
            continue
        if channel.permissions_for(member).view_channel:
            try:
                await channel.set_permissions(
                    member, overwrite=_deny_all_overwrite(),
                    reason="Gel : isolation forcée (salon encore visible malgré le rôle de gel)",
                )
                fixed.append(channel.id)
            except (discord.Forbidden, discord.HTTPException):
                log.warning(f"Gel : impossible de forcer l'isolation sur {channel.name} ({guild.name}).")
    if fixed:
        await asyncio.sleep(2)
    still_visible = [
        c for c in guild.channels
        if c.id not in allowed_channel_ids and c.permissions_for(member).view_channel
    ]
    return fixed, not still_visible


def _build_freeze_embed(
    guild: discord.Guild, member_id: int, member_label: str, moderator_label: str,
    reason: str, minutes: int, expires_at: "datetime",
) -> discord.Embed:
    title = "🎫 Ticket de gel — NE PAS MODIFIER CE MESSAGE" if LANG == "fr" else "🎫 Freeze ticket — DO NOT EDIT THIS MESSAGE"
    desc = (
        f"**Membre :** {member_label}\n"
        f"**Raison :** {reason}\n"
        f"**Modérateur :** {moderator_label}\n"
        f"**Durée :** {minutes} minute(s)\n"
        f"**Fin prévue :** <t:{int(expires_at.timestamp())}:F> (<t:{int(expires_at.timestamp())}:R>)\n\n"
        "Tu peux discuter ici avec l'équipe de modération."
        if LANG == "fr" else
        f"**Member:** {member_label}\n"
        f"**Reason:** {reason}\n"
        f"**Moderator:** {moderator_label}\n"
        f"**Duration:** {minutes} minute(s)\n"
        f"**Expected end:** <t:{int(expires_at.timestamp())}:F> (<t:{int(expires_at.timestamp())}:R>)\n\n"
        "Feel free to discuss here with the moderation team."
    )
    payload = {"member_id": member_id, "expires_at": expires_at.isoformat()}
    desc += "\n```json\n" + json.dumps(payload) + "\n```"
    embed = discord.Embed(title=title, description=desc[:4096], color=0x3498DB, timestamp=discord.utils.utcnow())
    embed.set_footer(text=FREEZE_MESSAGE_MARKER)
    return embed


async def _unfreeze_member(
    guild: discord.Guild, member_id: int, moderator_label: str, *, auto: bool = False,
) -> tuple[bool, str]:
    """Point d'entrée UNIQUE pour dégeler quelqu'un (bouton, /degel, ou
    expiration automatique) : restaure les rôles sauvegardés, retire le rôle
    de gel, supprime le salon dédié, nettoie l'état persistant et journalise.
    Ne plante jamais bruyamment si le membre a quitté entre-temps — dans ce
    cas on nettoie quand même l'état et le salon."""
    store = _frozen_members_store(guild.id)
    record = store.get(str(member_id))
    if record is None:
        return False, "membre non gelé" if LANG == "fr" else "member not frozen"

    task = _frozen_unfreeze_tasks.pop((guild.id, member_id), None)
    if task is not None and not task.done():
        task.cancel()

    member = guild.get_member(member_id)

    # Surcharges directes posées sur le membre pendant le gel (isolation forcée)
    for cid in record.get("member_override_channel_ids", []):
        ch = guild.get_channel(cid)
        if ch is not None and member is not None:
            try:
                await ch.set_permissions(member, overwrite=None, reason="Fin du gel : retrait de l'isolation forcée")
            except (discord.Forbidden, discord.HTTPException):
                log.warning(f"Gel : impossible de retirer l'isolation forcée sur {ch.name} ({guild.name}).")

    if member is not None:
        freeze_role = guild.get_role(_get_setting(guild.id, "freeze_role_id"))
        saved_role_ids = record.get("saved_role_ids", [])
        roles_to_restore = [guild.get_role(rid) for rid in saved_role_ids]
        roles_to_restore = [r for r in roles_to_restore if r is not None]
        reason = (
            f"Fin du gel (auto, durée écoulée)" if auto else f"Dégel par {moderator_label}"
        )
        # Restauration des rôles à 2 par seconde, puis retrait du rôle de gel.
        for role in roles_to_restore:
            try:
                await member.add_roles(role, reason=reason)
            except (discord.Forbidden, discord.HTTPException):
                log.warning(f"Gel : impossible de restaurer le rôle {role.name} de {member} sur {guild.name} (dégel).")
            await asyncio.sleep(FREEZE_ROLE_OP_DELAY)
        try:
            if freeze_role is not None and freeze_role in member.roles:
                await member.remove_roles(freeze_role, reason=reason)
        except (discord.Forbidden, discord.HTTPException):
            log.warning(f"Gel : impossible de retirer le rôle de gel de {member} sur {guild.name} (dégel).")

    # Ticket éventuel (le salon général des gelés, lui, est conservé)
    channel_id = record.get("channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel is not None and channel.id != _get_setting(guild.id, "freeze_channel_id"):
        try:
            await channel.delete(reason="Fin du gel : suppression du ticket")
        except (discord.Forbidden, discord.HTTPException):
            log.warning(f"Gel : impossible de supprimer le ticket sur {guild.name}.")

    store.pop(str(member_id), None)
    _set_setting(guild.id, "frozen_members", store)
    await _save_frozen_members(guild)

    display_target = member or await _resolve_user_for_modlog(guild, member_id)
    await _post_modlog_entry(
        guild, "degel", display_target,
        (_hb("Automatique (durée écoulée)", "Automatic (duration elapsed)") if auto else moderator_label),
        record.get("reason", ""),
    )
    return True, ""


async def _force_unfreeze_member(guild: discord.Guild, member_id: int, moderator_label: str) -> tuple[bool, str]:
    """Filet de secours pour /ungel : si un enregistrement de gel valide
    existe encore, se comporte exactement comme _unfreeze_member (restauration
    complète des rôles). Sinon — enregistrement manquant ou corrompu, par
    exemple à cause d'une donnée de stockage perdue ou supprimée par erreur —
    dégèle quand même « au mieux » : retire le rôle de gel s'il est présent
    et supprime tout salon de gel résiduel visiblement lié à ce membre, sans
    jamais bloquer sous prétexte que l'état stocké est introuvable."""
    store = _frozen_members_store(guild.id)
    if str(member_id) in store:
        return await _unfreeze_member(guild, member_id, moderator_label)

    task = _frozen_unfreeze_tasks.pop((guild.id, member_id), None)
    if task is not None and not task.done():
        task.cancel()

    member = guild.get_member(member_id)
    did_something = False

    freeze_role_id = _get_setting(guild.id, "freeze_role_id")
    freeze_role = guild.get_role(freeze_role_id) if freeze_role_id else None
    if member is not None and freeze_role is not None and freeze_role in member.roles:
        try:
            await member.remove_roles(freeze_role, reason=f"Dégel forcé par {moderator_label} (aucune donnée de gel trouvée)")
            did_something = True
        except (discord.Forbidden, discord.HTTPException):
            log.warning(f"Gel : dégel forcé — impossible de retirer le rôle de gel de {member} sur {guild.name}.")

    category_id = _get_setting(guild.id, "freeze_category_id")
    category = guild.get_channel(category_id) if category_id else None
    if isinstance(category, discord.CategoryChannel) and member is not None:
        base_name = "gel" if LANG == "fr" else "freeze"
        prefixes = (
            f"{FREEZE_TICKET_PREFIX}{member.name}"[:90].lower(),
            f"{base_name}-{member.name}"[:90].lower(),  # ancien format (salon par personne)
        )
        general_id = _get_setting(guild.id, "freeze_channel_id")
        for channel in list(category.text_channels):
            if channel.id != general_id and channel.name.lower().startswith(prefixes):
                try:
                    await channel.delete(reason=f"Dégel forcé par {moderator_label} : nettoyage du salon résiduel")
                    did_something = True
                except (discord.Forbidden, discord.HTTPException):
                    log.warning(f"Gel : dégel forcé — impossible de supprimer {channel.name} sur {guild.name}.")

    if not did_something:
        return False, (
            "membre non gelé (ni rôle de gel, ni salon dédié, ni donnée trouvée)" if LANG == "fr"
            else "member not frozen (no freeze role, no dedicated channel, no data found)"
        )

    display_target = member or await _resolve_user_for_modlog(guild, member_id)
    await _post_modlog_entry(
        guild, "degel", display_target, moderator_label,
        ("Dégel forcé — aucune donnée de gel n'a été retrouvée" if LANG == "fr"
         else "Forced unfreeze — no freeze data could be found"),
    )
    return True, ""


async def _freeze_expiry_task(guild_id: int, member_id: int, delay_seconds: float) -> None:
    try:
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
    except asyncio.CancelledError:
        return
    guild = bot.get_guild(guild_id)
    if guild is None:
        return
    await _unfreeze_member(guild, member_id, "", auto=True)


def _schedule_freeze_expiry(guild_id: int, member_id: int, delay_seconds: float) -> None:
    key = (guild_id, member_id)
    existing = _frozen_unfreeze_tasks.pop(key, None)
    if existing is not None and not existing.done():
        existing.cancel()
    task = asyncio.create_task(_freeze_expiry_task(guild_id, member_id, delay_seconds))
    _frozen_unfreeze_tasks[key] = task


FROZEN_WATCHDOG_INTERVAL_SECONDS = 5 * 60


async def _frozen_watchdog_loop() -> None:
    """Filet de sécurité, en plus de _restore_frozen_schedules_on_ready (qui
    ne s'exécute qu'au tout premier démarrage) : toutes les
    FROZEN_WATCHDOG_INTERVAL_SECONDS, revérifie pour chaque serveur les
    membres gelés dont la durée est déjà écoulée (ou qui n'ont plus, pour une
    raison ou une autre — process tué brutalement plutôt que redémarré
    proprement, tâche perdue — de dégel automatique programmé), et les
    dégèle immédiatement. C'est cette boucle qui garantit qu'un membre gelé
    finit toujours par être dégelé, même si le bot a redémarré au mauvais
    moment ou si une tâche a été perdue en route."""
    while True:
        try:
            await asyncio.sleep(FROZEN_WATCHDOG_INTERVAL_SECONDS)
            now = discord.utils.utcnow()
            for guild in list(bot.guilds):
                if guild.id == STORAGE_GUILD_ID:
                    continue
                store = _frozen_members_store(guild.id)
                if not store:
                    continue
                for member_id_str, record in list(store.items()):
                    try:
                        member_id = int(member_id_str)
                        expires_at = datetime.fromisoformat(record["expires_at"])
                    except (KeyError, ValueError, TypeError):
                        continue
                    task = _frozen_unfreeze_tasks.get((guild.id, member_id))
                    if task is not None and not task.done():
                        continue
                    if expires_at <= now:
                        log.warning(
                            f"Gel : dégel automatique de {member_id} sur {guild.name} rattrapé par le "
                            "filet de sécurité (aucune tâche programmée trouvée)."
                        )
                        await _unfreeze_member(guild, member_id, "", auto=True)
                    else:
                        _schedule_freeze_expiry(guild.id, member_id, (expires_at - now).total_seconds())
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Erreur dans la boucle de surveillance des membres gelés.")


async def _restore_frozen_schedules_on_ready() -> None:
    """Au démarrage du bot, reprogramme le dégel automatique de tout membre
    encore gelé (délai restant), ou dégèle immédiatement si la durée était
    déjà écoulée pendant que le bot était hors ligne."""
    for guild in bot.guilds:
        store = _frozen_members_store(guild.id)
        if not store:
            continue
        now = discord.utils.utcnow()
        for member_id_str, record in list(store.items()):
            try:
                member_id = int(member_id_str)
                expires_at = datetime.fromisoformat(record["expires_at"])
            except (KeyError, ValueError, TypeError):
                continue
            delay = (expires_at - now).total_seconds()
            _schedule_freeze_expiry(guild.id, member_id, max(delay, 0))


def _can_use_freeze(member) -> bool:
    """Accès aux commandes de gel (/gel, /degel, /ungel, bouton Dégeler) :
    administrateurs, OU rôles / membres choisis dans le panel."""
    if _has_effective_administrator(member):
        return True
    guild = getattr(member, "guild", None)
    if guild is None:
        return False
    if member.id in (_get_setting(guild.id, "freeze_allowed_user_ids") or []):
        return True
    allowed_roles = set(_get_setting(guild.id, "freeze_allowed_role_ids") or [])
    return any(r.id in allowed_roles for r in getattr(member, "roles", []))


class FreezeUnfreezeConfirmView(discord.ui.View):
    """Deuxième étape de la double confirmation : n'apparaît que brièvement,
    en message éphémère, suite au premier clic sur « Dégeler »."""

    def __init__(self, member_id: int):
        super().__init__(timeout=60)
        self.member_id = member_id

    @discord.ui.button(label="✅ " + ("Confirmer le dégel" if LANG == "fr" else "Confirm unfreeze"), style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _can_use_freeze(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content="⏳ " + ("Dégel en cours…" if LANG == "fr" else "Unfreezing…"), view=None,
        )
        success, failure_reason = await _unfreeze_member(interaction.guild, self.member_id, str(interaction.user))
        await interaction.followup.send(
            (f"✅ Membre dégelé par {interaction.user.mention}." if success else f"❌ Échec : {failure_reason}")
            if LANG == "fr" else
            (f"✅ Member unfrozen by {interaction.user.mention}." if success else f"❌ Failed: {failure_reason}"),
            ephemeral=True,
        )

    @discord.ui.button(label="❌ " + ("Annuler" if LANG == "fr" else "Cancel"), style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ " + ("Annulé." if LANG == "fr" else "Cancelled."), view=None)


class FreezeView(discord.ui.View):
    """Vue persistante (survit aux redémarrages) postée dans le salon de gel.
    custom_id fixe : le membre visé est relu depuis l'embed du message au
    moment du clic, jamais stocké sur l'instance — administrateurs
    uniquement, avec double confirmation avant toute action réelle."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔓 " + ("Dégeler" if LANG == "fr" else "Unfreeze"),
        style=discord.ButtonStyle.danger, custom_id="freeze_unfreeze_start",
    )
    async def unfreeze_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _can_use_freeze(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        if not interaction.message.embeds:
            await interaction.response.send_message("❌ Message invalide.", ephemeral=True)
            return
        raw = interaction.message.embeds[0].description or ""
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            await interaction.response.send_message("❌ Données de gel illisibles.", ephemeral=True)
            return
        data = json.loads(raw[start:end + 1])
        member_id = data["member_id"]
        await interaction.response.send_message(
            ("⚠️ Confirmer le dégel de <@%d> ? Cette action lui restaurera ses rôles d'origine." % member_id)
            if LANG == "fr" else
            ("⚠️ Confirm unfreezing <@%d>? This will restore their original roles." % member_id),
            view=FreezeUnfreezeConfirmView(member_id),
            ephemeral=True,
        )


def _freeze_member_id_from_message(message: discord.Message) -> "int | None":
    if not message.embeds:
        return None
    raw = message.embeds[0].description or ""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return int(json.loads(raw[start:end + 1])["member_id"])
    except (ValueError, KeyError, TypeError):
        return None


class FreezeTicketOpenView(discord.ui.View):
    """Vue persistante du salon général des gelés : bouton « Ouvrir un ticket »."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 " + ("Ouvrir un ticket" if LANG == "fr" else "Open a ticket"),
        style=discord.ButtonStyle.primary, custom_id="freeze_ticket_open",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not _get_setting(guild.id, "freeze_tickets_enabled"):
            await interaction.response.send_message(
                "❌ Les tickets de gel sont désactivés." if LANG == "fr" else "❌ Freeze tickets are disabled.",
                ephemeral=True,
            )
            return
        store = _frozen_members_store(guild.id)
        record = store.get(str(interaction.user.id))
        if record is None:
            await interaction.response.send_message(
                "❌ Tu n'es pas gelé(e)." if LANG == "fr" else "❌ You are not frozen.", ephemeral=True,
            )
            return
        existing = guild.get_channel(record.get("channel_id") or 0)
        if existing is not None:
            await interaction.response.send_message(
                f"🎫 Tu as déjà un ticket ouvert : {existing.mention}" if LANG == "fr"
                else f"🎫 You already have an open ticket: {existing.mention}",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        freeze_role = await get_or_create_freeze_role(guild)
        try:
            channel = await create_freeze_ticket_channel(guild, interaction.user, freeze_role, record)
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Gel : création du ticket impossible.")
            await interaction.followup.send(
                "❌ Impossible de créer le ticket." if LANG == "fr" else "❌ Could not create the ticket.",
                ephemeral=True,
            )
            return
        record["channel_id"] = channel.id
        store[str(interaction.user.id)] = record
        _set_setting(guild.id, "frozen_members", store)
        await _save_frozen_members(guild)
        await interaction.followup.send(
            f"✅ Ticket ouvert : {channel.mention}" if LANG == "fr" else f"✅ Ticket opened: {channel.mention}",
            ephemeral=True,
        )


class FreezeTicketView(discord.ui.View):
    """Vue persistante du ticket : fermer le ticket / dégeler le membre."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 " + ("Fermer le ticket" if LANG == "fr" else "Close ticket"),
        style=discord.ButtonStyle.secondary, custom_id="freeze_ticket_close",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        member_id = _freeze_member_id_from_message(interaction.message)
        user = interaction.user
        allowed = (
            user.id == member_id or _can_use_freeze(user)
            or getattr(user.guild_permissions, "moderate_members", False)
        )
        if not allowed:
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        guild = interaction.guild
        store = _frozen_members_store(guild.id)
        record = store.get(str(member_id)) if member_id is not None else None
        if record is not None and record.get("channel_id") == interaction.channel.id:
            record["channel_id"] = None
            _set_setting(guild.id, "frozen_members", store)
            await _save_frozen_members(guild)
        await interaction.response.send_message(
            "🔒 Ticket fermé, suppression du salon dans 5 secondes…" if LANG == "fr"
            else "🔒 Ticket closed, deleting the channel in 5 seconds…",
        )
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket de gel fermé par {user}")
        except (discord.Forbidden, discord.HTTPException):
            log.warning(f"Gel : impossible de supprimer le ticket fermé sur {guild.name}.")

    @discord.ui.button(
        label="🔓 " + ("Dégeler" if LANG == "fr" else "Unfreeze"),
        style=discord.ButtonStyle.danger, custom_id="freeze_ticket_unfreeze",
    )
    async def unfreeze_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _can_use_freeze(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        member_id = _freeze_member_id_from_message(interaction.message)
        if member_id is None:
            await interaction.response.send_message(
                "❌ Données de gel illisibles." if LANG == "fr" else "❌ Unreadable freeze data.", ephemeral=True,
            )
            return
        await interaction.response.send_message(
            (f"⚠️ Confirmer le dégel de <@{member_id}> ? Cette action lui restaurera ses rôles d'origine.")
            if LANG == "fr" else
            (f"⚠️ Confirm unfreezing <@{member_id}>? This will restore their original roles."),
            view=FreezeUnfreezeConfirmView(member_id),
            ephemeral=True,
        )


@bot.tree.command(
    name="gel" if LANG == "fr" else "freeze",
    description="Gèle un membre : retire ses rôles et ne lui laisse que le salon des gelés"
    if LANG == "fr"
    else "Freezes a member: removes their roles and leaves only the frozen channel",
)
@discord.app_commands.describe(
    membre="Le membre à geler" if LANG == "fr" else "The member to freeze",
    raison="La raison du gel (obligatoire)" if LANG == "fr" else "The reason for the freeze (required)",
    duree_minutes="Durée du gel en minutes (max 40320)" if LANG == "fr" else "Freeze duration in minutes (max 40320)",
)
async def freeze_command(
    interaction: discord.Interaction,
    membre: discord.Member,
    raison: str,
    duree_minutes: discord.app_commands.Range[int, 1, 40320],
):
    if not _can_use_freeze(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    guild = interaction.guild
    if membre.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Tu ne peux pas viser toi-même." if LANG == "fr" else "❌ You can't target yourself.",
            ephemeral=True,
        )
        return
    if membre.id == guild.owner_id:
        await interaction.response.send_message(
            "❌ Impossible de viser le propriétaire du serveur." if LANG == "fr"
            else "❌ You can't target the server owner.",
            ephemeral=True,
        )
        return
    if not _has_effective_administrator(interaction.user) and (
        membre.guild_permissions.administrator or membre.top_role >= interaction.user.top_role
    ):
        await interaction.response.send_message(
            "❌ Tu ne peux pas geler un administrateur ni un membre au même niveau ou au-dessus de toi."
            if LANG == "fr" else "❌ You can't freeze an administrator or someone at/above your level.",
            ephemeral=True,
        )
        return
    store = _frozen_members_store(guild.id)
    if str(membre.id) in store:
        await interaction.response.send_message(
            "❌ Ce membre est déjà gelé." if LANG == "fr" else "❌ This member is already frozen.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    freeze_role = await get_or_create_freeze_role(guild)
    general_channel = await get_or_create_freeze_channel(guild, freeze_role)
    # Toutes les permissions refusées au rôle de gel sur TOUS les autres salons.
    await _apply_freeze_role_hidden_everywhere(guild, freeze_role, skip_channel_ids={general_channel.id})
    await _refresh_freeze_general_message(guild)

    saved_role_ids = [
        r.id for r in membre.roles
        if not r.is_default() and r.id != freeze_role.id and not r.managed and r < guild.me.top_role
    ]

    now = discord.utils.utcnow()
    expires_at = now + timedelta(minutes=duree_minutes)
    record = {
        "saved_role_ids": saved_role_ids,
        "channel_id": None,  # = salon du ticket, une fois ouvert
        "expires_at": expires_at.isoformat(),
        "started_at": now.isoformat(),
        "reason": raison,
        "moderator_id": interaction.user.id,
        "member_override_channel_ids": [],
    }

    # 1) rôle de gel d'abord : le membre est restreint immédiatement
    try:
        await membre.add_roles(freeze_role, reason=f"[{interaction.user}] {raison}")
    except (discord.Forbidden, discord.HTTPException):
        await interaction.followup.send(
            "❌ Permission/hiérarchie insuffisante pour modifier les rôles de ce membre."
            if LANG == "fr" else "❌ Insufficient permission/hierarchy to change this member's roles.",
            ephemeral=True,
        )
        return

    # état persisté AVANT le retrait des rôles : rien n'est perdu en cas de crash
    store[str(membre.id)] = record
    _set_setting(guild.id, "frozen_members", store)
    await _save_frozen_members(guild)
    _schedule_freeze_expiry(guild.id, membre.id, duree_minutes * 60)

    # 2) retrait des rôles à 2 par seconde (évite le warning/rate-limit Discord)
    removed_ids: list[int] = []
    for role_id in saved_role_ids:
        role = guild.get_role(role_id)
        if role is None:
            continue
        try:
            await membre.remove_roles(role, reason=f"[{interaction.user}] {raison}")
            removed_ids.append(role_id)
        except (discord.Forbidden, discord.HTTPException):
            log.warning(f"Gel : impossible de retirer le rôle {role.name} de {membre} sur {guild.name}.")
        await asyncio.sleep(FREEZE_ROLE_OP_DELAY)
    record["saved_role_ids"] = removed_ids

    # 3) vérification réelle : le membre ne doit voir que le salon général
    fixed_ids, isolated = await _verify_freeze_isolation(guild, membre.id, freeze_role, {general_channel.id})
    record["member_override_channel_ids"] = fixed_ids
    store[str(membre.id)] = record
    _set_setting(guild.id, "frozen_members", store)
    await _save_frozen_members(guild)

    try:
        await general_channel.send(
            f"{membre.mention} " + ("tu as été gelé(e)." if LANG == "fr" else "you have been frozen."),
            delete_after=30,
        )
    except (discord.Forbidden, discord.HTTPException):
        pass

    await _post_modlog_entry(guild, "gel", membre, str(interaction.user), raison, duration_minutes=duree_minutes)

    msg = (
        f"✅ {membre.mention} a été gelé(e) pour {duree_minutes} minute(s) — il/elle ne voit que {general_channel.mention}."
        if LANG == "fr" else
        f"✅ {membre.mention} was frozen for {duree_minutes} minute(s) — they only see {general_channel.mention}."
    )
    if fixed_ids:
        msg += (
            f"\n🛠️ {len(fixed_ids)} salon(s) restaient visibles : isolation forcée appliquée au membre."
            if LANG == "fr" else
            f"\n🛠️ {len(fixed_ids)} channel(s) were still visible: forced isolation applied to the member."
        )
    if not isolated:
        msg += (
            "\n⚠️ Le membre garde peut-être l'accès à certains salons (rôle géré/permission Administrateur impossible à retirer). Vérifie manuellement."
            if LANG == "fr" else
            "\n⚠️ The member may still see some channels (a managed role/Administrator permission can't be removed). Please check manually."
        )
    await interaction.followup.send(msg, ephemeral=True)


@bot.tree.command(
    name="geltickets" if LANG == "fr" else "freezetickets",
    description="Active/désactive les tickets de gel et règle les rôles mentionnés"
    if LANG == "fr"
    else "Enables/disables freeze tickets and sets which roles get pinged",
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    actif="Activer (True) ou désactiver (False) les tickets de gel" if LANG == "fr" else "Enable (True) or disable (False) freeze tickets",
    role_ajouter="Rôle à ajouter aux mentions des tickets" if LANG == "fr" else "Role to add to ticket pings",
    role_retirer="Rôle à retirer des mentions des tickets" if LANG == "fr" else "Role to remove from ticket pings",
)
async def freeze_tickets_command(
    interaction: discord.Interaction,
    actif: typing.Optional[bool] = None,
    role_ajouter: typing.Optional[discord.Role] = None,
    role_retirer: typing.Optional[discord.Role] = None,
):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    guild = interaction.guild
    await interaction.response.defer(ephemeral=True)
    if role_ajouter is not None or role_retirer is not None:
        ids = list(_get_setting(guild.id, "freeze_ticket_ping_role_ids") or [])
        if role_ajouter is not None and role_ajouter.id not in ids:
            ids.append(role_ajouter.id)
        if role_retirer is not None and role_retirer.id in ids:
            ids.remove(role_retirer.id)
        _set_setting(guild.id, "freeze_ticket_ping_role_ids", ids)
        await save_guild_config(guild)
    if actif is not None:
        await _set_freeze_tickets_enabled(guild, actif)
    await interaction.followup.send(_freeze_tickets_status_text(guild), ephemeral=True)


def _freeze_tickets_status_text(guild: discord.Guild) -> str:
    enabled = bool(_get_setting(guild.id, "freeze_tickets_enabled"))
    roles = " ".join(f"<@&{rid}>" for rid in _freeze_ping_role_ids(guild)) or ("*aucun*" if LANG == "fr" else "*none*")
    if LANG == "fr":
        return f"🎫 Tickets de gel : **{'activés' if enabled else 'désactivés'}**\nRôles mentionnés : {roles}"
    return f"🎫 Freeze tickets: **{'enabled' if enabled else 'disabled'}**\nPinged roles: {roles}"


@bot.tree.command(
    name="degel" if LANG == "fr" else "unfreeze",
    description="Dégèle un membre immédiatement, avant la fin de la durée prévue "
    if LANG == "fr"
    else "Unfreezes a member immediately, before the planned duration ends ",
)
@discord.app_commands.describe(membre="Le membre à dégeler" if LANG == "fr" else "The member to unfreeze")
async def unfreeze_command(interaction: discord.Interaction, membre: discord.Member):
    if not _can_use_freeze(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    success, failure_reason = await _unfreeze_member(interaction.guild, membre.id, str(interaction.user))
    if not success:
        await interaction.followup.send(
            f"❌ Action impossible : {failure_reason}" if LANG == "fr" else f"❌ Action failed: {failure_reason}",
            ephemeral=True,
        )
        return
    await interaction.followup.send(
        f"✅ {membre.mention} a été dégelé(e)." if LANG == "fr" else f"✅ {membre.mention} was unfrozen.",
        ephemeral=True,
    )


@bot.tree.command(
    name="ungel",
    description=(
        "Force le dégel d'un membre même sans données de gel (dépannage, admin)"
        if LANG == "fr"
        else "Force-unfreezes a member even without freeze data (troubleshooting, admin)"
    ),
)
@discord.app_commands.describe(membre="Le membre à dégeler de force" if LANG == "fr" else "The member to force-unfreeze")
async def ungel_command(interaction: discord.Interaction, membre: discord.Member):
    """Commande de dépannage : contrairement à /degel, ne renvoie jamais
    « membre non gelé » simplement parce que la donnée stockée a disparu ou
    a été corrompue (ex. suite à une manipulation dans le salon de stockage).
    Utilise toujours _unfreeze_member (restauration complète) si une donnée
    valide existe encore, sinon retire quand même le rôle de gel et supprime
    tout salon de gel résiduel du membre visé — voir _force_unfreeze_member."""
    if not _can_use_freeze(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    success, failure_reason = await _force_unfreeze_member(interaction.guild, membre.id, str(interaction.user))
    if not success:
        await interaction.followup.send(
            f"❌ Action impossible : {failure_reason}" if LANG == "fr" else f"❌ Action failed: {failure_reason}",
            ephemeral=True,
        )
        return
    await interaction.followup.send(
        f"✅ {membre.mention} a été dégelé(e) de force." if LANG == "fr" else f"✅ {membre.mention} was force-unfrozen.",
        ephemeral=True,
    )


@bot.tree.command(
    name="mute",
    description="Met un membre en sourdine (ou demande la sourdine s'il te manque la permission)"
    if LANG == "fr"
    else "Mutes a member (or requests it if you're missing the permission)",
)
@discord.app_commands.describe(
    membre="Le membre à mettre en sourdine" if LANG == "fr" else "The member to mute",
    raison="La raison de la sourdine (obligatoire)" if LANG == "fr" else "The reason for the mute (required)",
    duree_minutes="Durée en minutes (max 40320)" if LANG == "fr" else "Duration in minutes (max 40320)",
)
async def mute_command(
    interaction: discord.Interaction,
    membre: discord.Member,
    raison: str,
    duree_minutes: discord.app_commands.Range[int, 1, 40320] = 60,
):
    await _run_sanction_flow(interaction, membre, "mute", raison, duration=duree_minutes)


@bot.tree.command(
    name="kick",
    description="Expulse un membre (ou demande l'expulsion s'il te manque la permission)"
    if LANG == "fr"
    else "Kicks a member (or requests it if you're missing the permission)",
)
@discord.app_commands.describe(
    membre="Le membre à expulser" if LANG == "fr" else "The member to kick",
    raison="La raison de l'expulsion (obligatoire)" if LANG == "fr" else "The reason for the kick (required)",
)
async def kick_command(interaction: discord.Interaction, membre: discord.Member, raison: str):
    await _run_sanction_flow(interaction, membre, "kick", raison)


@bot.tree.command(
    name="ban",
    description="Bannit un membre (ou demande le bannissement s'il te manque la permission)"
    if LANG == "fr"
    else "Bans a member (or requests it if you're missing the permission)",
)
@discord.app_commands.describe(
    membre="Le membre à bannir" if LANG == "fr" else "The member to ban",
    raison="La raison du bannissement (obligatoire)" if LANG == "fr" else "The reason for the ban (required)",
)
async def ban_command(interaction: discord.Interaction, membre: discord.Member, raison: str):
    await _run_sanction_flow(interaction, membre, "ban", raison)


@bot.tree.command(
    name="diagnostic-permissions" if LANG == "fr" else "permissions-diagnostic",
    description="Explique pourquoi un membre peut (ou non) sanctionner directement (admin uniquement)"
    if LANG == "fr"
    else "Explains why a member can (or can't) directly sanction (administrators only)",
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(membre="Le membre à diagnostiquer" if LANG == "fr" else "The member to diagnose")
async def diagnostic_permissions_command(interaction: discord.Interaction, membre: discord.Member):
    """Outil de débogage : affiche, action par action (mute/kick/ban/unmute/
    unban), la raison exacte pour laquelle _can_member_direct_sanction
    renvoie True ou False pour ce membre — permet de trancher entre
    « comportement voulu » (owner/bot owner/rôle Fondateur/permission
    Discord réelle) et véritable bug, sans avoir à deviner."""
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    guild = interaction.guild
    fresh = guild.get_member(membre.id) or membre

    lines = []
    is_owner_of_bot = _is_bot_owner(fresh.id)
    is_admin_perm = fresh.guild_permissions.administrator
    is_guild_owner = fresh.id == guild.owner_id
    owner_role_id = _get_setting(guild.id, "owner_role_id")
    owner_role = guild.get_role(owner_role_id) if owner_role_id else None
    has_owner_role = bool(owner_role and owner_role in fresh.roles)

    lines.append(
        f"**{'Propriétaire/copropriétaire DU BOT' if LANG == 'fr' else 'BOT owner/co-owner'} "
        f"(Discord Developer Portal > Team)** : {'✅ OUI' if is_owner_of_bot else '❌ non'}"
    )
    lines.append(
        f"**{'Permission Administrateur (cumulée, tous rôles confondus)' if LANG == 'fr' else 'Administrator permission (cumulative, across all roles)'}** : "
        f"{'✅ OUI' if is_admin_perm else '❌ non'}"
    )
    lines.append(
        f"**{'Propriétaire du serveur' if LANG == 'fr' else 'Server owner'}** : {'✅ OUI' if is_guild_owner else '❌ non'}"
    )
    lines.append(
        f"**{'Rôle Fondateur configuré (owner_role_id)' if LANG == 'fr' else 'Configured Founder role (owner_role_id)'}** : "
        + (
            (f"✅ OUI — {owner_role.mention}" if has_owner_role else f"❌ non (rôle configuré : {owner_role.mention}, mais {fresh.mention} ne l'a pas)")
            if owner_role is not None
            else ("❌ aucun rôle Fondateur configuré sur ce serveur" if LANG == "fr" else "❌ no Founder role configured on this server")
        )
    )
    lines.append("")
    lines.append("**" + ("Permissions Discord précises (cumulées, tous rôles)" if LANG == "fr" else "Precise Discord permissions (cumulative, all roles)") + "** :")
    for action, perm_name in SANCTION_ACTION_DISCORD_PERMISSION.items():
        has_perm = getattr(fresh.guild_permissions, perm_name, False)
        lines.append(f"• `{action}` ({perm_name}) : {'✅' if has_perm else '❌'}")

    lines.append("")
    lines.append("**" + ("Résultat : sanction directe possible pour…" if LANG == "fr" else "Result: direct sanction possible for…") + "**")
    for action in ("mute", "kick", "ban", "unmute", "unban"):
        can_direct = _can_member_direct_sanction(fresh, action)
        lines.append(f"• `/{action}` : {'✅ DIRECT (sans demande)' if can_direct else '⏳ passe par la demande (ou refus si désactivée)'}")

    role_names = ", ".join(r.name for r in fresh.roles if not r.is_default()) or ("aucun" if LANG == "fr" else "none")
    lines.append("")
    lines.append(f"**{'Rôles actuels' if LANG == 'fr' else 'Current roles'}** : {role_names}")

    embed = discord.Embed(
        title=f"🔍 {'Diagnostic permissions' if LANG == 'fr' else 'Permissions diagnostic'} — {fresh}",
        description="\n".join(lines)[:4096],
        color=0x5865F2,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="note",
    description="Enregistre une note dans l'historique, sans action Discord réelle (administrateurs uniquement)"
    if LANG == "fr"
    else "Logs a note in the history, with no real Discord action (administrators only)",
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    membre="Le membre concerné" if LANG == "fr" else "The member concerned",
    raison="La raison de la note (obligatoire)" if LANG == "fr" else "The reason for the note (required)",
)
async def note_command(interaction: discord.Interaction, membre: discord.Member, raison: str):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    if membre.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Tu ne peux pas viser toi-même." if LANG == "fr" else "❌ You can't target yourself.",
            ephemeral=True,
        )
        return

    n = await _post_modlog_entry(interaction.guild, "autre", membre, str(interaction.user), raison)
    await interaction.response.send_message(
        f"✅ Sanction « autre » enregistrée dans l'historique de {membre.mention} ({n})."
        if LANG == "fr"
        else f"✅ \"Other\" sanction logged in {membre.mention}'s history ({n}).",
        ephemeral=True,
    )
    await _start_target_response_flow(interaction.guild, membre, "autre", str(interaction.user), raison)


async def _run_unsanction_flow(interaction: discord.Interaction, membre: discord.User, action: str, raison: str):
    """Logique commune à /unmute et /unban (même principe que
    _run_sanction_flow : direct si permission précise, sinon demande si
    activée, sinon refus)."""
    _print_sanction_diagnostic(interaction.user, action, context=f"/{action}")
    can_direct = _can_member_direct_sanction(interaction.user, action)
    if not (_member_is_configured_staff(interaction.user) or can_direct):
        await interaction.response.send_message(
            "❌ Tu n'as aucune permission." if LANG == "fr" else "❌ You have no permission.",
            ephemeral=True,
        )
        return

    target_id = membre.id

    if target_id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Tu ne peux pas viser toi-même." if LANG == "fr" else "❌ You can't target yourself.",
            ephemeral=True,
        )
        return
    if target_id == interaction.guild.owner_id:
        await interaction.response.send_message(
            "❌ Impossible de viser le propriétaire du serveur." if LANG == "fr"
            else "❌ You can't target the server owner.",
            ephemeral=True,
        )
        return

    if can_direct:
        await interaction.response.defer(ephemeral=True)
        success, failure_reason = await _execute_unsanction_direct(
            interaction.guild, interaction.user, target_id, action, raison
        )
        if not success:
            await interaction.followup.send(
                f"❌ Action impossible : {failure_reason}" if LANG == "fr"
                else f"❌ Action failed: {failure_reason}",
                ephemeral=True,
            )
            return

        display_target = await _resolve_user_for_modlog(interaction.guild, target_id)
        await _post_modlog_entry(interaction.guild, action, display_target, str(interaction.user), raison)
        await interaction.followup.send(
            f"✅ Annulation « {action} » appliquée à {display_target.mention}." if LANG == "fr"
            else f"✅ Reversal \"{action}\" applied to {display_target.mention}.",
            ephemeral=True,
        )
        return

    mod_request_enabled = bool(_get_setting(interaction.guild.id, "mod_request_enabled"))
    if not mod_request_enabled:
        await interaction.response.send_message(
            "❌ Tu n'as aucune permission." if LANG == "fr" else "❌ You have no permission.",
            ephemeral=True,
        )
        return

    mod_request_channel_id = _get_setting(interaction.guild.id, "mod_request_channel_id")
    if not mod_request_channel_id:
        await interaction.response.send_message(
            "❌ Le système de demande de sanction n'est pas encore configuré sur ce serveur "
            "(salon des demandes à définir avec `/roles-staff`)."
            if LANG == "fr"
            else "❌ The sanction-request system isn't configured on this server yet "
            "(request channel needs to be set with `/staff-roles`).",
            ephemeral=True,
        )
        return
    approver_role_ids = _mod_request_approver_role_ids(interaction.guild.id, action)

    now = time.time()
    last_use = _mod_request_last_use.get(interaction.user.id, 0)
    if now - last_use < MOD_REQUEST_COOLDOWN_SECONDS:
        wait = int(MOD_REQUEST_COOLDOWN_SECONDS - (now - last_use))
        await interaction.response.send_message(
            f"⏱️ Attends encore {wait}s avant de faire une nouvelle demande." if LANG == "fr"
            else f"⏱️ Wait {wait}s more before making a new request.",
            ephemeral=True,
        )
        return
    _mod_request_last_use[interaction.user.id] = now

    channel = interaction.guild.get_channel(mod_request_channel_id)
    if channel is None:
        await interaction.response.send_message(
            "❌ Salon de demandes introuvable (réglage `mod_request_channel_id` invalide, "
            "reconfigure-le avec `/roles-staff`)." if LANG == "fr"
            else "❌ Request channel not found (invalid `mod_request_channel_id` setting, "
            "reconfigure it with `/staff-roles`).",
            ephemeral=True,
        )
        return

    display_target = await _resolve_user_for_modlog(interaction.guild, target_id)
    embed = _build_mod_request_embed(action, display_target, interaction.user, raison)
    mentions = " ".join(f"<@&{rid}>" for rid in approver_role_ids)

    try:
        await channel.send(content=mentions or None, embed=embed, view=ModRequestView())
    except Exception:
        log.exception("Échec de l'envoi de la demande d'annulation dans le salon dédié.")
        await interaction.response.send_message(
            "❌ Échec de l'envoi de la demande." if LANG == "fr" else "❌ Failed to send the request.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"✅ Demande envoyée dans {channel.mention} pour validation." if LANG == "fr"
        else f"✅ Request sent to {channel.mention} for approval.",
        ephemeral=True,
    )


@bot.tree.command(
    name="unmute",
    description="Retire la sourdine d'un membre (ou demande le retrait s'il te manque la permission)"
    if LANG == "fr"
    else "Unmutes a member (or requests it if you're missing the permission)",
)
@discord.app_commands.describe(
    membre="Le membre à démute" if LANG == "fr" else "The member to unmute",
    raison="Raison du retrait de sourdine (obligatoire)" if LANG == "fr" else "Reason for the unmute (required)",
)
async def unmute_command(interaction: discord.Interaction, membre: discord.User, raison: str):
    await _run_unsanction_flow(interaction, membre, "unmute", raison)


@bot.tree.command(
    name="unban",
    description="Retire le bannissement d'un membre (ou demande le retrait s'il te manque la permission)"
    if LANG == "fr"
    else "Unbans a member (or requests it if you're missing the permission)",
)
@discord.app_commands.describe(
    membre="Le membre banni à débannir (pseudo ou ID)" if LANG == "fr" else "The banned member to unban (name or ID)",
    raison="Raison du retrait de bannissement (obligatoire)" if LANG == "fr" else "Reason for the unban (required)",
)
async def unban_command(interaction: discord.Interaction, membre: discord.User, raison: str):
    await _run_unsanction_flow(interaction, membre, "unban", raison)


@bot.tree.command(
    name="historique" if LANG == "fr" else "history",
    description=(
        "Affiche l'historique de modération d'un membre (warn/mute/kick/ban)" if LANG == "fr"
        else "Shows a member's moderation history (warn/mute/kick/ban)"
    ),
)
@discord.app_commands.describe(
    membre="Le membre dont on veut voir l'historique" if LANG == "fr" else "The member whose history to view",
)
async def history_command(interaction: discord.Interaction, membre: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(t("no_perm_moderate"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    entries = await get_member_history(interaction.guild, membre)

    if not entries:
        await interaction.followup.send(t("history_empty", target=membre.mention), ephemeral=True)
        return

    lines = []
    for e in entries[-25:]:
        date = e["date"].strftime("%Y-%m-%d %H:%M")
        guild_name = e.get("guild_name") or interaction.guild.name
        lines.append(
            t(
                "history_line",
                emoji=MODLOG_EMOJI.get(e["type"], "•"),
                date=date,
                type=e["type"].upper(),
                guild_name=guild_name,
                moderator=e["moderator"],
                reason=e["reason"],
            )
        )

    embed = discord.Embed(
        title=t("history_title", target=str(membre)),
        description="\n".join(lines)[:4096],
        color=0xE74C3C,
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


async def _notify_guild_owner_icon_removed(guild: discord.Guild) -> None:
    """Prévient le/la propriétaire du serveur que l'icône a été supprimée
    suite à une modification détectée pendant un raid. Contrairement au nom
    ou aux salons/rôles, l'ancienne icône ne peut pas être restaurée de
    façon fiable (Discord ne garantit pas l'accès à l'ancien fichier une
    fois remplacé) : on informe donc la personne qu'elle doit en reposer
    une manuellement si elle le souhaite."""
    try:
        owner = guild.owner or await guild.fetch_member(guild.owner_id)
    except Exception:
        owner = None
    if owner is None:
        log.warning(f"Impossible de retrouver le/la propriétaire de {guild.name} pour le MP icône.")
        return

    text = (
        f"🖼️ **{guild.name}** : l'icône du serveur a été modifiée pendant un raid détecté par "
        "l'anti-nuke. Je ne peux pas restaurer l'ancienne icône de façon fiable (Discord ne garde "
        "pas toujours l'ancien fichier accessible une fois remplacé), donc je l'ai supprimée "
        "(retour à l'icône par défaut). Si tu veux la remettre, tu devras en reposer une toi-même "
        "depuis tes propres fichiers (Paramètres du serveur > Vue d'ensemble)."
        if LANG == "fr"
        else
        f"🖼️ **{guild.name}**: the server icon was changed during a raid detected by anti-nuke. "
        "I can't reliably restore the previous icon (Discord doesn't always keep the old file "
        "accessible once replaced), so I removed it (back to the default icon). If you want it "
        "back, you'll need to re-upload it yourself from your own files (Server Settings > Overview)."
    )
    try:
        await owner.send(text)
    except Exception:
        log.warning(f"Impossible d'envoyer un MP icône au/à la propriétaire de {guild.name} (MP fermés ?).")


async def _rollback_scan(guild: discord.Guild, target: discord.abc.User, minutes: int):
    since = discord.utils.utcnow() - timedelta(minutes=minutes)
    actions = []

    relevant = {
        discord.AuditLogAction.channel_create: "channel_create",
        discord.AuditLogAction.channel_delete: "channel_delete",
        discord.AuditLogAction.role_create: "role_create",
        discord.AuditLogAction.role_delete: "role_delete",
        discord.AuditLogAction.channel_update: "channel_update",
        discord.AuditLogAction.overwrite_create: "overwrite",
        discord.AuditLogAction.overwrite_update: "overwrite",
        discord.AuditLogAction.webhook_create: "webhook_create",
        discord.AuditLogAction.message_delete: "message_delete",
        discord.AuditLogAction.message_bulk_delete: "message_bulk_delete",
        discord.AuditLogAction.guild_update: "guild_update",
    }

    async for entry in guild.audit_logs(limit=500, user=target):
        if entry.created_at < since:
            break
        kind = relevant.get(entry.action)
        if kind is None:
            continue
        actions.append({"kind": kind, "entry": entry})

    return actions


async def _rollback_execute_one(guild: discord.Guild, item: dict, dry_run: bool, lang_fr: bool) -> tuple[str | None, bool]:
    """Traite UNE action de rollback et renvoie (ligne à afficher, exécutée ?).
    Ne dépend du résultat d'aucune autre action du même lot : chaque action
    cible un objet Discord identifié par son propre ID d'audit log, résolu
    uniquement via le cache local discord.py déjà en mémoire (guild.get_channel,
    guild.get_role...) — aucune requête réseau de vérification préalable.
    C'est ce qui permet à `_rollback_execute` de lancer tout le lot en parallèle
    via asyncio.gather sans risque d'incohérence entre actions."""
    kind = item["kind"]
    entry = item["entry"]
    target_obj = entry.target
    executed_one = False
    line = None

    try:
        if kind == "channel_create":
            channel = guild.get_channel(entry.target.id) if entry.target else None
            name = getattr(target_obj, "name", str(entry.target))
            line = t("rollback_line_channel_create", name=name)
            if not dry_run and channel is not None:
                await channel.delete(reason="Rollback anti-raid")
                executed_one = True

        elif kind == "channel_delete":
            before = entry.before
            name = getattr(before, "name", None) or "salon"
            ctype = str(getattr(before, "type", "text"))
            line = t("rollback_line_channel_delete", name=name, ctype=ctype)
            if not dry_run:
                category = None
                cat_id = getattr(before, "category_id", None) or getattr(before, "category", None)
                if isinstance(cat_id, int):
                    category = guild.get_channel(cat_id)
                channel_type = getattr(before, "type", discord.ChannelType.text)
                if channel_type == discord.ChannelType.voice:
                    await guild.create_voice_channel(name=name, category=category, reason="Rollback anti-raid (recréation)")
                elif channel_type == discord.ChannelType.category:
                    await guild.create_category(name=name, reason="Rollback anti-raid (recréation)")
                else:
                    await guild.create_text_channel(name=name, category=category, reason="Rollback anti-raid (recréation)")
                executed_one = True

        elif kind == "role_create":
            role = guild.get_role(entry.target.id) if entry.target else None
            name = getattr(target_obj, "name", str(entry.target))
            line = t("rollback_line_role_create", name=name)
            if not dry_run and role is not None:
                await role.delete(reason="Rollback anti-raid")
                executed_one = True

        elif kind == "overwrite":
            channel = guild.get_channel(entry.extra.id) if getattr(entry, "extra", None) else None
            cname = getattr(channel, "name", str(getattr(entry, "extra", "salon")))
            line = t("rollback_line_overwrite", name=cname)
            if not dry_run and channel is not None and entry.before is not None:
                overwrite_target = entry.extra
                allow = getattr(entry.before, "allow", None)
                deny = getattr(entry.before, "deny", None)
                if allow is not None and deny is not None:
                    po = discord.PermissionOverwrite.from_pair(allow, deny)
                    try:
                        resolved = guild.get_role(overwrite_target.id) or guild.get_member(overwrite_target.id)
                    except Exception:
                        resolved = None
                    if resolved is not None:
                        await channel.set_permissions(resolved, overwrite=po, reason="Rollback anti-raid (restauration)")
                        executed_one = True

        elif kind == "webhook_create":
            name = getattr(target_obj, "name", str(entry.target))
            cname = getattr(entry.extra, "channel", None) or ""
            line = t("rollback_line_webhook", name=name, channel=cname)
            if not dry_run:
                try:
                    for webhook in await guild.webhooks():
                        if webhook.id == entry.target.id:
                            await webhook.delete(reason="Rollback anti-raid")
                            executed_one = True
                            break
                except discord.Forbidden:
                    pass

        elif kind == "role_delete":
            before = entry.before
            name = getattr(before, "name", None) or (LANG == "fr" and "rôle-restauré" or "restored-role")
            line = t("rollback_line_role_delete", name=name)
            if not dry_run:
                perms = getattr(before, "permissions", None) or discord.Permissions.none()
                colour = getattr(before, "colour", None) or discord.Colour.default()
                hoist = bool(getattr(before, "hoist", False))
                mentionable = bool(getattr(before, "mentionable", False))
                await guild.create_role(
                    name=name, permissions=perms, colour=colour,
                    hoist=hoist, mentionable=mentionable,
                    reason="Rollback anti-nuke (recréation du rôle supprimé)",
                )
                executed_one = True

        elif kind == "message_delete":
            author = entry.target
            channel_id = getattr(getattr(entry, "extra", None), "channel_id", None) or getattr(
                getattr(entry, "extra", None), "channel", None
            )
            channel = guild.get_channel(channel_id) if isinstance(channel_id, int) else channel_id
            cname = getattr(channel, "mention", "#salon")
            author_name = str(author) if author else "?"
            line = t("rollback_line_message_delete", author=author_name, channel=cname)

            if not dry_run and author is not None and channel is not None:
                restored = await _find_archived_message_content(author, channel, entry.created_at)
                if restored is not None:
                    content, files = restored
                    try:
                        embed = discord.Embed(
                            description=content[:4000] or ("*(vide)*" if LANG == "fr" else "*(empty)*"),
                            color=0xE67E22,
                        )
                        embed.set_author(name=f"{author_name} ({'restauré' if LANG == 'fr' else 'restored'})")
                        if files:
                            await channel.send(embed=embed, files=files)
                        else:
                            await channel.send(embed=embed)
                        executed_one = True
                    except Exception:
                        pass

        elif kind == "message_bulk_delete":
            count_deleted = getattr(getattr(entry, "extra", None), "count", None) or "?"
            channel_id = getattr(getattr(entry, "extra", None), "channel_id", None)
            channel = guild.get_channel(channel_id) if isinstance(channel_id, int) else None
            cname = getattr(channel, "mention", "#salon")
            line = (
                (f"⚠️ Suppression en masse de {count_deleted} message(s) dans {cname} — restauration "
                 "automatique impossible individuellement (Discord ne liste pas les auteurs dans ce "
                 "type d'entrée). Utilise `/recherche-messages` pour retrouver les messages archivés d'un membre précis.")
                if LANG == "fr" else
                (f"⚠️ Bulk deletion of {count_deleted} message(s) in {cname} — cannot be automatically "
                 "restored one by one (Discord doesn't list authors for this entry type). Use `/recherche-messages` "
                 "to find a specific member's archived messages.")
            )

        elif kind == "guild_update":
            before = entry.before
            new_name = getattr(before, "name", None)
            icon_line = None
            if new_name and new_name != guild.name:
                line = t("rollback_line_guild_name", name=new_name)
                if not dry_run:
                    await guild.edit(name=new_name, reason="Rollback anti-nuke (nom du serveur)")
                    executed_one = True

            if hasattr(before, "icon"):
                icon_line = t("rollback_line_guild_icon")
                if not dry_run:
                    try:
                        await guild.edit(icon=None, reason="Rollback anti-nuke (icône modifiée supprimée)")
                        executed_one = True
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    asyncio.create_task(_notify_guild_owner_icon_removed(guild))
            if icon_line:
                line = f"{line}\n{icon_line}" if line else icon_line

    except discord.NotFound:
        pass
    except (discord.Forbidden, discord.HTTPException) as exc:
        line = t("rollback_error_line", label=kind, error=str(exc))

    return line, executed_one


async def _rollback_execute(guild: discord.Guild, actions: list, dry_run: bool, lang_fr: bool, throttle: bool = False):
    """Exécute le lot d'actions. Par défaut (throttle=False, utilisé par le
    rollback AUTOMATIQUE anti-nuke) tout part EN PARALLÈLE (asyncio.gather) :
    la fenêtre d'analyse y est courte (ANTINUKE_ROLLBACK_MINUTES) donc très
    peu d'actions à annuler, pas besoin de se brider. Avec throttle=True
    (COMMANDE MANUELLE /rollback, fenêtre pouvant aller jusqu'à 1440 minutes
    donc potentiellement beaucoup plus d'actions), on limite la concurrence
    avec un sémaphore pour éviter de saturer d'un coup les buckets HTTP de
    Discord et de se prendre une vague de warnings 429 (voir logs)."""
    if not actions:
        return [], 0

    if throttle:
        semaphore = asyncio.Semaphore(5)

        async def _run_one(item):
            async with semaphore:
                return await _rollback_execute_one(guild, item, dry_run, lang_fr)

        results = await asyncio.gather(
            *(_run_one(item) for item in actions),
            return_exceptions=True,
        )
    else:
        results = await asyncio.gather(
            *(_rollback_execute_one(guild, item, dry_run, lang_fr) for item in actions),
            return_exceptions=True,
        )

    lines = []
    executed = 0
    for item, result in zip(actions, results):
        if isinstance(result, Exception):
            log.exception(f"Erreur inattendue lors d'une action de rollback ({item.get('kind')}).", exc_info=result)
            lines.append(t("rollback_error_line", label=item.get("kind", "?"), error=str(result)))
            continue
        line, executed_one = result
        if line:
            lines.append(line)
        if executed_one:
            executed += 1

    return lines, executed


async def _run_antinuke_auto_rollback(guild: discord.Guild, actor: discord.abc.User) -> None:
    """Déclenché automatiquement par l'anti-nuke : annule les actions de `actor`
    des ANTINUKE_ROLLBACK_MINUTES dernières minutes (création/suppression de
    salons, rôles, messages, changement de nom/icône du serveur).
    Un verrou (_antinuke_rollback_in_progress) empêche deux rollbacks concurrents
    pour le même (serveur, auteur) — sinon un raid massif redéclenche le seuil
    anti-nuke plusieurs fois et chaque déclenchement relance un rollback complet
    en double, en échec sur tout ce que le précédent a déjà supprimé."""
    key = (guild.id, actor.id)
    if key in _antinuke_rollback_in_progress:
        return
    _antinuke_rollback_in_progress.add(key)
    try:
        await asyncio.sleep(ANTINUKE_ROLLBACK_DELAY_SECONDS)

        try:
            actions = await _rollback_scan(guild, actor, ANTINUKE_ROLLBACK_MINUTES)
        except Exception:
            log.exception(f"Erreur lors du scan de rollback automatique pour {actor} sur {guild.name}.")
            return

        if not actions:
            return

        try:
            lines, executed = await _rollback_execute(guild, actions, dry_run=False, lang_fr=(LANG == "fr"))
        except Exception:
            log.exception(f"Erreur lors de l'exécution du rollback automatique pour {actor} sur {guild.name}.")
            return

        description = "\n".join(lines)[:4000]
        embed = discord.Embed(
            title=f"⏪ Rollback automatique anti-nuke — {actor}",
            description=f"{executed} action(s) sur {len(actions)} annulée(s) automatiquement.\n\n{description}"
            if LANG == "fr" else
            f"{executed}/{len(actions)} action(s) automatically undone.\n\n{description}",
            color=0x2ECC71,
        )
        try:
            channel = await get_or_create_audit_channel(guild)
            await channel.send(embed=embed)
        except Exception:
            log.exception(f"Impossible de poster le résumé du rollback automatique sur {guild.name}.")
    finally:
        _antinuke_rollback_in_progress.discard(key)


@bot.tree.command(
    name="rollback" if LANG == "fr" else "rollback",
    description=(
        "Annule les actions récentes d'un membre (raid) via l'audit log" if LANG == "fr"
        else "Undoes a member's recent actions (raid) using the audit log"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    membre="Sélectionne un membre, ou colle un ID (fonctionne même s'il a quitté/été banni)" if LANG == "fr"
    else "Pick a member, or paste an ID (works even if they left/were banned)",
    minutes="Depuis combien de minutes chercher dans l'audit log (max 1440)" if LANG == "fr"
    else "How many minutes back to search the audit log (max 1440)",
    confirmer="True pour exécuter réellement (par défaut : simulation seulement)" if LANG == "fr"
    else "True to actually execute (default: simulation only)",
)
async def rollback_command(
    interaction: discord.Interaction,
    membre: discord.User,
    minutes: discord.app_commands.Range[int, 1, 1440] = 30,
    confirmer: bool = False,
):
    if interaction.user.id != interaction.guild.owner_id and not _is_bot_owner(interaction.user.id):
        await interaction.response.send_message(t("no_perm_admin_rollback"), ephemeral=True)
        return

    guild = interaction.guild
    membre_obj = guild.get_member(membre.id) or membre

    if isinstance(membre_obj, discord.Member):
        if interaction.user.id != interaction.guild.owner_id and not _role_hierarchy_ok(interaction.user, interaction.guild.me, membre_obj):
            await interaction.response.send_message(t("rollback_target_bot_owner"), ephemeral=True)
            return
    elif membre_obj.id == guild.owner_id:
        await interaction.response.send_message(t("rollback_target_bot_owner"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)

    actions = await _rollback_scan(guild, membre_obj, minutes)

    if not actions:
        try:
            await interaction.followup.send(t("rollback_nothing", target=membre_obj.mention, minutes=minutes))
        except discord.HTTPException as e:
            _log_send_failure(f"rollback: échec d'envoi (rien à annuler) pour {membre_obj}", e)
        return

    dry_run = not confirmer
    lines, executed = await _rollback_execute(guild, actions, dry_run, LANG == "fr", throttle=True)

    title = t("rollback_dry_run_title" if dry_run else "rollback_live_title", target=str(membre_obj))
    description = "\n".join(lines)[:4000]
    embed = discord.Embed(title=title, description=description, color=0xFF8C00 if dry_run else 0x2ECC71)
    if dry_run:
        embed.set_footer(text=t("rollback_dry_run_footer"))

    try:
        await interaction.followup.send(embed=embed)
    except discord.HTTPException as e:
        _log_send_failure(f"rollback: échec d'envoi du résumé pour {membre_obj}", e)
        return

    if not dry_run:
        try:
            channel = await get_or_create_local_modlog_channel(guild)
            await channel.send(
                embed=discord.Embed(
                    title=f"⏪ Rollback — {membre_obj}",
                    description=f"{executed} action(s) sur {len(actions)} exécutées par {interaction.user}.\n\n{description}",
                    color=0x2ECC71,
                )
            )
            await interaction.followup.send(
                t("rollback_done", target=membre_obj.mention, n=executed, modlog=channel.mention),
                ephemeral=True,
            )
        except discord.HTTPException as e:
            _log_send_failure(f"rollback: échec d'envoi de la confirmation pour {membre_obj}", e)
        except Exception:
            try:
                await interaction.followup.send(
                    t("rollback_done_no_modlog", target=membre_obj.mention, n=executed),
                    ephemeral=True,
                )
            except discord.HTTPException as e:
                _log_send_failure(f"rollback: échec d'envoi de la confirmation (sans modlog) pour {membre_obj}", e)
    else:
        try:
            await interaction.followup.send(t("rollback_confirm_hint"), ephemeral=True)
        except discord.HTTPException as e:
            _log_send_failure(f"rollback: échec d'envoi du rappel simulation pour {membre_obj}", e)



def _audit_search_allowed(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    if not _get_setting(interaction.guild.id, "audit_search_enabled"):
        return False
    channel_id = _get_setting(interaction.guild.id, "audit_search_channel_id")
    if channel_id and interaction.channel.id != channel_id:
        return False
    return True


async def _send_audit_search_denied(interaction: discord.Interaction) -> None:
    channel_id = _get_setting(interaction.guild.id, "audit_search_channel_id") if interaction.guild else 0
    if channel_id:
        text = (
            f"❌ Cette commande est désactivée sur ce serveur, ou doit être utilisée dans <#{channel_id}>."
            if LANG == "fr"
            else f"❌ This command is disabled on this server, or must be used in <#{channel_id}>."
        )
    else:
        text = (
            "❌ Cette commande est désactivée sur ce serveur (active-la avec `/recherche-config`)."
            if LANG == "fr"
            else "❌ This command is disabled on this server (enable it with `/search-config`)."
        )
    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(
    name="recherche-config" if LANG == "fr" else "search-config",
    description=(
        "Active/désactive la recherche de logs sur ce serveur et choisit leur salon dédié"
        if LANG == "fr"
        else "Enable/disable log search on this server and pick their dedicated channel"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(
    active="Active ou désactive /recherche-historique et /recherche-messages sur ce serveur" if LANG == "fr"
    else "Enable or disable /history-search and /recherche-messages on this server",
    salon="Salon où ces commandes doivent être utilisées (laisser vide pour les autoriser partout)" if LANG == "fr"
    else "Channel where these commands must be used (leave empty to allow them anywhere)",
)
async def recherche_config_command(
    interaction: discord.Interaction,
    active: bool = None,
    salon: discord.TextChannel = None,
):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    guild = interaction.guild
    if active is not None:
        _set_setting(guild.id, "audit_search_enabled", active)
    if salon is not None:
        _set_setting(guild.id, "audit_search_channel_id", salon.id)

    saved = await save_guild_config(guild)
    enabled = _get_setting(guild.id, "audit_search_enabled")
    channel_id = _get_setting(guild.id, "audit_search_channel_id")
    channel_txt = f"<#{channel_id}>" if channel_id else ("*n'importe où*" if LANG == "fr" else "*anywhere*")

    text = (
        (
            f"🔎 Commandes `/recherche-historique` et `/recherche-messages` : {'✅ activées' if enabled else '⛔ désactivées'}\n"
            f"Salon autorisé : {channel_txt}\n\n"
            + ("✅ Enregistré." if saved else "⚠️ Appliqué pour cette session, mais PAS enregistré (serveur base de données indisponible) — sera perdu au redémarrage.")
        )
        if LANG == "fr"
        else (
            f"🔎 `/history-search` and `/recherche-messages` commands: {'✅ enabled' if enabled else '⛔ disabled'}\n"
            f"Allowed channel: {channel_txt}\n\n"
            + ("✅ Saved." if saved else "⚠️ Applied for this session, but NOT saved (database server unavailable) — will be lost on restart.")
        )
    )
    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(
    name="recherche-historique" if LANG == "fr" else "history-search",
    description=(
        "Consulte le dossier complet d'un membre par ID (utile si banni/parti)" if LANG == "fr"
        else "Look up a member's full record by ID (useful if banned/left)"
    ),
)
@discord.app_commands.describe(
    identifiant="L'identifiant Discord (ID) du membre" if LANG == "fr" else "The member's Discord ID",
)
async def recherche_historique_command(interaction: discord.Interaction, identifiant: str):
    if not _audit_search_allowed(interaction):
        await _send_audit_search_denied(interaction)
        return

    if not identifiant.isdigit():
        await interaction.response.send_message(
            "❌ Ce n'est pas un identifiant Discord valide (uniquement des chiffres)." if LANG == "fr"
            else "❌ Not a valid Discord ID (digits only).",
            ephemeral=True,
        )
        return

    identifiant_int = int(identifiant)
    await interaction.response.defer(ephemeral=True)

    db_guild = get_db_guild()
    if db_guild is None:
        await interaction.followup.send(
            "❌ Serveur base de données introuvable (AUDIT_DB_GUILD_ID mal configuré ou bot absent).",
            ephemeral=True,
        )
        return

    try:
        index_channel = await get_or_create_member_index_channel(db_guild)
        thread = await _find_member_thread(index_channel, identifiant_int)
    except Exception:
        log.exception(f"Erreur lors de la recherche du fil d'historique pour {identifiant_int}.")
        await interaction.followup.send("❌ Erreur lors de la recherche du fil d'historique.", ephemeral=True)
        return

    if thread is None:
        await interaction.followup.send(
            f"ℹ️ Aucun fil d'historique trouvé pour l'identifiant `{identifiant_int}`.", ephemeral=True
        )
        return

    await interaction.followup.send(f"📜 Historique de `{identifiant_int}` : {thread.mention}", ephemeral=True)


def _parse_date_fr(texte: str) -> typing.Optional[date_cls]:
    """Accepte JJ/MM/AAAA, JJ-MM-AAAA, AAAA-MM-JJ, et en repli MM/JJ/AAAA si le jour/mois français est invalide."""
    texte = texte.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(texte, fmt).date()
        except ValueError:
            continue
    return None


def _parse_heure_fr(texte: str) -> typing.Optional[tuple[int, typing.Optional[int]]]:
    """Accepte HH, HH:MM ou HHhMM. Retourne (heure, minute_ou_None)."""
    texte = texte.strip().lower().replace("h", ":") if "h" in texte.strip().lower() else texte.strip()
    if ":" in texte:
        parts = texte.split(":")
        if len(parts) not in (1, 2):
            return None
        try:
            heure = int(parts[0])
            minute = int(parts[1]) if len(parts) == 2 and parts[1] != "" else None
        except ValueError:
            return None
    elif texte.isdigit():
        heure = int(texte)
        minute = None
    else:
        return None
    if not (0 <= heure <= 23) or (minute is not None and not (0 <= minute <= 59)):
        return None
    return heure, minute


async def _collect_full_log_entries(thread) -> list[dict]:
    """Reconstitue les entrées de logs (embed + pièces jointes associées) d'un fil de logs complets,
    triées du plus ancien au plus récent."""
    entries: list[dict] = []
    current: typing.Optional[dict] = None
    async for msg in thread.history(limit=None, oldest_first=True):
        if msg.embeds and msg.embeds[0].footer and str(msg.embeds[0].footer.text or "").startswith("ID:"):
            if current is not None:
                entries.append(current)
            current = {"embed_message": msg, "embed": msg.embeds[0], "attachment_messages": []}
        elif current is not None and msg.attachments:
            current["attachment_messages"].append(msg)
    if current is not None:
        entries.append(current)
    return entries


@bot.tree.command(
    name="recherche-messages" if LANG == "fr" else "search-messages",
    description=(
        "Recherche les messages logués d'un membre par ID, avec filtre date/heure optionnel"
        if LANG == "fr"
        else "Search a member's logged messages by ID, with an optional date/time filter"
    ),
)
@discord.app_commands.describe(
    identifiant="L'identifiant Discord (ID) du membre" if LANG == "fr" else "The member's Discord ID",
)
async def recherche_messages_command(interaction: discord.Interaction, identifiant: str):
    if not _audit_search_allowed(interaction):
        await _send_audit_search_denied(interaction)
        return

    if not identifiant.isdigit():
        await interaction.response.send_message(
            "❌ Ce n'est pas un identifiant Discord valide (uniquement des chiffres)." if LANG == "fr"
            else "❌ Not a valid Discord ID (digits only).",
            ephemeral=True,
        )
        return

    identifiant_int = int(identifiant)

    def _same_author_and_channel(message: discord.Message) -> bool:
        return message.author.id == interaction.user.id and message.channel.id == interaction.channel.id

    await interaction.response.send_message(
        "📅 Donne-moi une date et une heure, ce n'est pas obligatoire.\n"
        "Format : `JJ/MM/AAAA` puis, en option, l'heure (`HH:MM` ou `HHh`) — ex: `24/01/2026`, `24/01/2026 4h`.\n"
        "Réponds `aucune` pour tout voir sans filtre, ou `annuler` pour abandonner."
        if LANG == "fr"
        else "📅 Give me a date and time, this is optional.\n"
        "Format: `DD/MM/YYYY` then, optionally, the time (`HH:MM` or `HHh`) — e.g.: `24/01/2026`, `24/01/2026 4h`.\n"
        "Reply `none` to see everything unfiltered, or `cancel` to abort."
    )

    try:
        reply_date = await bot.wait_for("message", check=_same_author_and_channel, timeout=60)
    except asyncio.TimeoutError:
        await interaction.followup.send("⏱️ Délai dépassé, commande annulée.")
        return

    content_date = reply_date.content.strip()
    if content_date.lower() in ("annuler", "cancel"):
        await interaction.followup.send("❌ Annulé.")
        return

    date_filtre: typing.Optional[date_cls] = None
    heure_filtre: typing.Optional[tuple[int, typing.Optional[int]]] = None

    if content_date.lower() not in ("aucune", "aucun", "non", "none", "-", ""):
        tokens = content_date.replace("_", " ").split()

        date_filtre = _parse_date_fr(tokens[0])
        if date_filtre is None:
            await interaction.followup.send(
                "❌ Date invalide, format attendu `JJ/MM/AAAA` (ex: `24/01/2026`)."
            )
            return

        if len(tokens) >= 2:
            heure_filtre = _parse_heure_fr(tokens[1])
            if heure_filtre is None:
                await interaction.followup.send(
                    "❌ Heure invalide, format attendu `HH:MM` ou `HHh` (ex: `14:30`, `4h`)."
                )
                return

    db_guild = get_db_guild()
    if db_guild is None:
        await interaction.followup.send("❌ Serveur base de données introuvable (AUDIT_DB_GUILD_ID mal configuré ou bot absent).")
        return

    try:
        index_channel = await get_or_create_full_log_index_channel(db_guild)
        thread = await _find_full_log_thread(index_channel, identifiant_int)
    except Exception:
        log.exception(f"Erreur lors de la recherche du fil de logs complets pour {identifiant_int}.")
        await interaction.followup.send("❌ Erreur lors de la recherche du fil de logs.")
        return

    if thread is None:
        await interaction.followup.send(f"ℹ️ Aucun log trouvé pour l'identifiant `{identifiant_int}`.")
        return

    try:
        entries = await _collect_full_log_entries(thread)
    except Exception:
        log.exception(f"Erreur lors de la lecture du fil de logs complets pour {identifiant_int}.")
        await interaction.followup.send("❌ Erreur lors de la lecture du fil de logs.")
        return

    matches = []
    for entry in entries:
        dt_paris = entry["embed_message"].created_at.astimezone(PARIS_TZ)
        if date_filtre is not None and dt_paris.date() != date_filtre:
            continue
        if heure_filtre is not None:
            heure, minute = heure_filtre
            if dt_paris.hour != heure:
                continue
            if minute is not None and dt_paris.minute != minute:
                continue
        matches.append((dt_paris, entry))

    if not matches:
        await interaction.followup.send(f"ℹ️ Aucun message ne correspond aux critères pour `{identifiant_int}`.")
        return

    if len(matches) <= 10:
        await interaction.followup.send(f"📜 {len(matches)} message(s) trouvé(s) pour `{identifiant_int}` :")
        for dt_paris, entry in matches:
            embed_message = entry["embed_message"]

            files = []
            for att in embed_message.attachments:
                try:
                    files.append(await att.to_file())
                except Exception:
                    pass

            try:
                if files:
                    await interaction.channel.send(embed=entry["embed"], files=files)
                else:
                    await interaction.channel.send(embed=entry["embed"])
            except Exception:
                await interaction.channel.send(embed=entry["embed"])
                await interaction.channel.send(embed_message.jump_url)

            for att_msg in entry["attachment_messages"]:
                old_files = []
                for att in att_msg.attachments:
                    try:
                        old_files.append(await att.to_file())
                    except Exception:
                        pass
                if old_files:
                    try:
                        await interaction.channel.send(files=old_files)
                    except Exception:
                        await interaction.channel.send(att_msg.jump_url)
        return

    lines = [
        f"• {dt_paris.strftime('%d/%m/%Y %H:%M')} (Paris) — {entry['embed_message'].jump_url}"
        for dt_paris, entry in matches[:50]
    ]
    header = f"📜 {len(matches)} message(s) trouvé(s) pour `{identifiant_int}` (trop nombreux pour être réaffichés en détail, liens directs ci-dessous"
    header += ", 50 premiers) :" if len(matches) > 50 else ") :"
    description = "\n".join(lines)[:4000]
    embed = discord.Embed(title=header, description=description, color=0x2ECC71)
    await interaction.followup.send(embed=embed)


async def _iter_channel_threads(channel: discord.TextChannel):
    """Parcourt tous les fils (actifs puis archivés) d'un salon, tous membres
    confondus. Utilisé quand /recherche-logs est appelée sans `membre`."""
    for th in channel.threads:
        yield th
    try:
        async for th in channel.archived_threads(limit=None):
            yield th
    except Exception:
        pass


async def _date_debut_autocomplete(interaction: discord.Interaction, current: str):
    """Propose des dates au format JJ/MM/AAAA : « Aujourd'hui » en premier, puis
    les dates où un fil de logs contient déjà des messages pour le `membre`
    sélectionné (si renseigné). Reste un champ texte libre : toute autre date
    tapée à la main est acceptée."""
    try:
        guild = interaction.guild
        today = datetime.now(PARIS_TZ).date()
        dates_disponibles: list = [today]

        if guild is not None:
            channel_id = _get_setting(guild.id, "message_log_channel_id")
            channel = guild.get_channel(channel_id) if channel_id else None
            membre = getattr(interaction.namespace, "membre", None)
            if channel is not None and membre is not None:
                thread = await _find_message_log_thread(channel, membre.id)
                if thread is not None:
                    try:
                        async for msg in thread.history(limit=500, oldest_first=False):
                            d = msg.created_at.astimezone(PARIS_TZ).date()
                            if d not in dates_disponibles:
                                dates_disponibles.append(d)
                            if len(dates_disponibles) >= 25:
                                break
                    except Exception:
                        pass

        results = []
        for d in dates_disponibles[:25]:
            label = d.strftime("%d/%m/%Y")
            display = f"{label} ({'aujourd’hui' if d == today and LANG == 'fr' else 'today'})" if d == today else label
            if current and not label.startswith(current) and current not in display.lower():
                continue
            results.append(discord.app_commands.Choice(name=display, value=label))
        return results[:25]
    except Exception:
        log.exception("Erreur dans l'autocomplétion de date_debut.")
        return []


async def _heure_debut_autocomplete(interaction: discord.Interaction, current: str):
    """Propose les 24 heures pleines (00:00 à 23:00). Reste un champ texte libre."""
    try:
        results = []
        for h in range(24):
            label = f"{h:02d}:00"
            if current and current not in label:
                continue
            results.append(discord.app_commands.Choice(name=label, value=label))
        return results[:25]
    except Exception:
        log.exception("Erreur dans l'autocomplétion de heure_debut.")
        return []


@bot.tree.command(
    name="recherche-logs" if LANG == "fr" else "search-logs",
    description=(
        "Recherche dans les logs de messages de CE serveur : par membre, par date/heure, ou les deux"
        if LANG == "fr"
        else "Search THIS server's message logs: by member, by date/time, or both"
    ),
)
@discord.app_commands.describe(
    membre="Ne montrer que les messages de ce membre (optionnel)" if LANG == "fr"
    else "Only show messages from this member (optional)",
    date_debut="Date à consulter, format JJ/MM/AAAA (ex: 24/01/2026)" if LANG == "fr"
    else "Date to look up, format DD/MM/YYYY (e.g. 24/01/2026)",
    heure_debut="Heure précise à consulter (optionnel, sinon toute la journée)" if LANG == "fr"
    else "Specific hour to look up (optional, otherwise the whole day)",
)
@discord.app_commands.autocomplete(date_debut=_date_debut_autocomplete, heure_debut=_heure_debut_autocomplete)
async def recherche_logs_command(
    interaction: discord.Interaction,
    membre: discord.Member = None,
    date_debut: str = None,
    heure_debut: str = None,
):
    guild = interaction.guild

    if membre is None and date_debut is None:
        await interaction.response.send_message(
            "❌ Précise au moins un critère : un `membre`, ou une `date_debut` "
            "(sinon la recherche porterait sur tout l'historique du salon)."
            if LANG == "fr"
            else "❌ Give at least one filter: a `membre`, or a `date_debut` "
            "(otherwise the search would cover the channel's entire history).",
            ephemeral=True,
        )
        return

    if not _module_enabled(guild.id, "messagelog"):
        await interaction.response.send_message(
            "❌ Le module « Logs messages » n'est pas activé sur ce serveur (`/panel` > Modules)."
            if LANG == "fr"
            else "❌ The « Message logs » module isn't enabled on this server (`/panel` > Modules).",
            ephemeral=True,
        )
        return

    channel_id = _get_setting(guild.id, "message_log_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel is None:
        await interaction.response.send_message(
            "❌ Aucun salon de logs de messages n'est configuré sur ce serveur (`/panel` > Modules > Logs messages)."
            if LANG == "fr"
            else "❌ No message log channel is configured on this server (`/panel` > Modules > Message logs).",
            ephemeral=True,
        )
        return

    start_dt = end_dt = None
    if date_debut is not None:
        d = _parse_date_fr(date_debut)
        if d is None:
            await interaction.response.send_message(
                f"❌ Date invalide (`{date_debut}`), format attendu `JJ/MM/AAAA` (ex: `24/01/2026`)."
                if LANG == "fr"
                else f"❌ Invalid date (`{date_debut}`), expected format `DD/MM/YYYY` (e.g. `24/01/2026`).",
                ephemeral=True,
            )
            return

        if heure_debut:
            parsed = _parse_heure_fr(heure_debut)
            if parsed is None:
                await interaction.response.send_message(
                    f"❌ Heure invalide (`{heure_debut}`), format attendu `HH:MM` ou `HHh` (ex: `14:30`, `4h`)."
                    if LANG == "fr"
                    else f"❌ Invalid time (`{heure_debut}`), expected format `HH:MM` or `HHh` (e.g. `14:30`, `4h`).",
                    ephemeral=True,
                )
                return
            heure, _minute = parsed
            start_dt = datetime(d.year, d.month, d.day, heure, 0, 0, tzinfo=PARIS_TZ)
            end_dt = datetime(d.year, d.month, d.day, heure, 59, 59, tzinfo=PARIS_TZ)
        else:
            start_dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=PARIS_TZ)
            end_dt = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=PARIS_TZ)

    await interaction.response.defer(ephemeral=True, thinking=True)

    history_kwargs = {"oldest_first": True}
    if start_dt is not None:
        history_kwargs["after"] = start_dt.astimezone(timezone.utc)
        history_kwargs["before"] = end_dt.astimezone(timezone.utc)
        history_kwargs["limit"] = None
    else:
        history_kwargs["limit"] = 5000

    matches = []
    scanned = 0

    if membre is not None:
        thread = await _find_message_log_thread(channel, membre.id)
        if thread is None:
            await interaction.followup.send(
                "ℹ️ Aucun log de messages n'existe encore pour ce membre sur ce serveur."
                if LANG == "fr"
                else "ℹ️ No message log exists yet for this member on this server.",
                ephemeral=True,
            )
            return
        async for msg in thread.history(**history_kwargs):
            scanned += 1
            if msg.embeds and msg.embeds[0].footer and str(msg.embeds[0].footer.text or "").startswith("ID:"):
                matches.append(msg)
    else:
        threads_scanned = 0
        for thread in [t async for t in _iter_channel_threads(channel)]:
            threads_scanned += 1
            if threads_scanned > 200:
                break
            try:
                async for msg in thread.history(**history_kwargs):
                    scanned += 1
                    if msg.embeds and msg.embeds[0].footer and str(msg.embeds[0].footer.text or "").startswith("ID:"):
                        matches.append(msg)
            except Exception:
                continue
        matches.sort(key=lambda m: m.created_at)

    if not matches:
        capped_note = (
            f" (recherche limitée aux {scanned} messages les plus récents, sans filtre de date)"
            if start_dt is None and scanned >= history_kwargs["limit"]
            else ""
        )
        await interaction.followup.send(
            f"ℹ️ Aucun log ne correspond aux critères{capped_note}." if LANG == "fr"
            else f"ℹ️ No log matches the given filters{capped_note}.",
            ephemeral=True,
        )
        return

    lines = [
        f"• {msg.created_at.astimezone(PARIS_TZ).strftime('%d/%m/%Y %H:%M')} (Paris) — {msg.jump_url}"
        for msg in matches[:50]
    ]
    header = f"📜 {len(matches)} message(s) trouvé(s) dans {channel.mention}"
    header += " (trop nombreux pour être réaffichés en détail, 50 premiers liens ci-dessous) :" if len(matches) > 50 else " :"
    description = "\n".join(lines)[:4000]
    embed = discord.Embed(title=header, description=description, color=0x2ECC71)
    await interaction.followup.send(embed=embed, ephemeral=True)


SERVER_LOG_SCAN_LIMIT_NO_DATE = 5000
SERVER_LOG_SCAN_LIMIT_WITH_DATE = 20000


def _parse_server_log_message(msg: discord.Message) -> typing.Optional[dict]:
    if not msg.embeds:
        return None
    embed = msg.embeds[0]
    footer = embed.footer.text if embed.footer and embed.footer.text else ""
    m = _SERVER_LOG_FOOTER_RE.search(footer)
    if not m:
        return None
    return {
        "message": msg,
        "action": m.group(1),
        "actor": int(m.group(2)),
        "target": int(m.group(3)),
        "entry_id": m.group(4),
        "title": embed.title or "",
        "summary": embed.description or "",
    }


async def _server_log_date_autocomplete(interaction: discord.Interaction, current: str):
    today = datetime.now(PARIS_TZ).date()
    results = []
    for i in range(14):
        d = today - timedelta(days=i)
        label = d.strftime("%d/%m/%Y")
        display = f"{label} ({'aujourd’hui' if LANG == 'fr' else 'today'})" if i == 0 else label
        if current and current not in label:
            continue
        results.append(discord.app_commands.Choice(name=display, value=label))
    return results


class ServerLogSearchView(discord.ui.View):
    """Résultats de /recherche-logs-serveur, paginés (précédent / suivant)."""

    PER_PAGE = 8

    def __init__(self, user_id: int, title: str, lines: list, note: str = ""):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.title = title
        self.lines = lines
        self.note = note
        self.page = 0
        self._sync_buttons()

    @property
    def page_count(self) -> int:
        return max(1, (len(self.lines) + self.PER_PAGE - 1) // self.PER_PAGE)

    def build_embed(self) -> discord.Embed:
        chunk = self.lines[self.page * self.PER_PAGE:(self.page + 1) * self.PER_PAGE]
        embed = discord.Embed(title=self.title[:256], description="\n".join(chunk)[:4000], color=0x5865F2)
        footer = f"Page {self.page + 1}/{self.page_count}"
        if self.note:
            footer += f" — {self.note}"
        embed.set_footer(text=footer[:2048])
        return embed

    def _sync_buttons(self) -> None:
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.page_count - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ces résultats ne sont pas les tiens." if LANG == "fr" else "❌ These results aren't yours.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(self.page_count - 1, self.page + 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


@bot.tree.command(
    name="recherche-logs-serveur" if LANG == "fr" else "search-server-logs",
    description=(
        "Recherche dans les logs d'actions du serveur : par membre, type d'action, date/heure" if LANG == "fr"
        else "Search the server action logs: by member, action type, date/time"
    ),
)
@discord.app_commands.describe(
    membre="Membre concerné, comme auteur OU comme cible de l'action (optionnel)" if LANG == "fr"
    else "Member involved, as actor OR target of the action (optional)",
    identifiant="ID Discord d'un membre parti/banni (à la place de `membre`)" if LANG == "fr"
    else "Discord ID of a member who left/was banned (instead of `membre`)",
    role_membre="Le membre est l'auteur de l'action, sa cible, ou les deux (défaut)" if LANG == "fr"
    else "Member is the actor of the action, its target, or both (default)",
    categorie="Type d'action à afficher (optionnel)" if LANG == "fr" else "Type of action to show (optional)",
    date_debut="Date à consulter, format JJ/MM/AAAA (ex: 24/01/2026)" if LANG == "fr"
    else "Date to look up, format DD/MM/YYYY (e.g. 24/01/2026)",
    heure_debut="Heure précise (nécessite une date ; sinon toute la journée)" if LANG == "fr"
    else "Specific hour (needs a date; otherwise the whole day)",
)
@discord.app_commands.choices(
    role_membre=[
        discord.app_commands.Choice(name="Auteur de l'action" if LANG == "fr" else "Actor", value="actor"),
        discord.app_commands.Choice(name="Cible de l'action" if LANG == "fr" else "Target", value="target"),
        discord.app_commands.Choice(name="Les deux" if LANG == "fr" else "Both", value="both"),
    ],
    categorie=[
        discord.app_commands.Choice(name=(fr if LANG == "fr" else en)[:100], value=key)
        for key, (fr, en) in SERVER_LOG_CATEGORIES.items()
    ],
)
@discord.app_commands.autocomplete(date_debut=_server_log_date_autocomplete, heure_debut=_heure_debut_autocomplete)
async def recherche_logs_serveur_command(
    interaction: discord.Interaction,
    membre: discord.User = None,
    identifiant: str = None,
    role_membre: str = "both",
    categorie: str = None,
    date_debut: str = None,
    heure_debut: str = None,
):
    guild = interaction.guild

    if not _module_enabled(guild.id, "serverlog"):
        await interaction.response.send_message(
            "❌ Le module « Logs serveur » n'est pas activé sur ce serveur (`/panel` > Configuration serveur)."
            if LANG == "fr"
            else "❌ The « Server logs » module isn't enabled on this server (`/panel` > Server settings).",
            ephemeral=True,
        )
        return

    channel_id = _get_setting(guild.id, "server_log_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel is None:
        await interaction.response.send_message(
            "❌ Aucun salon de logs serveur n'est configuré (`/panel` > Configuration serveur > Salon de logs serveur)."
            if LANG == "fr"
            else "❌ No server log channel is configured (`/panel` > Server settings > Server log channel).",
            ephemeral=True,
        )
        return

    member_id = None
    if membre is not None:
        member_id = membre.id
    elif identifiant:
        if not identifiant.strip().isdigit():
            await interaction.response.send_message(
                "❌ Ce n'est pas un identifiant Discord valide (uniquement des chiffres)." if LANG == "fr"
                else "❌ Not a valid Discord ID (digits only).",
                ephemeral=True,
            )
            return
        member_id = int(identifiant.strip())

    start_dt = end_dt = None
    if heure_debut and not date_debut:
        await interaction.response.send_message(
            "❌ Précise aussi une `date_debut` avec l'heure." if LANG == "fr"
            else "❌ Please also give a `date_debut` with the time.",
            ephemeral=True,
        )
        return
    if date_debut:
        d = _parse_date_fr(date_debut)
        if d is None:
            await interaction.response.send_message(
                f"❌ Date invalide (`{date_debut}`), format attendu `JJ/MM/AAAA` (ex: `24/01/2026`)."
                if LANG == "fr"
                else f"❌ Invalid date (`{date_debut}`), expected format `DD/MM/YYYY` (e.g. `24/01/2026`).",
                ephemeral=True,
            )
            return
        if heure_debut:
            parsed = _parse_heure_fr(heure_debut)
            if parsed is None:
                await interaction.response.send_message(
                    f"❌ Heure invalide (`{heure_debut}`), format attendu `HH:MM` ou `HHh` (ex: `14:30`, `4h`)."
                    if LANG == "fr"
                    else f"❌ Invalid time (`{heure_debut}`), expected format `HH:MM` or `HHh` (e.g. `14:30`, `4h`).",
                    ephemeral=True,
                )
                return
            heure, _minute = parsed
            start_dt = datetime(d.year, d.month, d.day, heure, 0, 0, tzinfo=PARIS_TZ)
            end_dt = datetime(d.year, d.month, d.day, heure, 59, 59, tzinfo=PARIS_TZ)
        else:
            start_dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=PARIS_TZ)
            end_dt = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=PARIS_TZ)

    await interaction.response.defer(ephemeral=True, thinking=True)

    if start_dt is not None:
        limit = SERVER_LOG_SCAN_LIMIT_WITH_DATE
        history_kwargs = {
            "limit": limit, "oldest_first": True,
            "after": start_dt.astimezone(timezone.utc), "before": end_dt.astimezone(timezone.utc),
        }
    else:
        limit = SERVER_LOG_SCAN_LIMIT_NO_DATE
        history_kwargs = {"limit": limit, "oldest_first": False}

    matches = []
    scanned = 0
    capped = False
    try:
        sources = []
        if member_id is not None:
            member_thread = await _find_message_log_thread(channel, member_id)
            if member_thread is not None:
                sources.append(member_thread)
        else:
            async for th in _iter_channel_threads(channel):
                sources.append(th)
                if len(sources) >= 200:
                    break
        sources.append(channel)

        seen = set()
        for source in sources:
            source_count = 0
            try:
                async for msg in source.history(**history_kwargs):
                    scanned += 1
                    source_count += 1
                    parsed_entry = _parse_server_log_message(msg)
                    if parsed_entry is None:
                        continue
                    dedupe_key = parsed_entry["entry_id"] or (
                        parsed_entry["action"], parsed_entry["actor"], parsed_entry["target"],
                        int(msg.created_at.timestamp()),
                    )
                    if dedupe_key in seen:
                        continue
                    if categorie and _audit_category(parsed_entry["action"]) != categorie:
                        continue
                    if member_id is not None:
                        is_actor = parsed_entry["actor"] == member_id
                        is_target = parsed_entry["target"] == member_id
                        if role_membre == "actor" and not is_actor:
                            continue
                        if role_membre == "target" and not is_target:
                            continue
                        if role_membre not in ("actor", "target") and not (is_actor or is_target):
                            continue
                    seen.add(dedupe_key)
                    matches.append(parsed_entry)
            except discord.Forbidden:
                raise
            except Exception:
                log.exception(f"Lecture d'un fil de logs serveur impossible sur {guild.name}.")
                continue
            if source_count >= limit:
                capped = True
    except discord.Forbidden:
        await interaction.followup.send(
            f"❌ Je ne peux pas lire l'historique de {channel.mention} (permission manquante)." if LANG == "fr"
            else f"❌ I can't read the history of {channel.mention} (missing permission).",
            ephemeral=True,
        )
        return
    except Exception:
        log.exception(f"Erreur lors de la recherche dans les logs serveur de {guild.name}.")
        await interaction.followup.send(
            "❌ Erreur lors de la lecture des logs." if LANG == "fr" else "❌ Error while reading the logs.",
            ephemeral=True,
        )
        return

    if not matches:
        note = (
            (f" (recherche limitée aux {scanned} messages les plus récents)" if start_dt is None
             else f" (recherche limitée à {scanned} messages)")
            if capped and LANG == "fr"
            else (f" (search limited to the {scanned} most recent messages)" if capped else "")
        )
        await interaction.followup.send(
            f"ℹ️ Aucune action ne correspond aux critères{note}." if LANG == "fr"
            else f"ℹ️ No action matches the given filters{note}.",
            ephemeral=True,
        )
        return

    matches.sort(key=lambda e: e["message"].created_at, reverse=True)
    total = len(matches)
    matches = matches[:500]
    lines = []
    for e in matches:
        dt_paris = e["message"].created_at.astimezone(PARIS_TZ).strftime("%d/%m/%Y %H:%M")
        summary = e["summary"] if len(e["summary"]) <= 170 else e["summary"][:169] + "…"
        lines.append(f"`{dt_paris}` **{e['title']}**\n↳ {summary} — [{'voir' if LANG == 'fr' else 'view'}]({e['message'].jump_url})")

    title = (
        f"📜 {total} action(s) trouvée(s) dans #{channel.name}" if LANG == "fr"
        else f"📜 {total} action(s) found in #{channel.name}"
    )
    note_parts = []
    if total > 500:
        note_parts.append("500 plus récentes affichées" if LANG == "fr" else "500 most recent shown")
    if capped:
        note_parts.append(
            f"recherche limitée à {scanned} messages" if LANG == "fr" else f"search limited to {scanned} messages"
        )
    view = ServerLogSearchView(interaction.user.id, title, lines, " • ".join(note_parts))
    if view.page_count > 1:
        await interaction.followup.send(embed=view.build_embed(), view=view, ephemeral=True)
    else:
        await interaction.followup.send(embed=view.build_embed(), ephemeral=True)





SEVERITY_SCORE_PENALTY = {
    "CRITICAL": 22,
    "HIGH": 12,
    "MEDIUM": 6,
    "LOW": 3,
    "INFO": 1,
}

SECURITY_GRADES = [
    (95, "A+", 0x2ECC71, "Excellent — configuration exemplaire.", "Excellent — exemplary setup."),
    (85, "A", 0x27AE60, "Très bon niveau de sécurité.", "Very good security level."),
    (70, "B", 0x2ECC71, "Bon niveau, quelques points à corriger.", "Good level, a few points to fix."),
    (55, "C", 0xF1C40F, "Niveau moyen — des risques réels existent.", "Average level — real risks exist."),
    (35, "D", 0xE67E22, "Faible — plusieurs failles importantes.", "Weak — several significant flaws."),
    (0, "F", 0xE74C3C, "Critique — le serveur est vulnérable.", "Critical — the server is vulnerable."),
]

AUDIT_CATEGORY_META = {
    "roles": {"emoji": "🎭", "fr": "Rôles, permissions & salons", "en": "Roles, permissions & channels"},
    "guild_settings": {"emoji": "⚙️", "fr": "Réglages du serveur", "en": "Server settings"},
    "bots_webhooks": {"emoji": "🤖", "fr": "Bots & webhooks", "en": "Bots & webhooks"},
    "bot_config": {"emoji": "🧩", "fr": "Configuration du bot", "en": "Bot configuration"},
    "recent_activity": {"emoji": "🕵️", "fr": "Activité récente suspecte", "en": "Recent suspicious activity"},
}
AUDIT_CATEGORY_ORDER = ["roles", "guild_settings", "bots_webhooks", "bot_config", "recent_activity"]


def compute_security_score(findings) -> int:
    """Calcule un score de 0 à 100 à partir de la liste de Finding."""
    penalty = sum(SEVERITY_SCORE_PENALTY.get(f.severity, 0) for f in findings)
    return max(0, 100 - penalty)


def security_grade(score: int):
    """Renvoie (lettre, couleur, phrase) pour un score donné."""
    for minimum, letter, color, phrase_fr, phrase_en in SECURITY_GRADES:
        if score >= minimum:
            return letter, color, (phrase_fr if LANG == "fr" else phrase_en)
    return "F", 0xE74C3C, ("Critique — le serveur est vulnérable." if LANG == "fr" else "Critical — the server is vulnerable.")


def _tag_category(findings, category: str):
    for f in findings:
        f.category = category
    return findings


async def run_full_security_audit(guild: discord.Guild):
    """Rassemble TOUTES les vérifications, catégorise chaque résultat, et
    renvoie (findings, score, grade_letter, grade_color)."""
    findings = []
    findings += _tag_category(await audit_guild(guild, lang=LANG, bot_member=guild.me), "roles")
    findings += _tag_category(audit_bots(guild, lang=LANG), "bots_webhooks")
    findings += _tag_category(await audit_webhooks(guild, lang=LANG), "bots_webhooks")
    findings += _tag_category(await audit_recent_activity(guild, lang=LANG), "recent_activity")
    findings += _tag_category(await audit_bot_config(guild, lang=LANG), "bot_config")

    score = compute_security_score(findings)
    letter, color, _phrase = security_grade(score)
    return findings, score, letter, color


def build_audit_hero_embed(guild: discord.Guild, findings, score: int, letter: str, color: int) -> discord.Embed:
    """Carte de résumé en tête du rapport : la seule chose qu'un admin
    pressé a besoin de lire pour comprendre où en est son serveur."""
    bar_filled = round(score / 10)
    bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)

    counts = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    count_line = "   ".join(
        f"{SEVERITY_META[sev]['emoji']} {counts[sev]}" for sev in SEVERITY_ORDER if counts.get(sev)
    ) or ("Aucun problème 🎉" if LANG == "fr" else "No issues 🎉")

    _, _, phrase = security_grade(score)

    embed = discord.Embed(
        title=(f"🏆 Audit de sécurité — {guild.name}" if LANG == "fr" else f"🏆 Security audit — {guild.name}"),
        description=f"# {letter}   •   {score}/100\n{bar}\n*{phrase}*\n\n{count_line}",
        color=color,
    )

    worst = sorted(findings, key=lambda f: SEVERITY_ORDER.index(f.severity))[:3]
    if worst:
        lines = []
        for f in worst:
            meta = SEVERITY_META[f.severity]
            lines.append(f"{meta['emoji']} **{f.title}**")
        embed.add_field(
            name=("🎯 À corriger en priorité" if LANG == "fr" else "🎯 Fix these first"),
            value="\n".join(lines),
            inline=False,
        )

    embed.set_footer(
        text=(
            "Détail complet ci-dessous, classé par thème · Utilise /configuration-complete "
            "(ou le panel) pour corriger automatiquement une partie de ces points."
            if LANG == "fr"
            else "Full detail below, sorted by theme · Use /configuration-complete "
            "(or the panel) to automatically fix some of these points."
        )
    )
    return embed


def _finding_field(f) -> tuple:
    """Formate un Finding en (nom, valeur) lisible, sans jargon "Risque:/Fix:"."""
    meta = SEVERITY_META[f.severity]
    name = f"{meta['emoji']} {f.title}"[:256]
    value = f"{f.risk}\n**{'🔧 Correction' if LANG == 'fr' else '🔧 Fix'} :** {f.fix}"
    if len(value) > 1024:
        value = value[:1000] + "…"
    return name, value


def build_audit_category_embeds(guild: discord.Guild, findings) -> list:
    """Un embed par catégorie (thème), triée en interne par sévérité, avec
    une couleur qui reflète le pire problème du groupe. Les catégories sans
    aucun problème sont simplement omises (pas de bruit inutile)."""
    embeds = []
    by_category = {cat: [] for cat in AUDIT_CATEGORY_ORDER}
    for f in findings:
        by_category.setdefault(getattr(f, "category", "roles"), []).append(f)

    for cat in AUDIT_CATEGORY_ORDER:
        items = by_category.get(cat) or []
        if not items:
            continue
        items_sorted = sorted(items, key=lambda f: SEVERITY_ORDER.index(f.severity))
        meta = AUDIT_CATEGORY_META[cat]
        worst_color = SEVERITY_META[items_sorted[0].severity]["color"]

        current = discord.Embed(
            title=f"{meta['emoji']} {meta[LANG]}",
            color=worst_color,
        )
        field_count = 0
        char_count = 0
        for f in items_sorted:
            name, value = _finding_field(f)
            added_len = len(name) + len(value)
            if field_count >= 20 or (char_count + added_len) > 5200:
                embeds.append(current)
                current = discord.Embed(title=f"{meta['emoji']} {meta[LANG]} ({'suite' if LANG == 'fr' else 'cont.'})", color=worst_color)
                field_count = 0
                char_count = 0
            current.add_field(name=name, value=value, inline=False)
            field_count += 1
            char_count += added_len
        embeds.append(current)

    return embeds


def build_pretty_audit_embeds(guild: discord.Guild, findings, score: int, letter: str, color: int, requester: str = None) -> list:
    hero = build_audit_hero_embed(guild, findings, score, letter, color)
    if requester:
        hero.set_author(name=(f"Relancé par {requester}" if LANG == "fr" else f"Re-run by {requester}"))

    if not findings:
        hero.add_field(
            name=("✅ Rien à signaler" if LANG == "fr" else "✅ Nothing to report"),
            value=(
                "Aucun problème détecté sur les points vérifiés. Continue de relancer l'audit "
                "régulièrement : la configuration du serveur évolue avec le temps."
                if LANG == "fr"
                else "No issues detected on the checked points. Keep re-running the audit "
                "regularly: the server's configuration changes over time."
            ),
            inline=False,
        )
        return [hero]

    return [hero] + build_audit_category_embeds(guild, findings)


async def run_audit_and_post(guild: discord.Guild, requester: str = None):
    """Remplace l'ancienne fonction du même nom (redéfinie ici) : lance TOUS
    les contrôles (existants + nouveaux) et poste le rapport redessiné dans
    le salon d'audit. /audit-securite et le bouton du /panel utilisent cette
    version automatiquement, sans rien avoir à changer de leur côté."""
    channel = await get_or_create_audit_channel(guild)
    findings, score, letter, color = await run_full_security_audit(guild)
    embeds = build_pretty_audit_embeds(guild, findings, score, letter, color, requester=requester)
    await _send_embeds_safely(channel, embeds)
    return channel



WIDGET_ENABLED_FINDING = {
    "severity": "LOW",
    "fr": {
        "label": "Le widget public du serveur est activé",
        "risk": "Le widget expose publiquement (sur un site tiers, sans connexion Discord) le nom du serveur, son icône et la liste des membres en ligne, à n'importe qui possédant le lien.",
        "fix": "Si ce n'est pas nécessaire, désactive-le : Paramètres du serveur > Widget.",
    },
    "en": {
        "label": "The server's public widget is enabled",
        "risk": "The widget publicly exposes (on a third-party site, without a Discord login) the server name, icon and list of online members to anyone with the link.",
        "fix": "If not needed, disable it: Server Settings > Widget.",
    },
}

NO_MESSAGE_LOG_FINDING = {
    "severity": "MEDIUM",
    "fr": {
        "label": "Aucun salon de logs de messages configuré",
        "risk": "Sans logs de messages, il est impossible de retrouver un message supprimé ou modifié après coup — un point aveugle en cas d'incident (modération, litige, enquête).",
        "fix": "Configure-le via `/panel` > Configuration serveur > Salon de logs de messages, ou laisse `/configuration-complete` le créer pour toi.",
    },
    "en": {
        "label": "No message log channel configured",
        "risk": "Without message logs, a deleted or edited message can't be recovered afterwards — a blind spot in case of an incident (moderation, dispute, investigation).",
        "fix": "Configure it via `/panel` > Server settings > Message log channel, or let `/configuration-complete` create it for you.",
    },
}

NO_SERVER_LOG_FINDING = {
    "severity": "MEDIUM",
    "fr": {
        "label": "Aucun salon de logs d'actions serveur configuré",
        "risk": "Sans ce salon, les actions de modération et les événements serveur (rôles, salons, sanctions...) ne sont pas centralisés ni consultables via `/recherche-historique`.",
        "fix": "Configure-le via `/panel` > Configuration serveur > Salon de logs serveur, ou laisse `/configuration-complete` le créer pour toi.",
    },
    "en": {
        "label": "No server action log channel configured",
        "risk": "Without this channel, moderation actions and server events (roles, channels, sanctions...) aren't centralized or searchable via `/recherche-historique`.",
        "fix": "Configure it via `/panel` > Server settings > Server log channel, or let `/configuration-complete` create it for you.",
    },
}

NO_OWNER_ROLE_FINDING = {
    "severity": "LOW",
    "fr": {
        "label": "Aucun rôle Fondateur défini pour le bot",
        "risk": "Sans rôle Fondateur, seuls le propriétaire réel du serveur et les administrateurs Discord ont accès complet aux commandes sensibles du bot — ce qui peut être trop restrictif pour une équipe de confiance.",
        "fix": "Optionnel : définis-le via `/panel` > Configuration du staff > Rôle Fondateur, si tu veux déléguer sans donner Administrateur Discord.",
    },
    "en": {
        "label": "No Founder role defined for the bot",
        "risk": "Without a Founder role, only the real server owner and Discord administrators get full access to the bot's sensitive commands — which can be too restrictive for a trusted team.",
        "fix": "Optional: set it via `/panel` > Staff settings > Founder role, if you want to delegate without granting Discord Administrator.",
    },
}

MOD_REQUEST_MISCONFIGURED_FINDING = {
    "severity": "LOW",
    "fr": {
        "label": "Système de demandes de sanction activé mais sans salon défini",
        "risk": "Le système est activé (`mod_request_enabled`) mais aucun salon n'est défini pour recevoir les demandes : elles risquent de se perdre.",
        "fix": "Configure un salon via `/panel`, ou laisse `/configuration-complete` le créer pour toi.",
    },
    "en": {
        "label": "Sanction-request system enabled but no channel set",
        "risk": "The system is enabled (`mod_request_enabled`) but no channel is set to receive requests: they may be lost.",
        "fix": "Configure a channel via `/panel`, or let `/configuration-complete` create one for you.",
    },
}

NO_MIN_ACCOUNT_AGE_FINDING = {
    "severity": "MEDIUM",
    "fr": {
        "label": "Aucun âge minimum de compte requis pour rejoindre",
        "risk": "Sans âge minimum, des comptes créés à la volée (souvent utilisés pour le raid ou le spam) peuvent rejoindre immédiatement le serveur sans aucun frein.",
        "fix": "Définis une valeur raisonnable (ex : 24h) via `/panel` > Configuration serveur, ou laisse `/configuration-complete` appliquer une valeur par défaut sûre.",
    },
    "en": {
        "label": "No minimum account age required to join",
        "risk": "Without a minimum age, freshly created accounts (often used for raiding or spam) can join the server immediately with no friction at all.",
        "fix": "Set a reasonable value (e.g. 24h) via `/panel` > Server settings, or let `/configuration-complete` apply a safe default.",
    },
}

TOO_FEW_STAFF_FINDING = {
    "severity": "INFO",
    "fr": {
        "label": "Une seule personne (ou aucune) dispose de droits d'administration effectifs",
        "risk": "En cas d'indisponibilité (compte piraté, perte d'accès, absence), plus personne ne peut administrer le serveur ni réagir à un incident.",
        "fix": "Assure-toi qu'au moins une deuxième personne de confiance a un accès d'administration ou le rôle Fondateur du bot.",
    },
    "en": {
        "label": "Only one person (or none) has effective administration rights",
        "risk": "If that person becomes unavailable (hacked account, lost access, absence), nobody else can administer the server or respond to an incident.",
        "fix": "Make sure at least one more trusted person has admin access or the bot's Founder role.",
    },
}


async def audit_bot_config(guild: discord.Guild, lang: str = "fr"):
    """Vérifie que la configuration DU BOT (pas seulement celle de Discord)
    ne laisse pas de trous béants : logs absents, pas d'âge minimum, etc."""
    findings = []

    if guild.widget_enabled:
        findings.append(_mk(WIDGET_ENABLED_FINDING, lang))

    if not _get_setting(guild.id, "message_log_channel_id"):
        findings.append(_mk(NO_MESSAGE_LOG_FINDING, lang))

    if not _get_setting(guild.id, "server_log_channel_id"):
        findings.append(_mk(NO_SERVER_LOG_FINDING, lang))

    if not _get_setting(guild.id, "owner_role_id"):
        findings.append(_mk(NO_OWNER_ROLE_FINDING, lang))

    if _get_setting(guild.id, "mod_request_enabled") and not _get_setting(guild.id, "mod_request_channel_id"):
        findings.append(_mk(MOD_REQUEST_MISCONFIGURED_FINDING, lang))

    if not _get_setting(guild.id, "min_account_age_hours"):
        findings.append(_mk(NO_MIN_ACCOUNT_AGE_FINDING, lang))

    effective_admin_count = 0
    owner_role_id = _get_setting(guild.id, "owner_role_id")
    for member in guild.members:
        if member.bot:
            continue
        if member.id == guild.owner_id or member.guild_permissions.administrator:
            effective_admin_count += 1
        elif owner_role_id and any(r.id == owner_role_id for r in member.roles):
            effective_admin_count += 1
    if effective_admin_count <= 1:
        findings.append(_mk(TOO_FEW_STAFF_FINDING, lang))

    return findings

AUTOCONFIG_EVERYONE_DANGEROUS_KEYS = [
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "manage_webhooks", "manage_messages", "mention_everyone",
    "kick_members", "ban_members", "manage_nicknames",
]


async def _autoconfig_create_log_channel(guild: discord.Guild, *, name: str, setting_key: str) -> discord.TextChannel:
    everyone = guild.default_role
    overwrites = {
        everyone: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, embed_links=True, read_message_history=True, manage_messages=True
        ),
    }
    for role in guild.roles:
        if role.permissions.administrator and not role.is_default():
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)
    channel = await guild.create_text_channel(
        name=name,
        overwrites=overwrites,
        reason="Auto-config : création d'un salon de logs manquant",
    )
    _set_setting(guild.id, setting_key, channel.id)
    return channel


async def _autoconfig_fix_message_log(guild: discord.Guild) -> str:
    channel = await _autoconfig_create_log_channel(
        guild,
        name="📝-logs-messages" if LANG == "fr" else "📝-message-logs",
        setting_key="message_log_channel_id",
    )
    return f"#{channel.name}"


async def _autoconfig_fix_server_log(guild: discord.Guild) -> str:
    channel = await _autoconfig_create_log_channel(
        guild,
        name="📋-logs-serveur" if LANG == "fr" else "📋-server-logs",
        setting_key="server_log_channel_id",
    )
    return f"#{channel.name}"


async def _autoconfig_fix_mod_request(guild: discord.Guild) -> str:
    everyone = guild.default_role
    overwrites = {
        everyone: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, embed_links=True, read_message_history=True
        ),
    }
    for role in guild.roles:
        if role.permissions.administrator and not role.is_default():
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    channel = await guild.create_text_channel(
        name="🚨-demandes-sanction" if LANG == "fr" else "🚨-sanction-requests",
        overwrites=overwrites,
        reason="Auto-config : création du salon de demandes de sanction",
    )
    _set_setting(guild.id, "mod_request_channel_id", channel.id)
    _set_setting(guild.id, "mod_request_enabled", True)
    return f"#{channel.name}"


async def _autoconfig_fix_everyone_perms(guild: discord.Guild) -> str:
    everyone = guild.default_role
    perms = everyone.permissions
    changed = [key for key in AUTOCONFIG_EVERYONE_DANGEROUS_KEYS if getattr(perms, key, False)]
    if changed:
        updated = discord.Permissions(perms.value)
        for key in changed:
            setattr(updated, key, False)
        await everyone.edit(permissions=updated, reason="Auto-config : retrait de permissions dangereuses de @everyone")
    return ", ".join(changed) if changed else ("aucune" if LANG == "fr" else "none")



SECURE_CHANNEL_DANGEROUS_KEYS = [
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "manage_webhooks", "manage_messages", "mention_everyone",
    "kick_members", "ban_members", "moderate_members",
]


FULL_SETUP_VERIFICATION_LEVEL = discord.VerificationLevel.highest
FULL_SETUP_SLOWMODE_SECONDS = 5
GENERAL_CHANNEL_NAME = "général" if LANG == "fr" else "general"

GENERAL_CHANNEL_WELCOME = (
    "👋 **Bienvenue sur {guild} !**\n\n"
    "Ce salon a été créé et paramétré automatiquement par le bot :\n"
    "• Lenteur ({slowmode}s) activée pour limiter le spam.\n"
    "• Vérification, filtre de contenu et widget réglés au niveau le plus strict.\n\n"
    "Utilise `/aide` pour tout comprendre, ou `/panel` pour ajuster ces réglages."
    if LANG == "fr"
    else "👋 **Welcome to {guild}!**\n\n"
    "This channel was created and configured automatically by the bot:\n"
    "• Slowmode ({slowmode}s) enabled to limit spam.\n"
    "• Verification, content filter and widget set to the strictest level.\n\n"
    "Use `/aide` to understand everything, or `/panel` to adjust these settings."
)


async def _full_setup_apply(guild: discord.Guild) -> dict:
    """Applique TOUT d'un coup, sans sélection : réglages extrêmes, nettoyage
    des permissions, rôles, logs et salon général paramétré. Renvoie un dict
    de sections -> lignes de résultat (pour un embed détaillé et groupé)."""
    results = {"guild": [], "roles": [], "channels": [], "logs": []}

    try:
        kwargs = {}
        if guild.verification_level != FULL_SETUP_VERIFICATION_LEVEL:
            kwargs["verification_level"] = FULL_SETUP_VERIFICATION_LEVEL
        if int(guild.explicit_content_filter.value) != 2:
            kwargs["explicit_content_filter"] = discord.ContentFilter.all_members
        if guild.widget_enabled:
            kwargs["widget_enabled"] = False
        if kwargs:
            await guild.edit(reason="Configuration complète en un clic", **kwargs)
        _set_setting(guild.id, "min_account_age_hours", 24)
        results["guild"].append(
            "✅ Vérification **Extrême**, filtre de contenu **tous les membres**, widget désactivé, âge minimum de compte 24h."
            if LANG == "fr"
            else "✅ **Highest** verification, content filter for **all members**, widget disabled, 24h minimum account age."
        )
    except discord.Forbidden:
        results["guild"].append("❌ Permission manquante pour les réglages serveur." if LANG == "fr" else "❌ Missing permission for server settings.")
    except Exception:
        log.exception(f"Configuration complète : échec réglages serveur sur {guild.name}.")
        results["guild"].append("❌ Erreur lors des réglages serveur." if LANG == "fr" else "❌ Error updating server settings.")

    try:
        detail = await _autoconfig_fix_everyone_perms(guild)
        results["guild"].append(
            (f"✅ Permissions retirées de @everyone : {detail}." if detail not in ("aucune", "none")
             else "✅ @everyone était déjà propre.")
            if LANG == "fr"
            else (f"✅ Permissions removed from @everyone: {detail}." if detail != "none" else "✅ @everyone was already clean.")
        )
    except discord.Forbidden:
        results["guild"].append("❌ Permission manquante pour modifier @everyone." if LANG == "fr" else "❌ Missing permission to edit @everyone.")
    except Exception as e:
        log.exception(f"Configuration complète : échec correction @everyone sur {guild.name}.")
        results["guild"].append(f"❌ {'Erreur' if LANG == 'fr' else 'Error'} @everyone ({e.__class__.__name__}).")

    fixed, failed = 0, 0
    for channel in guild.channels:
        try:
            overwrite = channel.overwrites_for(guild.default_role)
        except Exception:
            continue
        bad_keys = [k for k in SECURE_CHANNEL_DANGEROUS_KEYS if getattr(overwrite, k, None) is True]
        if not bad_keys:
            continue
        try:
            for key in bad_keys:
                setattr(overwrite, key, None)
            await channel.set_permissions(guild.default_role, overwrite=overwrite, reason="Configuration complète en un clic")
            fixed += 1
        except discord.Forbidden:
            failed += 1
        except Exception:
            log.exception(f"Configuration complète : échec permissions salon {channel} sur {guild.name}.")
            failed += 1
    if fixed or failed:
        line = f"✅ {fixed} salon(s) corrigé(s)" if LANG == "fr" else f"✅ {fixed} channel(s) fixed"
        if failed:
            line += f", ❌ {failed} " + ("échec(s)." if LANG == "fr" else "failure(s).")
        results["channels"].append(line)

    slowed = 0
    for channel in guild.text_channels:
        if channel.slowmode_delay == 0:
            try:
                await channel.edit(slowmode_delay=FULL_SETUP_SLOWMODE_SECONDS, reason="Configuration complète en un clic")
                slowed += 1
            except Exception:
                pass
    if slowed:
        results["channels"].append(
            f"✅ Lenteur de {FULL_SETUP_SLOWMODE_SECONDS}s appliquée à {slowed} salon(s)." if LANG == "fr"
            else f"✅ {FULL_SETUP_SLOWMODE_SECONDS}s slowmode applied to {slowed} channel(s)."
        )

    try:
        was_enabled = _module_enabled(guild.id, "verification")
        if not was_enabled:
            _set_setting(guild.id, "module_verification_enabled", True)
        verified_role, unverified_role, updated = await _auto_setup_verification(guild)
        results["roles"].append(
            (
                f"✅ Vérification activée : rôles **{verified_role.name}** / **{unverified_role.name}** "
                f"prêts, {updated} salon(s) masqué(s) au rôle non vérifié (personnalisable via `/panel`)."
                if not was_enabled else
                f"✅ Vérification (déjà activée) : rôles **{verified_role.name}** / **{unverified_role.name}** "
                f"resynchronisés, {updated} salon(s) mis à jour."
            ) if LANG == "fr" else (
                f"✅ Verification enabled: **{verified_role.name}** / **{unverified_role.name}** roles ready, "
                f"{updated} channel(s) hidden from the unverified role (customize via `/panel`)."
                if not was_enabled else
                f"✅ Verification (already enabled): **{verified_role.name}** / **{unverified_role.name}** "
                f"roles resynced, {updated} channel(s) updated."
            )
        )
    except discord.Forbidden:
        results["roles"].append(
            "❌ Permission manquante pour configurer la vérification (rôles/salons)." if LANG == "fr"
            else "❌ Missing permission to configure verification (roles/channels)."
        )
    except Exception:
        log.exception(f"Configuration complète : échec de l'auto-configuration de la vérification sur {guild.name}.")
        results["roles"].append(
            "❌ Erreur lors de la configuration de la vérification." if LANG == "fr"
            else "❌ Error configuring verification."
        )

    for needed, fn, label in (
        (not _get_setting(guild.id, "message_log_channel_id"), _autoconfig_fix_message_log, "salon de logs de messages" if LANG == "fr" else "message log channel"),
        (not _get_setting(guild.id, "server_log_channel_id"), _autoconfig_fix_server_log, "salon de logs serveur" if LANG == "fr" else "server log channel"),
    ):
        if not needed:
            continue
        try:
            created = await fn(guild)
            results["logs"].append(f"✅ {label.capitalize()} créé : {created}." if LANG == "fr" else f"✅ {label.capitalize()} created: {created}.")
        except discord.Forbidden:
            results["logs"].append(f"❌ Permission manquante pour créer le {label}." if LANG == "fr" else f"❌ Missing permission to create the {label}.")
        except Exception as e:
            log.exception(f"Configuration complète : échec création {label} sur {guild.name}.")
            results["logs"].append(f"❌ {'Erreur' if LANG == 'fr' else 'Error'} {label} ({e.__class__.__name__}).")

    if _get_setting(guild.id, "mod_request_enabled") and not _get_setting(guild.id, "mod_request_channel_id"):
        try:
            created = await _autoconfig_fix_mod_request(guild)
            results["logs"].append(f"✅ Salon de demandes de sanction créé : {created}." if LANG == "fr" else f"✅ Sanction-request channel created: {created}.")
        except Exception as e:
            log.exception(f"Configuration complète : échec création salon de demandes sur {guild.name}.")
            results["logs"].append(f"❌ {'Erreur' if LANG == 'fr' else 'Error'} salon de demandes ({e.__class__.__name__}).")

    general = discord.utils.get(guild.text_channels, name=GENERAL_CHANNEL_NAME.replace(" ", "-").lower())
    if general is None:
        try:
            general = await guild.create_text_channel(
                name=GENERAL_CHANNEL_NAME,
                slowmode_delay=FULL_SETUP_SLOWMODE_SECONDS,
                reason="Configuration complète en un clic : création du salon général",
            )
            welcome = GENERAL_CHANNEL_WELCOME.format(
                guild=guild.name, slowmode=FULL_SETUP_SLOWMODE_SECONDS,
            )
            await general.send(welcome)
            results["channels"].append(
                f"✅ Salon {general.mention} créé et paramétré (message de bienvenue posté)." if LANG == "fr"
                else f"✅ {general.mention} channel created and configured (welcome message posted)."
            )
        except discord.Forbidden:
            results["channels"].append("❌ Permission manquante pour créer le salon général." if LANG == "fr" else "❌ Missing permission to create the general channel.")
        except Exception as e:
            log.exception(f"Configuration complète : échec création salon général sur {guild.name}.")
            results["channels"].append(f"❌ {'Erreur' if LANG == 'fr' else 'Error'} salon général ({e.__class__.__name__}).")

    return results


def _full_setup_results_embed(guild: discord.Guild, results: dict) -> discord.Embed:
    embed = discord.Embed(
        title=("✅ Configuration complète terminée" if LANG == "fr" else "✅ Full setup complete"),
        description=(f"Tout a été paramétré automatiquement sur **{guild.name}**." if LANG == "fr" else f"Everything was configured automatically on **{guild.name}**."),
        color=0x2ECC71,
    )
    section_titles = {
        "guild": ("⚙️ Sécurité & réglages" if LANG == "fr" else "⚙️ Security & settings"),
        "roles": ("🎭 Rôles" if LANG == "fr" else "🎭 Roles"),
        "channels": ("📺 Salons" if LANG == "fr" else "📺 Channels"),
        "logs": ("📝 Journalisation" if LANG == "fr" else "📝 Logging"),
    }
    for key, title in section_titles.items():
        lines = results.get(key) or []
        if lines:
            embed.add_field(name=title, value="\n".join(lines)[:1024], inline=False)
    if not any(results.values()):
        embed.description = "✅ " + ("Rien à faire, tout était déjà configuré." if LANG == "fr" else "Nothing to do, everything was already configured.")
    embed.set_footer(
        text=("Pense à assigner les rôles créés aux bonnes personnes, et relance /audit-securite pour voir la nouvelle note." if LANG == "fr"
              else "Remember to assign the newly created roles to the right people, and re-run /audit-securite to see the new grade.")
    )
    return embed


class FullSetupView(discord.ui.View):
    def __init__(self, author_id: int, guild: discord.Guild):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.guild = guild

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Seule la personne ayant lancé la configuration complète peut confirmer." if LANG == "fr"
                else "❌ Only the person who started the full setup can confirm.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

    @discord.ui.button(label="✅ Confirmer et tout configurer" if LANG == "fr" else "✅ Confirm and configure everything", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            "⏳ " + ("Configuration en cours, ça peut prendre un peu de temps sur les gros serveurs..." if LANG == "fr"
                     else "Setting up, this can take a moment on large servers..."),
            ephemeral=True,
        )
        results = await _full_setup_apply(self.guild)
        await interaction.followup.send(embed=_full_setup_results_embed(self.guild, results), ephemeral=True)

    @discord.ui.button(label="❌ Annuler" if LANG == "fr" else "❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=("Annulé — aucun changement appliqué." if LANG == "fr" else "Cancelled — no changes applied."),
            view=self,
        )


def _full_setup_intro_embed(guild: discord.Guild) -> discord.Embed:
    return discord.Embed(
        title=("🚀 Configuration complète en un clic" if LANG == "fr" else "🚀 One-click full setup"),
        description=(
            "Sécurise ET configure le serveur en une seule fois, sans rien à choisir :\n"
            "• Vérification **Extrême**, filtre de contenu, widget, âge minimum de compte 24h.\n"
            "• Nettoyage des permissions dangereuses (@everyone + salons).\n"
            f"• Lenteur ({FULL_SETUP_SLOWMODE_SECONDS}s) sur les salons qui n'en ont pas.\n"
            f"• Vérification activée : rôles **{VERIFIED_ROLE_DEFAULT_NAME}** / **{UNVERIFIED_ROLE_DEFAULT_NAME}** "
            "auto-créés, salons non privés masqués tant qu'on n'est pas vérifié (personnalisable ensuite via `/panel`).\n"
            "• Création des salons de logs manquants.\n"
            f"• Création du salon **{GENERAL_CHANNEL_NAME}** avec message de bienvenue posté automatiquement.\n\n"
            "**Aucun salon ou rôle existant n'est jamais supprimé ou renommé.**"
            if LANG == "fr"
            else "Secures AND configures the server at once, with nothing to choose:\n"
            "• **Highest** verification, content filter, widget, 24h minimum account age.\n"
            "• Cleans up dangerous permissions (@everyone + channels).\n"
            f"• Slowmode ({FULL_SETUP_SLOWMODE_SECONDS}s) on channels that don't have one.\n"
            f"• Enables verification: auto-creates **{VERIFIED_ROLE_DEFAULT_NAME}** / **{UNVERIFIED_ROLE_DEFAULT_NAME}** "
            "roles, hides non-private channels until verified (customizable later via `/panel`).\n"
            "• Creates any missing log channels.\n"
            f"• Creates the **{GENERAL_CHANNEL_NAME}** channel with an auto-posted welcome message.\n\n"
            "**No existing channel or role is ever deleted or renamed.**"
        ),
        color=0xE67E22,
    )


class ConfigQuickSetupButton(discord.ui.Button):
    """Bouton unique du panel : ouvre la confirmation de configuration
    complète (voir aussi /configuration-complete)."""

    def __init__(self, row: int):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Configuration complète (1 clic)" if LANG == "fr" else "Full setup (1 click)",
            emoji="🚀",
            row=row,
            custom_id="config_open_full_setup",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(t("no_perm"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=None,
            embed=_full_setup_intro_embed(interaction.guild),
            view=FullSetupView(interaction.user.id, interaction.guild),
        )


@bot.tree.command(
    name="configuration-complete" if LANG == "fr" else "full-setup",
    description=(
        "Configure TOUT le serveur en un seul clic : sécurité extrême, salons, rôles, logs, salon général"
        if LANG == "fr"
        else "Configures the ENTIRE server in one click: extreme security, channels, roles, logs, general channel"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def full_setup_command(interaction: discord.Interaction):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    await interaction.response.send_message(
        embed=_full_setup_intro_embed(interaction.guild),
        view=FullSetupView(interaction.user.id, interaction.guild),
        ephemeral=True,
    )



@bot.tree.command(
    name="parametres-recommandes" if LANG == "fr" else "recommended-settings",
    description=(
        "Affiche un guide des paramètres serveur recommandés (lecture seule, ne modifie rien)"
        if LANG == "fr"
        else "Shows a guide of recommended server settings (read-only, changes nothing)"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def recommended_settings_command(interaction: discord.Interaction):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return

    embed = discord.Embed(
        title=("📚 Paramètres serveur recommandés" if LANG == "fr" else "📚 Recommended server settings"),
        color=0x3498DB,
        description=(
            "Guide de référence — utilise `/configuration-complete` pour appliquer "
            "automatiquement la plupart de ces points."
            if LANG == "fr"
            else "Reference guide — use `/configuration-complete` to automatically apply "
            "most of these points."
        ),
    )
    rows = [
        ("Vérification" if LANG == "fr" else "Verification",
         "Élevé (compte vérifié + 10 min minimum)" if LANG == "fr" else "High (verified account + 10 min minimum)"),
        ("Filtre de contenu" if LANG == "fr" else "Content filter",
         "Tous les membres" if LANG == "fr" else "All members"),
        ("Widget public" if LANG == "fr" else "Public widget",
         "Désactivé, sauf besoin explicite" if LANG == "fr" else "Disabled, unless explicitly needed"),
        ("@everyone" if LANG == "fr" else "@everyone",
         "Jamais Administrateur / Gérer le serveur / rôles / salons / webhooks" if LANG == "fr"
         else "Never Administrator / Manage Server / roles / channels / webhooks"),
        ("Âge minimum de compte" if LANG == "fr" else "Minimum account age",
         "24h minimum, plus en période de raid" if LANG == "fr" else "24h minimum, more during a raid period"),
        ("Rôles Administrateur" if LANG == "fr" else "Administrator roles",
         "Le moins possible, jamais donné « par défaut » à un rôle de bienvenue" if LANG == "fr"
         else "As few as possible, never given \"by default\" to a welcome role"),
        ("Logs" if LANG == "fr" else "Logs",
         "Salon de logs de messages ET de logs serveur configurés" if LANG == "fr"
         else "Both a message log channel AND a server log channel configured"),
        ("Invitations" if LANG == "fr" else "Invites",
         "Éviter les invitations sans expiration ET sans limite d'utilisation" if LANG == "fr"
         else "Avoid invites with neither an expiry NOR a use limit"),
        ("Bots" if LANG == "fr" else "Bots",
         "Aucun bot non vérifié avec Administrateur ou des permissions sensibles" if LANG == "fr"
         else "No unverified bot with Administrator or sensitive permissions"),
    ]
    for name, value in rows:
        embed.add_field(name=name, value=value, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="synchroniser-commandes" if LANG == "fr" else "sync-commands",
    description=(
        "Force la resynchronisation des commandes slash sur CE serveur (dépannage)"
        if LANG == "fr"
        else "Force a resync of slash commands on THIS server (troubleshooting)"
    ),
)
@discord.app_commands.default_permissions(administrator=True)
async def sync_commands_command(interaction: discord.Interaction):
    if not _has_effective_administrator(interaction.user):
        await interaction.response.send_message(t("no_perm"), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    ok = await _sync_commands_for_guild(interaction.guild, attempts=2)
    if ok:
        await interaction.followup.send(
            "✅ Commandes resynchronisées sur ce serveur." if LANG == "fr"
            else "✅ Commands resynced on this server.",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            "❌ Échec de la synchronisation (voir les logs du bot). Réessaie dans quelques minutes."
            if LANG == "fr"
            else "❌ Sync failed (see bot logs). Try again in a few minutes.",
            ephemeral=True,
        )



def _help_support_invite_url() -> str:
    return os.environ.get("BOT_SUPPORT_SERVER_INVITE", "https://discord.gg/xkgP9rv84k").strip()


class OpenPanelButton(discord.ui.Button):
    """Raccourci qui ouvre directement /panel, DANS le même message, sans
    avoir à retaper la commande."""

    def __init__(self, row: int = 0):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Ouvrir le panel" if LANG == "fr" else "Open the panel",
            emoji="🛠️",
            row=row,
            custom_id="help_open_panel",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _has_effective_administrator(interaction.user):
            await interaction.response.send_message(
                (
                    "❌ Seuls les administrateurs (ou le rôle Fondateur du bot) peuvent ouvrir le panel. "
                    "Demande à un membre du staff de le faire, ou utilise le serveur de support si tu as besoin d'aide."
                )
                if LANG == "fr"
                else (
                    "❌ Only administrators (or the bot's Founder role) can open the panel. "
                    "Ask a staff member to do it, or use the support server if you need help."
                ),
                ephemeral=True,
            )
            return
        await interaction.response.edit_message(
            content=None,
            embed=await _build_config_panel_embed(interaction.guild),
            view=ConfigPanelView(),
        )


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(OpenPanelButton(row=0))
        invite = _help_support_invite_url()
        if invite:
            self.add_item(discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Serveur de support" if LANG == "fr" else "Support server",
                emoji="💬",
                url=invite,
                row=0,
            ))


def _build_help_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title=("🆘 Besoin d'aide ?" if LANG == "fr" else "🆘 Need help?"),
        description=(
            "Toute la configuration du bot passe par **`/panel`** : webhooks, liens, invitations, "
            "rôles staff, rôle Fondateur, liste blanche, mots interdits, audit de sécurité noté, "
            "auto-configuration et sécurisation complète du serveur — tout est regroupé au même endroit, "
            "avec des boutons, pas besoin de retenir 30 commandes différentes.\n\n"
            "Clique sur **Ouvrir le panel** ci-dessous pour y aller directement (réservé aux "
            "administrateurs / rôle Fondateur)."
            if LANG == "fr"
            else "All of the bot's configuration goes through **`/panel`**: webhooks, links, invites, "
            "staff roles, Founder role, whitelist, banned words, graded security audit, "
            "auto-configuration and full server hardening — everything lives in one place, "
            "with buttons, no need to remember 30 different commands.\n\n"
            "Click **Open the panel** below to jump straight there (administrators / Founder role only)."
        ),
        color=0x3498DB,
    )
    embed.add_field(
        name=("🔐 Sécurité" if LANG == "fr" else "🔐 Security"),
        value=(
            "`/audit-securite` — audit complet noté (A+ à F)\n"
            "`/configuration-complete` — configure tout le serveur en un clic\n"
            "`/parametres-recommandes` — guide des bonnes pratiques"
            if LANG == "fr"
            else "`/audit-securite` — full graded audit (A+ to F)\n"
            "`/configuration-complete` — configures the entire server in one click\n"
            "`/parametres-recommandes` — best-practices guide"
        ),
        inline=False,
    )
    embed.add_field(
        name=("⚙️ Tout configurer" if LANG == "fr" else "⚙️ Configure everything"),
        value=("`/panel` — le point d'entrée unique, avec des boutons" if LANG == "fr" else "`/panel` — the single entry point, with buttons"),
        inline=False,
    )
    embed.set_footer(
        text=(
            f"{guild.name} · Version {BOT_VERSION} · Besoin d'un coup de main humain ? Rejoins le serveur de support."
            if LANG == "fr"
            else f"{guild.name} · Version {BOT_VERSION} · Need human help? Join the support server."
        )
    )
    return embed


@bot.tree.command(
    name="aide" if LANG == "fr" else "help",
    description=(
        "Comment s'y retrouver avec le bot — raccourci vers /panel et lien du serveur de support"
        if LANG == "fr"
        else "How to find your way around the bot — shortcut to /panel and support server link"
    ),
)
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=_build_help_embed(interaction.guild),
        view=HelpView(),
        ephemeral=True,
    )


log.info(
    "Module avancé chargé : /audit-securite (refait), /configuration-complete, "
    "/parametres-recommandes, /aide — + boutons panel associés."
)

bot.run(TOKEN)