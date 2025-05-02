import asyncio
from datetime import datetime

LEVEL_ROLES = [
    {"id": 1366518019303669830, "seconds": 10},  # Ersetze durch echte Rollen-ID
    {"id": 1366518057115062383, "seconds": 20},
    {"id": 1366518080179540000, "seconds": 30},
]

async def badge_level_task(bot):
    print("badge_level_task wurde aufgerufen!")  # Debug
    await bot.wait_until_ready()
    print("Badge Level Task gestartet!")  # Debug
    while not bot.is_closed():
        for guild in bot.guilds:
            print(f"Prüfe Server: {guild.name}")  # Debug
            for member in guild.members:
                if member.bot or not member.joined_at:
                    continue
                seconds_on_server = (datetime.utcnow() - member.joined_at.replace(tzinfo=None)).total_seconds()
                print(f"{member.display_name} ist seit {int(seconds_on_server)} Sekunden auf dem Server.")  # Debug
                for role_info in LEVEL_ROLES:
                    role = guild.get_role(role_info["id"])
                    if role:
                        print(f"Gefundene Rolle: {role.name} (ID: {role.id})")  # Debug
                    if role and seconds_on_server >= role_info["seconds"]:
                        if role not in member.roles:
                            print(f"Füge {role.name} zu {member.display_name} hinzu")  # Debug
                            try:
                                await member.add_roles(role, reason="Level/Badge System")
                                print(f"Rolle {role.name} erfolgreich zu {member.display_name} hinzugefügt!")  # Debug
                            except Exception as e:
                                print(f"Fehler beim Hinzufügen der Rolle: {e}")  # Debug
        await asyncio.sleep(5)