import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# لم نعد بحاجة إلى undetected_chromedriver أو selenium_stealth

# --- إعدادات عامة ---
timers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

# --- دالة لقراءة الحسابات من ملف user.txt ---
def read_accounts(filename="user.txt"):
    """تقرأ الحسابات من ملف نصي وتعيدها كقائمة."""
    accounts = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    username_line = lines[i].strip()
                    password_line = lines[i+1].strip()
                    
                    if "username:" in username_line and "password:" in password_line:
                        username = username_line.split("username:", 1)[1].strip()
                        password = password_line.split("password:", 1)[1].strip()
                        accounts.append({"username": username, "password": password})
    except FileNotFoundError:
        print(f"خطأ: ملف {filename} غير موجود. تأكد من وجود الملف في المستودع.")
        return []
    return accounts

# --- دالة مساعدة لإنشاء تأخير عشوائي ---
def sleeper():
    """تنشئ تأخيراً زمنياً قصيراً وعشوائياً لمحاكاة السلوك البشري."""
    time.sleep(float("0." + random.choice(timers[1:9]) + random.choice(timers)))

# --- الدالة الرئيسية لتسجيل الدخول ---
def login_to_tiktok(username, password):
    """
    تقوم بتسجيل الدخول إلى حساب تيك توك واحد، وتستخرج معلوماته.
    """
    print(f"\n[بدء] محاولة تسجيل الدخول للحساب: {username}")

    # إعداد المتصفح باستخدام selenium القياسي مع خيارات لإخفاء البوت
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # خيارات قوية لإخفاء البوت
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = webdriver.Chrome(options=options)

    # تنفيذ سكربت لإزالة خاصية webdriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        start_time = time.time()
        driver.get("https://www.tiktok.com/login/phone-or-email/email")

        # --- إدخال اسم المستخدم ---
        username_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email or username']"))
        )
        for char in username:
            username_field.send_keys(char)
            sleeper()

        # --- إدخال كلمة المرور ---
        password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password']")
        for char in password:
            password_field.send_keys(char)
            sleeper()

        # --- النقر على زر تسجيل الدخول ---
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        login_button.click()

        # --- استخراج معلومات الحساب بعد تسجيل الدخول ---
        print(f"[نجاح] تم تسجيل الدخول بنجاح للحساب: {username}. جاري استخراج المعلومات...")
        
        profile_icon = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@data-e2e='top-nav-avatar']//img"))
        )
        profile_icon.click()
        
        profile_username_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//h1[@data-e2e='user-title']"))
        )
        profile_username = profile_username_element.text

        try:
            bio_element = driver.find_element(By.XPATH, "//h2[@data-e2e='user-bio']")
            bio = bio_element.text
        except:
            bio = "لا يوجد وصف"

        end_time = time.time()
        duration = end_time - start_time

        print("-" * 30)
        print(f"  ✅ تم تسجيل الدخول بنجاح!")
        print(f"  📧 البريد الإلكتروني: {username}")
        print(f"  👤 اسم المستخدم في تيك توك: {profile_username}")
        print(f"  📝 الوصف: {bio}")
        print(f"  ⏱️ تمت العملية في {duration:.2f} ثانية")
        print("-" * 30)

    except Exception as e:
        print(f"[خطأ] فشلت عملية تسجيل الدخول للحساب {username}: {e}")

    finally:
        driver.quit()
        print(f"[انتهاء] تم الانتهاء من معالجة الحساب: {username}")


# --- نقطة بداية تشغيل البرنامج ---
if __name__ == "__main__":
    accounts_to_login = read_accounts("user.txt")
    
    if not accounts_to_login:
        print("لم يتم العثور على حسابات صالحة في ملف user.txt. الرجاء التحقق من الملف.")
    else:
        print(f"تم العثور على {len(accounts_to_login)} حساباً. بدء المعالجة المتسلسلة...")
        
        for account in accounts_to_login:
            login_to_tiktok(account['username'], account['password'])

        print("\nاكتملت جميع محاولات تسجيل الدخول.")
