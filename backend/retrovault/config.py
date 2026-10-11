import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')

def integer(name: str, default: int, minimum: int = 1) -> int:
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f'{name} must be >= {minimum}')
    return value

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://retro:retro_local@localhost:55432/retrovault')
APP_ORIGIN = os.getenv('APP_ORIGIN', 'http://localhost:3000')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
SIMULATION_INTERVAL = integer('SIMULATION_INTERVAL_SECONDS', 1800)
IMPORT_INTERVAL = integer('IMPORT_INTERVAL_SECONDS', 86400)
SESSION_TTL = integer('SESSION_TTL_SECONDS', 86400)
RENTAL_DAYS = integer('RENTAL_DAYS', 7)
SALE_STOCK = integer('SALE_STOCK', 3)
RENTAL_STOCK = integer('RENTAL_STOCK', 2)
SALE_PRICE = integer('SALE_PRICE_CENTS', 9990)
RENTAL_PRICE = integer('RENTAL_PRICE_CENTS', 1490)
PLATFORMS = {'snes': 'Super Nintendo Entertainment System', 'gba': 'Game Boy Advance',
             'ps1': 'PlayStation', 'ps2': 'PlayStation 2', 'psp': 'PlayStation Portable',
             'nds': 'Nintendo DS'}
LABELS = {'snes': 'SNES', 'gba': 'GBA', 'ps1': 'PlayStation', 'ps2': 'PlayStation 2', 'psp': 'PSP', 'nds': 'Nintendo DS'}
