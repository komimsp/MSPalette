import discord
from discord.ext import commands
import json
import requests
import os
from datetime import datetime
import warnings
from urllib3.exceptions import InsecureRequestWarning
from msp import invoke_method, get_session_id, ticket_header

warnings.simplefilter('ignore', InsecureRequestWarning)

# Stałe dane logowania
USERNAME = "testbots1"  # Twoja nazwa użytkownika
PASSWORD = "q12345"     # Twoje hasło
SERVER = "pl"           # Serwer (np. 'pl')

# Funkcja logowania do MSP2
async def login_msp2():
    """Logowanie do MSP2 przy użyciu stałych danych."""
    global ticket, actor_id

    # Wywołanie metody logowania na serwerze MSP2
    code, resp = invoke_method(
        SERVER,
        "MovieStarPlanet.WebService.User.AMFUserServiceWeb.Login",
        [
            USERNAME,
            PASSWORD,
            [],
            None,
            None,
            "MSP1-Standalone:XXXXXX"
        ],
        get_session_id()
    )

    if not resp or 'loginStatus' not in resp:
        print("Nie udało się połączyć z serwerem. Spróbuj ponownie później.")
        return

    status = resp['loginStatus'].get('status', 'Brak informacji')
    if status != "Success":
        print(f"Logowanie nie powiodło się. Status: {status}")
        return

    ticket = resp['loginStatus']['ticket']
    actor_id = resp['loginStatus']['actor']['ActorId']
    print("Zalogowano pomyślnie!")

# Funkcja do serializacji daty na format JSON
def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {obj.__class__.__name__} not serializable")

# Funkcja do uzyskania sesji
def get_session_id():
    return "mock_session_id"

# Inicjalizacja bota
intents = discord.Intents.default()
intents.message_content = True  # Umożliwia odczytywanie treści wiadomości

# Inicjalizacja bota
bot = commands.Bot(command_prefix='/', intents=intents)

# Uruchomienie bota i logowanie po starcie
@bot.event
async def on_ready():
    """Wykonaj logowanie po uruchomieniu bota."""
    print(f"Zalogowano jako {bot.user.name}")
    await login_msp2()  # Automatyczne logowanie

# Funkcja do pobierania informacji o ubraniu
@bot.command()
async def itemid(ctx, cloth_id: int):
    """Pobiera dane o ubraniu z MSP2."""
    global SERVER

    # Wywołanie metody z serwera MSP
    code, resp = invoke_method(
        SERVER,
        "MovieStarPlanet.WebService.MovieStar.AMFMovieStarService.LoadClothesWithThemeByIds",
        [[cloth_id]],
        get_session_id()
    )

    # Walidacja odpowiedzi
    if not resp or not isinstance(resp, list) or len(resp) == 0 or 'ClothItem' not in resp[0]:
        await ctx.send(f"Nie znaleziono informacji o ubraniu z ID: {cloth_id}")
        return

    item = resp[0]['ClothItem']
    theme_id = resp[0].get('Theme', {}).get('ThemeId', 'Brak informacji')  # Pobranie ThemeId

    # Pobieranie danych ubrania
    clothing_info = {
        'ClothesId': item['ClothesId'],
        'Name': item['Name'],
        'SWF': item.get('SWF', 'N/A'),
        'Price': item.get('Price', 0),
        'Diamonds': item.get('Discount', 0),
        'VIP': "Tak" if item.get('Vip') else "Nie",
        'LastUpdated': format_date(item.get('LastUpdated', 'Unknown')),
        'PublishableDate': format_date(item.get('PublishableDate', 'Unknown')),
        'ThemeId': theme_id,
        'ColorScheme': [color for color in item.get('ColorScheme', '').split(',') if color.startswith('0x')]
    }

    # Ustawianie koloru embeda
    try:
        main_color = int(clothing_info['ColorScheme'][0], 16)
    except (ValueError, IndexError):
        main_color = 0x000000

    # Ścieżka do obrazu
    local_image_path = os.path.join(
        r"C:\Users\windo\Desktop\msp-py-main\MSP-Clothes-preview-main",
        f"{clothing_info['ClothesId']}.png"
    )

    if not os.path.exists(local_image_path):
        await ctx.send(f"Nie znaleziono obrazu dla ID: {cloth_id} w podanej lokalizacji.")
        return

    # Tworzenie embeda
    embed = discord.Embed(
        title=f"{clothing_info['Name']} (ID: {clothing_info['ClothesId']})",
        description="Informacje o ubraniu",
        color=main_color
    )

    # Formatowanie pól w dwóch kolumnach
    embed.add_field(
        name="**item**", 
        value=(
            f"✍️ **Nazwa:** {clothing_info['Name']}\n"
             f"💎 **Cena Diamantów:** {clothing_info['Diamonds']} Diamonds\n"
            f"💰 **Cena SC:** {clothing_info['Price']} SC\n"
            f"👑 **VIP:** {clothing_info['VIP']}\n"
        ),
        inline=True
    )
    embed.add_field(
        name="**other**", 
        value=(
            f"🖼️ **Plik SWF:** {clothing_info['SWF']}\n"
            f"🎭 **Theme ID:** {clothing_info['ThemeId']}\n"
            f"📅 **Data publikacji:** {clothing_info['PublishableDate']}\n"
            f"📅 **Ostatnia aktualizacja:** {clothing_info['LastUpdated']}\n"
        ),
        inline=True
    )

    # Lista kolorów
    color_scheme = "\n".join(
        [f"{i+1} >> `{color}`" for i, color in enumerate(clothing_info['ColorScheme'])]
    ) or "Brak danych o kolorach."
    embed.add_field(name="🎨 **Lista kolorów**", value=color_scheme, inline=False)

    embed.set_image(url=f"attachment://{os.path.basename(local_image_path)}")
    embed.set_footer(text=":)")

    # Wysyłanie embeda wraz z obrazem
    with open(local_image_path, 'rb') as file:
        picture = discord.File(file, filename=os.path.basename(local_image_path))
        await ctx.send(embed=embed, file=picture)


# Funkcja formatująca daty
def format_date(date_obj):
    if date_obj == 'Unknown' or not date_obj:
        return "Nieznana data"
    try:
        # Jeśli data jest już obiektem datetime
        if isinstance(date_obj, datetime):
            return date_obj.strftime("%d-%m-%Y %H:%M:%S")
        # Jeśli data jest ciągiem znaków
        date_obj = datetime.strptime(date_obj, "%Y-%m-%dT%H:%M:%S")
        return date_obj.strftime("%d-%m-%Y %H:%M:%S")
    except (ValueError, TypeError):
        return "Niepoprawny format daty"

# Uruchomienie bota
bot.run('ODk0MTUxNzM2MTM3MjQ4Nzk5.GnEJf5.VBS-BWuTUM3vWtDV55A23U7lH6YGj4CPTYkqSA')
