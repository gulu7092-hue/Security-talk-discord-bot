import discord
from discord.ext import commands
import json
import os
import re
from datetime import datetime, timedelta

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = "!"
WARN_THRESHOLD = 15  # mute temporaire
BAN_THRESHOLD = 20   # ban permanent

# Mots interdits (à compléter)
BANNED_WORDS = [
    "connard", "enculé", "pute", "merde", "fdp", "ntm", "salope",
    "batard", "bâtard", "nique", "tg", "ta gueule"
]

# Insultes envers le bot
BOT_INSULTS = [
    "bot débile", "bot nul", "bot pourri", "bot con", "bot merdique",
    "débile", "nul", "pourri", "con", "merdique"
]

# Mots gentils
NICE_WORDS = ["merci", "s'il te plaît", "please", "svp", "merci beaucoup"]

# Liens suspects
SUSPICIOUS_LINKS = ["discord.gift", "free-nitro", "steamcommunity.ru", "bit.ly"]

# ─── INTENTS ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ─── DONNÉES EN MÉMOIRE ───────────────────────────────────────────────────────
infractions: dict[int, int] = {}              # user_id → count
spam_tracker: dict[int, list] = {}            # user_id → [timestamps]
friendliness_score: dict[int, int] = {}       # user_id → score (0-100)

# ─── UTILS ────────────────────────────────────────────────────────────────────
def get_infractions(user_id: int) -> int:
    return infractions.get(user_id, 0)

def get_friendliness_score(user_id: int) -> int:
    """Retourne le score d'amabilité (défaut 100)"""
    return friendliness_score.get(user_id, 100)

def update_friendliness(user_id: int, change: int):
    """Met à jour le score d'amabilité (min 0, max 100)"""
    current = get_friendliness_score(user_id)
    new_score = max(0, min(100, current + change))
    friendliness_score[user_id] = new_score
    print(f"[Friendliness] {user_id}: {current} → {new_score}")

def get_bot_tone(score: int) -> dict:
    """Retourne le ton du bot selon le score"""
    if score >= 80:
        return {
            "emoji": "😊",
            "greeting": "👋 Bonjour",
            "response": "Bien sûr !",
            "confused": "Hmm, je ne comprends pas... 🤔",
            "help": "Je suis là pour t'aider ! 💪"
        }
    elif score >= 60:
        return {
            "emoji": "😐",
            "greeting": "Salut",
            "response": "D'accord",
            "confused": "Je ne comprends pas.",
            "help": "Je peux t'aider."
        }
    elif score >= 40:
        return {
            "emoji": "😑",
            "greeting": "Yo",
            "response": "Ok",
            "confused": "Pas compris.",
            "help": "Dis-moi ce que tu veux."
        }
    elif score >= 20:
        return {
            "emoji": "😠",
            "greeting": "Quoi",
            "response": "Entendu",
            "confused": "Noté.",
            "help": "Parle clairement."
        }
    else:
        return {
            "emoji": "😤",
            "greeting": "...",
            "response": "Quoi ?",
            "confused": "...",
            "help": "Laisse-moi tranquille."
        }

async def add_infraction(message: discord.Message, reason: str):
    uid = message.author.id
    infractions[uid] = infractions.get(uid, 0) + 1
    count = infractions[uid]
    
    # Baisser l'amabilité si gros mot
    if "Mot interdit" in reason:
        update_friendliness(uid, -10)
    
    await log_action(message.guild, message.author, reason, count)
    
    if count >= BAN_THRESHOLD:
        try:
            await message.author.send(
                f"❌ Tu as été **banni définitivement** du serveur **{message.guild.name}** "
                f"pour avoir atteint {BAN_THRESHOLD} infractions."
            )
        except:
            pass
        await message.guild.ban(message.author, reason=f"[AutoMod] {BAN_THRESHOLD} infractions atteintes")
    elif count >= WARN_THRESHOLD:
        try:
            mute_role = discord.utils.get(message.guild.roles, name="Muted")
            if mute_role:
                until = datetime.utcnow() + timedelta(hours=1)
                await message.author.add_roles(mute_role, reason=f"[AutoMod] {WARN_THRESHOLD} infractions")
                await message.channel.send(
                    f"🔇 {message.author.mention} a été **mute 1h** ({count} infractions)."
                )
        except Exception as e:
            print(f"Erreur mute: {e}")
    else:
        await message.channel.send(
            f"⚠️ {message.author.mention} — **avertissement {count}** : {reason}"
        )

async def log_action(guild: discord.Guild, user: discord.Member, reason: str, count: int):
    log_channel = discord.utils.get(guild.text_channels, name="mod-logs")
    if log_channel:
        embed = discord.Embed(
            title="🛡️ Action de modération",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Utilisateur", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Raison", value=reason, inline=False)
        embed.add_field(name="Infractions totales", value=str(count), inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        await log_channel.send(embed=embed)

def is_spam(user_id: int) -> bool:
    now = datetime.utcnow()
    if user_id not in spam_tracker:
        spam_tracker[user_id] = []
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if (now - t).seconds < 5]
    spam_tracker[user_id].append(now)
    return len(spam_tracker[user_id]) >= 5  # 5 msgs en 5 secondes = spam

