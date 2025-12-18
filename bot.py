import os
import re
import json
import time
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- إعدادات ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
USE_PROXY = os.environ.get("USE_PROXY", "false").lower() == "true"
PROXY_IP = os.environ.get("PROXY_IP")
PROXY_PORT = os.environ.get("PROXY_PORT")

# --- ملفات ---
ACCOUNTS_FILE = 'user.txt'
SESSIONS_FILE = 'sessions.txt'

logging.basicConfig(
    format="asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- قائمة User-Agents ---
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
]

# --- حالات المحادثة ---
(EMAIL, PASSWORD, USERNAME, BIRTHDAY, BIRTHMONTH, BIRTHYEAR, VERIFICATION_CODE, ACCOUNT_CHOICE) = range(7)

# --- قوائم مؤقتة ---
creation_queue = []
login_queue = []

# --- دوال مساعدة ---
def read_accounts():
    """يقرأ الحسابات من ملف user.txt."""
    accounts = {}
    if not os.path.exists(ACCOUNTS_FILE):
        return accounts
    with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if ':' in line:
                email, password = line.strip().split(':', 1)
                accounts[email] = password
    return accounts

def read_sessions():
    """يقرأ الجلسات من ملف sessions.json."""
    sessions = {}
    if not os.path.exists(SESSIONS_FILE):
        return sessions
    try:
        with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}
    return sessions

def save_account(email, password):
    """يحفظ حساب في ملف user.txt."""
    accounts = read_accounts()
    accounts[email] = password
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        for email, password in accounts.items():
            f.write(f"{email}:{password}\n")

def save_session(email, cookies):
    """يحفظ الجلسة (الكوكيز) في ملف sessions.json."""
    sessions = read_sessions()
    # تحويل كائنات الكوكيز إلى قائمة من القواميس
    cookies_list = [{'name': c['name'], 'value': c['value']} for c in cookies]
    sessions[email] = cookies_list
    with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, indent=4)

def delete_session(email):
    """يحذف جلسة من ملف sessions.json."""
    sessions = read_sessions()
    if email in sessions:
        del sessions[email]
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, indent=4)
        return True
    return False

