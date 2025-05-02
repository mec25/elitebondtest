import discord
from discord.ext import commands

class ChannelSelect(discord.ui.Select):
    def __init__(self, channels, embed, author):
        options = [
            discord.SelectOption(label=channel.name, value=str(channel.id))
            for channel in channels
        ]
        super().__init__(placeholder="Wähle einen Kanal...", min_values=1, max_values=1, options=options)
        self.embed = embed
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Du darfst diese Auswahl nicht benutzen.", ephemeral=True)
            return
        channel_id = int(self.values[0])
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            await channel.send(embed=self.embed)
            await interaction.response.send_message(f"Embed wurde in {channel.mention} gesendet!", ephemeral=True)
        else:
            await interaction.response.send_message("Kanal nicht gefunden.", ephemeral=True)

class ChannelSelectView(discord.ui.View):
    def __init__(self, channels, embed, author):
        super().__init__(timeout=60)
        self.add_item(ChannelSelect(channels, embed, author))

class EmbedCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="embed")
    @commands.has_permissions(administrator=True)
    async def embed_command(self, ctx, *, text: str):
        embed = discord.Embed(
            description=text,
            color=discord.Color.blue()
        )
        channels = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
        view = ChannelSelectView(channels, embed, ctx.author)
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send(
            f"{ctx.author.mention}, wähle einen Kanal für das Embed aus:",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(EmbedCommands(bot))