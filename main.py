import discord
from discord.ext import commands, tasks
from pymongo import MongoClient
from urllib.parse import quote_plus
import discord.utils
import random
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
import asyncio

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Konfigurationsvariablen
COIN_CHANNEL_ID = 1366503697059676230  # Daily Coins Channel
LEVEL_CHANNEL_ID = 1366503709156180089  # Level-System Channel
TICKET_CHANNEL_ID = 1365855616911802408  # Ticket Channel
TICKET_CATEGORY_ID = None  # Setze die ID der Kategorie, in der Tickets erstellt werden sollen
SHOP_IMAGE = "shop.jpg"  # Pfad zum Shop-Bild (im gleichen Verzeichnis)
SHOP_PRICE = 10  # Preis für Shop-Items
SHOP_OPTIONS = ["CanvaPro", "Netflix", "Spotify"]  # Verfügbare Produkte
XP_COOLDOWN = 60  # 60 Sekunden Cooldown für XP
XP_PER_LEVEL_EARLY = 100  # 100 XP pro Level bis Level 10
XP_PER_LEVEL_LATE = 200  # 200 XP pro Level ab Level 10
LEVEL_THRESHOLD = 10  # Schwellenwert für XP-Änderung
TOKEN = "MTM2NTg2MTk1MDUzNzYwMTA0NA.GSIV9W.gLvwxlcDJoxhum6_INjHEOFHYJntx91FIT-4ho"  # Dein Bot-Token



# Funktion: Level berechnen und aktualisieren
def update_user_level(user_id, user_data):
    xp = user_data["xp"]
    current_level = user_data["level"]
    new_level = current_level

    if current_level < LEVEL_THRESHOLD:
        xp_needed = current_level * XP_PER_LEVEL_EARLY
        xp_next_level = (current_level + 1) * XP_PER_LEVEL_EARLY
    else:
        xp_needed = (LEVEL_THRESHOLD * XP_PER_LEVEL_EARLY) + (current_level - LEVEL_THRESHOLD) * XP_PER_LEVEL_LATE
        xp_next_level = (LEVEL_THRESHOLD * XP_PER_LEVEL_EARLY) + (current_level - LEVEL_THRESHOLD + 1) * XP_PER_LEVEL_LATE

    while xp >= xp_next_level and current_level < 25:
        new_level += 1
        if new_level < LEVEL_THRESHOLD:
            xp_next_level = (new_level + 1) * XP_PER_LEVEL_EARLY
        else:
            xp_next_level = (LEVEL_THRESHOLD * XP_PER_LEVEL_EARLY) + (new_level - LEVEL_THRESHOLD + 1) * XP_PER_LEVEL_LATE

    if new_level != current_level:
        bot.db_users.update_one({"_id": user_id}, {"$set": {"level": new_level}})
        print(f"[DEBUG] Benutzer {user_id} hat Level {new_level} erreicht!")

    return new_level, xp_needed, xp_next_level

