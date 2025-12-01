# ✅ Готово к деплою на VPS

## 🎯 Что реализовано

### 1. ✅ Автоматический News Scheduler
- **Статус**: Работает локально с TextBlob
- **Интервал**: 15 минут (настраивается)
- **API**: CryptoPanic (протестировано, работает)
- **Fallback**: TextBlob вместо FinBERT (torch не требуется)
- **Логи**: Подробное логирование всех операций

### 2. ✅ Поддержка SPOT/FUTURES
- **Статус**: Реализовано и протестировано
- **Типы**: SPOT, LINEAR (USDT futures), INVERSE (coin futures)
- **Leverage**: Настраивается через .env
- **Dashboard**: Отображает тип рынка и плечо

### 3. ✅ Dashboard UI
- **3 вкладки**: Overview, News, Logs
- **Real-time**: WebSocket обновления
- **Фильтры**: Логи по категориям
- **Market Type**: Отображение SPOT/FUTURES

## 📦 Установленные зависимости

### Локально (Windows):
```
✅ textblob - для sentiment analysis
✅ ccxt - для работы с биржами
✅ scikit-learn - для ML моделей
✅ requests - для API запросов
✅ flask-socketio - для real-time updates
✅ gevent - для WebSocket
✅ python-dotenv - для .env
✅ pandas, numpy - для данных
```

### Опциональные (НЕ установлены):
```
⏹️ torch (~2GB) - для FinBERT
⏹️ transformers - для FinBERT
⏹️ sentencepiece - для FinBERT
```

**Примечание**: Бот работает БЕЗ torch, используя TextBlob fallback для sentiment анализа.

## 🚀 Деплой на VPS

### Шаг 1: Подключиться к VPS

```bash
ssh root@85.209.134.246
cd /opt/aicryptobot
```

### Шаг 2: Задеплоить обновления

```bash
bash deploy_from_git.sh
```

Скрипт автоматически:
1. ✅ Остановит службу
2. ✅ Сделает backup .env
3. ✅ Подтянет изменения из GitHub
4. ✅ Восстановит .env
5. ✅ Установит зависимости: `pip install -r requirements.txt`
6. ✅ Перезапустит службу

### Шаг 3: Проверить логи

```bash
journalctl -u aibot-dashboard -f
```

**Ожидаемые логи:**
```
[NEWS] 📝 Using TextBlob for sentiment analysis (torch not installed)
[NEWS] Scheduler initialized: 15min interval, symbols: ['BTC', 'ETH']
[NEWS] ✅ Scheduler started
[NEWS] 📰 Fetching news...
[NEWS] Fetched X news items for BTC
[MARKET] Type: SPOT
```

### Шаг 4: Открыть Dashboard

```
URL: http://85.209.134.246
Login: (Basic Auth credentials)
```

**Проверить:**
- ✅ Вкладка "Обзор" - показывает Market: SPOT
- ✅ Вкладка "Новости" - через 15 мин появятся новости
- ✅ Вкладка "Логи" - видны логи категорий

## 📝 Текущие настройки (.env)

```env
# News
NEWS_UPDATE_INTERVAL_MINUTES=15  # Каждые 15 минут
CRYPTOPANIC_API_KEY=c47b5bf2f88baf217f90b9e0ea7c6deb68983632

# Market Type
MARKET_TYPE=spot  # spot, futures, linear, inverse
LEVERAGE=1        # Плечо (для futures)
```

## ⚙️ Конфигурация

### Изменить интервал новостей:

```bash
# На VPS
nano /opt/aicryptobot/.env

# Изменить:
NEWS_UPDATE_INTERVAL_MINUTES=30  # 30 минут вместо 15

# Перезапустить:
systemctl restart aibot-dashboard
```

### Переключить на FUTURES:

```bash
nano /opt/aicryptobot/.env

# Изменить:
MARKET_TYPE=futures  # Активировать фьючерсы
LEVERAGE=3           # Плечо 3x

systemctl restart aibot-dashboard
```

## 🔍 Тестирование

### 1. Проверить News API:

```bash
ssh root@85.209.134.246
cd /opt/aicryptobot

# Запустить Python в venv
source venv/bin/activate
python -c "
import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('CRYPTOPANIC_API_KEY')
response = requests.get('https://cryptopanic.com/api/v1/posts/', params={
    'auth_token': api_key,
    'currencies': 'BTC',
    'kind': 'news'
})
print(f'Status: {response.status_code}')
print(f'News count: {len(response.json().get(\"results\", []))}')
"
```

**Ожидаемо:**
```
Status: 200
News count: 10-20
```

### 2. Проверить Market Type:

```bash
curl -s http://127.0.0.1:5000/api/config | python -m json.tool | grep market_type
```

**Ожидаемо:**
```json
"market_type": "spot",
"is_futures": false
```

### 3. Проверить News Endpoint:

```bash
curl -s http://127.0.0.1:5000/api/news | python -m json.tool
```

**Ожидаемо через 15 минут:**
```json
{
  "news": [
    {
      "symbol": "BTC",
      "title": "Bitcoin reaches...",
      "source": "CryptoPanic",
      "sentiment": 0.85,
      "category": "positive"
    }
  ],
  "sentiment_history": [...]
}
```

