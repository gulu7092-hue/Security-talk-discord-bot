import discord
from discord.ext import commands
import json
import os
import re
from datetime import datetime, timedelta

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = "!"
WARN_THRESHOLD = 15    # mute temporaire
BAN_THRESHOLD  = 20    # ban permanent

# Mots interdits (à compléter)
BANNED_WORDS = [
    "connard", "enculé", "pute", "merde", "fdp", "ntm", "salope",
    "batard", "bâtard", "nique", "tg", "ta gueule"
]

# Liens suspects
SUSPICIOUS_LINKS = ["discord.gift", "free-nitro", "steamcommunity.ru", "bit.ly"]

# ─── INTENTS ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ─── DONNÉES EN MÉMOIRE ───────────────────────────────────────────────────────
infractions: dict[int, int] = {}   # user_id → count
spam_tracker: dict[int, list] = {} # user_id → [timestamps]

# ─── UTILS ────────────────────────────────────────────────────────────────────
def get_infractions(user_id: int) -> int:
    return infractions.get(user_id, 0)

async def add_infraction(message: discord.Message, reason: str):
    uid = message.author.id
    infractions[uid] = infractions.get(uid, 0) + 1
    count = infractions[uid]

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

    await bot.process_commands(message)

async def handle_mention(message: discord.Message):
    content = message.content.replace(f"<@{bot.user.id}>", "").strip().lower()

    responses = {
        "aide":        "📋 Commandes dispo : `!infractions @user`, `!reset @user`, `!warn @user <raison>`, `!ban @user`",
        "help":        "📋 Commandes dispo : `!infractions @user`, `!reset @user`, `!warn @user <raison>`, `!ban @user`",
        "bonjour":     f"👋 Bonjour {message.author.mention} ! Je surveille le serveur 🛡️",
        "salut":       f"👋 Salut {message.author.mention} ! Tout va bien ici 😎",
        "ping":        "🏓 Pong !",
        "":            f"Oui {message.author.mention} ? Dis `@bot aide` pour voir ce que je peux faire.",
    }

    for keyword, reply in responses.items():
        if keyword in content:
            await message.reply(reply)
            return

    await message.reply(
        f"Je t'entends {message.author.mention} 👂 — mais je ne comprends pas encore ça. "
        f"Dis `@{bot.user.name} aide` pour voir mes commandes."
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
