import os
import time
import random
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import undetected_chromedriver as uc

# --- إعدادات عامة ---
# قائمة بأجزاء من الأرقام لإنشاء تأخيرات عشوائية
timers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

# --- قراءة بيانات الحسابات من الملف ---
def read_accounts(filename="user.txt"):
    """تقرأ الحسابات من ملف نصي وتعيدها كقائمة."""
    accounts = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i in range(0, len(lines), 2):
                # التأكد من وجود سطر يوزر نيم وباسورد
                if i + 1 < len(lines):
                    username_line = lines[i].strip()
                    password_line = lines[i+1].strip()
                    
                    # استخلاص القيم بعد النقطتين
                    if "username:" in username_line and "password:" in password_line:
                        username = username_line.split("username:", 1)[1].strip()
                        password = password_line.split("password:", 1)[1].strip()
                        accounts.append({"username": username, "password": password})
    except FileNotFoundError:
        print(f"خطأ: ملف {filename} غير موجود.")
        return []
    return accounts

# --- دالة مساعدة لإنشاء تأخير عشوائي ---
def sleeper():
    """تنشئ تأخيراً زمنياً قصيراً وعشوائياً لمحاكاة السلوك البشري."""
    # تأخير عشوائي بين 0.1 و 0.9 ثانية
    time.sleep(float("0." + random.choice(timers[1:9]) + random.choice(timers)))

# --- الدالة الرئيسية لتسجيل الدخول لكل حساب ---
def login_to_tiktok(account):
    """
    تقوم بتسجيل الدخول إلى حساب تيك توك واحد، وتستخرج معلوماته.
    """
    username = account['username']
    password = account['password']
    
    print(f"\n[بدء] محاولة تسجيل الدخول للحساب: {username}")

    # إعداد المتصفح لكل خيط على حدة
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # إضافة خيار headless إذا أردت تشغيله بدون واجهة رسومية
    # options.add_argument("--headless")
    
    driver = uc.Chrome(use_subprocess=True, headless=False, options=options)

    # إخفاء البوت
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    try:
        start_time = time.time()
        driver.get("https://www.tiktok.com/login/phone-or-email/email")

        # --- إدخال اسم المستخدم ---
        try:
            # انتظر حتى يظهر حقل البريد الإلكتروني
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email or username']"))
            )
            for char in username:
                username_field.send_keys(char)
                sleeper()
        except Exception as e:
            print(f"[خطأ] لم يتم العثور على حقل اسم المستخدم لحساب {username}: {e}")
            driver.quit()
            return

        # --- إدخال كلمة المرور ---
        try:
            password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password']")
            for char in password:
                password_field.send_keys(char)
                sleeper()
        except Exception as e:
            print(f"[خطأ] لم يتم العثور على حقل كلمة المرور لحساب {username}: {e}")
            driver.quit()
            return

        # --- النقر على زر تسجيل الدخول ---
        try:
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            login_button.click()
        except Exception as e:
            print(f"[خطأ] لم يتم العثور على زر تسجيل الدخول لحساب {username}: {e}")
            driver.quit()
            return

        # --- استخراج معلومات الحساب بعد تسجيل الدخول ---
        try:
            print(f"[نجاح] تم تسجيل الدخول بنجاح للحساب: {username}. جاري استخراج المعلومات...")
            
            # الانتظار حتى تظهر أيقونة الملف الشخصي ثم النقر عليها
            profile_icon = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@data-e2e='top-nav-avatar']//img"))
            )
            profile_icon.click()
            
            # الانتظار حتى يتم تحميل اسم المستخدم في الصفحة الشخصية
            profile_username_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//h1[@data-e2e='user-title']"))
            )
            profile_username = profile_username_element.text

            # استخراج الوصف (Bio)
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
            print(f"[خطأ] فشل استخراج معلومات الحساب {username} بعد تسجيل الدخول: {e}")

    except Exception as e:
        print(f"[خطأ] فشلت عملية تسجيل الدخول للحساب {username}: {e}")

    finally:
        # إبقاء المتصفح مفتوحاً لفترة قصيرة للمشاهدة ثم إغلاقه
        time.sleep(5)
        driver.quit()
        print(f"[انتهاء] تم الانتهاء من معالجة الحساب: {username}")


# --- نقطة بداية تشغيل البرنامج ---
if __name__ == "__main__":
    accounts_to_login = read_accounts("user.txt")
    
    if not accounts_to_login:
        print("لم يتم العثور على حسابات صالحة في ملف user.txt. الرجاء التحقق من الملف.")
    else:
        print(f"تم العثور على {len(accounts_to_login)} حساباً. بدء التشغيل المتوازي...")
        
        threads = []
        for account in accounts_to_login:
            # إنشاء خيط (thread) لكل حساب
            thread = threading.Thread(target=login_to_tiktok, args=(account,))
            threads.append(thread)
            thread.start() # بدء الخيط
        
        # انتظار جميع الخيوط حتى تنتهي عملها
        for thread in threads:
            thread.join()
            
        print("\nاكتملت جميع محاولات تسجيل الدخول.")