def get_driver_options():
    """إعداد خيارات المتصفح."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
    return options

# --- دوال التسجيل والتحقق ---
def create_tiktok_account(email, username, password, birthday_day, birthday_month, birthday_year):
    """إنشاء حساب تيك توك جديد باستخدام البيانات المقدمة."""
    driver = None
    try:
        service = ChromeDriverManager().install()
        options = get_driver_options()
        if USE_PROXY and PROXY_IP and PROXY_PORT:
            options.add_argument(f'--proxy-server=http://{PROXY_IP}:{PROXY_PORT}')
            logger.info(f"Using proxy: {PROXY_IP}:{PROXY_PORT}")
        else:
            logger.info("Proxy is disabled.")

        driver = webdriver.Chrome(service=service, options=options)
        stealth(driver, vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

        logger.info(f"Navigating to signup page for {email}")
        driver.get("https://www.tiktok.com/signup/")

        # الخطوة 1: استخدام البريد الإلكتروني
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Use email')]"))
        ).click()
        time.sleep(2)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        ).send_keys(email)
        time.sleep(1)

        # الخطوة 2: كلمة المرور
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
        ).click()
        time.sleep(1)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
        ).send_keys(password)
        time.sleep(1)

        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
        ).click()
        time.sleep(1)

        # الخطوة 3: تاريخ الميلاد
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@name='birthday_day']"))
        ).send_keys(birthday_day)
        time.sleep(1)
        
        month_field = driver.find_element(By.XPATH, "//select[@name='birthday_month']")
        from selenium.webdriver.support.ui import Select
        Select(month_field).select_by_visible_text(birthday_month)
        time.sleep(1)
        
        year_field = driver.find_element(By.XPATH, "//input[@name='birthday_year']")
        year_field.send_keys(birthday_year)
        time.sleep(1)

        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
        ).click()
        time.sleep(2)

        # الخطوة 4: اسم المستخدم
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username']"))
        ).send_keys(username)
        time.sleep(1)

        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
        ).click()
        time.sleep(2)

        # الخطوة 5: إنهاء الحساب
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign up')]"))
        ).click()
        
        logger.info(f"Account creation initiated for {username}. Waiting for verification page...")
        
        # انتظار صفحة التحقق
        WebDriverWait(driver, 30).until(
            EC.url_contains("verification")
        )
        logger.info(f"Verification page detected for {username}.")
        return {"status": "verification_needed", "message": f"تم إنشاء الحساب '{username}'. تم إرسال رمز تحقق إلى بريدك الإلكتروني {email}."}

    except Exception as e:
        if driver:
            driver.quit()
        logger.error(f"Error during account creation for {email}: {e}", exc_info=True)
        return {"status": "failed", "message": f"فشل إنشاء الحساب: {str(e)}"}

def login_with_session(email, cookies):
    """تسجيل الدخول باستخدام الجلسة (الكوكيز) المحفوظة."""
    driver = None
    try:
        service = ChromeDriverManager().install()
        options = get_driver_options()
        if USE_PROXY and PROXY_IP and PROXY_PORT:
            options.add_argument(f'--proxy-server=http://{PROXY_IP}:{PROXY_PORT}')
            logger.info(f"Using proxy for login with session: {PROXY_IP}:{PROXY_PORT}")
        else:
            logger.info("Proxy is disabled for session login.")

        driver = webdriver.Chrome(service=service, options=options)
        stealth(driver, vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

        # الذهاب إلى صفحة تسجيل الدخول وإضافة الكوكيز
        driver.get("https://www.tiktok.com/login/phone-or-email/email")
        
        # إضافة الكوكيز إلى المتصفح
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"Could not add cookie {cookie.get('name')}: {e}")

        driver.refresh()
        time.sleep(3)

        # التحقق من أننا في الصفحة الرئيسية بعد تسجيل الدخول
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-e2e='top-nav-avatar']//img"))
        )
        
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
        logger.error(f"Error during session login for {email}: {e}", exc_info=True)
        return {"status": "failed", "message": f"فشل تسجيل الدخول بالجلسة: {str(e)}"}

def login_and_get_info(email, password, verification_code=None):
    """تسجيل الدخول العادي باستخدام البريد وكلمة المرور."""
    driver = None
    try:
        service = ChromeDriverManager().install()
        options = get_driver_options()
        if USE_PROXY and PROXY_IP and PROXY_PORT:
            options.add_argument(f'--proxy-server=http://{PROXY_IP}:{PROXY_PORT}')
            logger.info(f"Using proxy for login: {PROXY_IP}:{PROXY_PORT}")
        else:
            logger.info("Proxy is disabled for standard login.")

        driver = webdriver.Chrome(service=service, options=options)
        stealth(driver, vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

        driver.get("https://www.tiktok.com/login/phone-or-email/email")
        
        WebDriverWait(driver, 15).until(
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
            return {"status": "need_new_password", "message": "كلمة المرور خاطئة. يرجى تسجيل الدخول يدوياً من التطبيق لتغييرها."}

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

# --- معالجات التليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القائمة الرئيسية."""
    keyboard = [
        [InlineKeyboardButton("تسجيل دخول جديد", callback_data='new_login')],
        [InlineKeyboardButton("إنشاء حساب جديد", callback_data='create_account')],
        [InlineKeyboardButton("تسجيل دخول باستخدام جلسة", callback_data='session_login')],
        [InlineKeyboardButton("إدارة الجلسات", callback_data='manage_sessions')],
        [InlineKeyboardButton("عدد الحسابات", callback_data='count_accounts')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("أهلاً بك! اختر ما تريد فعله:", reply_markup=reply_markup)
    return ConversationHandler.END

async def new_login_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يطلب البريد الإلكتروني لتسجيل الدخول العادي."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="أرسل لي بريدك الإلكتروني وكلمة المرور:")
    return EMAIL

async def get_email(update: ContextTypes.DEFAULT_TYPE):
    """يستقبل البريد الإلكتروني."""
    context.user_data['email'] = update.message.text
    await update.message.reply_text("ممتاز. الآن أرسل لي كلمة المرور:")
    return PASSWORD

async def get_password(update: ContextTypes.DEFAULT_TYPE):
    """يستقبل كلمة المرور ويبدأ عملية تسجيل الدخول."""
    context.user_data['password'] = update.message.text
    email = context.user_data['email']
    password = context.user_data['password']
    
    login_queue.append({'email': email, 'password': password, 'update': update, 'context': context})
    await update.message.reply_text(f"تم استلام طلب تسجيل دخول. سيتم البدء في المعالجة...")
    await process_login_queue(update, context)
    return ConversationHandler.END

async def get_verification_code(update: Update, ContextTypes.DEFAULT_TYPE):
    """يستقبل رمز التحقق لإكمال تسجيل الدخول."""
    code = update.message.text
    if login_queue:
        account_data = login_queue[0]
        account_data['verification_code'] = code
        await update.message.reply_text("جاري التحقق من الرمز...")
        
        result = login_and_get_info(account_data['email'], account_data['password'], verification_code=code)
        
        if result['status'] == 'success':
            save_account(account_data['email'], account_data['password'])
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
            
    login_queue.clear()
    await update.message.reply_text("اكتملت جميع الطلبات.")
    return ConversationHandler.END

async def create_account_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يطلب بيانات إنشاء الحساب."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="لإنشاء حساب جديد، أرسل لي البيانات بالصيغة التالية (كل سطر في رسالة منفصلة):\n\n`email: بريدك_الإلكتروني`\n`username: اسم_المستخدم`\n`password: كلمة_المرور`\n`birthday_day: يوم_الميلاد (مثال: 15)`\n`birthday_month: شهر_الميلاد (مثال: January)`\n`birthday_year: سنة_الميلاد (مثال: 1990)")
    return EMAIL

async def get_account_details(update: Update, ContextTypes.DEFAULT_TYPE):
    """يستقبل ويتحقق من صحة البيانات المرسالة."""
    text = update.message.text
    try:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        details = {line.split(':', 1)[0].strip(): line.split(':', 1)[1].strip() for line in lines}
        
        email = details.get('email')
        username = details.get('username')
        password = details.get('password')
        birthday_day = details.get('birthday_day')
        birthday_month = details.get('birthday_month')
        birthday_year = details.get('birthday_year')

        if not all([email, username, password, birthday_day, birthday_month, birthday_year]):
            await update.message.reply_text("الرجاء التأكد من إرسال جميع البيانات المطلوبة بالصيغة الصحيحة.")
            return EMAIL

        creation_queue.append({
            'email': email, 'username': username, 'password': password,
            'birthday_day': birthday_day, 'birthday_month': birthday_month, 'birthday_year': birthday_year,
            'update': update, 'context': context
        })
        await update.message.reply_text("تم استلام البيانات. جاري إنشاء الحساب، قد يستغرق بعض الوقت...")
    except (ValueError, IndexError):
        await update.message.reply_text("خطأ في صيغة البيانات المرسلة. يرجى التحقق وإعادة الإرسال.")
        return EMAIL

async def session_login_prompt(update: Update, ContextTypes.DEFAULT_TYPE):
    """يطلب من المستخدم اختيار حساباً من الحسابات التي لديها جلسة."""
    query = update.callback_query
    await query.answer()
    
    sessions = read_sessions()
    if not sessions:
        await query.edit_message_text(text="لا توجد جلسات محفوظة حالياً.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(email, callback_data=f'session_login_{email}')] for email in sessions.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="اختر الحساب الذي تريد تسجيل الدخول إليه باستخدام الجلسة:", reply_markup=reply_markup)
    return ConversationHandler.END

async def process_session_login(update: Update, ContextTypes.DEFAULT_TYPE):
    """يقوم بتسجيل الدخول باستخدام الجلسة."""
    query = update.callback_query
    await query.answer()
    email = query.data.split('_', 1)[1]
    
    sessions = read_sessions()
    cookies = sessions.get(email)
    
    if not cookies:
        await query.edit_message_text(text="لم يتم العثور على جلسة لهذا الحساب.")
        return ConversationHandler.END

    await query.edit_message_text(text=f"جاري تسجيل الدخول إلى {email} باستخدام الجلسة المحفوظة...")
    
    result = login_with_session(email, cookies)
    
    if result['status'] == 'success':
        info = result['info']
        msg = (f"✅ **تم تسجيل الدخول بنجاح!**\n\n"
               f"👤 **اسم المستخدم:** {info['username']}\n"
               f"📝 **الوصف:** {info['bio']}\n"
               f"👥 **المتابعون:** {info['followers']}")
        await query.edit_message_text(text=msg, parse_mode='Markdown')
    else:
        await query.edit_message_text(text=f"❌ فشل تسجيل الدخول: {result['message']}")

async def manage_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الجلسات (عرضها وحذفها)."""
    query = update.callback_query
    await query.answer()
    
    sessions = read_sessions()
    if not sessions:
        await query.edit_message_text(text="لا توجد جلسات محفوظة حالياً.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(f"حذف {email}", callback_data=f'delete_session_{email}')] for email in sessions.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="اختر الجلسة التي تريد حذفها:", reply_markup=reply_markup)
    return ConversationHandler.END

async def delete_session(update: Update, ContextTypes.DEFAULT_TYPE):
    """حذف جلسة محددة."""
    query = update.callback_query
    await query.answer()
    email = query.data.split('_', 1)[1]
    
    if delete_session(email):
        await query.edit_message_text(text=f"تم حذف جلسة {email} بنجاح.")
    else:
        await query.edit_message_text(text="فشل حذف الجلسة.")
    return ConversationHandler.END

async def count_accounts(update: Update, ContextTypes.DEFAULT_TYPE):
    """يعرض عدد الحسابات والجلسات."""
    query = update.callback_query
    await query.answer()
    
    accounts = read_accounts()
    sessions = read_sessions()
    
    account_count = len(accounts)
    session_count = len(sessions)
    
    msg = (f"📊 **إحصائيات الحسابات والجلسات:**\n\n"
           f"   - عدد الحسابات المحفوظة: {account_count}\n"
           f"   - عدد الجلسات المحفوظة: {session_count}\n\n"
           f"**قائمة الحسابات المحفوظة:**\n")
    
    if accounts:
        for email in accounts.keys():
            msg += f"   - {email}\n"
    else:
        msg += "   (لا توجد)\n"

    msg += "\n**قائمة الجلسات المحفوظة:**\n"
    if sessions:
        for email in sessions.keys():
            msg += f"   - {email} (بجلسة)\n"
    else:
        msg += "   (لا توجد)\n"

    await query.edit_message_text(text=msg)


async def cancel(update: Update, ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية الحالية."""
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

# --- معالجات معالجة الطلبات ---
async def process_login_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلبات تسجيل الدخول العادي بشكل تسلسلي."""
    for i, account in enumerate(login_queue):
        email = account['email']
        password = account['password']
        
        await update.message.reply_text(f"جاري معالجة الحساب رقم {i+1}: {email}...")
        
        result = login_and_get_info(email, password)
        
        if result['status'] == 'success':
            save_account(email, password)
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
            
    login_queue.clear()
    await update.message.reply_text("اكتملت جميع طلبات تسجيل الدخول.")
    return ConversationHandler.END

async def process_creation_queue(update: Update, ContextTypes.DEFAULT_TYPE):
    """معالجة طلبات إنشاء الحسابات بشكل تسلسلي."""
    for i, account_data in enumerate(creation_queue):
        email = account_data['email']
        await update.message.reply_text(f"جاري معالجة إنشاء الحساب رقم {i+1}: {email}...")
        
        result = create_tiktok_account(
            account_data['email'], account_data['username'], account_data['password'],
            account_data['birthday_day'], account_data['birthday_month'], account_data['birthday_year']
        )
        
        if result['status'] == 'verification_needed':
            save_account_details(account_data['email'], account_data['password'], account_data['username'])
            await update.message.reply_text(result['message'])
        else:
            await update.message.reply_text(f"❌ فشل إنشاء الحساب: {result['message']}")
            
    creation_queue.clear()
    await update.message.reply_text("اكتملت جميع طلبات إنشاء الحسابات.")

# --- الدالة الرئيسية ---
def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set!")
        return
        
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(new_login_prompt, pattern='^new_login$'),
            CallbackQueryHandler(create_account_prompt, pattern='^create_account$'),
            CallbackQueryHandler(session_login_prompt, pattern='^session_login$'),
            CallbackQueryHandler(manage_sessions, pattern='^manage_sessions$'),
            CallbackQueryHandler(count_accounts, pattern='^count_accounts$'),
        ],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_account_details)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_account_details)],
            BIRTHMONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_account_details)],
            BIRTHYEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_account_details)],
            VERIFICATION_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_verification_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_chat=True,
        per_message=False,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(delete_session, pattern='^delete_session_'))
    
    application.run_polling()

if __name__ == "__main__":
    main()
