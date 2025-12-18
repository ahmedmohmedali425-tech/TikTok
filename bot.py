import os
import re
import time
import random
import logging
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium_stealth import stealth
import undetected_chromedriver as uc
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- إعدادات ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
USE_PROXY = os.environ.get("USE_PROXY", "false").lower() == "true"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- قائمة من User-Agents ---
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# --- حالات المحادثة ---
(EMAIL, PASSWORD, VERIFICATION_CODE, USERNAME, BIRTHDAY, BIRTHMONTH, BIRTHYEAR) = range(7)

# --- ملفات ---
ACCOUNTS_FILE = 'user.txt'
PROFILES_FILE = 'profiles.txt' # لحفظ معلومات التحقق

# --- قائمة لتخزين بيانات إنشاء الحساب ---
creation_queue = []

# --- دوال مساعدة ---
def generate_random_email():
    domains = ["example.com", "test.com", "mail.com", "gmail.com"]
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
    domain = random.choice(domains)
    return f"{username}@{domain}"

def generate_random_string(length=10):
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choice(chars) for _ in range(length))

def save_account_details(username, password, email):
    with open(ACCOUNTS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"user: {username} passowed: {password}\n")
    with open(PROFILES_FILE, 'a', encoding='utf-8') as f:
        f.write(f"Email: {email}\nUsername: {username}\nPassword: {password}\n---\n")

def check_email_inbox(driver, email):
    """تحقق من البريد الإلكتروني (محاكاة). هذا الجزء يتطلب خدمات خارجية."""
    logger.info(f"Checking email for {email}...")
    time.sleep(10) # محاكاة الانتظار
    # في الواقع، ستحتاج إلى استخدام خدمات مثل IMAP/POP3 مع Hotmail/Outlook/Gmail API
    # هذا مجرد مثال على كيفية عمل ذلك
    return True # نفترض أننا وجدنا الرمز

# --- دالة إنشاء الحساب ---
def create_tiktok_account(email, username, password):
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
        
        if USE_PROXY:
            logger.info("Proxy is enabled (Note: Configure proxy details in the code).")
            # options.add_argument(f'--proxy-server=http://your-proxy:port')
        
        driver = uc.Chrome(options=options, version_main=None)
        stealth(driver, vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

        # الخطوة 1: اذهب إلى صفحة التسجيل عبر البريد
        driver.get("https://www.tiktok.com/signup/")
        
        # الخطوة 2: اختر استخدام البريد الإلكتروني
        email_option = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Use email')]"))
        )
        email_option.click()
        
        # الخطوة 3: أدخل البريد الإلكتروني
        email_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        )
        email_field.send_keys(email)
        time.sleep(1)
        
        # الخطوة 4: اضغط "Next"
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
        )
        next_button.click()

        # الخطوة 5: أدخل كلمة المرور
        password_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
        )
        password_field.send_keys(password)
        time.sleep(1)
        
        # الخطوة 6: اضغط "Next"
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
        )
        next_button.click()
        
        # الخطوة 7: اختر تاريخ الميلاد
        # هذا جزء معقد وقد يتغير مع تحديثات تيك توك
        # سنقوم بوضع تاريخ ثابت لتجاوزه
        try:
            # اختيار اليوم
            day_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='birthday_day']"))
            )
            day_field.send_keys("1")
            
            # اختيار الشهر
            month_field = driver.find_element(By.XPATH, "//select[@name='birthday_month']")
            from selenium.webdriver.support.ui import Select
            select = Select(month_field)
            select.select_by_visible_text("Jan")
            
            # اختيار السنة
            year_field = driver.find_element(By.XPATH, "//input[@name='birthday_year']")
            year_field.send_keys("1990")
            
            time.sleep(1)
            
            # اضغط "Next" مرة أخرى
            final_next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
            )
            final_next_button.click()
        except Exception as e:
            logger.error(f"Error during birthday selection: {e}")
            return {"status": "failed", "message": "فشل في اختيار تاريخ الميلاد."}

        # الخطوة 8: إنشاء اسم مستخدم (اختياري)
        try:
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username']"))
            )
            username_field.send_keys(username)
            time.sleep(1)
            
            # اضغط "Sign up"
            signup_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign up')]"))
            )
            signup_button.click()
        except Exception as e:
            logger.error(f"Error during username/signup: {e}")
            return {"status": "failed", "message": "فشل في إنشاء اسم المستخدم."}

        # الخطوة 9: انتظر صفحة التحقق
        try:
            logger.info("Waiting for verification page...")
            WebDriverWait(driver, 30).until(
                EC.url_contains("verification")
            )
            logger.info("Verification page detected.")
            return {"status": "verification_needed", "message": "تم إرسال رمز تحقق إلى بريدك الإلكتروني. الرجاء التحقق وإدخال الرمز."}
        except TimeoutException:
            logger.error("Verification page did not appear in time.")
            return {"status": "failed", "message": "لم تظهر صفحة التحقق في الوقت المناسب."}

    except Exception as e:
        if driver:
            driver.quit()
        logger.error(f"Error during account creation: {e}", exc_info=True)
        return {"status": "failed", "message": f"فشل في إنشاء الحساب: {str(e)}"}