# --- Coin-System ---
class CoinSystemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 Tägliche Coins abholen", style=discord.ButtonStyle.green, custom_id="claim_coins_new")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_id = interaction.user.id
            print(f"[DEBUG] Claim Button - User ID: {user_id}")
            user_hinzufügen(user_id)
            user = bot.db_users.find_one({"_id": user_id})
            if not user:
                await interaction.response.send_message("Ein Fehler ist aufgetreten, G! 🚨", ephemeral=True)
                return

            now = int(discord.utils.utcnow().timestamp())
            last_claim = user.get("last_claim", 0)
            cooldown = 24 * 60 * 60  # 24 Stunden

            if now - last_claim >= cooldown:
                bot.db_users.update_one({"_id": user_id}, {"$inc": {"coins": 10}, "$set": {"last_claim": now}})
                embed = discord.Embed(
                    title="💰 Tägliche Coins abgeholt! 💰",
                    description="Du hast 10 Coins abgeholt, G! Komm morgen wieder! 🚀",
                    color=0x00FF00
                )
                embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                remaining_time = cooldown - (now - last_claim)
                hours = remaining_time // 3600
                minutes = (remaining_time % 3600) // 60
                seconds = remaining_time % 60
                embed = discord.Embed(
                    title="⏳ Cooldown aktiv! ⏳",
                    description=f"Du kannst erst in {hours}h {minutes}m {seconds}s wieder Coins abholen, G! 🕒",
                    color=0xFF0000
                )
                embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"[ERROR] Fehler im claim_button: {e}")
            await interaction.response.send_message(f"Ein Fehler ist aufgetreten, G! 🚨 Fehler: {str(e)}", ephemeral=True)

    @discord.ui.button(label="💎 Coins abfragen", style=discord.ButtonStyle.blurple, custom_id="check_coins_new")
    async def check_coins_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_id = interaction.user.id
            print(f"[DEBUG] Check Coins Button - User ID: {user_id}")
            user_hinzufügen(user_id)
            user = bot.db_users.find_one({"_id": user_id})
            if not user:
                await interaction.response.send_message("Ein Fehler ist aufgetreten, G! 🚨", ephemeral=True)
                return

            coins = user.get("coins", 0)
            embed = discord.Embed(
                title="💎 Deine Coins 💎",
                description=f"Du hast **{coins} Coins**, G! 💪",
                color=0x00FF00
            )
            embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"[ERROR] Fehler im check_coins_button: {e}")
            await interaction.response.send_message(f"Ein Fehler ist aufgetreten, G! 🚨 Fehler: {str(e)}", ephemeral=True)

    @discord.ui.button(label="🛒 Shop öffnen", style=discord.ButtonStyle.red, custom_id="open_shop_new")
    async def open_shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            print("[DEBUG] Shop öffnen Button gedrückt.")
            await interaction.response.defer(ephemeral=True)

            shop_image = discord.File(SHOP_IMAGE, filename="shop.jpg")

            class ShopView(discord.ui.View):
                def __init__(self, user_id):
                    super().__init__(timeout=60)
                    self.user_id = user_id

                @discord.ui.select(
                    placeholder="Wähle ein Produkt aus, G! 🚀",
                    options=[
                        discord.SelectOption(label=option, description=f"Kostet {SHOP_PRICE} Coins", value=option)
                        for option in SHOP_OPTIONS
                    ],
                    custom_id="shop_select_new",
                    min_values=1,
                    max_values=1
                )
                async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
                    try:
                        await interaction.response.defer(ephemeral=True)
                        selected_item = select.values[0]
                        print(f"[DEBUG] Produkt ausgewählt: {selected_item}")
                        user_data = bot.db_users.find_one({"_id": self.user_id})
                        if not user_data:
                            await interaction.followup.send("Ein Fehler ist aufgetreten, G! 🚨", ephemeral=True)
                            return

                        coins = user_data.get("coins", 0)

                        embed = discord.Embed(
                            title="💰 Kaufbestätigung 💰",
                            description=f"Willst du **{selected_item}** für {SHOP_PRICE} Coins kaufen, G? 🚀\n"
                                        f"**Deine Coins:** {coins}",
                            color=0xFF0000
                        )
                        embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")

                        class ConfirmView(discord.ui.View):
                            def __init__(self, user_id, selected_item):
                                super().__init__(timeout=60)
                                self.user_id = user_id
                                self.selected_item = selected_item

                            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                                return interaction.user.id == self.user_id

                            @discord.ui.button(label="Ja", style=discord.ButtonStyle.green)
                            async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                                try:
                                    user_data = bot.db_users.find_one({"_id": self.user_id})
                                    if not user_data:
                                        await interaction.response.send_message("Ein Fehler ist aufgetreten, G! 🚨", ephemeral=True)
                                        return

                                    coins = user_data.get("coins", 0)
                                    if coins >= SHOP_PRICE:
                                        bot.db_users.update_one(
                                            {"_id": self.user_id},
                                            {"$inc": {"coins": -SHOP_PRICE}, "$push": {"purchases": self.selected_item}}
                                        )
                                        await interaction.response.edit_message(
                                            embed=discord.Embed(
                                                title="✅ Kauf erfolgreich! ✅",
                                                description=f"Du hast **{self.selected_item}** für {SHOP_PRICE} Coins gekauft, G! 🚀\n"
                                                            f"**Neuer Coin-Stand:** {coins - SHOP_PRICE}",
                                                color=0x00FF00
                                            ).set_footer(text="© 2025 Elite-Bond. All rights reserved."),
                                            view=None
                                        )
                                    else:
                                        await interaction.response.edit_message(
                                            embed=discord.Embed(
                                                title="❌ Zu wenig Coins! ❌",
                                                description=f"Du hast nur {coins} Coins, brauchst aber {SHOP_PRICE}, G! 💥",
                                                color=0xFF0000
                                            ).set_footer(text="© 2025 Elite-Bond. All rights reserved."),
                                            view=None
                                        )
                                except Exception as e:
                                    print(f"[ERROR] Fehler im yes_button: {e}")
                                    await interaction.response.edit_message(
                                        embed=discord.Embed(
                                            title="❌ Fehler! ❌",
                                            description="Ein Fehler ist aufgetreten, G! 🚨",
                                            color=0xFF0000
                                        ).set_footer(text="© 2025 Elite-Bond. All rights reserved."),
                                        view=None
                                    )

                            @discord.ui.button(label="Nein", style=discord.ButtonStyle.red)
                            async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                                try:
                                    await interaction.response.edit_message(
                                        embed=discord.Embed(
                                            title="❌ Kauf abgebrochen! ❌",
                                            description="Kauf abgebrochen, G! 🚫",
                                            color=0xFF0000
                                        ).set_footer(text="© 2025 Elite-Bond. All rights reserved."),
                                        view=None
                                    )
                                except Exception as e:
                                    print(f"[ERROR] Fehler im no_button: {e}")
                                    await interaction.response.edit_message(
                                        embed=discord.Embed(
                                            title="❌ Fehler! ❌",
                                            description="Ein Fehler ist aufgetreten, G! 🚨",
                                            color=0xFF0000
                                        ).set_footer(text="© 2025 Elite-Bond. All rights reserved."),
                                        view=None
                                    )

                        confirm_view = ConfirmView(self.user_id, selected_item)
                        await interaction.followup.send(embed=embed, view=confirm_view, ephemeral=True)
                    except Exception as e:
                        print(f"[ERROR] Fehler im select_callback: {e}")
                        await interaction.followup.send("Ein Fehler ist aufgetreten, G! 🚨", ephemeral=True)

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    return interaction.user.id == self.user_id

            shop_view = ShopView(interaction.user.id)
            await interaction.followup.send(file=shop_image, view=shop_view, ephemeral=True)
        except Exception as e:
            print(f"[ERROR] Fehler im open_shop_button: {e}")
            await interaction.followup.send("Du hast zu wenig Coins für den Shop.. Sammel weiter G", ephemeral=True)

