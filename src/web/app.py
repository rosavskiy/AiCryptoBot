"""
Flask Web Dashboard
===================
Real-time web interface for monitoring trading bot
"""

import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.config_loader import get_config

# Setup logging to file
log_dir = Path(__file__).parent.parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'dashboard.log'

# Configure file handler for persistent logs
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)
# Use local time in logs
import time
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
# Make sure we use local time, not UTC
logging.Formatter.converter = time.localtime

logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent.parent.parent / 'templates'),
    static_folder=str(Path(__file__).parent.parent.parent / 'static')
)
app.config['SECRET_KEY'] = 'ai-crypto-bot-secret-key-2025'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global bot state
bot_state = {
    'status': 'stopped',  # stopped, running, paused
    'start_time': None,
    'balance': 10000.0,
    'initial_balance': 10000.0,
    'total_pnl': 0.0,
    'total_pnl_pct': 0.0,
    'open_positions': [],
    'closed_trades': [],
    'total_trades': 0,
    'winning_trades': 0,
    'losing_trades': 0,
    'win_rate': 0.0,
    'current_drawdown': 0.0,
    'max_drawdown': 0.0,
    'sharpe_ratio': 0.0,
    'last_signal': None,
    'ml_predictions': [],
    'logs': [],
    'news': [],  # News feed
    'sentiment_history': []  # Sentiment over time
}

# Bot controller reference
bot_controller = None

# News scheduler
news_scheduler = None


def set_bot_controller(controller):
    """Set reference to bot controller"""
    global bot_controller
    bot_controller = controller


@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/status')
def api_status():
    """Get bot status"""
    return jsonify(bot_state)


@app.route('/api/config')
def api_config():
    """Get bot configuration"""
    config = get_config()
    
    # Get market type info
    try:
        from src.trading.market_type import get_market_manager
        market_manager = get_market_manager()
        market_info = market_manager.get_market_info()
    except Exception as e:
        logger.error(f'Error getting market info: {e}')
        market_info = {'type': 'spot', 'is_spot': True, 'is_futures': False}
    
    return jsonify({
        'symbols': config.get('symbols', default=['BTC/USDT']),
        'interval': config.get('interval', default='15m'),
        'risk_per_trade': config.get('risk', 'risk_per_trade', default=0.01),
        'max_positions': config.get('risk', 'max_open_positions', default=3),
        'ml_threshold': config.get('trading', 'entry', 'ml_probability_min', default=0.6),
        'sentiment_enabled': config.get('sentiment', 'enabled', default=True),
        'telegram_enabled': config.get('telegram', 'enabled', default=False),
        'market_type': market_info['type'],
        'is_futures': market_info['is_futures'],
        'leverage': market_info.get('leverage', {})
    })


@app.route('/api/trades')
def api_trades():
    """Get trade history"""
    return jsonify({
        'open': bot_state['open_positions'],
        'closed': bot_state['closed_trades'][-50:]  # Last 50 trades
    })


@app.route('/api/performance')
def api_performance():
    """Get performance metrics"""
    return jsonify({
        'total_trades': bot_state['total_trades'],
        'winning_trades': bot_state['winning_trades'],
        'losing_trades': bot_state['losing_trades'],
        'win_rate': bot_state['win_rate'],
        'total_pnl': bot_state['total_pnl'],
        'total_pnl_pct': bot_state['total_pnl_pct'],
        'sharpe_ratio': bot_state['sharpe_ratio'],
        'max_drawdown': bot_state['max_drawdown'],
        'current_drawdown': bot_state['current_drawdown']
    })