# ─── EVENTS ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="le serveur 🛡️"
    ))

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    content_lower = message.content.lower()
    
    # ── 1. Mention du bot ─────────────────────────────────────────────────────
    if bot.user in message.mentions:
        await handle_mention(message)
        return
    
    # ── 2. Détection gros mots ────────────────────────────────────────────────
    for word in BANNED_WORDS:
        if word in content_lower:
            await message.delete()
            await add_infraction(message, f"Mot interdit : `{word}`")
            return
    
    # ── 3. Liens suspects ─────────────────────────────────────────────────────
    for link in SUSPICIOUS_LINKS:
        if link in content_lower:
            await message.delete()
            await add_infraction(message, f"Lien suspect : `{link}`")
            return
    
    # ── 4. Anti-spam ──────────────────────────────────────────────────────────
    if is_spam(message.author.id):
        await message.delete()
        await add_infraction(message, "Spam (5+ messages en 5 secondes)")
        return
    
    # ── 5. Augmenter amabilité si message gentil ──────────────────────────────
    for nice_word in NICE_WORDS:
        if nice_word in content_lower:
            update_friendliness(message.author.id, 3)
            break
    
    await bot.process_commands(message)

async def handle_mention(message: discord.Message):
    content = message.content.replace(f"<@{bot.user.id}>", "").strip().lower()
    user_id = message.author.id
    score = get_friendliness_score(user_id)
    tone = get_bot_tone(score)
    
    # ── Détection insultes envers le bot ──────────────────────────────────────
    for insult in BOT_INSULTS:
        if insult in content:
            update_friendliness(user_id, -15)
            new_score = get_friendliness_score(user_id)
            new_tone = get_bot_tone(new_score)
            await message.reply(f"{new_tone['emoji']} {new_tone['response']}")
            return
    
    # ── Détection mots gentils ────────────────────────────────────────────────
    for nice_word in NICE_WORDS:
        if nice_word in content:
            update_friendliness(user_id, 5)
            break
    
    # ── Réponses adaptées au ton ──────────────────────────────────────────────
    responses = {
        "aide": f"📋 Commandes dispo : `!infractions @user`, `!reset @user`, `!warn @user <raison>`, `!ban @user`",
        "help": f"📋 Commandes dispo : `!infractions @user`, `!reset @user`, `!warn @user <raison>`, `!ban @user`",
        "bonjour": f"{tone['emoji']} {tone['greeting']} {message.author.mention} ! {tone['help']}",
        "salut": f"{tone['emoji']} {tone['greeting']} {message.author.mention} ! Tout va bien ici",
        "ping": f"{tone['emoji']} Pong !",
        "": f"{tone['emoji']} Oui {message.author.mention} ? Dis `@bot aide` pour voir ce que je peux faire.",
    }
    
    for keyword, reply in responses.items():
        if keyword in content:
            await message.reply(reply)
            return
    
    await message.reply(
        f"{tone['emoji']} {tone['confused']} Dis `@{bot.user.name} aide` pour voir mes commandes."
    )

# ─── COMMANDES ────────────────────────────────────────────────────────────────
@bot.command(name="infractions")
@commands.has_permissions(manage_messages=True)
async def cmd_infractions(ctx, member: discord.Member):
    count = get_infractions(member.id)
    await ctx.send(f"📊 {member.mention} a **{count} infraction(s)** sur {BAN_THRESHOLD} avant le ban.")

@bot.command(name="reset")
@commands.has_permissions(administrator=True)
async def cmd_reset(ctx, member: discord.Member):
    infractions[member.id] = 0
    await ctx.send(f"✅ Infractions de {member.mention} remises à zéro.")

@bot.command(name="friendliness")
@commands.has_permissions(manage_messages=True)
async def cmd_friendliness(ctx, member: discord.Member):
    """Affiche le score d'amabilité d'un utilisateur"""
    score = get_friendliness_score(member.id)
    tone = get_bot_tone(score)
    await ctx.send(f"😊 {member.mention} a un score d'amabilité de **{score}/100** {tone['emoji']}")

@bot.command(name="reset-friendliness")
@commands.has_permissions(administrator=True)
async def cmd_reset_friendliness(ctx, member: discord.Member):
    """Remet le score d'amabilité à 100"""
    friendliness_score[member.id] = 100
    await ctx.send(f"✅ Score d'amabilité de {member.mention} remis à 100.")

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def cmd_warn(ctx, member: discord.Member, *, reason: str = "Aucune raison donnée"):
    fake_msg = ctx.message
    fake_msg.author = member
    await add_infraction(fake_msg, f"[Manuel] {reason}")
    await ctx.send(f"⚠️ {member.mention} a reçu un avertissement manuel : {reason}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def cmd_ban(ctx, member: discord.Member, *, reason: str = "Aucune raison"):
    await member.ban(reason=f"[Manuel] {reason}")
    await ctx.send(f"🔨 {member.mention} a été banni. Raison : {reason}")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def cmd_kick(ctx, member: discord.Member, *, reason: str = "Aucune raison"):
    await member.kick(reason=f"[Manuel] {reason}")
    await ctx.send(f"👢 {member.mention} a été kick. Raison : {reason}")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def cmd_clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 {amount} messages supprimés.", delete_after=3)

# ─── LANCEMENT ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(TOKEN)
