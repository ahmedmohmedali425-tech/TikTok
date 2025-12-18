import os
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import time
import random
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import undetected_chromedriver as uc

# --- إعدادات ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
USE_PROXY = os.environ.get("USE_PROXY", "false").lower() == "true"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- قائمة من User-Agents حقيقية للتناوب عليها ---
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0',
]

# --- حالات المحادثة ---
(USERNAME, PASSWORD, VERIFICATION_CODE) = range(3)

# --- ملف لحفظ الحسابات ---
ACCOUNTS_FILE = 'user.txt'

# --- قائمة لتخزين بيانات الدخول المتعددة ---
login_queue = []

# --- دالة مساعدة لقراءة وحفظ الحسابات ---
def read_accounts():
    accounts = {}
    if not os.path.exists(ACCOUNTS_FILE):
        return accounts
    with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if 'user:' in line and 'passowed:' in line:
                try:
                    user_part, pass_part = line.strip().split('passowed:', 1)
                    username = user_part.split('user:', 1)[1].strip()
                    password = pass_part.strip()
                    if username and password:
                        accounts[username] = password
                except (ValueError, IndexError):
                    continue
    return accounts

def save_account(username, password):
    accounts = read_accounts()
    accounts[username] = password
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        for username, password in accounts.items():
            f.write(f"user: {username} passowed: {password}\n")

# --- دالة تسجيل الدخول ---
def login_and_get_info(email, password, verification_code=None, update=None, context=None):
    driver = None
    try:
        options = webdriver.ChromeOptions()
        
        # --- خيارات قوية لإخفاء البوت ---
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-default-apps")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option('prefs', {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False
        })

        # --- تغيير الـ User-Agent بشكل دوري ---
        random_user_agent = random.choice(USER_AGENTS)
        options.add_argument(f'user-agent={random_user_agent}')
        logger.info(f"Using User-Agent: {random_user_agent}")

        # --- إعدادات البروكسي (اختياري) ---
        if USE_PROXY:
            # هذه هي مجرد أمثلة، يجب استبدالها ببيانات بروكسي حقيقية
            # PROXY_IP = "192.168.1.1"
            # PROXY_PORT = "8080"
            # options.add_argument(f'--proxy-server=http://{PROXY_IP}:{PROXY_PORT}')
            logger.info("Proxy is enabled (Note: Configure proxy details in the code).")
        else:
            logger.info("Proxy is disabled.")

        # --- استخدام مدير الـ WebDriver الخاص بـ undetected-chromedriver ---
        driver = uc.Chrome(options=options, version_main=None, use_subprocess=False)

        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32", # تغيير النظام ليتناسب الـ User-Agent
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

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
        [InlineKeyboardButton("عدد الحسابات المسجلة", callback_data='count_accounts')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("أهلاً بك! اختر ما تريد فعله:", reply_markup=reply_markup)
    return ConversationHandler.END

async def new_login_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="أرسل لي معلومات تسجيل الدخول بصيغة:\n\n`user: اسم_المستخدم passowed: كلمة_المرور`\n\nيمكنك إرسال عدة أسطر لتسجيل دخول أكثر من حساب.")
    return USERNAME

async def get_login_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("الرجاء إرسال المعلومات بصيغة صحيحة.")
        return USERNAME

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if 'user:' in line and 'passowed:' in line:
            try:
                user_part, pass_part = line.split('passowed:', 1)
                username = user_part.split('user:', 1)[1].strip()
                password = pass_part.strip()
                if username and password:
                    login_queue.append({'username': username, 'password': password, 'update': update, 'context': context})
            except (ValueError, IndexError):
                await update.message.reply_text(f"خطأ في الصيغة للسطر: {line}. تم تجاهله.")
                continue
        else:
            await update.message.reply_text(f"خطأ في الصيغة للسطر: {line}. تم تجاهله.")
            continue
    
    if not login_queue:
        await update.message.reply_text("لم يتم العثور على بيانات صالحة. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

    await update.message.reply_text(f"تم استلام {len(login_queue)} طلب تسجيل دخول. سيتم البدء في المعالجة...")
    await process_login_queue(update, context)
    return ConversationHandler.END

async def process_login_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for i, account in enumerate(login_queue):
        username = account['username']
        password = account['password']
        
        await update.message.reply_text(f"جاري معالجة الحساب رقم {i+1}: {username}...")
        
        result = login_and_get_info(username, password)
        
        if result['status'] == 'success':
            save_account(username, password)
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

async def count_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accounts = read_accounts()
    count = len(accounts)
    if count == 0:
        await query.edit_message_text(text="لا توجد حسابات مسجلة حالياً.")
    else:
        await query.edit_message_text(text=f"يوجد {count} حساب مسجل في القائمة. البوت يعمل بشكل صحيح وهو نشط.")
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
        entry_points=[CallbackQueryHandler(new_login_prompt, pattern='^new_login$')],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_login_info)],
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
