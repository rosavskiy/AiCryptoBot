# 🚀 Deployment Guide

## 📦 Файлы деплоймента

### Созданные файлы:

1. **Dockerfile** - образ для Docker контейнера
2. **docker-compose.yml** - оркестрация контейнеров
3. **.env.example** - пример переменных окружения
4. **setup_vps.sh** - автоматическая установка на VPS
5. **nginx/nginx.conf** - конфигурация Nginx
6. **deploy.sh** - быстрый деплой через rsync
7. **.dockerignore** - исключения для Docker

---

## 🐳 Вариант 1: Docker Deployment (Рекомендуется)

### Шаг 1: Подготовка

```bash
# На локальной машине
# Создайте .env файл
cp .env.example .env
nano .env  # Добавьте API ключи
```

### Шаг 2: Сборка и запуск локально (тест)

```bash
# Соберите образ
docker build -t aibot:latest .

# Запустите контейнер
docker-compose up -d

# Проверьте логи
docker-compose logs -f

# Откройте http://localhost:5000
```

### Шаг 3: Деплой на VPS

```bash
# На VPS установите Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установите Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Скопируйте проект на VPS
scp -r . user@vps_ip:/opt/aicryptobot/

# На VPS запустите
cd /opt/aicryptobot
docker-compose up -d

# Проверьте статус
docker-compose ps
docker-compose logs -f
```

---

## 🖥️ Вариант 2: Native VPS Deployment

### Шаг 1: Загрузка скрипта на VPS

```bash
# Скопируйте setup_vps.sh на VPS
scp setup_vps.sh user@vps_ip:~/

# Подключитесь к VPS
ssh user@vps_ip

# Сделайте скрипт исполняемым
chmod +x setup_vps.sh

# Запустите установку
./setup_vps.sh
```

### Шаг 2: Настройка после установки

```bash
# Перейдите в директорию
cd /opt/aicryptobot

# Отредактируйте .env
nano .env

# Отредактируйте config
nano config/settings.yaml

# Обучите модели (опционально)
source venv/bin/activate
python scripts/train_ensemble.py
```

### Шаг 3: Запуск сервисов

```bash
# Запустите dashboard
sudo systemctl start aibot-dashboard
sudo systemctl enable aibot-dashboard

# Проверьте статус
sudo systemctl status aibot-dashboard

# Посмотрите логи
tail -f logs/dashboard.log
```

---

## 🔒 Вариант 3: С Nginx и SSL

### Шаг 1: Настройте домен

```bash
# Укажите A-запись вашего домена на IP VPS
# Например: bot.yourdomain.com -> 123.45.67.89
```

### Шаг 2: Установите SSL сертификат

```bash
# После настройки Nginx из setup_vps.sh
sudo nano /etc/nginx/sites-available/aibot
# Замените YOUR_DOMAIN на ваш домен

# Получите SSL сертификат
sudo certbot --nginx -d bot.yourdomain.com

# Certbot автоматически настроит HTTPS
```

### Шаг 3: Раскомментируйте HTTPS блок

```bash
# Отредактируйте nginx.conf
sudo nano /etc/nginx/sites-available/aibot

# Раскомментируйте HTTPS server блок
# Замените YOUR_DOMAIN на ваш домен

# Перезагрузите Nginx
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🚀 Quick Deploy (для обновлений)

### После первой установки используйте deploy.sh:

```bash
# Отредактируйте deploy.sh
nano deploy.sh
# Укажите VPS_USER и VPS_HOST

# Сделайте исполняемым
chmod +x deploy.sh

# Запустите деплой
./deploy.sh

# Скрипт автоматически:
# 1. Синхронизирует файлы через rsync
# 2. Перезапустит сервисы
# 3. Покажет статус
```

---

## 📊 Мониторинг

### Проверка статуса:

```bash
# Systemd сервисы
sudo systemctl status aibot-dashboard

# Логи
tail -f /opt/aicryptobot/logs/dashboard.log
tail -f /opt/aicryptobot/logs/bot.log

# Docker (если используете)
docker-compose logs -f
docker stats

# Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Ресурсы:

```bash
# Использование CPU/RAM
htop

# Дисковое пространство
df -h

# Сетевые подключения
sudo netstat -tulpn | grep 5000
```

---

## 🔧 Troubleshooting

### Проблема: Бот не запускается

```bash
# Проверьте логи
sudo journalctl -u aibot-dashboard -n 50 -f

# Проверьте права доступа
ls -la /opt/aicryptobot
sudo chown -R $USER:$USER /opt/aicryptobot

# Проверьте виртуальное окружение
source venv/bin/activate
python --version
pip list
```

