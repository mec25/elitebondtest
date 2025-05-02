import json
import os
import asyncio
from datetime import datetime
import discord
import io
from PIL import Image, ImageDraw, ImageFont
import requests

LEVEL_FILE = "levels.json"
LEADERBOARD_FILE = "leaderboard_channel.json"

def load_levels():
    if not os.path.exists(LEVEL_FILE):
        return {}
    with open(LEVEL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_levels(data):
    with open(LEVEL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def get_user_level_data(user_id):
    data = load_levels()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1}
        save_levels(data)
    return data[str(user_id)]

def update_user_level_data(user_id, xp=None, level=None):
    data = load_levels()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1}
    if xp is not None:
        data[str(user_id)]["xp"] = xp
    if level is not None:
        data[str(user_id)]["level"] = level
    save_levels(data)

def get_level_xp(level):
    # XP needed for next level (simple formula)
    return 100 + (level - 1) * 140

def get_leaderboard():
    data = load_levels()
    sorted_users = sorted(data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)
    return sorted_users

def save_leaderboard_channel(guild_id, channel_id):
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    data[str(guild_id)] = channel_id
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def get_leaderboard_channel(guild_id):
    if not os.path.exists(LEADERBOARD_FILE):
        return None
    with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(str(guild_id))

async def add_xp(bot, user, amount, channel=None):
    user_data = get_user_level_data(user.id)
    old_level = user_data["level"]
    user_data["xp"] += amount
    # Level up logic
    while user_data["xp"] >= get_level_xp(user_data["level"]):
        user_data["xp"] -= get_level_xp(user_data["level"])
        user_data["level"] += 1
        await send_levelup_card(bot, user, user_data["level"], user_data["xp"], channel)
    update_user_level_data(user.id, xp=user_data["xp"], level=user_data["level"])

async def send_levelup_card(bot, user, level=None, xp=None, channel=None):
    user_data = get_user_level_data(user.id)
    if level is None:
        level = user_data["level"]
    if xp is None:
        xp = user_data["xp"]
    leaderboard = get_leaderboard()
    rank = next((i+1 for i, (uid, _) in enumerate(leaderboard) if int(uid) == user.id), None)
    xp_needed = get_level_xp(level)
    percent = int((xp / xp_needed) * 100)

    # Bildgröße und Farben
    width, height = 700, 220
    background_color = (40, 15, 20)
    bar_color = (120, 40, 60)
    bar_fill = (0, 180, 255)
    text_color = (255, 255, 255)
    accent = (255, 255, 255)

    # Bild erstellen
    img = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(img)

    # Fonts (Passe ggf. den Pfad an oder nutze einen Standard-Font)
    try:
        font_bold = ImageFont.truetype("arialbd.ttf", 36)
        font = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except:
        font_bold = ImageFont.load_default()
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Profilbild laden und rund machen
    avatar_asset = user.display_avatar.replace(size=128)
    avatar_bytes = await avatar_asset.read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    mask = Image.new("L", avatar.size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0) + avatar.size, fill=255)
    avatar.putalpha(mask)
    img.paste(avatar, (30, 30), avatar)

    # Name und Platz
    draw.text((180, 40), f"{user.display_name}", font=font_bold, fill=text_color)
    draw.text((width - 180, 40), f"Platz Nr. {rank}", font=font_bold, fill=accent, anchor="ra")

    # Level und XP
    draw.text((180, 90), f"Level: {level}", font=font, fill=text_color)
    draw.text((180, 120), f"XP: {xp}/{xp_needed}", font=font, fill=text_color)

    # Fortschrittsbalken
    bar_x, bar_y, bar_w, bar_h = 180, 160, 480, 22
    draw.rounded_rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h], 12, fill=bar_color)
    fill_w = int(bar_w * percent / 100)
    if fill_w > 0:
        draw.rounded_rectangle([bar_x, bar_y, bar_x+fill_w, bar_y+bar_h], 12, fill=bar_fill)

    # Level-Marker (wie im Bild)
    for i, lvl in enumerate(range(level, level+5)):
        pos = bar_x + int(bar_w * (i+1)/5)
        draw.ellipse((pos-16, bar_y-28, pos+16, bar_y), fill=(0, 180, 255, 180))
        draw.text((pos, bar_y-18), f"{lvl*5}", font=font_small, fill=(255,255,255), anchor="mm")

    # Bild speichern und senden
    with io.BytesIO() as image_binary:
        img.save(image_binary, 'PNG')
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename="levelup.png")
        if channel is None:
            try:
                await user.send(file=file)
            except Exception:
                pass
        else:
            await channel.send(file=file)

async def leaderboard_task(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            channel_id = get_leaderboard_channel(guild.id)
            if channel_id:
                channel = guild.get_channel(channel_id)
                if channel:
                    leaderboard = get_leaderboard()
                    desc = ""
                    for i, (uid, data) in enumerate(leaderboard[:10]):
                        member = guild.get_member(int(uid))
                        name = member.display_name if member else f"User {uid}"
                        desc += f"**#{i+1} {name}** — Level {data['level']} | XP {data['xp']}\n"
                    embed = discord.Embed(
                        title="🏆 Leaderboard",
                        description=desc or "Noch keine Daten.",
                        color=discord.Color.gold()
                    )
                    await channel.purge(limit=10)
                    await channel.send(embed=embed)
        await asyncio.sleep(60 * 60 * 12)  # alle 12h