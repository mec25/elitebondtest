import discord
from discord.ext import commands
from coin_storage import get_user_data, update_user_data
from coin_views import CoinSystemView
import os
from level_badge import badge_level_task
from level_system import add_xp, leaderboard_task, save_leaderboard_channel, send_levelup_card

TOKEN = "MTM2NTg2MTk1MDUzNzYwMTA0NA.GqUW2a.TdZALT4FN76IJv2nyYv_JkC7VI03CYj0dZHXYY"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    async def setup_hook(self):
        self.loop.create_task(badge_level_task(self))
        self.loop.create_task(leaderboard_task(self))
        await self.load_extension("embed_command")  # <-- asynchron laden
        await self.load_extension("ticket_system")
        await self.load_extension("admin_panel")

bot = MyBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} ist online!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await add_xp(bot, message.author, 5, message.channel)
    await bot.process_commands(message)

# Entferne oder kommentiere diesen Block, falls vorhanden:
# @bot.event
# async def on_voice_state_update(member, before, after):
#     # XP für Voice-Channel: alle 5 Minuten 10 XP
#     if after.channel and not before.channel:
#         async def voice_xp_loop():
#             while member.voice and member.voice.channel:
#                 await asyncio.sleep(300)  # 5 Minuten
#                 await add_xp(bot, member, 10)
#         bot.loop.create_task(voice_xp_loop())

@bot.command()
@commands.has_permissions(administrator=True)
async def givexp(ctx, member: discord.Member, amount: int):
    await add_xp(bot, member, amount, ctx.channel)
    await ctx.send(f"{member.mention} hat {amount} XP erhalten!")

@bot.command()
@commands.has_permissions(administrator=True)
async def setleaderboard(ctx):
    save_leaderboard_channel(ctx.guild.id, ctx.channel.id)
    await ctx.send("Leaderboard-Channel gesetzt! Das Leaderboard wird hier alle 12h aktualisiert.")

@bot.command()
async def coinsetup(ctx):
    embed = discord.Embed(
        title="🛠️ COIN-SYSTEM 🛠️",
        description=(
            "🔥 **Tägliche Coins abholen:** Hol dir 10 Coins pro Tag, G! 🚀\n"
            "🧊 **Coins abfragen:** Check, wie viele Coins du hast!\n"
            "🛒 **Shop öffnen:** Tausch deine Coins gegen Rewards ein!\n\n"
            "Wähl eine Aktion unten aus, G! 💪"
        ),
        color=0xFF0000
    )
    embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
    await ctx.send(embed=embed, view=CoinSystemView())

@bot.command()
@commands.has_permissions(administrator=True)
async def setcoins(ctx, member: discord.Member, amount: int):
    if amount < 0:
        await ctx.send("Der Betrag muss positiv sein, G!")
        return
    update_user_data(member.id, coins=amount)
    await ctx.send(f"{member.mention} hat jetzt **{amount} Coins**, G!")

@bot.command()
async def xp(ctx):
    user = ctx.author
    await send_levelup_card(bot, user, None, None, ctx.channel)

if __name__ == "__main__":
    bot.run(TOKEN)