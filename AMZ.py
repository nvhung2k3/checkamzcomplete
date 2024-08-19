# Import necessary modules
import time
import threading
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import requests
from GPMLoginAPI import GPMLoginAPI
from selenium.webdriver.chrome import service
from selenium.webdriver.chrome.options import Options
from UndetectChromeDriver import UndetectChromeDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from screeninfo import get_monitors
from colorama import init, Fore, Style
from amazoncaptcha import AmazonCaptcha

api = GPMLoginAPI('http://127.0.0.1:19995')
init()
print(Fore.GREEN + 'ADD CARD AMZ V1' + Style.RESET_ALL)
number_of_profiles = int(input('Nhập số luồng chạy profile: '))
proxy = input('Nhập proxy (Định dạng: host:port:username:password): ')

# Read the TXT file
def read_credentials(file_path):
    credentials = []
    with open(file_path, 'r') as file:
        for line in file:
            email, password, code_2fa = line.strip().split('|')
            credentials.append({
                'email': email,
                'password': password,
                '2fa': code_2fa
            })
    return credentials

credentials = read_credentials('C:\\Users\\Admin\\Downloads\\CHECKACCCOMPLETE\\mailcheck.txt')

monitor = get_monitors()[0]
screen_width = monitor.width
screen_height = monitor.height
columns = 4
rows = 3
window_width = screen_width // columns
window_height = screen_height // rows

profile_counter = 1
profile_counter_lock = threading.Lock()

active_positions = []
active_positions_lock = threading.Lock()

def create_profile(profile_number):
    profile_name = f"addcard{profile_number}"

    print(f'CREATE PROFILE {profile_name}------------------')
    createdResult = api.Create(profile_name, proxy)
    createdProfileId = None
    if createdResult is not None:
        status = bool(createdResult['status'])
        if status:
            createdProfileId = str(createdResult['profile_id'])
    print(f"Created profile ID {profile_name}: {createdProfileId}")

    return createdProfileId

def position_window(driver, x, y, width, height):
    driver.set_window_position(x, y)
    driver.set_window_size(width, height)

def get_next_position():
    with active_positions_lock:
        if len(active_positions) >= columns * rows:
            active_positions.clear()
        all_positions = [(col * window_width, row * window_height)
                         for row in range(rows) for col in range(columns)]
        next_position = next(pos for pos in all_positions if pos not in active_positions)
        active_positions.append(next_position)
        return next_position

def solve_captcha(driver):
    link = driver.find_element(By.XPATH, "//div[@class='a-row a-text-center']//img").get_attribute('src')
    captcha = AmazonCaptcha.fromlink(link)
    captcha_value = AmazonCaptcha.solve(captcha)
    input_field = driver.find_element(By.ID, 'captchacharacters')
    input_field.send_keys(captcha_value)
    time.sleep(2)
    button = driver.find_element(By.CLASS_NAME, 'a-button-text')
    button.click()
    time.sleep(2)
def log_to_file(file_path, email, password, code_2fa):
    with open(file_path, 'a') as file:
        file.write(f'{email}|{password}|{code_2fa}\n')
