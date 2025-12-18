# استخدم صورة بايثون رسمية كأساس
FROM python:3.10-slim

# تعيين مجلد العمل داخل الحاوية
WORKDIR /app

# تثبيت المتصفح والمكتبات اللازمة له
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# إضافة مفتاح جوجل ومستودع كروم
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list

# تثبيت جوجل كروم
RUN apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملفات المشروع إلى الحاوية
COPY requirements.txt .
COPY bot.py .
COPY user.txt .

# تثبيت مكتبات بايثون
RUN pip install --no-cache-dir -r requirements.txt

# الأمر الذي سيتم تشغيله لبدء البوت
CMD ["python", "bot.py"]
