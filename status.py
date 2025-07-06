import time
import datetime
import os
import threading
import requests

# === COLORS ===
PINK = '\033[95m'
RESET = '\033[0m'

def get_time():
    return f"{PINK}[{datetime.datetime.now().strftime('%H:%M:%S')}]{RESET}"

os.system('cls' if os.name == 'nt' else 'clear')
print(f"{PINK} SectorX - Status Rotator {RESET}\n")

# Ask how many statuses
try:
    total = int(input("How many statuses you want? "))
except:
    print("Invalid number")
    exit()

statuses = []
for i in range(total):
    text = input(f"{PINK}Status > {RESET}")
    statuses.append(text)

# Delay
try:
    delay = int(input("\nDelay? (in seconds) >  "))
except:
    delay = 10

# Token
token = input("Enter your USER token: ")

# Headers for requests
headers = {
    'Authorization': token,
    'Content-Type': 'application/json'
}

url = 'https://discord.com/api/v9/users/@me/settings'

def set_status(text):
    payload = {
        "custom_status": {
            "text": text
        }
    }
    try:
        r = requests.patch(url, json=payload, headers=headers)
        if r.status_code == 200:
            print(f"{get_time()} > Changed to: {text}")
        else:
            print(f"{get_time()} > Failed: {r.status_code} | {r.text}")
    except Exception as e:
        print(f"{get_time()} > ERROR: {e}")

def rotator():
    while True:
        for status in statuses:
            set_status(status)
            time.sleep(delay)

# Run
threading.Thread(target=rotator).start()