def run_profile(profile_number):
    retries = 3  # Number of retries
    for attempt in range(retries):
        createdProfileId = create_profile(profile_number)
        if createdProfileId:
            print(f'START PROFILE addcard{profile_number}------------------')
            startedResult = api.Start(createdProfileId)
            if startedResult is not None:
                status = bool(startedResult['status'])
                if status:
                    seleniumRemoteDebugAddress = str(startedResult["selenium_remote_debug_address"])
                    gpmDriverPath = str(startedResult["selenium_driver_location"])

                    try:
                        # Init selenium
                        options = Options()
                        options.debugger_address = seleniumRemoteDebugAddress
                        myService = service.Service(gpmDriverPath)
                        driver = UndetectChromeDriver(service=myService, options=options)

                        # Calculate the window position based on available positions
                        x, y = get_next_position()

                        # Debugging prints to verify position calculations
                        print(f"Profile {profile_number} -> Position: ({x}, {y}), Size: ({window_width}, {window_height})")

                        # Position the window
                        position_window(driver, x, y, window_width, window_height)
                        driver.GetByGpm("https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3F_encoding%3DUTF8%26ref_%3Dnav_ya_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0")
                        wait = WebDriverWait(driver, 10)
                        
                        # Check for CAPTCHA
                        try:
                            captcha_img = driver.find_element(By.XPATH, "//div[@class='a-row a-text-center']//img")
                            if captcha_img:
                                solve_captcha(driver)
                        except:
                            pass

                        email_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="ap_email"]')))
                        email = credentials[profile_number - 1]['email']
                        password = credentials[profile_number - 1]['password']
                        code_2fa = credentials[profile_number - 1]['2fa']
                        # nhap mail
                        driver.execute_script("arguments[0].value = arguments[1];", email_input, email)
                        time.sleep(random.uniform(2, 4))
                        continue_button = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="continue"]')))
                        driver.execute_script("arguments[0].click();", continue_button)

                        try:
                            captcha_img = driver.find_element(By.XPATH, "//div[@class='a-row a-text-center']//img")
                            if captcha_img:
                                solve_captcha(driver)
                        except:
                            pass
                        # Wait for the password input element to be present
                        password_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="ap_password"]')))
                        driver.execute_script("arguments[0].value = arguments[1];", password_input, password)
                        time.sleep(random.uniform(2, 4))
                        # Wait for the sign-in submit button to be present
                        sign_in_button = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="signInSubmit"]')))
                        driver.execute_script("arguments[0].click();", sign_in_button)
                        # wait otp
                        time.sleep(random.uniform(2, 4))
                        otp_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="auth-mfa-otpcode"]')))
                        # lấy otp
                        # 2fa 
                        response = requests.get(f'https://2fa.live/tok/{code_2fa}')
                        response_data = response.json()
                        otp_code = response_data['token']
                        # Enter the 2FA code
                        driver.execute_script("arguments[0].value = arguments[1];", otp_input, otp_code)
                        # Click the "Remember device" checkbox
                        remember_device_checkbox = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="auth-mfa-remember-device"]')))
                        driver.execute_script("arguments[0].click();", remember_device_checkbox)
                        time.sleep(random.uniform(1, 2))
                         # Click the submit button
                        submit_button = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="auth-signin-button"]')))
                        driver.execute_script("arguments[0].click();", submit_button)
                        
                        time.sleep(2)
                        # Check for "Account on hold temporarily" and log as dead
                        try:
                            account_hold_message = driver.find_element(By.XPATH, "//h4[text()='Account on hold temporarily']")
                            if account_hold_message:
                                script = '''
                                const elscreen = document.createElement('div');
                                elscreen.style.cssText = 'position: fixed;inset: 0px;background: rgb(206 236 206 / 89%);z-index: 20000;display: flex;justify-content: center;align-items: center;font-size: 80pt;color: #FF4500;';
                                elscreen.innerHTML = 'ACC DIE';
                                document.body.appendChild(elscreen);
                            '''
                                driver.execute_script(script)
                                log_to_file('AccDie.txt', email, password, code_2fa)
                                time.sleep(5)
                                break
                                
                        except:
                            pass

                        
                        # Check for "skip" link and click it if present
                        try:
                            skip_link = wait.until(EC.presence_of_element_located((By.XPATH, '//a[@id="ap-account-fixup-phone-skip-link"]')))
                            driver.execute_script("arguments[0].click();", skip_link)
                        except:
                            pass

                        time.sleep(2)
                        wait = WebDriverWait(driver, 30)
                        wait.until(EC.any_of(
                            
                            EC.presence_of_element_located((By.ID, 'navbar')),
                            EC.presence_of_element_located((By.ID, 'navbar-backup-backup'))
                        ))
                        driver.GetByGpm("https://www.amazon.com/cpe/yourpayments/transactions")
                        wait = WebDriverWait(driver, 10)

                        try:

                            # Check if the "Completed" text is present
                            driver.find_element(By.XPATH, '//span[text()="Completed"]')
                            script = '''
                                const elscreen = document.createElement('div');
                                elscreen.style.cssText = 'position: fixed;inset: 0px;background: rgb(206 236 206 / 89%);z-index: 20000;display: flex;justify-content: center;align-items: center;font-size: 80pt;color: #005a1c;';
                                elscreen.innerHTML = 'BÚ';
                                document.body.appendChild(elscreen);
                            '''
                            driver.execute_script(script)
                            log_to_file('AccComplete.txt', email, password, code_2fa)
                        except:
                            # If "Completed" is not found, execute the "NO BÚ" script
                            script = '''
                                const elscreen = document.createElement('div');
                                elscreen.style.cssText = 'position: fixed;inset: 0px;background: rgb(206 236 206 / 89%);z-index: 20000;display: flex;justify-content: center;align-items: center;font-size: 80pt;color: #FF4500;';
                                elscreen.innerHTML = 'NO BÚ';
                                document.body.appendChild(elscreen);
                            '''
                            driver.execute_script(script)
                            log_to_file('AccNoComplete.txt', email, password, code_2fa)

                        

                        time.sleep(5)
                        break

                    except Exception as e:
                        print(f"Error in thread addcard{profile_number}: {e}")
                        print('DELETE PROFILE ------------------')
                        api.Delete(createdProfileId)
                        print(f"Deleted: {createdProfileId}")
                        if attempt < retries - 1:
                            print(f"Retry {attempt + 1} for profile addcard{profile_number}")
                        else:
                            print(f"Failed after {retries} attempts for profile addcard{profile_number}")
                    finally:
                        try:
                            driver.close()
                            driver.quit()
                        except Exception as e:
                            print(f"Error closing driver in thread addcard{profile_number}: {e}")

            print(f'CLOSE PROFILE addcard{profile_number}------------------')

def run_profiles_dynamically():
    global profile_counter
    with ThreadPoolExecutor(max_workers=number_of_profiles) as executor:
        futures = {}
        for _ in range(min(number_of_profiles, len(credentials))):
            with profile_counter_lock:
                profile_number = profile_counter
                profile_counter += 1
            futures[executor.submit(run_profile, profile_number)] = profile_number

        while futures:
            for future in as_completed(futures):
                profile_number = futures.pop(future)
                if profile_counter <= len(credentials):
                    print(f'Profile {profile_number} has finished. Starting a new profile...')
                    with profile_counter_lock:
                        new_profile_number = profile_counter
                        profile_counter += 1
                    futures[executor.submit(run_profile, new_profile_number)] = new_profile_number

if __name__ == "__main__":
    try:
        run_profiles_dynamically()
    except KeyboardInterrupt:
        print('Process interrupted by user. Exiting...')
