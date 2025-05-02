import discord
from coin_storage import get_user_data, update_user_data

SHOP_PRODUCTS = [
    {"label": "Produkt 1", "value": "produkt1", "price": 20},
    {"label": "Produkt 2", "value": "produkt2", "price": 50},
    {"label": "Produkt 3", "value": "produkt3", "price": 100},
]

class ShopDropdown(discord.ui.Select):
    def __init__(self, user_id):
        options = [
            discord.SelectOption(
                label=f"{prod['label']} ({prod['price']} Coins)",
                value=prod["value"],
                description=f"Kaufe {prod['label']} für {prod['price']} Coins"
            )
            for prod in SHOP_PRODUCTS
        ]
        super().__init__(placeholder="Wähle ein Produkt aus...", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Shop-Menü!", ephemeral=True)
            return

        selected = self.values[0]
        product = next((p for p in SHOP_PRODUCTS if p["value"] == selected), None)
        user_data = get_user_data(interaction.user.id)
        if user_data["coins"] < product["price"]:
            await interaction.response.send_message(f"Du hast nicht genug Coins für {product['label']}! 😢", ephemeral=True)
            return

        update_user_data(interaction.user.id, coins=user_data["coins"] - product["price"])
        await interaction.response.send_message(f"Du hast **{product['label']}** für {product['price']} Coins gekauft! 🎉", ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.add_item(ShopDropdown(user_id))