# --- Level-System ---
async def update_rank_leaderboard():
    channel = bot.get_channel(LEVEL_CHANNEL_ID)
    if not channel:
        print(f"[ERROR] Level-Channel {LEVEL_CHANNEL_ID} nicht gefunden!")
        return None, None

    users_data = bot.db_users.find().sort([("level", -1), ("xp", -1)])
    leaderboard = [(user["_id"], user["level"], user["xp"]) for user in users_data][:15]  # Top 15

    embed = discord.Embed(
        title="🏆 RANK-LEADERBOARD 🏆",
        description=(
            "🔥 Die Top-Level-Gs (Platz 1-15) 💪\n\n"
            "📊 **Wie funktioniert das Levelsystem?**\n"
            f"- Verdiene XP durch Nachrichten: 5 XP (<20 Zeichen), 10 XP (20-50 Zeichen), 15 XP (>50 Zeichen).\n"
            f"- Cooldown: {XP_COOLDOWN} Sekunden pro Nachricht.\n"
            f"- Bis Level {LEVEL_THRESHOLD}: {XP_PER_LEVEL_EARLY} XP pro Level.\n"
            f"- Ab Level {LEVEL_THRESHOLD}: {XP_PER_LEVEL_LATE} XP pro Level.\n\n"
            "🔘 **Buttons:**\n"
            "- 📊 **Meine Rank-Card:** Zeigt deine persönliche Rank-Card (nur für dich sichtbar).\n"
            "- ⬅️ **Zurück:** Blättert zu den vorherigen Rängen.\n"
            "- ➡️ **Vorwärts:** Blättert zu den nächsten Rängen."
        ),
        color=0xFF0000
    )

    index = 1
    for user_id, level, xp in leaderboard:
        try:
            member = await bot.fetch_user(user_id)
            rank_emoji = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"#{index}"
            embed.add_field(
                name=f"{rank_emoji} {member.name}",
                value=f"**Level:** {level} | **XP:** {xp} 🔥",
                inline=False
            )
        except discord.errors.NotFound:
            embed.add_field(
                name=f"#{index} Benutzer nicht gefunden",
                value=f"**Level:** {level} | **XP:** {xp} 🔥",
                inline=False
            )
        index += 1

    embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
    view = RankLeaderboardView(start_rank=1)

    return embed, view

