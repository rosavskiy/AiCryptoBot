# 🚀 Deployment Steps для VPS 85.209.134.246

## Шаг 1: Подключение к VPS

```bash
ssh root@85.209.134.246
```

---

## Шаг 2: Загрузка setup скрипта (на локальной машине Windows)

```powershell
# В PowerShell на Windows:
scp setup_vps.sh root@85.209.134.246:~/
```

**ИЛИ создайте файл вручную на VPS:**

```bash
# На VPS:
nano ~/setup_vps.sh
# Вставить содержимое из setup_vps.sh
chmod +x ~/setup_vps.sh
```

---

## Шаг 3: Запуск автоматической установки

```bash
# На VPS:
./setup_vps.sh
```

Скрипт автоматически:
- ✅ Обновит систему
- ✅ Установит Python 3.11, pip, git, nginx
- ✅ Настроит firewall (SSH, HTTP, HTTPS)
- ✅ Создаст директорию `/opt/aicryptobot`
- ✅ Создаст systemd сервисы
- ✅ Настроит nginx

---

## Шаг 4: Загрузка проекта

### ✅ Рекомендуется: Через Git (автоматические обновления)

```bash
cd /opt/aicryptobot

# Клонировать репозиторий
git clone https://github.com/rosavskiy/AiCryptoBot.git .

# Настроить git (опционально)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

**Преимущества Git:**
- ✅ Автоматические обновления одной командой
- ✅ История изменений
- ✅ Легкий откат при проблемах
- ✅ Используйте `deploy_from_git.sh` для обновлений

**Для обновлений в будущем:**
```bash
cd /opt/aicryptobot
bash deploy_from_git.sh
# Автоматически: pull + backup .env + restart
```

### Альтернатива: Загрузка zip (не рекомендуется)

```powershell
# На Windows PowerShell:
Compress-Archive -Path d:\Projects\AiCryptoBot\* -DestinationPath d:\AiCryptoBot.zip -Force
scp d:\AiCryptoBot.zip root@85.209.134.246:/opt/aicryptobot/
```

```bash
# На VPS:
cd /opt/aicryptobot
apt install unzip -y
unzip AiCryptoBot.zip
rm AiCryptoBot.zip
```

---

## Шаг 5: Настройка проекта на VPS

```bash
cd /opt/aicryptobot

# Создать виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Создать директории
mkdir -p logs data models

# Создать .env файл
cp .env.example .env
nano .env
```

### Заполните .env файл:

```env
# ОБЯЗАТЕЛЬНО:
BYBIT_API_KEY=ваш_testnet_key
BYBIT_API_SECRET=ваш_testnet_secret
BYBIT_TESTNET=true

CRYPTOPANIC_API_KEY=ваш_cryptopanic_key

# Flask secret (сгенерировать случайный)
FLASK_SECRET_KEY=случайная-строка-минимум-32-символа

# Остальное оставить по умолчанию
```

**Генерация Flask Secret Key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Шаг 6: Проверка работы

```bash
# Тест запуска dashboard
cd /opt/aicryptobot
source venv/bin/activate
python run_dashboard.py
```

Должно показать:
```
 * Running on http://0.0.0.0:5000
```

Откройте в браузере: **http://85.209.134.246:5000**

Если работает - нажмите `Ctrl+C` и переходите к следующему шагу.

---

## Шаг 7: Запуск как systemd сервис

```bash
# Запустить сервис
sudo systemctl start aibot-dashboard

# Проверить статус
sudo systemctl status aibot-dashboard

# Включить автозапуск
sudo systemctl enable aibot-dashboard

# Посмотреть логи
tail -f /opt/aicryptobot/logs/dashboard.log
```

---

## Шаг 8: Настройка Nginx (опционально)

```bash
# Отредактировать конфигурацию
sudo nano /etc/nginx/sites-available/aibot

# Заменить YOUR_DOMAIN_HERE на:
# - IP адрес: 85.209.134.246
# - Или домен (если есть)

# Пример для IP:
server_name 85.209.134.246;

# Проверить конфигурацию
sudo nginx -t

