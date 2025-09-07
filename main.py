import discord
from discord import app_commands, ui
from discord.ext import tasks
import os
import datetime
from dotenv import load_dotenv
import sys
import threading
from flask import Flask

# --- Flask ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot działa!"

# --- Wczytanie tokena ---
load_dotenv()
token = os.getenv("DISCORD_BOT_TOKEN")
if not token:
    print("Błąd: brak tokena Discord. Ustaw DISCORD_BOT_TOKEN w Render lub w .env")
    sys.exit(1)

# --- Ustawienia ---
PICK_ROLE_ID = 1413424476770664499
AIRDROP_CHANNEL_ID = 1206228467260330055
AIRDROP_ROLE_ID = 1413113420135268428
ZANCUDO_IMAGE_URL = "https://cdn.discordapp.com/attachments/1224129510535069766/1414194392214011974/image.png"
CAYO_IMAGE_URL = "https://cdn.discordapp.com/attachments/1224129510535069766/1414204332747915274/image.png"

captures = {}

# --- Discord Client ---
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- Klasy UI ---
class PlayerSelectMenu(ui.Select):
    def __init__(self, capture_id):
        self.capture_id = capture_id
        options = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in captures.get(self.capture_id, {}).get("participants", [])
        ]
        super().__init__(placeholder="Wybierz do 25 graczy", max_values=min(25, len(options)), options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

class PickPlayersView(ui.View):
    def __init__(self, capture_id):
        super().__init__()
        self.capture_id = capture_id
        self.player_select_menu = PlayerSelectMenu(capture_id)
        self.add_item(self.player_select_menu)

    @ui.button(label="Potwierdź wybór", style=discord.ButtonStyle.green)
    async def confirm_pick(self, interaction: discord.Interaction, button: ui.Button):
        selected_values = self.player_select_menu.values
        if len(selected_values) > 25:
            await interaction.response.send_message("Możesz wybrać maksymalnie 25 osób!", ephemeral=True)
            return
        selected_members = [interaction.guild.get_member(int(mid)) for mid in selected_values if interaction.guild.get_member(int(mid))]
        total_participants = len(captures.get(self.capture_id, {}).get("participants", []))
        final_embed = discord.Embed(
            title="Lista osób na captures!",
            description=f"Osoby które zostały wybrane na capt spośród {total_participants} osób to:",
            color=discord.Color(0xFFFFFF)
        )
        final_embed.add_field(name="Wybrani gracze:", value="\n".join(f"{i+1}. {m.mention} | **{m.display_name}**" for i, m in enumerate(selected_members)), inline=False)
        final_embed.set_footer(text=f"Wystawione przez {interaction.user.display_name} • {discord.utils.utcnow().strftime('%d.%m.%Y %H:%M')}")
        await interaction.response.send_message(embed=final_embed)

class CapturesView(ui.View):
    def __init__(self, capture_id):
        super().__init__(timeout=None)
        self.capture_id = capture_id

    @ui.button(label="Zapisz się na capt", style=discord.ButtonStyle.green, custom_id="join_capt")
    async def join_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user not in captures.get(self.capture_id, {}).get("participants", []):
            captures.setdefault(self.capture_id, {"participants": []})["participants"].append(interaction.user)
            await interaction.response.send_message("Zostałeś(aś) zapisany(a) na captures!", ephemeral=True)
        else:
            await interaction.response.send_message("Jesteś już zapisany(a) na captures!", ephemeral=True)

    @ui.button(label="Pickuj osoby", style=discord.ButtonStyle.blurple, custom_id="pick_players")
    async def pick_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.get_role(PICK_ROLE_ID):
            await interaction.response.send_message("Nie masz uprawnień do użycia tego przycisku.", ephemeral=True)
            return
        participants = captures.get(self.capture_id, {}).get("participants", [])
        if not participants:
            await interaction.response.send_message("Nikt jeszcze się nie zapisał!", ephemeral=True)
            return
        await interaction.response.send_message("Wybierz do 25 graczy z listy:", view=PickPlayersView(self.capture_id), ephemeral=True)

# --- Eventy i komendy ---
@client.event
async def on_ready():
    print(f'Zalogowano jako {client.user}')
    await tree.sync()
    send_airdrop_notifications.start()
    send_airdrop_announcements.start()

@tree.command(name="create-capt", description="Tworzy ogłoszenie o captures.")
@app_commands.describe(image_url="Link do obrazka dla embedu (opcjonalnie)")
async def create_capt(interaction: discord.Interaction, image_url: str = None):
    capture_id = interaction.id
    captures[capture_id] = {"participants": []}
    embed = discord.Embed(
        title="CAPTURES!",
        description="Aby wpisać się na captures kliknij w przycisk poniżej!",
        color=discord.Color(0xFFFFFF)
    )
    if image_url:
        embed.set_image(url=image_url)
    await interaction.response.send_message(content="@everyone", embed=embed, view=CapturesView(capture_id))

@tree.command(name="ping-zancudo", description="Wysyła ogłoszenie o ataku na Fort Zancudo.")
@app_commands.describe(role="Rola do spingowania", channel="Kanał, na którym się zbieracie")
async def ping_zancudo(interaction: discord.Interaction, role: discord.Role, channel: discord.VoiceChannel):
    await interaction.response.defer()
    embed = discord.Embed(
        title="Atak na FORT ZANCUDO!",
        description=f"Zapraszam wszystkich na {channel.mention}, atakujemy teren bazy wojskowej!",
        color=discord.Color(0xFFFFFF)
    )
    embed.set_image(url=ZANCUDO_IMAGE_URL)
    await interaction.channel.send(content=f"@everyone {role.mention}", embed=embed)

@tree.command(name="ping-cayo", description="Wysyła ogłoszenie o ataku na Cayo Perico.")
@app_commands.describe(role="Rola do spingowania", channel="Kanał, na którym się zbieracie")
async def ping_cayo(interaction: discord.Interaction, role: discord.Role, channel: discord.VoiceChannel):
    await interaction.response.defer()
    embed = discord.Embed(
        title="Atak na CAYO PERICO!",
        description=f"Zapraszam wszystkich na {channel.mention} - atakujemy wyspę Cayo Perico!",
        color=discord.Color(0xFFFFFF)
    )
    embed.set_image(url=CAYO_IMAGE_URL)
    await interaction.channel.send(content=f"@everyone {role.mention}", embed=embed)

# --- Zadania okresowe ---
@tasks.loop(minutes=60)
async def send_airdrop_notifications():
    now = datetime.datetime.now()
    if now.minute == 30 and (now.hour % 4) == 3:
        channel = client.get_channel(AIRDROP_CHANNEL_ID)
        if channel:
            await channel.send("Uwaga! AirDrop za 30 minut na kanale voice'owym! Zbierać się!")

@tasks.loop(minutes=60)
async def send_airdrop_announcements():
    now = datetime.datetime.now()
    if now.minute == 0 and (now.hour % 4) == 0:
        channel = client.get_channel(AIRDROP_CHANNEL_ID)
        role = client.get_role(AIRDROP_ROLE_ID)
        if channel and role:
            await channel.send(f"@everyone {role.mention} AirDrop {now.hour:02d}:00. Zbierać się i na # voice!")

# --- Uruchomienie Discord Bota w osobnym wątku ---
def run_discord_bot():
    client.run(token)

threading.Thread(target=run_discord_bot).start()

# --- Uruchomienie Flask ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
