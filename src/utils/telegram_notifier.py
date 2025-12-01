"""
Telegram Bot for Notifications and Remote Control
==================================================
Отправляет уведомления о сделках и позволяет управлять ботом удалённо
"""

import logging
from typing import Optional, Dict, List
import asyncio
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from ..config.config_loader import get_config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Telegram bot for trading notifications and control
    """
    
    def __init__(self):
        """Initialize Telegram notifier"""
        self.config = get_config()
        
        # Telegram configuration
        self.bot_token = self.config.get('telegram', 'bot_token', default=None)
        self.chat_id = self.config.get('telegram', 'chat_id', default=None)
        
        # Notification settings
        self.notify_trades = self.config.get('telegram', 'notify_trades', default=True)
        self.notify_signals = self.config.get('telegram', 'notify_signals', default=True)
        self.notify_errors = self.config.get('telegram', 'notify_errors', default=True)
        self.notify_daily_summary = self.config.get('telegram', 'notify_daily_summary', default=True)
        
        # Bot state
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self.enabled = False
        
        # Trading bot reference (will be set externally)
        self.trading_bot = None
        
        if self.bot_token and self.chat_id:
            try:
                self.bot = Bot(token=self.bot_token)
                self.enabled = True
                logger.info("[TELEGRAM] Telegram notifier initialized")
            except Exception as e:
                logger.error(f"[TELEGRAM] Initialization error: {e}")
                self.enabled = False
        else:
            logger.warning("[TELEGRAM] Bot token or chat ID not configured")
    
    async def send_message(self, message: str, parse_mode: str = 'Markdown'):
        """
        Send message to Telegram
        
        Args:
            message: Message text
            parse_mode: Message formatting (Markdown or HTML)
        """
        if not self.enabled:
            return
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.debug(f"[TELEGRAM] Message sent: {message[:50]}...")
        except Exception as e:
            logger.error(f"[TELEGRAM] Error sending message: {e}")
    
    async def notify_trade_opened(self, trade_info: Dict):
        """
        Notify about opened trade
        
        Args:
            trade_info: Dictionary with trade information
        """
        if not self.notify_trades:
            return
        
        side_emoji = "🟢" if trade_info['side'] == 'long' else "🔴"
        
        message = f"""
{side_emoji} *TRADE OPENED*

*Symbol:* {trade_info.get('symbol', 'N/A')}
*Side:* {trade_info['side'].upper()}
*Entry Price:* ${trade_info.get('entry_price', 0):,.2f}
*Position Size:* {trade_info.get('size', 0):.4f}
*Stop Loss:* ${trade_info.get('stop_loss', 0):,.2f}
*Take Profit:* ${trade_info.get('take_profit', 0):,.2f}

*ML Confidence:* {trade_info.get('ml_confidence', 0):.1%}
*Sentiment:* {trade_info.get('sentiment_score', 0):.2f}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(message)
    
    async def notify_trade_closed(self, trade_info: Dict):
        """
        Notify about closed trade
        
        Args:
            trade_info: Dictionary with trade information
        """
        if not self.notify_trades:
            return
        
        pnl = trade_info.get('pnl', 0)
        pnl_emoji = "💰" if pnl > 0 else "❌"
        
        message = f"""
{pnl_emoji} *TRADE CLOSED*

*Symbol:* {trade_info.get('symbol', 'N/A')}
*Side:* {trade_info['side'].upper()}
*Entry:* ${trade_info.get('entry_price', 0):,.2f}
*Exit:* ${trade_info.get('exit_price', 0):,.2f}

*PnL:* ${pnl:,.2f} ({trade_info.get('pnl_pct', 0):.2f}%)
*Duration:* {trade_info.get('duration', 'N/A')}
*Reason:* {trade_info.get('close_reason', 'N/A')}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(message)
    
    async def notify_signal(self, signal_info: Dict):
        """
        Notify about trading signal
        
        Args:
            signal_info: Dictionary with signal information
        """
        if not self.notify_signals:
            return
        
        signal = signal_info.get('signal', 0)
        if signal == 0:
            return  # Don't notify for neutral signals
        
        signal_emoji = "📈" if signal > 0 else "📉"
        signal_text = "BUY" if signal > 0 else "SELL"
        
        message = f"""
{signal_emoji} *NEW SIGNAL: {signal_text}*

*Symbol:* {signal_info.get('symbol', 'N/A')}
*Price:* ${signal_info.get('current_price', 0):,.2f}

*ML Prediction:* {signal_info.get('ml_signal', 0)} (conf: {signal_info.get('ml_confidence', 0):.1%})
*Sentiment:* {signal_info.get('sentiment_score', 0):.2f}
*Combined Signal:* {signal}

*Recommended Entry:* ${signal_info.get('entry_price', 0):,.2f}
*Stop Loss:* ${signal_info.get('stop_loss', 0):,.2f}
*Take Profit:* ${signal_info.get('take_profit', 0):,.2f}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(message)
    
    async def notify_error(self, error_msg: str, details: str = ""):
        """
        Notify about error
        
        Args:
            error_msg: Error message
            details: Additional details
        """
        if not self.notify_errors:
            return
        
        message = f"""
⚠️ *ERROR OCCURRED*

*Message:* {error_msg}

{f'*Details:* {details}' if details else ''}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(message)
    
    async def notify_daily_summary(self, summary: Dict):
        """
        Send daily trading summary
        
        Args:
            summary: Dictionary with daily summary
        """
        if not self.notify_daily_summary:
            return
        
        total_pnl = summary.get('total_pnl', 0)
        pnl_emoji = "💰" if total_pnl > 0 else "📊"
        
        message = f"""
{pnl_emoji} *DAILY SUMMARY*