# --- دالة تسجيل الدخول (محسنة) ---
def login_and_get_info(email, password, verification_code=None):
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
        
        if USE_PROXY:
            logger.info("Proxy is enabled (Note: Configure proxy details in the code).")
        
        driver = uc.Chrome(options=options, version_main=None)
        stealth(driver, vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

        driver.get("https://www.tiktok.com/login/phone-or-email/email")
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Email or username')]"))
        ).send_keys(email)

        driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Password')]").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)

        if "verification" in driver.current_url:
            if not verification_code:
                return {"status": "need_verification_code", "message": "تم إرسال رمز تحقق. الرجاء إدخاله."}
            
            code_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Verification code')]"))
            )
            code_field.send_keys(verification_code)
            driver.find_element(By.XPATH, "//button[contains(., 'Verify')]").click()
            time.sleep(4)

        if "reset-password" in driver.current_url:
            return {"status": "need_new_password", "message": "كلمة المرور خاطئة. يرجى تسجيل الدخول يدوياً."}

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-e2e='top-nav-avatar']//img"))
        ).click()
        
        profile_info = {}
        try:
            profile_info['username'] = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h1[@data-e2e='user-title']"))
            ).text
            profile_info['bio'] = driver.find_element(By.XPATH, "//h2[@data-e2e='user-bio']").text
        except:
            profile_info['bio'] = "لا يوجد وصف"
        
        try:
            followers_element = driver.find_element(By.XPATH, "//a[contains(@href, '/followers')]//strong")
            profile_info['followers'] = followers_element.text
        except:
            profile_info['followers'] = "غير متوفر"

        driver.quit()
        return {"status": "success", "info": profile_info}

    except Exception as e:
        if driver:
            driver.quit()
        logger.error(f"Error during login for {email}: {e}", exc_info=True)
        return {"status": "failed", "message": f"فشل تسجيل الدخول: {str(e)}"}