## 📊 Мониторинг

### Статус службы:

```bash
systemctl status aibot-dashboard
```

### Логи в реальном времени:

```bash
journalctl -u aibot-dashboard -f
```

### Фильтр по категории:

```bash
# Только новости
journalctl -u aibot-dashboard | grep NEWS

# Только ML
journalctl -u aibot-dashboard | grep ML

# Ошибки
journalctl -u aibot-dashboard | grep ERROR
```

### Проверить scheduler работает:

```bash
journalctl -u aibot-dashboard -f | grep "\[NEWS\]"
```

**Ожидаемо каждые 15 минут:**
```
[NEWS] 📰 Fetching news...
[NEWS] Fetched X items
[NEWS] 📊 Analysis complete
```

## ⚠️ Важные замечания

### 1. TextBlob vs FinBERT

**Текущее состояние**: Используется TextBlob
**Качество**: Базовое (polarity -1 to 1)
**Преимущества**: 
- Легковесный
- Быстрый
- Не требует GPU
- Работает из коробки

**FinBERT (опционально)**:
- Требует: `pip install torch transformers sentencepiece`
- Размер: ~2GB
- Качество: Специально для финансовых новостей
- Медленнее: ~0.5сек на новость

### 2. CryptoPanic API Лимиты

**Бесплатный тариф**: 100 запросов/день

**При интервале 15 минут**:
- 4 запроса/час × 24 часа = 96 запросов/день ✅
- Остается 4 запроса для ручных обновлений

**При интервале 10 минут**:
- 6 запросов/час × 24 часа = 144 запросов/день ❌
- Превышение лимита!

**Рекомендация**: 15-30 минут

### 3. FUTURES Trading

⚠️ **ВНИМАНИЕ**: Фьючерсная торговля с плечом ОЧЕНЬ РИСКОВАННА!

**Перед активацией**:
1. Протестируйте на testnet минимум 2 недели
2. Начинайте с плеча 1-3x
3. НЕ используйте > 5x без опыта
4. Следите за margin level
5. Используйте stop-loss

**Активация только после:**
- ✅ Успешной SPOT торговли 1+ месяц
- ✅ Положительного P&L
- ✅ Понимания ликвидации
- ✅ Тестирования на testnet

## 🎯 Следующие шаги

### 1. Деплой (сейчас):
```bash
ssh root@85.209.134.246
cd /opt/aicryptobot
bash deploy_from_git.sh
```

### 2. Мониторинг (15-30 минут):
- Открыть dashboard
- Переключиться на вкладку "Новости"
- Дождаться первого обновления
- Проверить sentiment отображается

### 3. Оптимизация (опционально):
- Установить FinBERT на VPS (если нужно качество)
- Настроить интервал обновлений
- Добавить больше символов (ETH, BNB...)

### 4. Тестирование FUTURES (через месяц+):
- Переключить на testnet
- Активировать MARKET_TYPE=futures
- Тестировать с малым leverage
- Только после успеха - на production

## 📞 Troubleshooting

### Проблема: News не появляются

**Решение**:
```bash
# 1. Проверить API key
grep CRYPTOPANIC_API_KEY /opt/aicryptobot/.env

# 2. Проверить логи
journalctl -u aibot-dashboard | grep NEWS

# 3. Протестировать API вручную
curl "https://cryptopanic.com/api/v1/posts/?auth_token=YOUR_KEY&currencies=BTC"
```

### Проблема: Market Type не отображается

**Решение**:
```bash
# 1. Проверить .env
grep MARKET_TYPE /opt/aicryptobot/.env

# 2. Проверить API
curl http://127.0.0.1:5000/api/config | grep market_type

# 3. Перезапустить
systemctl restart aibot-dashboard
```

### Проблема: Scheduler не запускается

**Решение**:
```bash
# 1. Проверить зависимости
source /opt/aicryptobot/venv/bin/activate
python -c "import textblob; print('OK')"

# 2. Скачать TextBlob данные
python -m textblob.download_corpora

# 3. Перезапустить
systemctl restart aibot-dashboard
```

### Проблема: FinBERT ошибка

**Это нормально!** Бот работает без FinBERT.

Если хотите FinBERT:
```bash
source /opt/aicryptobot/venv/bin/activate
pip install torch transformers sentencepiece
systemctl restart aibot-dashboard
```

## ✅ Checklist перед деплоем

- [x] Код закоммичен в GitHub
- [x] requirements.txt обновлен
- [x] .env содержит NEWS_UPDATE_INTERVAL_MINUTES
- [x] .env содержит MARKET_TYPE
- [x] CryptoPanic API протестирован
- [x] News scheduler работает локально
- [x] Market type отображается в UI
- [x] TextBlob fallback работает
- [x] Документация создана

## 🚀 Готово!

Всё готово к деплою. Выполните команду на VPS:

```bash
ssh root@85.209.134.246 "cd /opt/aicryptobot && bash deploy_from_git.sh"
```

Через 15 минут после запуска вы увидите первые новости в dashboard! 🎉