### Проблема: Dashboard недоступен

```bash
# Проверьте порт
sudo netstat -tulpn | grep 5000

# Проверьте firewall
sudo ufw status
sudo ufw allow 5000/tcp

# Проверьте Nginx
sudo nginx -t
sudo systemctl status nginx
```

### Проблема: SSL не работает

```bash
# Проверьте сертификаты
sudo certbot certificates

# Обновите сертификаты
sudo certbot renew

# Проверьте конфигурацию
sudo nginx -t
```

---

## 🔄 Обновление

### Обновление кода:

```bash
# Вариант 1: Через deploy.sh
./deploy.sh

# Вариант 2: Вручную
ssh user@vps_ip
cd /opt/aicryptobot
git pull  # Если используете git
sudo systemctl restart aibot-dashboard

# Вариант 3: Docker
docker-compose pull
docker-compose up -d --build
```

### Обновление зависимостей:

```bash
cd /opt/aicryptobot
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart aibot-dashboard
```

---

## 💾 Backup

### Автоматический бэкап:

```bash
# Создайте скрипт бэкапа
sudo nano /usr/local/bin/aibot-backup.sh

#!/bin/bash
BACKUP_DIR="/backup/aibot"
APP_DIR="/opt/aicryptobot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/aibot_$DATE.tar.gz \
    $APP_DIR/config \
    $APP_DIR/data \
    $APP_DIR/models \
    $APP_DIR/logs

# Удалить старые бэкапы (старше 7 дней)
find $BACKUP_DIR -name "aibot_*.tar.gz" -mtime +7 -delete

# Сделайте исполняемым
sudo chmod +x /usr/local/bin/aibot-backup.sh

# Добавьте в cron (каждый день в 3:00)
sudo crontab -e
0 3 * * * /usr/local/bin/aibot-backup.sh
```

---

## 📈 Performance Tuning

### Для production:

```yaml
# config/settings.yaml
logging:
  level: WARNING  # Меньше логов

# Используйте gunicorn вместо Flask dev server
pip install gunicorn gevent

# Запустите с gunicorn
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
    -w 1 -b 0.0.0.0:5000 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    src.web.app:app
```

---

## ✅ Checklist перед production:

- [ ] Изменены все пароли и API ключи
- [ ] Настроен SSL сертификат
- [ ] Настроен firewall (только 22, 80, 443)
- [ ] Включён автозапуск сервисов
- [ ] Настроен мониторинг
- [ ] Настроен бэкап
- [ ] Протестирован перезапуск сервера
- [ ] Обучены ML модели
- [ ] Проведён бэктест
- [ ] Запущен paper trading на 2+ недели

---

## 🌐 Recommended VPS Providers

### Для Asia-Pacific (лучший пинг к биржам):

1. **Contabo Singapore** - €6.99/month (4 vCPU, 8GB RAM)
   - Плюсы: Отличная цена, хорошая производительность
   - Минусы: Поддержка может быть медленной

2. **Hetzner Germany** - €9.5/month (4 vCPU, 8GB RAM)
   - Плюсы: Надёжность, быстрая поддержка
   - Минусы: Чуть дороже

3. **DigitalOcean Singapore** - $12/month (2 vCPU, 2GB RAM)
   - Плюсы: Простота использования, отличная документация
   - Минусы: Дороже аналогов

### Минимальные требования:

- **CPU**: 2+ vCPU
- **RAM**: 4GB (рекомендуется 8GB)
- **Storage**: 50GB SSD
- **Network**: 100+ Mbps
- **Location**: Singapore/Hong Kong (для Bybit)

---

## 📝 Quick Start Guide

### Самый быстрый способ (Docker):

```bash
# 1. Клонируйте на VPS
git clone https://github.com/yourusername/AiCryptoBot.git
cd AiCryptoBot

# 2. Создайте .env
cp .env.example .env
nano .env  # Добавьте API ключи

# 3. Запустите
docker-compose up -d

# 4. Откройте http://your_vps_ip:5000
```

### С автоустановкой (Native):

```bash
# 1. Загрузите скрипт
wget https://raw.githubusercontent.com/yourusername/AiCryptoBot/main/setup_vps.sh

# 2. Запустите
chmod +x setup_vps.sh
./setup_vps.sh

# 3. Следуйте инструкциям на экране
```

---

**Deployment package готов! 🎉**

Выберите подходящий вариант деплоя и следуйте инструкциям.
