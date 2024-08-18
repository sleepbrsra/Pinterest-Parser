import json
import os
import requests
from playwright.sync_api import sync_playwright
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

def load_config():
    if not os.path.exists('config.json'):
        with open('config.json', 'w') as config_file:
            json.dump({
                "email": "",
                "password": "",
                "save_credentials": False,
                "show_process": True
            }, config_file, indent=4)
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

def save_config(config):
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)

def prompt_for_credentials(config):
    if config['email'] and config['password']:
        use_saved = input(f"{Fore.YELLOW}Use saved credentials? (y/n): {Style.RESET_ALL}").strip().lower()
        if use_saved == 'y':
            return config['email'], config['password']
    
    email = input(f"{Fore.CYAN}Enter your email: {Style.RESET_ALL}").strip()
    password = input(f"{Fore.CYAN}Enter your password: {Style.RESET_ALL}").strip()

    save_credentials = input(f"{Fore.YELLOW}Save credentials for future use? (y/n): {Style.RESET_ALL}").strip().lower()
    if save_credentials == 'y':
        config['email'] = email
        config['password'] = password
        config['save_credentials'] = True
        save_config(config)
    else:
        config['save_credentials'] = False
        save_config(config)

    return email, password

def download_image(url, folder_path, show_process):
    try:
        if url and url.startswith('http'):
            response = requests.get(url)
            if response.status_code == 200:
                image_name = os.path.join(folder_path, url.split("/")[-1].split("?")[0])
                if show_process:
                    print(f"\n{Fore.CYAN}[INFO]{Style.RESET_ALL} Downloading image: {Fore.YELLOW}{url}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Saving to: {Fore.YELLOW}{image_name}{Style.RESET_ALL}")
                
                with open(image_name, 'wb') as f:
                    f.write(response.content)
                
                if os.path.exists(image_name):
                    print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Image successfully saved: {Fore.YELLOW}{image_name}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to save image: {Fore.YELLOW}{image_name}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to download image: {Fore.YELLOW}{url}{Style.RESET_ALL} (Status: {response.status_code})")
        else:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Invalid image URL: {Fore.YELLOW}{url}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Error downloading image: {e}")

def main():
    config = load_config()
    email, password = prompt_for_credentials(config)
    show_process = input(f"{Fore.YELLOW}Show process? (y/n): {Style.RESET_ALL}").strip().lower() == 'y'

    album_url = input(f"{Fore.CYAN}Enter Pinterest album URL: {Style.RESET_ALL}").strip()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not show_process)  # Launch browser in visible or headless mode
        page = browser.new_page()

        print(f"\n{Fore.CYAN}[INFO]{Style.RESET_ALL} Navigating to Pinterest login page...")
        page.goto("https://www.pinterest.com/login/")
        page.fill("input[name='id']", email)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")

        page.wait_for_load_state("networkidle")
        if "login" not in page.url:
            print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Login successful!")
        else:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Login failed, check your credentials and try again.")
            browser.close()
            exit()

        try:
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Navigating to album page: {Fore.YELLOW}{album_url}{Style.RESET_ALL}")
            page.goto(album_url)
            page.wait_for_load_state("domcontentloaded")
            
            if album_url in page.url:
                print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Successfully navigated to album page.")
            else:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to navigate to album page.")
                browser.close()
                exit()
        
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Error navigating to album page: {e}")
            browser.close()
            exit()

        last_height = page.evaluate("document.body.scrollHeight")
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            page.wait_for_timeout(2000)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        pin_links = page.query_selector_all('a[href*="/pin/"]')
        pin_urls = [link.get_attribute('href') for link in pin_links]

        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Found {Fore.YELLOW}{len(pin_urls)}{Style.RESET_ALL} pins.")

        folder_path = "downloaded_images"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        for pin_url in pin_urls:
            if not pin_url.startswith('http'):
                pin_url = 'https://www.pinterest.com' + pin_url
            page.goto(pin_url)
            page.wait_for_timeout(3000)
            img_element = page.query_selector('img[src*="originals"], img[srcset]')
            if img_element:
                img_url = img_element.get_attribute('src')
                if not img_url:
                    img_url = img_element.get_attribute('srcset').split()[-2]
                if img_url:
                    print(f"\n{Fore.CYAN}[INFO]{Style.RESET_ALL} Found image: {Fore.YELLOW}{img_url}{Style.RESET_ALL}")
                    download_image(img_url, folder_path, show_process)
                else:
                    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to find image URL.")
            else:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to find image element on page.")
        
        browser.close()

if __name__ == "__main__":
    main()
