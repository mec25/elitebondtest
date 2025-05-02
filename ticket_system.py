import discord
from discord.ext import commands
from discord.utils import get

class TicketModal(discord.ui.Modal, title="🎫 Ticket erstellen"):
    problem = discord.ui.TextInput(
        label="Beschreibe dein Problem",
        style=discord.TextStyle.paragraph,
        placeholder="Bitte schildere dein Anliegen so genau wie möglich...",
        required=True,
        max_length=500
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        problem_text = self.problem.value

        # Kategorie suchen oder erstellen
        category = get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        # Ticket-Channel erstellen
        channel_name = f"ticket-{user.name}".replace(" ", "-").lower()
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket von {user} ({user.id})"
        )

        # Embed im Ticket-Channel
        embed = discord.Embed(
            title=f"📑 Ticket von {user.display_name}. 📑",
            description=f"Hallo {user.mention}, G! 🚀\n\n**Dein Problem:**\n{problem_text}\n\nDas Team wird sich bald bei dir melden. Schreib hier, falls du mehr Infos hast! 😊",
            color=0xFF0000
        )
        embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")

        view = TicketActionView(user.id)
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Dein Ticket wurde erstellt: {channel.mention}", ephemeral=True)

class TicketActionView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.claimed_by = None

    @discord.ui.button(label="Schließen", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.guild_permissions.manage_channels or interaction.user.id == self.user_id:
            await interaction.channel.send("Ticket wird geschlossen...")

            # --- Ticket Log erstellen und in EINEM Channel posten ---
            guild = interaction.guild
            ticket_channel = interaction.channel
            messages = []
            async for msg in ticket_channel.history(limit=100, oldest_first=True):
                author = msg.author.display_name
                content = msg.content
                messages.append(f"{author}: {content}")
            log_text = "\n".join(messages) or "Keine Nachrichten im Ticket."

            # Channel "ticket-logs" suchen oder erstellen (nur für Admins sichtbar)
            log_channel = get(guild.text_channels, name="ticket-logs")
            if not log_channel:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                }
                for role in guild.roles:
                    if role.permissions.administrator:
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True)
                log_channel = await guild.create_text_channel("ticket-logs", overwrites=overwrites)

            # Log als Datei posten
            import io
            log_file = discord.File(io.BytesIO(log_text.encode("utf-8")), filename=f"{ticket_channel.name}-log.txt")
            await log_channel.send(
                f"Log für {ticket_channel.name} (geschlossen von {interaction.user.mention})",
                file=log_file
            )

            await ticket_channel.delete()
        else:
            await interaction.response.send_message("Du darfst dieses Ticket nicht schließen.", ephemeral=True)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="claim_ticket")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed_by is None:
            self.claimed_by = interaction.user
            await interaction.response.send_message(f"{interaction.user.mention} hat das Ticket übernommen!", ephemeral=False)
        else:
            await interaction.response.send_message("Das Ticket wurde bereits übernommen.", ephemeral=True)

class TicketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ticketsetup")
    @commands.has_permissions(administrator=True)
    async def ticketsetup(self, ctx):
        embed = discord.Embed(
            title="🎫 TICKET-SYSTEM 🎫",
            description="Erstelle ein Ticket, um mit dem Team zu sprechen, G! 🚀",
            color=0xFF0000
        )
        embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
        view = TicketCreateView(self.bot)
        await ctx.send(embed=embed, view=view)

class TicketCreateView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🎫 Ticket erstellen", style=discord.ButtonStyle.danger, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal(self.bot))

async def setup(bot):
    await bot.add_cog(TicketCommands(bot))