class RankLeaderboardView(discord.ui.View):
    def __init__(self, start_rank=1):
        super().__init__(timeout=None)
        self.start_rank = start_rank

    @discord.ui.button(label="📊 Meine Rank-Card", style=discord.ButtonStyle.blurple, custom_id="rank_card_new")
    async def rank_card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        user_hinzufügen(user_id)
        user = bot.db_users.find_one({"_id": user_id})
        if not user:
            await interaction.followup.send("Du bist noch nicht in der Datenbank, G! Schreib ein paar Nachrichten, um XP zu sammeln! 🚀", ephemeral=True)
            return

        level = user["level"]
        xp = user["xp"]
        _, xp_needed, xp_next_level = update_user_level(user_id, user)

        # Berechne Platzierung
        users_data = bot.db_users.find().sort([("level", -1), ("xp", -1)])
        leaderboard = [(u["_id"], u["level"], u["xp"]) for u in users_data]
        rank = next((index + 1 for index, (uid, _, _) in enumerate(leaderboard) if uid == user_id), "Unbekannt")

        # Lade das Hintergrundbild und skaliere es
        background = Image.open("1.png").convert("RGBA")
        background = background.resize((800, 300))

        # Erstelle ein Draw-Objekt
        draw = ImageDraw.Draw(background)

        # Basis-Schriftart
        base_font = ImageFont.load_default()

        def render_scaled_text(text, scale_factor, fill_color=(255, 255, 255, 255)):
            temp_image = Image.new("RGBA", (800, 300), (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_image)
            temp_draw.text((0, 0), text, font=base_font, fill=fill_color)
            bbox = temp_image.getbbox()
            if bbox:
                text_image = temp_image.crop(bbox)
                new_size = (int(text_image.width * scale_factor), int(text_image.height * scale_factor))
                return text_image.resize(new_size, Image.Resampling.LANCZOS)
            return None

        # Lade den Avatar asynchron
        async with aiohttp.ClientSession() as session:
            avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
            async with session.get(avatar_url) as response:
                if response.status != 200:
                    await interaction.followup.send("Fehler beim Laden deines Avatars, G! 🚨", ephemeral=True)
                    return
                avatar_data = await response.read()
                avatar_image = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
                avatar_image = avatar_image.resize((120, 120))

        # Erstelle einen Kreis für den Avatar
        mask = Image.new("L", (120, 120), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 120, 120), fill=255)
        avatar_image.putalpha(mask)

        # Positioniere den Avatar
        background.paste(avatar_image, (40, 40), avatar_image)

        # Zeichne den Username
        username = interaction.user.name.upper()
        username_img = render_scaled_text(username, scale_factor=3.0)
        if username_img:
            background.paste(username_img, (180, 20), username_img)

        # Zeichne Level und XP
        level_text = f"LEVEL: {level}"
        level_img = render_scaled_text(level_text, scale_factor=2.5)
        if level_img:
            background.paste(level_img, (180, 70), level_img)

        xp_text = f"XP: {xp}/{xp_next_level}"
        xp_img = render_scaled_text(xp_text, scale_factor=2.5)
        if xp_img:
            background.paste(xp_img, (180, 110), xp_img)

        # Zeichne Platzierung
        rank_text = f"Platz Nr. {rank}"
        rank_img = render_scaled_text(rank_text, scale_factor=2.5)
        if rank_img:
            background.paste(rank_img, (background.width - 250, 20), rank_img)

        # Fortschrittsleiste
        bar_width = 700
        bar_height = 30
        bar_x = 40
        bar_y = 220

        milestones = [5, 10, 15, 20, 25]
        if level <= milestones[0]:
            progress = level / milestones[0] * 0.2
        elif level <= milestones[1]:
            progress = 0.2 + (level - milestones[0]) / (milestones[1] - milestones[0]) * 0.2
        elif level <= milestones[2]:
            progress = 0.4 + (level - milestones[1]) / (milestones[2] - milestones[1]) * 0.2
        elif level <= milestones[3]:
            progress = 0.6 + (level - milestones[2]) / (milestones[3] - milestones[2]) * 0.2
        else:
            progress = 0.8 + (level - milestones[3]) / (milestones[4] - milestones[3]) * 0.2
            progress = min(progress, 1.0)

        filled_width = max(1, int(bar_width * progress))

        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], radius=10, fill=(100, 100, 100, 200))
        draw.rounded_rectangle([bar_x, bar_y, bar_x + filled_width, bar_y + bar_height], radius=10, fill=(0, 255, 0, 200))

        # Milestones und Icons
        for i, (milestone, icon_path) in enumerate(zip(milestones, ["media/i1.png", "media/i2.png", "media/i3.png", "media/i4.png", "media/i5.png"])):
            pos_x = bar_x + int((milestone / 25) * bar_width) - 20
            icon = Image.open(icon_path).convert("RGBA").resize((40, 40))
            icon_y = bar_y - 20
            background.paste(icon, (pos_x, icon_y), icon)

            milestone_text = str(milestone)
            milestone_img = render_scaled_text(milestone_text, scale_factor=2.0)
            if milestone_img:
                text_y = bar_y + bar_height + 10
                background.paste(milestone_img, (pos_x, text_y), milestone_img)

        # Speichere das Bild
        image_buffer = io.BytesIO()
        background.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        file = discord.File(image_buffer, filename="rank_card.png")
        await interaction.followup.send(file=file, ephemeral=True)

    @discord.ui.button(label="⬅️ Zurück", style=discord.ButtonStyle.grey, custom_id="rank_prev_new")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.start_rank = max(1, self.start_rank - 15)
        embed, view = await update_rank_leaderboard()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="➡️ Vorwärts", style=discord.ButtonStyle.grey, custom_id="rank_next_new")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.start_rank += 15
        embed, view = await update_rank_leaderboard()
        await interaction.response.edit_message(embed=embed, view=self)

