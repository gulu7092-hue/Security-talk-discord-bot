# 🛡️ Bot de Modération Discord

## Fonctionnalités

- ✅ **Anti gros mots** — supprime le message + infraction automatique
- ✅ **Anti liens suspects** — détecte les scams et faux Nitro
- ✅ **Anti-spam** — 5+ messages en 5 secondes = infraction
- ✅ **Système d'infractions** :
  - 15 infractions → Mute 1h
  - 20 infractions → Ban permanent automatique
- ✅ **Répond aux mentions** — dire "aide", "ping", "bonjour"...
- ✅ **Logs** dans le salon `#mod-logs`

## Commandes

| Commande | Permissions | Description |
|---|---|---|
| `!infractions @user` | Modérateur | Voir le nombre d'infractions |
| `!reset @user` | Admin | Remettre à zéro les infractions |
| `!warn @user <raison>` | Modérateur | Avertissement manuel |
| `!ban @user <raison>` | Ban Members | Ban manuel |
| `!kick @user <raison>` | Kick Members | Kick manuel |
| `!clear [nombre]` | Manage Messages | Supprimer des messages |

## Installation

### 1. Prérequis
- Python 3.10+
- Un token bot Discord

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Configurer le token
Créer un fichier `.env` :
```
DISCORD_BOT_TOKEN=ton_token_ici
```

Ou exporter la variable :
```bash
export DISCORD_BOT_TOKEN=ton_token_ici
```

### 4. Lancer le bot
```bash
python bot.py
```

## Déploiement sur Railway (recommandé, gratuit)

1. Aller sur [railway.app](https://railway.app) et créer un compte
2. Nouveau projet → "Deploy from GitHub repo"
3. Pousser ce dossier sur GitHub
4. Ajouter la variable d'environnement `DISCORD_BOT_TOKEN` dans Railway
5. Le bot tourne 24h/24 ✅

## Paramètres Discord requis

Dans le [Portail Développeur Discord](https://discord.com/developers/applications) :
- ✅ **Message Content Intent** activé
- ✅ **Server Members Intent** activé
- Permissions bot : `Administrator` (ou au minimum : Manage Messages, Ban Members, Kick Members, Manage Roles)

## Créer le salon de logs

Créer un salon texte appelé exactement **`mod-logs`** sur ton serveur pour recevoir les logs de modération.

## Personnalisation

Dans `bot.py`, tu peux modifier :
- `BANNED_WORDS` — liste des mots interdits
- `WARN_THRESHOLD` (défaut: 15) — infractions avant mute
- `BAN_THRESHOLD` (défaut: 20) — infractions avant ban
- `SUSPICIOUS_LINKS` — domaines suspects à bloquer
