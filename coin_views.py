import discord
import asyncio
from datetime import datetime, timedelta
from coin_storage import get_user_data, update_user_data
from shop import ShopView

class CoinSystemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Tägliche Coins abholen", style=discord.ButtonStyle.green, custom_id="daily_coins")
    async def daily_coins(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        user_data = get_user_data(user_id)
        last_claim = datetime.fromisoformat(user_data["last_claim"])
        now = datetime.utcnow()
        cooldown = timedelta(hours=24)
        if now - last_claim < cooldown:
            next_time = last_claim + cooldown
            remaining = (next_time - now).total_seconds()
            hours, remainder = divmod(int(remaining), 3600)
            minutes = remainder // 60
            try:
                await interaction.response.send_message(
                    f"Du kannst deine Coins erst wieder in {hours}h {minutes}m abholen, G! ⏳", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send(
                    f"Du kannst deine Coins erst wieder in {hours}h {minutes}m abholen, G! ⏳", ephemeral=True)

            async def notify_when_ready():
                await asyncio.sleep(remaining)
                try:
                    await interaction.user.send("Du kannst jetzt wieder deine täglichen Coins abholen, G! 💸")
                except Exception:
                    pass

            asyncio.create_task(notify_when_ready())
            return

        new_coins = user_data["coins"] + 10
        update_user_data(user_id, coins=new_coins, last_claim=now.isoformat())
        try:
            await interaction.response.send_message("Du hast **10 Coins** abgeholt, G! 💸", ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send("Du hast **10 Coins** abgeholt, G! 💸", ephemeral=True)
        try:
            await interaction.user.send("Du hast gerade deine täglichen Coins abgeholt! 💸")
        except Exception:
            pass

    @discord.ui.button(label="🔵 Coins abfragen", style=discord.ButtonStyle.blurple, custom_id="check_coins")
    async def check_coins(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        user_data = get_user_data(user_id)
        try:
            await interaction.response.send_message(
                f"Du hast aktuell **{user_data['coins']} Coins**, G! 💰", ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(
                f"Du hast aktuell **{user_data['coins']} Coins**, G! 💰", ephemeral=True)

    @discord.ui.button(label="🔴 Shop öffnen", style=discord.ButtonStyle.red, custom_id="open_shop")
    async def open_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message(
                "Wähle ein Produkt aus dem Shop aus:", view=ShopView(interaction.user.id), ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Wähle ein Produkt aus dem Shop aus:", view=ShopView(interaction.user.id), ephemeral=True)