# --- Ticket-System ---
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Ticket erstellen", style=discord.ButtonStyle.red, custom_id="create_ticket_new")
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        user_hinzufügen(user_id)
        user = bot.db_users.find_one({"_id": user_id})
        if not user:
            await interaction.response.send_message("Ein Fehler ist aufgetreten, G! 🚨", ephemeral=True)
            return

        guild = interaction.guild
        ticket_channel = discord.utils.get(guild.text_channels, name=f"ticket-{interaction.user.name.lower()}")
        if ticket_channel:
            await interaction.response.send_message(f"Du hast bereits ein offenes Ticket, G! Schau dir {ticket_channel.mention} an. 🚀", ephemeral=True)
            return

        modal = TicketModal(interaction.user)
        await interaction.response.send_modal(modal)

class TicketModal(discord.ui.Modal, title="Ticket Erstellen"):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.problem = discord.ui.TextInput(
            label="Beschreibe dein Problem",
            placeholder="Bitte beschreibe dein Problem hier...",
            required=True,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.problem)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = self.user

        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
        }
        ticket_channel = await guild.create_text_channel(
            f"ticket-{user.name.lower()}",
            category=category,
            overwrites=overwrites
        )

        bot.db_users.update_one(
            {"_id": user.id},
            {"$push": {"tickets": {"channel_id": ticket_channel.id, "created_at": int(discord.utils.utcnow().timestamp()), "claimed_by": None}}}
        )

        embed = discord.Embed(
            title=f"🎫 Ticket von {user.name} 🎫",
            description=f"Hallo {user.mention}, G! 🚀\n"
                        f"**Dein Problem:**\n{self.problem.value}\n\n"
                        "Das Team wird sich bald bei dir melden. Schreib hier, falls du mehr Infos hast! 😊",
            color=0xFF0000
        )
        embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")

        view = TicketActionsView(ticket_channel, user.id)
        await ticket_channel.send(embed=embed, view=view)

        await interaction.response.send_message(f"Dein Ticket wurde erstellt, G! Schau dir {ticket_channel.mention} an. 🚀", ephemeral=True)

class TicketActionsView(discord.ui.View):
    def __init__(self, ticket_channel, user_id):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.user_id = user_id
        self.claimed = False

    @discord.ui.button(label="Schließen", style=discord.ButtonStyle.red, custom_id="close_ticket_new")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        transcript = f"Transcript von {self.ticket_channel.name}\n\n"
        async for message in self.ticket_channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            transcript += f"[{timestamp}] {message.author.name}: {message.content}\n"

        transcript_file = io.BytesIO(transcript.encode("utf-8"))
        file = discord.File(transcript_file, filename=f"transcript-{self.ticket_channel.name}.txt")

        transcript_channel = interaction.guild.get_channel(1355316607098032219)
        if transcript_channel:
            await transcript_channel.send(f"Transcript von {self.ticket_channel.name}:", file=file)
        else:
            await interaction.followup.send("Fehler: Der Transcript-Channel wurde nicht gefunden, G! 🚨", ephemeral=True)

        await interaction.followup.send("Ticket wird geschlossen, G! 🚀", ephemeral=True)
        await self.ticket_channel.delete()

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_ticket_new")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Nur Teammitglieder können dieses Ticket übernehmen, G! 🚨", ephemeral=True)
            return

        if self.claimed:
            await interaction.response.send_message("Dieses Ticket wurde bereits übernommen, G! 🚀", ephemeral=True)
            return

        self.claimed = True
        self.children[1].disabled = True

        bot.db_users.update_one(
            {"_id": self.user_id, "tickets.channel_id": self.ticket_channel.id},
            {"$set": {"tickets.$.claimed_by": interaction.user.id}}
        )

        embed = discord.Embed(
            title="✅ Ticket übernommen ✅",
            description=f"{interaction.user.mention} hat dieses Ticket übernommen, G! 🚀",
            color=0x00FF00
        )
        embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
        await self.ticket_channel.send(embed=embed)

        await interaction.response.edit_message(view=self)

