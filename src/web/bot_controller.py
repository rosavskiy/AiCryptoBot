"""
Bot Controller
==============
Controls trading bot execution and provides interface for web dashboard
"""

import logging
import threading
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class BotController:
    """
    Controller for managing bot execution
    """
    
    def __init__(self, trading_bot):
        """
        Initialize controller
        
        Args:
            trading_bot: Instance of trading bot
        """
        self.bot = trading_bot
        self.running = False
        self.paused = False
        self.thread: Optional[threading.Thread] = None
        
        logger.info('[CONTROLLER] Bot controller initialized')
    
    def start(self):
        """Start the trading bot"""
        if self.running:
            logger.warning('[CONTROLLER] Bot is already running')
            return
        
        self.running = True
        self.paused = False
        
        # Start bot in separate thread
        self.thread = threading.Thread(target=self._run_bot, daemon=True)
        self.thread.start()
        
        logger.info('[CONTROLLER] Bot started')
    
    def stop(self):
        """Stop the trading bot"""
        if not self.running:
            logger.warning('[CONTROLLER] Bot is not running')
            return
        
        self.running = False
        self.paused = False
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info('[CONTROLLER] Bot stopped')
    
    def pause(self):
        """Pause the trading bot"""
        if not self.running:
            logger.warning('[CONTROLLER] Bot is not running')
            return
        
        self.paused = True
        logger.info('[CONTROLLER] Bot paused')
    
    def resume(self):
        """Resume the trading bot"""
        if not self.running:
            logger.warning('[CONTROLLER] Bot is not running')
            return
        
        self.paused = False
        logger.info('[CONTROLLER] Bot resumed')
    
    def _run_bot(self):
        """Internal method to run bot loop"""
        logger.info('[CONTROLLER] Bot loop started')
        
        try:
            while self.running:
                if not self.paused:
                    # Run bot iteration
                    self.bot.run_iteration()
                
                # Sleep between iterations
                time.sleep(5)  # Check every 5 seconds
        
        except Exception as e:
            logger.error(f'[CONTROLLER] Bot loop error: {e}', exc_info=True)
            self.running = False
        
        logger.info('[CONTROLLER] Bot loop stopped')
    
    def is_running(self) -> bool:
        """Check if bot is running"""
        return self.running
    
    def is_paused(self) -> bool:
        """Check if bot is paused"""
        return self.paused
    
    def get_status(self) -> str:
        """Get bot status"""
        if not self.running:
            return 'stopped'
        elif self.paused:
            return 'paused'
        else:
            return 'running'