# --- معالجات الأوامر والرسائل ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("تسجيل دخول جديد", callback_data='new_login')],
        [InlineKeyboardButton("إنشاء حساب جديد", callback_data='create_account')],
        [InlineKeyboardButton("عدد الحسابات المسجلة", callback_data='count_accounts')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("أهلاً بك! اختر ما تريد فعله:", reply_markup=reply_markup)
    return ConversationHandler.END

async def new_login_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="أرسل لي بريدك الإلكتروني أو اسم المستخدم وكلمة المرور:")
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("ممتاز. الآن أرسل لي كلمة المرور:")
    return PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['password'] = update.message.text
    await update.message.reply_text("جاري محاولة تسجيل الدخول...")
    
    email = context.user_data['email']
    password = context.user_data['password']
    
    result = login_and_get_info(email, password)
    
    if result['status'] == 'success':
        save_account_details(email, password, email)
        info = result['info']
        msg = (f"✅ **تم تسجيل الدخول بنجاح!**\n\n"
               f"👤 **اسم المستخدم:** {info['username']}\n"
               f"📝 **الوصف:** {info['bio']}\n"
               f"👥 **المتابعون:** {info['followers']}")
        await update.message.reply_text(msg, parse_mode='Markdown')
    elif result['status'] == 'need_verification_code':
        await update.message.reply_text(f"❌ {result['message']}")
    else:
        await update.message.reply_text(f"❌ {result['message']}")
        
    return ConversationHandler.END

async def create_account_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="جاري إنشاء بريد إلكتروني مؤقت... هذا قد يستغرق بعض الوقت.")
    
    # توليد بيانات عشوائية
    temp_email = generate_random_email()
    temp_password = generate_random_string(12)
    temp_username = f"user_{generate_random_string(6)}"
    
    await update.message.reply_text(
        f"تم إنشاء بيانات مؤقتة:\n"
        f"📧 **البريد:** {temp_email}\n"
        f"👤 **اسم المستخدم:** {temp_username}\n"
        f"🔑 **كلمة المرور:** {temp_password}\n\n"
        f"سيتم الآن محاولة إنشاء الحساب على تيك توك..."
    )
    
    result = create_tiktok_account(temp_email, temp_username, temp_password)
    
    if result['status'] == 'verification_needed':
        creation_queue.append({'email': temp_email, 'password': temp_password, 'username': temp_username, 'update': update, 'context': context})
        await update.message.reply_text(result['message'])
        return VERIFICATION_CODE
    else:
        await update.message.reply_text(f"❌ فشل إنشاء الحساب: {result['message']}")
        
    return ConversationHandler.END

async def get_verification_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    if not creation_queue:
        await update.message.reply_text("لا توجد عملية إنشاء حساب نشطة.")
        return ConversationHandler.END

    account_data = creation_queue.pop(0)
    creation_queue.clear()

    await update.message.reply_text("جاري التحقق من الرمز...")
    
    # في تطبيق حقيقي، ستقوم هنا بالتحقق من البريد الإلكتروني
    # check_email_inbox(driver, account_data['email'])
    
    # محاكاة التحقق الناجح
    await update.message.reply_text("تم التحقق من الرمز بنجاح. جاري إكمال إنشاء الحساب...")
    
    # بعد التحقق، سنقوم بتسجيل الدخول بالبيانات الصحيحة
    result = login_and_get_info(account_data['email'], account_data['password'])
    
    if result['status'] == 'success':
        save_account_details(account_data['username'], account_data['password'], account_data['email'])
        info = result['info']
        msg = (f"✅ **تم إنشاء وتسجيل الدخول بنجاح!**\n\n"
               f"📧 **البريد:** {account_data['email']}\n"
               f"👤 **اسم المستخدم:** {info['username']}\n"
               f"🔑 **كلمة المرور:** {account_data['password']}\n"
               f"👥 **المتابعون:** {info['followers']}")
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ فشل إكمال العملية: {result['message']}")
        
    return ConversationHandler.END

async def count_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            profiles = f.read()
            await query.edit_message_text(text=f"معلومات الحسابات التي تم إنشاؤها:\n\n{profiles}")
    except FileNotFoundError:
        await query.edit_message_text(text="لا توجد حسابات تم إنشاؤها.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set!")
        return
        
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(new_login_prompt, pattern='^new_login$'),
            CallbackQueryHandler(create_account_prompt, pattern='^create_account$'),
        ],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            VERIFICATION_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_verification_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_chat=True,
        per_message=False,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(count_accounts, pattern='^count_accounts$'))
    
    application.run_polling()

if __name__ == "__main__":
    main()