# --- Nachricht und Level ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    user_hinzufügen(user_id)
    user = bot.db_users.find_one({"_id": user_id})
    if not user:
        print(f"[ERROR] Benutzer {user_id} nicht in der Datenbank gefunden!")
        return

    now = int(discord.utils.utcnow().timestamp())
    last_xp = user.get("last_xp", 0)

    if now - last_xp >= XP_COOLDOWN:
        content_length = len(message.content)
        xp_gain = 5 if content_length < 20 else 10 if content_length <= 50 else 15

        if random.random() < 0.1:
            xp_gain *= 2
            await message.channel.send(f"🎉 Bonus! Du hast doppelte XP ({xp_gain} XP) erhalten, G! 🚀", delete_after=5)

        bot.db_users.update_one({"_id": user_id}, {"$inc": {"xp": xp_gain}, "$set": {"last_xp": now}})
        user = bot.db_users.find_one({"_id": user_id})
        new_level, _, _ = update_user_level(user_id, user)

        if new_level != user["level"]:
            await message.channel.send(f"🎉 Gratulation, {message.author.mention}! Du hast Level {new_level} erreicht, G! 🚀", delete_after=10)

    await bot.process_commands(message)

# --- Kick Synchronisierung ---
MAIN_SERVER_ID = 1365855616911802408
RELATED_SERVER_IDS = [
    1365855616911802408,  # Main-Server-ID jetzt auch in RELATED_SERVER_IDS
]

@bot.event
async def on_member_remove(member: discord.Member):
    if member.guild.id != MAIN_SERVER_ID:
        return

    try:
        embed = discord.Embed(
            title="❌ Dein Abo ist abgelaufen ❌",
            description="Um es zu verlängern oder bei Fragen melde dich beim Support, G! 🚨",
            color=0xFF0000
        )
        embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
        await member.send(embed=embed)
    except Exception as e:
        print(f"[ERROR] Konnte DM an {member.id} nicht senden: {e}")

    for server_id in RELATED_SERVER_IDS:
        try:
            guild = bot.get_guild(server_id)
            if guild and guild.get_member(member.id):
                await guild.kick(member, reason="Gekickt vom Hauptserver")
                print(f"[DEBUG] {member.id} wurde aus Server {server_id} gekickt.")
        except Exception as e:
            print(f"[ERROR] Fehler beim Kicken von {member.id} aus Server {server_id}: {e}")

# --- OAuth Join System ---
ALL_SERVER_IDS = [MAIN_SERVER_ID] + RELATED_SERVER_IDS
OAUTH_URL = "https://discord.com/oauth2/authorize?client_id=1361396825688375539&response_type=code&redirect_uri=https%3A%2F%2Fwww.oauth.malithwwc.de%2F&scope=identify+guilds.join+email+connections+guilds"

async def sync_member_roles(member, side_guild):
    main_guild = bot.get_guild(MAIN_SERVER_ID)
    if not main_guild:
        print(f"[ERROR] Main-Server {MAIN_SERVER_ID} nicht gefunden.")
        return

    main_member = main_guild.get_member(member.id)
    if not main_member:
        return

    side_member = side_guild.get_member(member.id)
    if not side_member:
        return

    main_roles = [role for role in main_member.roles if role.name != "@everyone"]
    side_roles = [role for role in side_member.roles if role.name != "@everyone"]

    for role in side_roles:
        if role.name not in [r.name for r in main_roles]:
            try:
                await side_member.remove_roles(role)
                await asyncio.sleep(1)
            except Exception as e:
                continue

    for role in main_roles:
        side_role = discord.utils.get(side_guild.roles, name=role.name)
        if not side_role:
            try:
                side_role = await side_guild.create_role(
                    name=role.name,
                    color=role.color,
                    hoist=role.hoist,
                    mentionable=role.mentionable,
                    permissions=role.permissions
                )
                await asyncio.sleep(1)
            except Exception as e:
                continue

        if side_role not in side_member.roles:
            try:
                await side_member.add_roles(side_role)
                await asyncio.sleep(1)
            except Exception as e:
                continue

@bot.event
async def on_member_join(member):
    if member.guild.id not in RELATED_SERVER_IDS:
        return
    await sync_member_roles(member, member.guild)

@bot.event
async def on_member_update(before, after):
    if before.guild.id != MAIN_SERVER_ID or before.roles == after.roles:
        return
    for side_server_id in RELATED_SERVER_IDS:
        side_guild = bot.get_guild(side_server_id)
        if side_guild:
            await sync_member_roles(after, side_guild)