@app.route('/api/control/start', methods=['POST'])
def api_start():
    """Start the bot"""
    # Start news scheduler if not running
    global news_scheduler
    if news_scheduler is None or not news_scheduler.is_running():
        start_news_scheduler()
    
    if bot_controller:
        try:
            bot_controller.start()
            bot_state['status'] = 'running'
            bot_state['start_time'] = datetime.now().isoformat()
            broadcast_status_update()
            return jsonify({'success': True, 'message': 'Bot started'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Demo mode - simulate bot start
    bot_state['status'] = 'running'
    bot_state['start_time'] = datetime.now().isoformat()
    broadcast_status_update()
    broadcast_log({'level': 'INFO', 'message': '🚀 Bot started in DEMO mode'})
    return jsonify({'success': True, 'message': 'Bot started (demo mode)'})


@app.route('/api/control/stop', methods=['POST'])
def api_stop():
    """Stop the bot"""
    if bot_controller:
        try:
            bot_controller.stop()
            bot_state['status'] = 'stopped'
            broadcast_status_update()
            return jsonify({'success': True, 'message': 'Bot stopped'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Demo mode - simulate bot stop
    bot_state['status'] = 'stopped'
    broadcast_status_update()
    broadcast_log({'level': 'INFO', 'message': '⏹️ Bot stopped'})
    return jsonify({'success': True, 'message': 'Bot stopped (demo mode)'})


@app.route('/api/control/pause', methods=['POST'])
def api_pause():
    """Pause the bot"""
    if bot_controller:
        try:
            bot_controller.pause()
            bot_state['status'] = 'paused'
            broadcast_status_update()
            return jsonify({'success': True, 'message': 'Bot paused'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Demo mode - simulate bot pause
    bot_state['status'] = 'paused'
    broadcast_status_update()
    broadcast_log({'level': 'WARNING', 'message': '⏸️ Bot paused'})
    return jsonify({'success': True, 'message': 'Bot paused (demo mode)'})


@app.route('/api/logs')
def api_logs():
    """Get recent logs from memory"""
    return jsonify({
        'logs': bot_state['logs'][-100:]  # Last 100 log entries
    })


@app.route('/api/logs/history')
def api_logs_history():
    """Get historical logs from file"""
    try:
        log_file = Path(__file__).parent.parent.parent / 'logs' / 'dashboard.log'
        
        if not log_file.exists():
            return jsonify({
                'logs': [],
                'message': 'No log file found yet'
            })
        
        # Read last 500 lines from log file
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-500:] if len(lines) > 500 else lines
        
        # Parse logs into structured format
        parsed_logs = []
        for line in last_lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to parse timestamp and message
            try:
                # Format: 2025-12-01 16:36:44,120 [INFO] message
                parts = line.split('[', 1)
                if len(parts) >= 2:
                    timestamp_part = parts[0].strip()
                    rest = parts[1]
                    level_end = rest.find(']')
                    if level_end > 0:
                        level = rest[:level_end].strip()
                        message = rest[level_end+1:].strip()
                        
                        # Categorize
                        category = 'general'
                        if '[NEWS]' in message or 'NEWS' in message:
                            category = 'news'
                        elif '[ML]' in message or 'prediction' in message.lower():
                            category = 'ml'
                        elif '[TRADE]' in message or 'сделк' in message.lower():
                            category = 'trade'
                        elif 'ERROR' in level or 'error' in message.lower():
                            category = 'error'
                        
                        parsed_logs.append({
                            'timestamp': timestamp_part,
                            'level': level,
                            'category': category,
                            'message': message
                        })
                    else:
                        # Fallback if can't parse properly
                        parsed_logs.append({
                            'timestamp': timestamp_part,
                            'level': 'INFO',
                            'category': 'general',
                            'message': line
                        })
            except:
                # If parsing fails, add raw line
                parsed_logs.append({
                    'timestamp': '',
                    'level': 'INFO',
                    'category': 'general',
                    'message': line
                })
        
        return jsonify({
            'logs': parsed_logs,
            'total': len(parsed_logs)
        })
        
    except Exception as e:
        logger.error(f'Error reading log history: {e}', exc_info=True)
        return jsonify({
            'logs': [],
            'error': str(e)
        }), 500


@app.route('/api/news')
def api_news():
    """Get news feed and sentiment"""
    return jsonify({
        'news': bot_state['news'][-50:],  # Last 50 news items
        'sentiment_history': bot_state['sentiment_history'][-20:]  # Last 20 sentiment readings
    })


# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Client connected"""
    logger.info('[WEB] Client connected')
    emit('status_update', bot_state)


@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected"""
    logger.info('[WEB] Client disconnected')


@socketio.on('request_update')
def handle_request_update():
    """Client requested update"""
    emit('status_update', bot_state)


def broadcast_status_update():
    """Broadcast status update to all connected clients"""
    socketio.emit('status_update', bot_state, namespace='/')


def broadcast_trade_update(trade_data):
    """Broadcast trade update"""
    socketio.emit('trade_update', trade_data, namespace='/')


def broadcast_log(log_data):
    """Broadcast log message"""
    # Determine category
    message = log_data.get('message', '')
    category = 'info'
    
    if any(word in message.lower() for word in ['новост', 'news', '📰', 'sentiment']):
        category = 'news'
    elif any(word in message.lower() for word in ['ml', 'модел', '🤖', '🧠', 'lstm', 'finbert', 'ensemble']):
        category = 'ml'
    elif any(word in message.lower() for word in ['сделк', 'позиц', 'trade', '🎯', 'open', 'close', 'buy', 'sell']):
        category = 'trade'
    elif log_data.get('level', 'INFO').upper() in ['ERROR', 'CRITICAL'] or '❌' in message:
        category = 'error'
    
    bot_state['logs'].append({
        'timestamp': datetime.now().isoformat(),
        'level': log_data.get('level', 'INFO'),
        'message': message,
        'category': category
    })
    # Keep only last 200 logs
    if len(bot_state['logs']) > 200:
        bot_state['logs'] = bot_state['logs'][-200:]
    
    socketio.emit('log_update', log_data, namespace='/')


def update_bot_state(**kwargs):
    """Update bot state and broadcast"""
    bot_state.update(kwargs)
    broadcast_status_update()


def add_news_item(title, source, sentiment, category='neutral'):
    """Add news item to feed"""
    news_item = {
        'timestamp': datetime.now().isoformat(),
        'title': title,
        'source': source,
        'sentiment': sentiment,
        'category': category  # positive, neutral, negative
    }
    bot_state['news'].append(news_item)
    
    # Keep only last 100 news items
    if len(bot_state['news']) > 100:
        bot_state['news'] = bot_state['news'][-100:]
    
    # Broadcast news update
    socketio.emit('news_update', news_item, namespace='/')
    
    # Log news
    sentiment_emoji = '😊' if category == 'positive' else '☹️' if category == 'negative' else '😐'
    broadcast_log({
        'level': 'INFO',
        'message': f'📰 Новость: {title[:50]}... (sentiment: {sentiment:.2f} {sentiment_emoji})'
    })


def update_sentiment(sentiment_score):
    """Update sentiment history"""
    sentiment_item = {
        'timestamp': datetime.now().isoformat(),
        'score': sentiment_score
    }
    bot_state['sentiment_history'].append(sentiment_item)
    
    # Keep only last 50 readings
    if len(bot_state['sentiment_history']) > 50:
        bot_state['sentiment_history'] = bot_state['sentiment_history'][-50:]
    
    # Log sentiment update
    broadcast_log({
        'level': 'INFO',
        'message': f'📊 Sentiment обновлен: {sentiment_score:.2f} ({get_sentiment_label(sentiment_score)})'
    })


def get_sentiment_label(score):
    """Get sentiment label from score"""
    if score > 0.3:
        return 'Очень позитивный'
    elif score > 0.1:
        return 'Позитивный'
    elif score > -0.1:
        return 'Нейтральный'
    elif score > -0.3:
        return 'Негативный'
    else:
        return 'Очень негативный'


def start_news_scheduler():
    """Start the news scheduler"""
    global news_scheduler
    
    try:
        from src.sentiment.news_scheduler import NewsScheduler
        
        # Get configuration
        interval = int(os.getenv('NEWS_UPDATE_INTERVAL_MINUTES', '15'))
        symbols = ['BTC', 'ETH']  # Can be configured
        
        # Create scheduler with callback
        news_scheduler = NewsScheduler(
            interval_minutes=interval,
            symbols=symbols,
            callback=on_news_update
        )
        
        news_scheduler.start()
        logger.info(f'[NEWS] ✅ Scheduler started: {interval} minute interval')
        broadcast_log({
            'level': 'INFO',
            'message': f'📰 News scheduler started (updates every {interval} minutes)'
        })
        
    except Exception as e:
        logger.error(f'[NEWS] ❌ Failed to start scheduler: {e}', exc_info=True)
        broadcast_log({
            'level': 'ERROR',
            'message': f'❌ Failed to start news scheduler: {e}'
        })


def on_news_update(data):
    """Callback when news are updated"""
    try:
        # Add news items to bot state
        for news_item in data['news']:
            add_news_item(
                title=news_item['title'],
                source=news_item['source'],
                sentiment=news_item['sentiment'],
                category=news_item['category']
            )
        
        # Update sentiment history
        update_sentiment(data['avg_sentiment'])
        
        logger.info(f'[NEWS] ✅ Updated {len(data["news"])} news items')
        
    except Exception as e:
        logger.error(f'[NEWS] ❌ Error processing news update: {e}', exc_info=True)


def run_web_server(host='127.0.0.1', port=5000, debug=False):
    """Run Flask web server"""
    logger.info(f'[WEB] Starting web dashboard on http://{host}:{port}')
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


def start_web_server_thread(host='127.0.0.1', port=5000):
    """Start web server in separate thread"""
    thread = threading.Thread(
        target=run_web_server,
        args=(host, port, False),
        daemon=True
    )
    thread.start()
    logger.info(f'[WEB] Dashboard started at http://{host}:{port}')
    return thread


def start_demo_updates():
    """Start demo data updates for testing"""
    import random
    
    demo_news_titles = [
        'Bitcoin reaches new all-time high amid institutional adoption',
        'SEC delays decision on Bitcoin ETF applications',
        'Major exchange announces support for new trading pairs',
        'Market analysis: Bitcoin consolidates before next move',
        'Regulatory concerns impact crypto market sentiment',
        'Ethereum upgrade goes live successfully',
        'Whale moves $100M in Bitcoin',
        'New DeFi protocol gains traction',
        'Fed announces interest rate decision',
        'Crypto trading volume surges 40%'
    ]
    
    demo_sources = ['CryptoPanic', 'CoinDesk', 'TradingView', 'Reuters', 'Bloomberg']
    
    def update_demo_data():
        news_counter = 0
        
        while True:
            if bot_state['status'] == 'running':
                # Simulate balance changes
                change = random.uniform(-50, 100)
                bot_state['balance'] = max(5000, bot_state['balance'] + change)
                bot_state['total_pnl'] = bot_state['balance'] - bot_state['initial_balance']
                bot_state['total_pnl_pct'] = (bot_state['total_pnl'] / bot_state['initial_balance']) * 100
                
                # Random news (every 10 cycles = ~20 seconds)
                if news_counter % 10 == 0 and random.random() < 0.5:
                    title = random.choice(demo_news_titles)
                    source = random.choice(demo_sources)
                    sentiment = random.uniform(-0.8, 0.9)
                    category = 'positive' if sentiment > 0.2 else 'negative' if sentiment < -0.2 else 'neutral'
                    
                    add_news_item(title, source, sentiment, category)
                    
                    # Update average sentiment every few news items
                    if len(bot_state['news']) > 0:
                        avg_sentiment = sum(n['sentiment'] for n in bot_state['news'][-10:]) / min(10, len(bot_state['news']))
                        update_sentiment(avg_sentiment)
                
                news_counter += 1
                
                # Random log messages
                if random.random() < 0.1:
                    messages = [
                        ('INFO', '📊 Анализ рынка...'),
                        ('INFO', '🤖 ML модель: BUY signal detected (65% confidence)'),
                        ('INFO', '🧠 LSTM предсказание: цена вверх (68%)'),
                        ('SUCCESS', '✅ Позиция открыта: BTC/USDT LONG @ $95,234'),
                        ('INFO', '📈 Обновление индикаторов...'),
                        ('WARNING', '⚠️ Низкая волатильность рынка'),
                    ]
                    level, msg = random.choice(messages)
                    broadcast_log({'level': level, 'message': msg})
                
                # Simulate trades
                if random.random() < 0.05 and len(bot_state['open_positions']) < 2:
                    side = random.choice(['long', 'short'])
                    price = random.uniform(94000, 96000)
                    bot_state['open_positions'].append({
                        'symbol': 'BTC/USDT',
                        'side': side,
                        'entry_price': price,
                        'current_price': price,
                        'pnl': 0,
                        'pnl_pct': 0,
                        'entry_time': datetime.now().isoformat()
                    })
                    broadcast_log({'level': 'SUCCESS', 'message': f'🎯 Opened {side.upper()} @ ${price:.2f}'})
                
                # Update open positions
                for pos in bot_state['open_positions']:
                    pos['current_price'] += random.uniform(-100, 100)
                    multiplier = 1 if pos['side'] == 'long' else -1
                    pos['pnl'] = (pos['current_price'] - pos['entry_price']) * 0.01 * multiplier
                    pos['pnl_pct'] = ((pos['current_price'] - pos['entry_price']) / pos['entry_price']) * 100 * multiplier
                
                # Close positions randomly
                if bot_state['open_positions'] and random.random() < 0.03:
                    pos = bot_state['open_positions'].pop(0)
                    trade = {
                        'symbol': pos['symbol'],
                        'side': pos['side'],
                        'entry_price': pos['entry_price'],
                        'exit_price': pos['current_price'],
                        'pnl': pos['pnl'],
                        'pnl_pct': pos['pnl_pct'],
                        'exit_time': datetime.now().isoformat(),
                        'exit_reason': random.choice(['take_profit', 'stop_loss', 'trailing_stop'])
                    }
                    bot_state['closed_trades'].append(trade)
                    bot_state['total_trades'] += 1
                    if pos['pnl'] > 0:
                        bot_state['winning_trades'] += 1
                    else:
                        bot_state['losing_trades'] += 1
                    bot_state['win_rate'] = (bot_state['winning_trades'] / bot_state['total_trades']) * 100 if bot_state['total_trades'] > 0 else 0
                    
                    result = '✅ Profit' if pos['pnl'] > 0 else '❌ Loss'
                    broadcast_log({'level': 'SUCCESS' if pos['pnl'] > 0 else 'ERROR', 
                                  'message': f'{result}: Closed {pos["side"].upper()} @ ${pos["current_price"]:.2f} | P&L: ${pos["pnl"]:.2f}'})
                
                broadcast_status_update()
            
            time.sleep(2)  # Update every 2 seconds
    
    demo_thread = threading.Thread(target=update_demo_data, daemon=True)
    demo_thread.start()
    logger.info('[WEB] Demo mode enabled - generating test data')



if __name__ == '__main__':
    # Test server with demo data
    logging.basicConfig(level=logging.INFO)
    start_demo_updates()
    run_web_server(debug=True)
