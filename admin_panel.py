import discord
from discord.ext import commands

OAUTH_CLIENT_ID = "1361396825688375539"
OAUTH_REDIRECT_URI = "https://www.oauth.malithwwc.de/"
OAUTH_AUTHORIZE_URL = (
    f"https://discord.com/oauth2/authorize?client_id={OAUTH_CLIENT_ID}"
    f"&response_type=code&redirect_uri={OAUTH_REDIRECT_URI}"
    "&scope=identify%20guilds.join%20email%20guilds%20connections"
)

class XPModal(discord.ui.Modal, title="XP vergeben"):
    def __init__(self, bot, target_user):
        super().__init__()
        self.bot = bot
        self.target_user = target_user
        self.amount = discord.ui.TextInput(label="XP-Menge", required=True)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = self.target_user
            amount = int(self.amount.value)
            await interaction.client.get_command("givexp").callback(interaction, user, amount)
            await interaction.response.send_message(f"{user.mention} hat {amount} XP erhalten!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Fehler: {e}", ephemeral=True)

class CoinsModal(discord.ui.Modal, title="Coins vergeben"):
    def __init__(self, bot, target_user):
        super().__init__()
        self.bot = bot
        self.target_user = target_user
        self.amount = discord.ui.TextInput(label="Coin-Menge", required=True)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = self.target_user
            amount = int(self.amount.value)
            await interaction.client.get_command("setcoins").callback(interaction, user, amount)
            await interaction.response.send_message(f"{user.mention} hat jetzt {amount} Coins!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Fehler: {e}", ephemeral=True)

class AdminPanelView(discord.ui.View):
    def __init__(self, bot, target_user):
        super().__init__(timeout=300)
        self.bot = bot
        self.target_user = target_user

    @discord.ui.button(label="XP vergeben", style=discord.ButtonStyle.primary, emoji="⭐")
    async def xp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(XPModal(self.bot, self.target_user))

    @discord.ui.button(label="Coins vergeben", style=discord.ButtonStyle.success, emoji="💰")
    async def coins_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CoinsModal(self.bot, self.target_user))

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="Verifizieren",
                style=discord.ButtonStyle.link,
                url=OAUTH_AUTHORIZE_URL,
                emoji="✅"
            )
        )

class AdminPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="panel")
    @commands.has_permissions(administrator=True)
    async def panel(self, ctx, member: discord.Member = None):
        if not member:
            await ctx.send("Bitte markiere einen User: `!panel @User`", ephemeral=True)
            return
        embed = discord.Embed(
            title="🛠️ Admin-Panel",
            description=(
                f"Wähle eine Aktion für {member.mention}:\n"
                "⭐ XP vergeben\n"
                "💰 Coins vergeben"
            ),
            color=0x2F3136
        )
        view = AdminPanelView(self.bot, target_user=member)
        await ctx.send(embed=embed, view=view, ephemeral=True)

    @commands.command(name="verify")
    async def verify(self, ctx):
        embed = discord.Embed(
            title="Elite-Bond Discord Login",
            description="Klicke auf **Verifizieren**, um dich mit Discord zu verbinden und automatisch dem Server beizutreten.\n\n"
                        f"Oder öffne den Link direkt: [Login mit Discord]({OAUTH_AUTHORIZE_URL})",
            color=0x5865F2
        )
        await ctx.send(embed=embed, view=VerifyView())

async def setup(bot):
    await bot.add_cog(AdminPanel(bot))