@tasks.loop(minutes=5)
async def periodic_member_role_sync():
    main_guild = bot.get_guild(MAIN_SERVER_ID)
    if not main_guild:
        print(f"[ERROR] Main-Server {MAIN_SERVER_ID} nicht gefunden.")
        return
    for member in main_guild.members:
        if member.bot:
            continue
        for side_server_id in RELATED_SERVER_IDS:
            side_guild = bot.get_guild(side_server_id)
            if side_guild:
                await sync_member_roles(member, side_guild)

class JoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verifizieren", style=discord.ButtonStyle.green, custom_id="verify_oauth")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        user_hinzufügen(user_id)
        user = bot.db_users.find_one({"_id": user_id})
        if not user:
            await interaction.response.send_message("Ein Fehler ist aufgetreten, G! 🚨", ephemeral=True)
            return

        if user.get("oauth_access_token"):
            await interaction.response.send_message("Du bist bereits verifiziert, G! Klicke auf 'Join', um den Servern beizutreten! 🚀", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Verifizierung erforderlich ✅",
            description=f"Klicke auf den Link, um dich zu verifizieren, G! 🚀\n\n[Verifizieren]({OAUTH_URL})\n\n"
                        "Nach der Autorisierung wirst du zu https://www.elite-bond.de/ weitergeleitet. Kehre dann hierher zurück und klicke auf 'Join'!",
            color=0x00FF00
        )
        embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🚀 Join", style=discord.ButtonStyle.blurple, custom_id="join_servers")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        user_hinzufügen(user_id)
        user = bot.db_users.find_one({"_id": user_id})
        if not user:
            await interaction.followup.send("Ein Fehler ist aufgetreten, G! 🚨", ephemeral=True)
            return

        access_token = user.get("oauth_access_token")
        if not access_token:
            await interaction.followup.send("Du musst dich erst verifizieren, G! Klicke auf 'Verifizieren' und folge dem Link! 🚀", ephemeral=True)
            return

        joined_servers = []
        async with aiohttp.ClientSession() as session:
            for server_id in ALL_SERVER_IDS:
                try:
                    guild = bot.get_guild(server_id)
                    if guild:
                        if guild.get_member(user_id):
                            print(f"[DEBUG] {user_id} ist bereits im Server {server_id}.")
                            joined_servers.append((guild, True))
                            continue

                        headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
                        data = {"access_token": access_token}
                        async with session.put(
                            f"https://discord.com/api/v10/guilds/{server_id}/members/{user_id}",
                            headers=headers,
                            json=data
                        ) as response:
                            if response.status in (201, 204):
                                joined_servers.append((guild, False))
                                print(f"[DEBUG] {user_id} wurde zu Server {server_id} hinzugefügt.")
                            else:
                                print(f"[ERROR] Fehler beim Hinzufügen von {user_id} zu Server {server_id}: {response.status} {await response.text()}")
                                joined_servers.append((guild, False))
                except Exception as e:
                    print(f"[ERROR] Fehler beim Hinzufügen von {user_id} zu Server {server_id}: {e}")

        embed = discord.Embed(
            title="🎉 Du bist den Servern beigetreten! 🎉",
            description="Hier sind die Server, denen du beigetreten bist, G! 🚀\n"
                        "Klicke auf 'Leave', um Server zu verlassen, die du nicht brauchst.",
            color=0x00FF00
        )
        for guild, already_joined in joined_servers:
            status = " (Bereits Mitglied)" if already_joined else ""
            embed.add_field(name=f"{guild.name}{status}", value=f"ID: {guild.id}", inline=False)
        embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")

        view = LeaveServerView(joined_servers)
        try:
            await interaction.user.send(embed=embed, view=view)
            await interaction.followup.send("Du bist allen Servern beigetreten, G! Check deine DMs für mehr Infos! 🚀", ephemeral=True)
        except Exception as e:
            await interaction.followup.send("Konnte dir keine DM senden, G! Stelle sicher, dass deine DMs offen sind! 🚨", ephemeral=True)
            print(f"[ERROR] Konnte DM an {user_id} nicht senden: {e}")

class LeaveServerView(discord.ui.View):
    def __init__(self, joined_servers):
        super().__init__(timeout=None)
        self.joined_servers = joined_servers
        for guild, _ in joined_servers:
            button = discord.ui.Button(label=f"Leave {guild.name}", style=discord.ButtonStyle.red, custom_id=f"leave_{guild.id}")
            button.callback = self.create_leave_callback(guild)
            self.add_item(button)

    def create_leave_callback(self, guild):
        async def callback(interaction: discord.Interaction):
            try:
                member = guild.get_member(interaction.user.id)
                if member:
                    await member.kick(reason="User hat den Server verlassen")
                    await interaction.response.send_message(f"Du hast {guild.name} verlassen, G! 🚀", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Du bist nicht mehr in {guild.name}, G! 🚨", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Fehler beim Verlassen von {guild.name}, G! 🚨", ephemeral=True)
                print(f"[ERROR] Fehler beim Verlassen von Server {guild.id} für {interaction.user.id}: {e}")
        return callback

