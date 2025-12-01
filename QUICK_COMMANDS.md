# 🚀 Quick Commands - Шпаргалка

## На Windows (разработка)

### Ежедневный workflow:

```powershell
cd d:\Projects\AiCryptoBot

# Проверить статус
git status

# Добавить все изменения
git add .

# Коммит
git commit -m "feat: описание изменений"

# Отправить на GitHub
git push origin main
```

### Одной командой:

```powershell
git add . ; git commit -m "update" ; git push
```

---

## На VPS (деплой)

### Первый раз (настройка):

```bash
# 1. Подключиться
ssh root@85.209.134.246

# 2. Загрузить setup скрипт (на Windows)
scp d:\Projects\AiCryptoBot\setup_vps.sh root@85.209.134.246:~/

# 3. Запустить setup
chmod +x ~/setup_vps.sh
./setup_vps.sh

# 4. Клонировать репозиторий
cd /opt/aicryptobot
git clone https://github.com/rosavskiy/AiCryptoBot.git .

# 5. Настроить .env
cp .env.example .env
nano .env
# Добавить: BYBIT_API_KEY, BYBIT_API_SECRET, CRYPTOPANIC_API_KEY

# 6. Установить зависимости
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 7. Запустить
sudo systemctl start aibot-dashboard
sudo systemctl enable aibot-dashboard
```

### Каждый раз (обновление):

```bash
ssh root@85.209.134.246
cd /opt/aicryptobot
bash deploy_from_git.sh
```

**Одной командой:**
```bash
ssh root@85.209.134.246 "cd /opt/aicryptobot && bash deploy_from_git.sh"
```

---

## Мониторинг

```bash
# Статус
sudo systemctl status aibot-dashboard

# Логи (реальное время)
tail -f /opt/aicryptobot/logs/dashboard.log

# Логи (последние 50 строк)
sudo journalctl -u aibot-dashboard -n 50

# Перезапуск
sudo systemctl restart aibot-dashboard

# Остановка
sudo systemctl stop aibot-dashboard
```

---

## Откат изменений

```bash
# На VPS:
cd /opt/aicryptobot

# Откатиться на 1 коммит назад
git reset --hard HEAD~1

# ИЛИ на конкретный коммит
git log --oneline -10  # Посмотреть коммиты
git reset --hard <commit-hash>

# Перезапустить
sudo systemctl restart aibot-dashboard
```

---

## Проверка работы

```bash
# Dashboard доступен?
curl http://localhost:5000/api/status

# Порт открыт?
sudo netstat -tulpn | grep 5000

# Процесс запущен?
ps aux | grep python
```

---

## Быстрые алиасы (опционально)

Добавить в `~/.bashrc` на VPS:

```bash
alias deploy='cd /opt/aicryptobot && bash deploy_from_git.sh'
alias logs='tail -f /opt/aicryptobot/logs/dashboard.log'
alias status='sudo systemctl status aibot-dashboard'
alias restart='sudo systemctl restart aibot-dashboard'
```

Применить:
```bash
source ~/.bashrc
```

Теперь просто:
```bash
deploy   # Обновить из Git
logs     # Посмотреть логи
status   # Статус сервиса
restart  # Перезапустить
```

---

## Full Cycle Example

```powershell
# === На Windows ===
cd d:\Projects\AiCryptoBot

# Изменил файл src/ml/predictor.py
# Протестировал локально

# Коммит и пуш
git add .
git commit -m "fix: исправлена ошибка в ML predictor"
git push origin main
```

```bash
# === На VPS ===
ssh root@85.209.134.246
cd /opt/aicryptobot
bash deploy_from_git.sh

# Готово! Изменения применены
# Dashboard: http://85.209.134.246:5000
```

---

## Dashboard URLs

- **Local**: http://localhost:5000
- **VPS**: http://85.209.134.246:5000
- **VPS (nginx)**: http://85.209.134.246

---

## Emergency Stop

```bash
# Немедленно остановить бота
ssh root@85.209.134.246 "sudo systemctl stop aibot-dashboard"

# ИЛИ
ssh root@85.209.134.246 "pkill -f 'python.*dashboard'"
```

---

**Сохраните эту шпаргалку! 📋**
