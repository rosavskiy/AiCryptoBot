# ⚡ Quick VPS Setup - root@85.209.134.246

## Шаг 1: Загрузить скрипты на VPS

```powershell
# На Windows PowerShell:
scp d:\Projects\AiCryptoBot\setup_vps_root.sh root@85.209.134.246:~/
scp d:\Projects\AiCryptoBot\create_service.sh root@85.209.134.246:~/
```

---

## Шаг 2: Подключиться и установить

```bash
ssh root@85.209.134.246

# Запустить установку
chmod +x ~/setup_vps_root.sh
bash ~/setup_vps_root.sh
```

Скрипт установит:
- ✅ Python 3.11
- ✅ Git, nginx, certbot
- ✅ Firewall (UFW)
- ✅ Создаст `/opt/aicryptobot`

---

## Шаг 3: Клонировать репозиторий

### Вариант A: Публичный репозиторий

Сделайте репо публичным на GitHub:
```
Settings → General → Danger Zone → Change visibility → Make public
```

Затем:
```bash
cd /opt/aicryptobot
git clone https://github.com/rosavskiy/AiCryptoBot.git .
```

### Вариант B: Приватный репозиторий (через Personal Access Token)

1. **Создать токен на GitHub:**
   - Зайти: https://github.com/settings/tokens
   - Generate new token (classic)
   - Выбрать scopes: `repo` (полный доступ к приватным репо)
   - Скопировать токен (показывается один раз!)

2. **Клонировать с токеном:**
```bash
cd /opt/aicryptobot

# Формат: https://TOKEN@github.com/username/repo.git
git clone https://ваш_токен@github.com/rosavskiy/AiCryptoBot.git .

# Пример:
# git clone https://ghp_xxxxxxxxxxxxxxxxxxxx@github.com/rosavskiy/AiCryptoBot.git .
```

### Вариант C: Загрузить вручную

Если не хотите возиться с токенами:

```powershell
# На Windows создать архив:
Compress-Archive -Path d:\Projects\AiCryptoBot\* -DestinationPath d:\AiCryptoBot.zip -Force

# Загрузить на VPS:
scp d:\AiCryptoBot.zip root@85.209.134.246:/opt/aicryptobot/
```

```bash
# На VPS распаковать:
cd /opt/aicryptobot
unzip AiCryptoBot.zip
rm AiCryptoBot.zip

# Инициализировать git вручную:
git init
git remote add origin https://github.com/rosavskiy/AiCryptoBot.git
git add .
git commit -m "initial"
```

---

## Шаг 4: Настроить Python окружение

```bash
cd /opt/aicryptobot

# Создать виртуальное окружение
python3.11 -m venv venv

# Активировать
source venv/bin/activate

# Установить зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Шаг 5: Настроить .env

```bash
cp .env.example .env
nano .env
```

**Обязательно заполнить:**
```env
BYBIT_API_KEY=ваш_testnet_key
BYBIT_API_SECRET=ваш_testnet_secret
BYBIT_TESTNET=true

CRYPTOPANIC_API_KEY=ваш_cryptopanic_key

FLASK_SECRET_KEY=случайная_строка_32_символа
```

**Генерация Flask secret:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Сохранить: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## Шаг 6: Создать systemd сервис

```bash
chmod +x ~/create_service.sh
bash ~/create_service.sh
```

---

## Шаг 7: Запустить бота

```bash
systemctl start aibot-dashboard
systemctl enable aibot-dashboard
systemctl status aibot-dashboard
```

Должен показать: **active (running)**

---

## Шаг 8: Проверить работу

```bash
# Логи
tail -f /opt/aicryptobot/logs/dashboard.log

# Или
journalctl -u aibot-dashboard -f
```

**Открыть в браузере:** http://85.209.134.246:5000

---

## 🔄 Обновление в будущем

```bash
ssh root@85.209.134.246
cd /opt/aicryptobot
bash deploy_from_git.sh
```

Скрипт автоматически:
1. Остановит бота
2. Сделает backup .env
3. Подтянет изменения с GitHub
4. Восстановит .env
5. Обновит зависимости
6. Перезапустит бота

---

## 🛠️ Полезные команды

```bash
# Статус
systemctl status aibot-dashboard

# Остановить
systemctl stop aibot-dashboard

# Запустить
systemctl start aibot-dashboard

# Перезапустить
systemctl restart aibot-dashboard

# Логи (последние 50 строк)
journalctl -u aibot-dashboard -n 50

# Логи (в реальном времени)
tail -f /opt/aicryptobot/logs/dashboard.log

# Проверить порт
netstat -tulpn | grep 5000
```

---

## ❌ Troubleshooting

### Проблема: Python 3.11 не найден

```bash
python3.11 --version
# Если ошибка, установить:
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install python3.11 python3.11-venv -y
```

### Проблема: Сервис не запускается

```bash
# Посмотреть логи ошибок
journalctl -u aibot-dashboard -n 100

# Проверить .env
cat /opt/aicryptobot/.env

# Попробовать запустить вручную
cd /opt/aicryptobot
source venv/bin/activate
python run_dashboard.py
```

### Проблема: Dashboard недоступен

```bash
# Проверить firewall
ufw status
ufw allow 5000/tcp

# Проверить, что слушает на 0.0.0.0
netstat -tulpn | grep 5000
```

---

## ✅ Готово!

Dashboard доступен: **http://85.209.134.246:5000**

Для обновлений используйте:
```bash
bash deploy_from_git.sh
```