@bot.command()
async def joinsetup(ctx):
    embed = discord.Embed(
        title="🚀 Server Join System 🚀",
        description="Verifiziere dich und trete allen Servern bei, G! 🚀\n"
                    "- Klicke auf 'Verifizieren', um dem Bot die Berechtigung zu geben.\n"
                    "- Klicke auf 'Join', um allen Servern beizutreten!",
        color=0xFF0000
    )
    embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
    view = JoinView()
    await ctx.send(embed=embed, view=view)

# --- Bot Start ---
@bot.event
async def on_ready():
    print(f"{bot.user} ist online!")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} Slash-Commands synchronisiert!")

        bot.add_view(CoinSystemView())
        bot.add_view(RankLeaderboardView())
        bot.add_view(TicketView())
        bot.add_view(JoinView())
        print("[DEBUG] Alle Views hinzugefügt.")

        main_guild = bot.get_guild(MAIN_SERVER_ID)
        if main_guild:
            for member in main_guild.members:
                if member.bot:
                    continue
                for side_server_id in RELATED_SERVER_IDS:
                    side_guild = bot.get_guild(side_server_id)
                    if side_guild:
                        await sync_member_roles(member, side_guild)

        if not periodic_member_role_sync.is_running():
            periodic_member_role_sync.start()

        # Coin-Channel
        coin_channel = bot.get_channel(COIN_CHANNEL_ID)
        if coin_channel:
            print(f"[DEBUG] Coin-Channel {COIN_CHANNEL_ID} gefunden.")
            message_exists = False
            async for message in coin_channel.history(limit=100):
                if message.author == bot.user and message.embeds and message.embeds[0].title == "💸 COIN-SYSTEM 💸":
                    message_exists = True
                    break
            if not message_exists:
                async for message in coin_channel.history(limit=100):
                    if message.author == bot.user:
                        await message.delete()
                embed = discord.Embed(
                    title="💸 COIN-SYSTEM 💸",
                    description="🔥 **Tägliche Coins abholen:** Hol dir 10 Coins pro Tag, G! 🚀\n"
                                "💎 **Coins abfragen:** Check, wie viele Coins du hast!\n"
                                "🛒 **Shop öffnen:** Tausch deine Coins gegen Rewards ein!\n\n"
                                "Wähl eine Aktion unten aus, G! 💪",
                    color=0xFF0000
                )
                embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
                await coin_channel.send(embed=embed, view=CoinSystemView())

        # Level-Channel
        level_channel = bot.get_channel(LEVEL_CHANNEL_ID)
        if level_channel:
            print(f"[DEBUG] Level-Channel {LEVEL_CHANNEL_ID} gefunden.")
            message_exists = False
            async for message in level_channel.history(limit=100):
                if message.author == bot.user and message.embeds and message.embeds[0].title == "🏆 RANK-LEADERBOARD 🏆":
                    message_exists = True
                    break
            if not message_exists:
                async for message in level_channel.history(limit=100):
                    if message.author == bot.user:
                        await message.delete()
                embed, view = await update_rank_leaderboard()
                if embed and view:
                    await level_channel.send(embed=embed, view=view)

        # Ticket-Channel
        ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
        if ticket_channel:
            print(f"[DEBUG] Ticket-Channel {TICKET_CHANNEL_ID} gefunden.")
            message_exists = False
            async for message in ticket_channel.history(limit=100):
                if message.author == bot.user and message.embeds and message.embeds[0].title == "🎫 TICKET-SYSTEM 🎫":
                    message_exists = True
                    break
            if not message_exists:
                async for message in ticket_channel.history(limit=100):
                    if message.author == bot.user:
                        await message.delete()
                embed = discord.Embed(
                    title="🎫 TICKET-SYSTEM 🎫",
                    description="Erstelle ein Ticket, um mit dem Team zu sprechen, G! 🚀",
                    color=0xFF0000
                )
                embed.set_footer(text="© 2025 Elite-Bond. All rights reserved.")
                await ticket_channel.send(embed=embed, view=TicketView())

    except Exception as e:
        print(f"[ERROR] Fehler beim on_ready: {e}")

bot.run(TOKEN)