# Перезагрузить nginx
sudo systemctl reload nginx
```

Теперь dashboard доступен через **http://85.209.134.246** (порт 80)

---

## Шаг 9: SSL сертификат (если есть домен)

```bash
# Если у вас есть домен (например: bot.yourdomain.com)

# 1. Настроить DNS:
#    A-запись: bot.yourdomain.com -> 85.209.134.246

# 2. Получить SSL сертификат:
sudo certbot --nginx -d bot.yourdomain.com

# Certbot автоматически настроит HTTPS
```

---

## Шаг 10: Мониторинг

### Проверка статуса:

```bash
# Статус сервиса
sudo systemctl status aibot-dashboard

# Логи (последние 50 строк)
sudo journalctl -u aibot-dashboard -n 50

# Логи в реальном времени
sudo journalctl -u aibot-dashboard -f

# Логи приложения
tail -f /opt/aicryptobot/logs/dashboard.log

# Использование ресурсов
htop
```

### Полезные команды:

```bash
# Перезапустить сервис
sudo systemctl restart aibot-dashboard

# Остановить сервис
sudo systemctl stop aibot-dashboard

# Отключить автозапуск
sudo systemctl disable aibot-dashboard

# Посмотреть открытые порты
sudo netstat -tulpn | grep LISTEN
```

---

## Шаг 11: Firewall

```bash
# Проверить статус
sudo ufw status

# Должны быть открыты:
# 22/tcp (SSH)
# 80/tcp (HTTP)
# 443/tcp (HTTPS)
# 5000/tcp (временно, для прямого доступа)

# Если нужно открыть порт 5000:
sudo ufw allow 5000/tcp

# После настройки nginx можно закрыть 5000:
sudo ufw delete allow 5000/tcp
```

---

## 🎯 Финальный чеклист

- [ ] VPS доступен через SSH
- [ ] setup_vps.sh выполнен успешно
- [ ] Проект загружен в /opt/aicryptobot
- [ ] Зависимости установлены (requirements.txt)
- [ ] .env файл настроен (API ключи)
- [ ] Dashboard запускается вручную
- [ ] Systemd сервис работает
- [ ] Dashboard доступен через http://85.209.134.246:5000
- [ ] Nginx настроен (опционально)
- [ ] SSL сертификат установлен (если есть домен)
- [ ] Логи пишутся корректно
- [ ] Автозапуск включен

---

## 🚨 Troubleshooting

### Проблема: setup_vps.sh не запускается

```bash
# Проверить формат файла (должен быть Unix)
file setup_vps.sh

# Если показывает CRLF, конвертировать:
sudo apt install dos2unix -y
dos2unix setup_vps.sh
chmod +x setup_vps.sh
```

### Проблема: Python 3.11 не найден

```bash
# Установить вручную
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

### Проблема: pip install не работает

```bash
# Обновить pip
python3.11 -m pip install --upgrade pip

# Установить wheel
pip install wheel setuptools

# Установить по одному пакету
pip install flask
pip install flask-socketio
# и т.д.
```

### Проблема: Dashboard недоступен извне

```bash
# Проверить, что слушает на 0.0.0.0, а не 127.0.0.1
sudo netstat -tulpn | grep 5000

# Проверить firewall
sudo ufw status
sudo ufw allow 5000/tcp

# Проверить, запущен ли сервис
sudo systemctl status aibot-dashboard
```

### Проблема: Ошибки в логах

```bash
# Посмотреть полные логи
sudo journalctl -u aibot-dashboard -n 100 --no-pager

# Проверить права доступа
ls -la /opt/aicryptobot
sudo chown -R $USER:$USER /opt/aicryptobot

# Проверить .env
cat /opt/aicryptobot/.env
```

---

## 📞 Следующие шаги после деплоя

1. **Тестирование на testnet** (минимум 2 недели)
2. **Мониторинг производительности**
3. **Настройка бэкапов** (см. DEPLOYMENT.md)
4. **Оптимизация параметров** в config/settings.yaml
5. **Переход на mainnet** (когда будете готовы)

---

**VPS готов к работе! 🎉**

Dashboard: http://85.209.134.246:5000