📊 *Performance*
Total PnL: ${total_pnl:,.2f}
Return: {summary.get('return_pct', 0):.2f}%
Win Rate: {summary.get('win_rate', 0):.1%}

📈 *Trades*
Total: {summary.get('total_trades', 0)}
Wins: {summary.get('winning_trades', 0)}
Losses: {summary.get('losing_trades', 0)}

💹 *Risk*
Max Drawdown: {summary.get('max_drawdown', 0):.2f}%
Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}

💼 *Balance*
Current: ${summary.get('current_balance', 0):,.2f}
Peak: ${summary.get('peak_balance', 0):,.2f}

📅 {datetime.now().strftime('%Y-%m-%d')}
"""
        await self.send_message(message)
    
    # Command handlers for bot control
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_msg = """
👋 *Welcome to AiCryptoBot!*

Available commands:
/status - Get current bot status
/balance - Show account balance
/positions - List open positions
/performance - Show performance metrics
/stop - Stop trading bot
/start_trading - Resume trading
/help - Show this help message
"""
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self.trading_bot:
            await update.message.reply_text("Trading bot not connected")
            return
        
        status = self.trading_bot.get_status()
        
        message = f"""
📊 *Bot Status*

*Running:* {'✅ Yes' if status.get('running') else '❌ No'}
*Mode:* {status.get('mode', 'N/A')}
*Open Positions:* {status.get('open_positions', 0)}
*Uptime:* {status.get('uptime', 'N/A')}

*Last Signal:* {status.get('last_signal_time', 'Never')}
*Last Trade:* {status.get('last_trade_time', 'Never')}
"""
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        if not self.trading_bot:
            await update.message.reply_text("Trading bot not connected")
            return
        
        balance = self.trading_bot.get_balance()
        
        message = f"""
💼 *Account Balance*

*Free:* ${balance.get('free', 0):,.2f}
*Used:* ${balance.get('used', 0):,.2f}
*Total:* ${balance.get('total', 0):,.2f}

*Initial Capital:* ${balance.get('initial', 0):,.2f}
*Total PnL:* ${balance.get('total_pnl', 0):,.2f}
*Return:* {balance.get('return_pct', 0):.2f}%
"""
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        if not self.trading_bot:
            await update.message.reply_text("Trading bot not connected")
            return
        
        positions = self.trading_bot.get_open_positions()
        
        if not positions:
            await update.message.reply_text("No open positions")
            return
        
        message = "*Open Positions:*\n\n"
        for i, pos in enumerate(positions, 1):
            side_emoji = "🟢" if pos['side'] == 'long' else "🔴"
            message += f"""
{side_emoji} *Position {i}*
Symbol: {pos['symbol']}
Side: {pos['side'].upper()}
Entry: ${pos['entry_price']:,.2f}
Size: {pos['size']:.4f}
Current PnL: ${pos.get('unrealized_pnl', 0):,.2f}

"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /performance command"""
        if not self.trading_bot:
            await update.message.reply_text("Trading bot not connected")
            return
        
        metrics = self.trading_bot.get_performance_metrics()
        
        message = f"""
📈 *Performance Metrics*

*Total Trades:* {metrics.get('total_trades', 0)}
*Win Rate:* {metrics.get('win_rate', 0):.1%}
*Profit Factor:* {metrics.get('profit_factor', 0):.2f}

*Total Return:* {metrics.get('total_return', 0):.2f}%
*Sharpe Ratio:* {metrics.get('sharpe_ratio', 0):.2f}
*Max Drawdown:* {metrics.get('max_drawdown', 0):.2f}%

*Avg Win:* ${metrics.get('avg_win', 0):,.2f}
*Avg Loss:* ${metrics.get('avg_loss', 0):,.2f}
"""
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        if not self.trading_bot:
            await update.message.reply_text("Trading bot not connected")
            return
        
        self.trading_bot.stop_trading()
        await update.message.reply_text("🛑 Trading bot stopped")
    
    async def cmd_start_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_trading command"""
        if not self.trading_bot:
            await update.message.reply_text("Trading bot not connected")
            return
        
        self.trading_bot.start_trading()
        await update.message.reply_text("✅ Trading bot started")
    
    def start_bot(self):
        """Start Telegram bot (non-blocking)"""
        if not self.enabled:
            logger.warning("[TELEGRAM] Bot not enabled")
            return
        
        try:
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CommandHandler("balance", self.cmd_balance))
            self.application.add_handler(CommandHandler("positions", self.cmd_positions))
            self.application.add_handler(CommandHandler("performance", self.cmd_performance))
            self.application.add_handler(CommandHandler("stop", self.cmd_stop))
            self.application.add_handler(CommandHandler("start_trading", self.cmd_start_trading))
            
            # Start bot in background
            logger.info("[TELEGRAM] Starting Telegram bot...")
            self.application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"[TELEGRAM] Error starting bot: {e}")
    
    def set_trading_bot(self, trading_bot):
        """
        Set reference to trading bot for command handling
        
        Args:
            trading_bot: Trading bot instance
        """
        self.trading_bot = trading_bot
        logger.info("[TELEGRAM] Trading bot reference set")


def get_telegram_notifier() -> TelegramNotifier:
    """
    Get singleton instance of Telegram notifier
    
    Returns:
        TelegramNotifier instance
    """
    if not hasattr(get_telegram_notifier, '_instance'):
        get_telegram_notifier._instance = TelegramNotifier()
    return get_telegram_notifier._instance


if __name__ == '__main__':
    # Test notifier
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    notifier = get_telegram_notifier()
    
    if notifier.enabled:
        print("✅ Telegram notifier enabled")
        
        # Test notification
        asyncio.run(notifier.send_message("🤖 AiCryptoBot test message"))
        print("📤 Test message sent")
    else:
        print("❌ Telegram notifier not configured")
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config")
