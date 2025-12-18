import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import undetected_chromedriver as uc

# --- إعدادات عامة ---
timers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

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

    # إعداد المتصفح للعمل بدون واجهة رسومية (headless) في GitHub Actions
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # تشغيل المتصفح في الخلفية
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = uc.Chrome(use_subprocess=True, headless=True, options=options)

    # إخفاء البوت
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Linux", # تحديد النظام الأساسي ليتوافق مع خادم GitHub
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

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
    # قراءة الحسابات من متغيرات البيئة (GitHub Secrets)
    accounts_str = os.environ.get("TIKTOK_ACCOUNTS")
    if not accounts_str:
        print("خطأ: لم يتم العثور على متغير TIKTOK_ACCOUNTS.")
    else:
        # تحويل النص من الـ Secret إلى قائمة من الحسابات
        accounts_list = [acc.strip() for acc in accounts_str.split('\n') if acc.strip()]
        
        print(f"تم العثور على {len(accounts_list)} حساباً. بدء المعالجة المتسلسلة...")
        
        for account_line in accounts_list:
            try:
                # تقسيم السطر إلى يوزر نيم وباسورد
                username, password = account_line.split(':', 1)
                username = username.strip()
                password = password.strip()
                login_to_tiktok(username, password)
            except ValueError:
                print(f"[خطأ] تنسيق السطر التالي غير صحيح: '{account_line}'. يجب أن يكون 'username:password'.")
            except Exception as e:
                print(f"[خطأ عام] أثناء معالجة السطر '{account_line}': {e}")

        print("\nاكتملت جميع محاولات تسجيل الدخول.")
