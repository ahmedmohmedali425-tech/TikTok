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
# قراءة التوكن من متغير بيئي لأمان أكبر
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# تفعيل السجلات لرؤية الأخطاء
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- حالات المحادثة (Conversation States) ---
(USERNAME, PASSWORD, VERIFICATION_CODE) = range(3)

# --- ملف لحفظ الحسابات ---
ACCOUNTS_FILE = 'user.txt'

# --- دالة مساعدة لقراءة الحسابات ---
def read_accounts():
    accounts = {}
    if not os.path.exists(ACCOUNTS_FILE):
        return accounts
    with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if ':' in line:
                email, password = line.strip().split(':', 1)
                accounts[email] = password
    return accounts

# --- دالة مساعدة لحفظ حساب ---
def save_account(email, password):
    accounts = read_accounts()
    accounts[email] = password
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        for email, password in accounts.items():
            f.write(f"{email}:{password}\n")

# --- دالة تسجيل الدخول (تعمل في خيط منفصل) ---
def login_and_get_info(email, password, verification_code=None):
    driver = None # التأكد من تعريف driver قبل try
    try:
        # إعدادات المتصفح للعمل على الخوادم (headless)
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new") # استخدام الوضع الجديد والأكثر استقراراً
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # تعديل ليتوافق مع بيئة GitHub بشكل أفضل
        driver = uc.Chrome(version_main=None, options=options, use_subprocess=False)

        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Linux", # تم تصحيح الخطأ الإملائي
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        driver.get("https://www.tiktok.com/login/phone-or-email/email")
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Email or username']"))
        ).send_keys(email)

        driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Password']").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(4) # انتظار أطول قليلاً للتحقق من أي إعادة توجيه

        # التحقق من وجود صفحة رمز التحقق
        if "verification" in driver.current_url:
            if not verification_code:
                return {"status": "need_verification_code", "message": "تم إرسال رمز تحقق إلى بريدك الإلكتروني. الرجاء إدخاله."}
            
            code_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Verification code']"))
            )
            code_field.send_keys(verification_code)
            driver.find_element(By.CSS_SELECTOR, "button[data-e2e='verify-button']").click()
            time.sleep(4)

        # التحقق من وجود صفحة تغيير كلمة المرور
        if "reset-password" in driver.current_url:
            return {"status": "need_new_password", "message": "كلمة المرور خاطئة أو منتهية الصلاحية. يرجى تسجيل الدخول يدوياً من التطبيق لتغييرها."}

        # إذا تم تسجيل الدخول بنجاح
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-e2e='top-nav-avatar'] img"))
        ).click()
        
        profile_info = {}
        try:
            profile_info['username'] = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1[data-e2e='user-title']"))
            ).text
            profile_info['bio'] = driver.find_element(By.CSS_SELECTOR, "h2[data-e2e='user-bio']").text
        except: profile_info['bio'] = "لا يوجد وصف"
        
        try:
            # استخدام محدد أكثر قوة لعدد المتابعين
            followers_element = driver.find_element(By.CSS_SELECTOR, "a[href*='/followers'] strong")
            profile_info['followers'] = followers_element.text
        except:
            profile_info['followers'] = "غير متوفر"

        driver.quit()
        return {"status": "success", "info": profile_info}

    except Exception as e:
        if driver:
            driver.quit()
        logger.error(f"Error during login for {email}: {e}")
        return {"status": "failed", "message": f"فشل تسجيل الدخول: {str(e)}"}

# --- معالجات الأوامر والرسائل ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("تسجيل دخول جديد", callback_data='new_login')],
        [InlineKeyboardButton("تسجيل الدخول بحساب محفوظ", callback_data='saved_login')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("أهلاً بك! اختر ما تريد فعله:", reply_markup=reply_markup)
    return ConversationHandler.END

async def new_login_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="أرسل لي بريدك الإلكتروني أو اسم المستخدم:")
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text("ممتاز. الآن أرسل لي كلمة المرور:")
    return PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['password'] = update.message.text
    username = context.user_data['username']
    password = context.user_data['password']
    
    await update.message.reply_text("جاري محاولة تسجيل الدخول... قد يستغرق هذا بعض الوقت.")
    
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
        await update.message.reply_text(result['message'])
        return VERIFICATION_CODE
    else:
        await update.message.reply_text(f"❌ {result['message']}")
        
    return ConversationHandler.END

async def get_verification_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['verification_code'] = update.message.text
    username = context.user_data['username']
    password = context.user_data['password']
    code = context.user_data['verification_code']
    
    await update.message.reply_text("جاري التحقق من الرمز...")
    result = login_and_get_info(username, password, verification_code=code)
    
    if result['status'] == 'success':
        save_account(username, password)
        info = result['info']
        msg = (f"✅ **تم تسجيل الدخول بنجاح!**\n\n"
               f"👤 **اسم المستخدم:** {info['username']}\n"
               f"📝 **الوصف:** {info['bio']}\n"
               f"👥 **المتابعون:** {info['followers']}")
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ فشل التحقق: {result['message']}")
        
    return ConversationHandler.END

async def saved_login_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accounts = read_accounts()
    if not accounts:
        await query.edit_message_text(text="لا توجد حسابات محفوظة حالياً.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(email, callback_data=f'login_{email}')] for email in accounts.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="اختر الحساب الذي تريد تسجيل الدخول به:", reply_markup=reply_markup)
    return ConversationHandler.END

async def handle_saved_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    email = query.data.split('_', 1)[1]
    accounts = read_accounts()
    password = accounts.get(email)
    
    if not password:
        await query.edit_message_text(text="حدث خطأ، لم يتم العثور على كلمة المرور لهذا الحساب.")
        return

    await query.edit_message_text(text=f"جاري تسجيل الدخول للحساب: {email}...")
    result = login_and_get_info(email, password)
    
    if result['status'] == 'success':
        info = result['info']
        msg = (f"✅ **تم تسجيل الدخول بنجاح!**\n\n"
               f"👤 **اسم المستخدم:** {info['username']}\n"
               f"📝 **الوصف:** {info['bio']}\n"
               f"👥 **المتابعون:** {info['followers']}")
        await query.edit_message_text(text=msg, parse_mode='Markdown')
    else:
        await query.edit_message_text(text=f"❌ فشل تسجيل الدخول: {result['message']}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set!")
        return
        
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            VERIFICATION_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_verification_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(new_login_prompt, pattern='^new_login$'))
    application.add_handler(CallbackQueryHandler(saved_login_prompt, pattern='^saved_login$'))
    application.add_handler(CallbackQueryHandler(handle_saved_login, pattern='^login_'))
    
    application.run_polling()

if __name__ == "__main__":
    main()
