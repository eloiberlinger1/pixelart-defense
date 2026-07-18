import json
import os
import time
import glob
from curl_cffi import requests

URL_CANVAS = 'https://intra.land/api/pixel/canvas?campus=Heilbronn'
URL_PLACE = 'https://intra.land/api/pixel/place'

WIDTH, HEIGHT = 128, 128
ACCOUNTS_DIR = 'accounts'

START_X = 61
START_Y = 90

SAFE_ZONES = [
    ((2, 20), (30, 47)),
    ((84, 94), (110, 118))
    ((33,76), (37,83))
]

DRAWINGS = [
    {
        "name": "Example_Small_Heart",
        "offset_x": 60,
        "offset_y": 40,
        "pixels": [
            [-1, 18, 18, -1, 18, 18, -1],
            [18, 18, 18, 18, 18, 18, 18],
            [-1, 18, 18, 18, 18, 18, -1],
            [-1, -1, 18, 18, 18, -1, -1],
            [-1, -1, -1, 18, -1, -1, -1]
        ]
    }
]

CUSTOM_PIXELS = {}
for drawing in DRAWINGS:
    ox, oy = drawing["offset_x"], drawing["offset_y"]
    for row_idx, row in enumerate(drawing["pixels"]):
        for col_idx, color in enumerate(row):
            if color != -1:
                CUSTOM_PIXELS[(ox + col_idx, oy + row_idx)] = color

def is_in_safe_zone(x, y):
    """Checks if a pixel is in a zone that should not be attacked."""
    for (tl_x, tl_y), (br_x, br_y) in SAFE_ZONES:
        if tl_x <= x <= br_x and tl_y <= y <= br_y:
            return True
    return False

def get_expected_color(x, y):
    """Determines the color a pixel MUST have."""
    if (x, y) in CUSTOM_PIXELS:
        return CUSTOM_PIXELS[(x, y)]
    
    if x < 42: return 14
    elif x < 85: return 1
    else: return 18

def get_all_accounts():
    accounts = []
    if not os.path.exists(ACCOUNTS_DIR):
        os.makedirs(ACCOUNTS_DIR)
        return accounts
    for filepath in glob.glob(os.path.join(ACCOUNTS_DIR, '*.json')):
        try:
            with open(filepath, 'r') as f:
                raw_cookies = json.load(f)
            cookie_str = "; ".join([f'{c["name"]}={c["value"]}' for c in raw_cookies])
            accounts.append((os.path.basename(filepath), cookie_str))
        except Exception:
            pass
    return accounts

def get_current_canvas(cookie_string):
    headers = {
        'accept': '*/*',
        'cookie': cookie_string,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
    }
    try:
        response = requests.get(URL_CANVAS, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            board = {}
            for i, color_code in enumerate(response.content):
                board[(i % WIDTH, i // WIDTH)] = color_code
            return board
    except Exception:
        pass
    return None

def find_mismatches(board):
    """Compares the map, ignores safe zones, and sorts from the center."""
    targets = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if is_in_safe_zone(x, y):
                continue
                
            current_color = board.get((x, y))
            expected_color = get_expected_color(x, y)
            
            if current_color != expected_color:
                targets.append((x, y, expected_color))
                
    targets.sort(key=lambda t: (abs(t[1] - START_Y), abs(t[0] - START_X), t[1], t[0]))
    return targets

def place_pixel(cookie_string, x, y, color):
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'cookie': cookie_string,
        'origin': 'https://intra.land',
        'referer': 'https://intra.land/pixel',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    payload = {"x": x, "y": y, "color": color, "campus": "Heilbronn"}
    try:
        response = requests.post(URL_PLACE, headers=headers, json=payload, impersonate="chrome120", timeout=15)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    accounts = get_all_accounts()
    
    if not accounts:
        print("No accounts available.")
        return

    print("Analyzing map...")
    board = get_current_canvas(accounts[0][1])
    
    if not board:
        print("Failed to retrieve map.")
        return

    targets = find_mismatches(board)
    print(f"-> {len(targets)} pixel(s) to correct/place starting from ({START_X}, {START_Y}).")

    if not targets:
        print("The flag and drawings are perfect!")
        return

    target_index = 0
    total_targets = len(targets)

    for filename, cookie_string in accounts:
        if target_index >= total_targets:
            break 

        print(f"\n=== Connection: {filename} ===")
        
        while target_index < total_targets:
            x, y, color = targets[target_index]
            print(f"[{filename}] Correcting at (x={x}, y={y}) with color {color}...")
            
            success, message = place_pixel(cookie_string, x, y, color)

            if success:
                print(f"-> Success! ({target_index + 1}/{total_targets})")
                target_index += 1
                try:
                    resp_data = json.loads(message)
                    if resp_data.get("balance", 0) <= 0:
                        break
                except json.JSONDecodeError:
                    pass
                time.sleep(2)
            else:
                try:
                    resp_data = json.loads(message)
                    if "error" in resp_data and resp_data["error"] == "no tokens":
                        print(f"-> Cooldown. Moving to next account.")
                        break
                except json.JSONDecodeError:
                    break

    print("\nAll accounts processed.")

if __name__ == "__main__":
    main()
