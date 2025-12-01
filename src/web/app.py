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

# Initialize SocketIO with better error handling
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,  # Disable verbose logging
    engineio_logger=False,  # Disable engine.io logging
    ping_timeout=60,
    ping_interval=25,
    manage_session=False  # Don't manage sessions automatically
)

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

# Real trading bot instance
trading_bot_instance = None
trading_bot_thread = None

# News scheduler
news_scheduler = None


def set_bot_controller(controller):
    """Set reference to bot controller"""
    global bot_controller
    bot_controller = controller


def initialize_trading_bot():
    """Initialize real trading bot for testnet"""
    global trading_bot_instance
    
    if trading_bot_instance is not None:
        return trading_bot_instance
    
    try:
        from src.trading.executor import TradingExecutor
        
        # Create trading executor in testnet mode
        config = get_config()
        
        # Force testnet mode
        testnet_mode = config.get('exchange', 'testnet', default=True)
        
        # Get API keys from environment
        import os
        if testnet_mode:
            # Try Binance testnet first
            api_key = os.getenv('BINANCE_TESTNET_API_KEY') or os.getenv('BYBIT_API_KEY')
            api_secret = os.getenv('BINANCE_TESTNET_API_SECRET') or os.getenv('BYBIT_API_SECRET')
        else:
            api_key = os.getenv('BINANCE_API_KEY') or os.getenv('BYBIT_API_KEY')
            api_secret = os.getenv('BINANCE_API_SECRET') or os.getenv('BYBIT_API_SECRET')
        
        logger.info(f'[BOT] Initializing trading bot (testnet={testnet_mode})...')
        
        trading_bot_instance = TradingExecutor(
            api_key=api_key,
            api_secret=api_secret,
            dry_run=False,  # Real execution
            testnet=testnet_mode,
            analyze_only=False
        )
        
        logger.info('[BOT] Trading bot initialized successfully')
        return trading_bot_instance
        
    except Exception as e:
        logger.error(f'[BOT] Failed to initialize trading bot: {e}', exc_info=True)
        return None


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
    """Start the real trading bot"""
    global trading_bot_instance, trading_bot_thread, bot_state
    
    try:
        # Initialize trading bot if not already done
        if trading_bot_instance is None:
            trading_bot_instance = initialize_trading_bot()
            
        if trading_bot_instance is None:
            return jsonify({
                'success': False, 
                'error': 'Failed to initialize trading bot'
            }), 500
        
        # Check if already running
        if bot_state['status'] == 'running':
            return jsonify({
                'success': False,
                'message': 'Bot is already running'
            })
        
        # Start news scheduler if not running
        global news_scheduler
        if news_scheduler is None or not news_scheduler.is_running():
            start_news_scheduler()
        
        # Start trading bot in separate thread
        def run_trading_loop():
            """Run trading bot loop"""
            logger.info('[BOT] Trading loop started')
            bot_state['status'] = 'running'
            bot_state['start_time'] = int(datetime.now().timestamp() * 1000)
            broadcast_status_update()
            
            try:
                # Get interval from config
                config = get_config()
                interval = config.get('trading', 'interval', default=900)  # 15 min
                
                while bot_state['status'] == 'running':
                    try:
                        # Run one trading iteration
                        logger.info('[BOT] Running trading iteration...')
                        result = trading_bot_instance.analyze_and_trade()
                        
                        # Update bot state with results
                        if result:
                            try:
                                update_bot_state_from_executor(result)
                            except Exception as state_error:
                                logger.warning(f'[BOT] Could not update state: {state_error}')
                        
                        # Broadcast update to web clients
                        try:
                            broadcast_status_update()
                        except Exception as broadcast_error:
                            logger.warning(f'[BOT] Could not broadcast update: {broadcast_error}')
                        
                    except Exception as e:
                        logger.error(f'[BOT] Error in trading iteration: {e}', exc_info=True)
                        try:
                            broadcast_log({'level': 'ERROR', 'message': f'Trading error: {str(e)}'})
                        except:
                            pass  # Don't fail if broadcast fails
                    
                    # Sleep until next iteration
                    logger.info(f'[BOT] Waiting {interval}s until next iteration...')
                    time.sleep(interval)
                    
            except Exception as e:
                logger.error(f'[BOT] Fatal error in trading loop: {e}', exc_info=True)
                bot_state['status'] = 'stopped'
                broadcast_status_update()
            
            logger.info('[BOT] Trading loop stopped')
        
        # Start thread
        trading_bot_thread = threading.Thread(target=run_trading_loop, daemon=True)
        trading_bot_thread.start()
        
        broadcast_log({'level': 'INFO', 'message': '🚀 Real trading bot started on TESTNET'})
        
        return jsonify({
            'success': True,
            'message': 'Trading bot started successfully',
            'testnet': True
        })
        
    except Exception as e:
        logger.error(f'[BOT] Error starting bot: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def update_bot_state_from_executor(result):
    """Update bot state from trading executor results"""
    try:
        # Update from executor state (RiskManager = portfolio_manager)
        if hasattr(trading_bot_instance, 'risk_manager'):
            rm = trading_bot_instance.risk_manager
            
            # Update balance from risk manager
            bot_state['balance'] = float(rm.current_capital)
            bot_state['total_pnl'] = float(rm.total_pnl) if hasattr(rm, 'total_pnl') else 0.0
            bot_state['total_pnl_pct'] = (rm.total_pnl / rm.initial_capital * 100) if rm.initial_capital > 0 else 0
            
            # Update positions from executor - ПРАВИЛЬНЫЕ ПОЛЯ!
            bot_state['open_positions'] = []
            if hasattr(trading_bot_instance, 'active_positions'):
                for symbol, pos_data in trading_bot_instance.active_positions.items():
                    # pos_data содержит: symbol, side, type, price, quantity, position_size, stop_loss, take_profit, timestamp, order_id, status
                    entry_price = float(pos_data.get('price', 0))
                    quantity = float(pos_data.get('quantity', 0))
                    position_size = float(pos_data.get('position_size', 0))
                    
                    bot_state['open_positions'].append({
                        'symbol': symbol,
                        'side': pos_data.get('side', 'buy').upper(),
                        'entry_price': entry_price,
                        'current_price': entry_price,  # Will be updated on next check
                        'quantity': quantity,
                        'position_size': position_size,
                        'stop_loss': float(pos_data.get('stop_loss', 0)),
                        'take_profit': float(pos_data.get('take_profit', 0)),
                        'pnl': 0.0,  # Will be calculated on next check
                        'pnl_pct': 0.0,
                        'order_id': str(pos_data.get('order_id', ''))
                    })
            
            logger.info(f'[BOT] State updated: {len(bot_state["open_positions"])} positions')
            
            # Update stats from trade logger
            if hasattr(trading_bot_instance, 'trade_logger'):
                try:
                    trades_df = trading_bot_instance.trade_logger.get_trades(limit=100)
                    # Check if DataFrame is not empty
                    if not trades_df.empty:
                        # Convert DataFrame to list of dicts
                        valid_trades = trades_df.to_dict('records')
                        bot_state['closed_trades'] = valid_trades[-50:]  # Last 50 trades
                        bot_state['total_trades'] = len(valid_trades)
                        bot_state['winning_trades'] = sum(1 for t in valid_trades if t.get('pnl', 0) > 0)
                        bot_state['losing_trades'] = sum(1 for t in valid_trades if t.get('pnl', 0) < 0)
                        bot_state['win_rate'] = (bot_state['winning_trades'] / max(bot_state['total_trades'], 1)) * 100
                except Exception as e:
                    logger.warning(f'[BOT] Could not load trade history: {e}')
            
            bot_state['current_drawdown'] = float(getattr(rm, 'current_drawdown', 0.0))
            bot_state['max_drawdown'] = float(getattr(rm, 'max_drawdown', 0.0))
            
    except Exception as e:
        logger.error(f'[BOT] Error updating state: {e}', exc_info=True)


@app.route('/api/control/stop', methods=['POST'])
def api_stop():
    """Stop the trading bot"""
    global bot_state
    
    if bot_state['status'] == 'stopped':
        return jsonify({
            'success': False,
            'message': 'Bot is not running'
        })
    
    # Stop the bot
    bot_state['status'] = 'stopped'
    broadcast_status_update()
    broadcast_log({'level': 'INFO', 'message': '⏹️ Trading bot stopped'})
    
    logger.info('[BOT] Bot stopped by user')
    
    return jsonify({'success': True, 'message': 'Bot stopped'})


@app.route('/api/control/pause', methods=['POST'])
def api_pause():
    """Pause the trading bot"""
    global bot_state
    
    if bot_state['status'] != 'running':
        return jsonify({
            'success': False,
            'message': 'Bot is not running'
        })
    
    # Pause the bot
    bot_state['status'] = 'paused'
    broadcast_status_update()
    broadcast_log({'level': 'WARNING', 'message': '⏸️ Trading bot paused'})
    
    logger.info('[BOT] Bot paused by user')
    
    return jsonify({'success': True, 'message': 'Bot paused'})


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
        # Get filter parameter (all, trading, system, errors)
        log_filter = request.args.get('filter', 'all')
        
        # Read both log files and merge
        log_dir = Path(__file__).parent.parent.parent / 'logs'
        all_logs = []
        
        # Read trading logs (main bot)
        trading_log = log_dir / 'trading.log'
        if trading_log.exists():
            with open(trading_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-1000:]:  # Last 1000 lines
                    all_logs.append(('trading', line))
        
        # Read dashboard logs (web server)
        dashboard_log = log_dir / 'dashboard.log'
        if dashboard_log.exists():
            with open(dashboard_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-500:]:  # Last 500 lines
                    all_logs.append(('dashboard', line))
        
        if not all_logs:
            return jsonify({
                'logs': [],
                'message': 'No log files found yet'
            })
        
        # Read last 500 lines from log file
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-500:] if len(lines) > 500 else lines
        
        # Parse logs into structured format
        parsed_logs = []
        for source, line in all_logs:
            line = line.strip()
            if not line:
                continue
            
            try:
                timestamp_part = ''
                level = 'INFO'
                message = line
                category = 'system' if source == 'dashboard' else 'trading'
                
                # Parse format: 2025-12-01 20:33:55,533 - module - LEVEL - message
                if ' - ' in line:
                    parts = line.split(' - ', 3)
                    if len(parts) >= 4:
                        timestamp_part = parts[0]
                        level = parts[2]
                        message = parts[3]
                
                # Categorize by message content
                if source == 'trading':
                    if any(x in message for x in ['[NEWS]', '[CRYPTOPANIC]', 'Fetched 0 news']):
                        category = 'news'
                    elif any(x in message for x in ['[ML]', '[TRAIN]', 'model', 'prediction', 'features']):
                        category = 'ml'
                    elif any(x in message for x in ['[SIGNAL]', '[TRADE]', '[ORDER]', 'position', 'BUY', 'SELL']):
                        category = 'trade'
                    elif any(x in message for x in ['[ANALYZE]', '[DATA]', 'Fetching', 'candles']):
                        category = 'analysis'
                    elif any(x in message for x in ['[PORTFOLIO]', 'Capital', 'Positions']):
                        category = 'portfolio'
                    elif 'ERROR' in level or '[ERROR]' in message:
                        category = 'error'
                    elif 'WARNING' in level or '[WARNING]' in message:
                        category = 'warning'
                
                # Apply filter
                if log_filter == 'trading' and category not in ['trade', 'analysis', 'portfolio', 'ml']:
                    continue
                elif log_filter == 'system' and source != 'dashboard':
                    continue
                elif log_filter == 'errors' and category not in ['error', 'warning']:
                    continue
                elif log_filter == 'ml' and category != 'ml':
                    continue
                
                parsed_logs.append({
                    'timestamp': timestamp_part,
                    'level': level,
                    'category': category,
                    'source': source,
                    'message': message
                })
                
            except Exception:
                parsed_logs.append({
                    'timestamp': '',
                    'level': 'INFO',
                    'category': 'system',
                    'source': source,
                    'message': line
                })
        
        # Sort by timestamp (newest first)
        parsed_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        parsed_logs = parsed_logs[:500]
        
        return jsonify({
            'logs': parsed_logs,
            'total': len(parsed_logs),
            'filter': log_filter
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
def make_serializable(obj):
    """Recursively convert object to JSON-serializable format"""
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    elif isinstance(obj, (int, float)):
        # Handle numpy types and ensure valid floats
        if hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        return float(obj) if isinstance(obj, float) else int(obj)
    elif isinstance(obj, dict):
        return {str(k): make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif hasattr(obj, 'isoformat'):  # datetime objects
        return obj.isoformat()
    elif hasattr(obj, 'tolist'):  # numpy arrays
        return obj.tolist()
    elif hasattr(obj, 'to_dict'):  # pandas objects
        return make_serializable(obj.to_dict())
    else:
        # Last resort - convert to string
        return str(obj)


def get_serializable_bot_state():
    """Get bot state safe for JSON serialization"""
    try:
        # Make a clean copy with only primitive types
        safe_state = {
            'status': str(bot_state.get('status', 'stopped')),
            'start_time': bot_state.get('start_time'),
            'balance': float(bot_state.get('balance', 10000.0)),
            'initial_balance': float(bot_state.get('initial_balance', 10000.0)),
            'total_pnl': float(bot_state.get('total_pnl', 0.0)),
            'total_pnl_pct': float(bot_state.get('total_pnl_pct', 0.0)),
            'open_positions': make_serializable(bot_state.get('open_positions', [])),
            'closed_trades': make_serializable(bot_state.get('closed_trades', []))[:50],  # Last 50
            'total_trades': int(bot_state.get('total_trades', 0)),
            'winning_trades': int(bot_state.get('winning_trades', 0)),
            'losing_trades': int(bot_state.get('losing_trades', 0)),
            'win_rate': float(bot_state.get('win_rate', 0.0)),
            'current_drawdown': float(bot_state.get('current_drawdown', 0.0)),
            'max_drawdown': float(bot_state.get('max_drawdown', 0.0)),
            'sharpe_ratio': float(bot_state.get('sharpe_ratio', 0.0)),
        }
        return safe_state
    except Exception as e:
        logger.error(f'[WEB] Error serializing bot_state: {e}', exc_info=True)
        # Return minimal safe state
        return {
            'status': 'stopped',
            'balance': 10000.0,
            'total_pnl': 0.0,
            'open_positions': [],
            'closed_trades': []
        }


@socketio.on('connect')
def handle_connect():
    """Client connected"""
    logger.info('[WEB] Client connected')
    
    # Sync bot status with actual trading thread state
    global trading_bot_thread
    if trading_bot_thread and trading_bot_thread.is_alive():
        # Trading thread is running, update status
        if bot_state['status'] == 'stopped':
            bot_state['status'] = 'running'
            if not bot_state['start_time']:
                bot_state['start_time'] = int(datetime.now().timestamp() * 1000)
    else:
        # No thread running
        if bot_state['status'] == 'running':
            bot_state['status'] = 'stopped'
    
    try:
        safe_state = get_serializable_bot_state()
        emit('status_update', safe_state)
    except Exception as e:
        logger.error(f'[WEB] Failed to emit status_update on connect: {e}')
        # Send minimal state
        emit('status_update', {'status': 'stopped', 'balance': 10000.0})


@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected"""
    logger.info('[WEB] Client disconnected')


@socketio.on_error()
def error_handler(e):
    """Handle SocketIO errors"""
    logger.warning(f'[WEB] SocketIO error: {e}')


@socketio.on_error_default
def default_error_handler(e):
    """Handle all other SocketIO errors"""
    logger.warning(f'[WEB] SocketIO default error: {e}')


@socketio.on('request_update')
def handle_request_update():
    """Client requested update"""
    try:
        safe_state = get_serializable_bot_state()
        emit('status_update', safe_state)
    except Exception as e:
        logger.error(f'[WEB] Failed to emit status_update on request: {e}')


def broadcast_status_update():
    """Broadcast status update to all connected clients"""
    try:
        safe_state = get_serializable_bot_state()
        socketio.emit('status_update', safe_state, namespace='/')
    except Exception as e:
        logger.error(f'[WEB] Failed to broadcast status_update: {e}')


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
