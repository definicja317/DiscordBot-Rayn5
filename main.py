import discord
from discord import app_commands, ui
from discord.ext import tasks
import os
import datetime
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_BOT_TOKEN")
client.run(token)

# Zastąp ID roli, która ma uprawnienia do "pikowania"
PICK_ROLE_ID = 1387501577748873284 
# Zastąp ID kanału, na który mają być wysyłane ogłoszenia
AIRDROP_CHANNEL_ID = 1387501580583964814
# Zastąp ID roli, która ma być pingowana w ogłoszeniach o AirDropie
AIRDROP_ROLE_ID = 1387501577782300781 
# Link do obrazka dla komendy /ping-zancudo
ZANCUDO_IMAGE_URL = "https://cdn.discordapp.com/attachments/1224129510535069766/1414194392214011974/image.png?ex=68beaea9&is=68bd5d29&hm=31655931b06dc52d7e1be6cd8521e7efe76be3dc57c8e68f816a322d06cce344&"
# Link do obrazka dla komendy /ping-cayo
CAYO_IMAGE_URL = "https://cdn.discordapp.com/attachments/1224129510535069766/1414204332747915274/image.png?ex=68beb7eb&is=68bd666b&hm=dd5a29a2777ff0470b0a01d97cbb2f15782fe53f9151a943abf71b4a3ea23542&"

# Słownik do przechowywania danych o capture
captures = {}

# Konfiguracja bota
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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

        selected_members = []
        for member_id in selected_values:
            member = interaction.guild.get_member(int(member_id))
            if member:
                selected_members.append(member)

        total_participants = len(captures.get(self.capture_id, {}).get("participants", []))

        final_embed = discord.Embed(
            title="Lista osób na captures!",
            description=f"Osoby które zostały wybrane na capt spośród {total_participants} osób to:",
            color=discord.Color(0xFFFFFF)
        )

        final_list = ""
        for i, member in enumerate(selected_members, 1):
            final_list += f"{i}. {member.mention} | **{member.display_name}**\n"
        
        final_embed.add_field(name="Wybrani gracze:", value=final_list, inline=False)
        final_embed.set_footer(text=f"Wystawione przez {interaction.user.display_name} • {discord.utils.utcnow().strftime('%d.%m.%Y %H:%M')}")
        
        await interaction.response.send_message(embed=final_embed)

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

class CapturesView(ui.View):
    def __init__(self, capture_id):
        super().__init__(timeout=None)
        self.capture_id = capture_id

    @ui.button(label="Zapisz się na capt", style=discord.ButtonStyle.green, custom_id="join_capt")
    async def join_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user not in captures.get(self.capture_id, {}).get("participants", []):
            if self.capture_id not in captures:
                captures[self.capture_id] = {"participants": []}
            captures[self.capture_id]["participants"].append(interaction.user)
            await interaction.response.send_message(f"Zostałeś(aś) zapisany(a) na captures!", ephemeral=True)
        else:
            await interaction.response.send_message(f"Jesteś już zapisany(a) na captures!", ephemeral=True)

    @ui.button(label="Pickuj osoby", style=discord.ButtonStyle.blurple, custom_id="pick_players")
    async def pick_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.get_role(PICK_ROLE_ID):
            await interaction.response.send_message("Nie masz uprawnień do użycia tego przycisku.", ephemeral=True)
            return

        participants = captures.get(self.capture_id, {}).get("participants", [])
        if not participants:
            await interaction.response.send_message("Nikt jeszcze się nie zapisał!", ephemeral=True)
            return
        
        await interaction.response.send_message(
            "Wybierz do 25 graczy z listy:",
            view=PickPlayersView(self.capture_id),
            ephemeral=True
        )

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

    await interaction.response.send_message(
        content="@everyone",
        embed=embed,
        view=CapturesView(capture_id)
    )

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
    await interaction.channel.send(
        content=f"@everyone {role.mention}",
        embed=embed
    )

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
    await interaction.channel.send(
        content=f"@everyone {role.mention}",
        embed=embed
    )

# Funkcja do wysyłania powiadomień o AirDropach 30 minut przed
@tasks.loop(minutes=60)
async def send_airdrop_notifications():
    now = datetime.datetime.now()
    if now.minute == 30 and (now.hour % 4) == 3:
        channel = client.get_channel(AIRDROP_CHANNEL_ID)
        if channel:
            await channel.send("Uwaga! AirDrop za 30 minut na kanale voice'owym! Zbierać się!")

# Funkcja do wysyłania ogłoszeń o AirDropach o pełnej godzinie
@tasks.loop(minutes=60)
async def send_airdrop_announcements():
    now = datetime.datetime.now()
    if now.minute == 0 and (now.hour % 4) == 0:
        channel = client.get_channel(AIRDROP_CHANNEL_ID)
        role = client.get_role(AIRDROP_ROLE_ID)
        if channel and role:
            await channel.send(f"@everyone {role.mention} AirDrop {now.hour:02d}:00. Zbierać się i na # voice!")

client.run(TOKEN)
