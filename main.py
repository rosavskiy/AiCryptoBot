"""
AI Crypto Trading Bot - Main Entry Point
=========================================
Automated crypto trading with ML, Sentiment, and Risk Management.
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.trading.executor import TradingExecutor
from src.config.config_loader import get_config


def setup_logging(log_level: str = 'INFO'):
    """
    Setup logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Log filename with timestamp
    log_file = log_dir / f"trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")
    
    return logger


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='AI Crypto Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (simulation) on testnet
  python main.py --dry-run
  
  # Live trading on testnet (15 min intervals)
  python main.py --testnet --interval 900
  
  # Live trading on mainnet (USE WITH CAUTION!)
  python main.py --mainnet --capital 1000
  
  # Single analysis without trading
  python main.py --analyze-only --symbol BTC/USDT
        """
    )
    
    # Trading mode
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate trades without execution (default: True)'
    )
    mode_group.add_argument(
        '--testnet',
        action='store_true',
        help='Trade on Bybit Testnet (recommended for testing)'
    )
    mode_group.add_argument(
        '--mainnet',
        action='store_true',
        help='Trade on Bybit Mainnet (REAL MONEY - BE CAREFUL!)'
    )
    
    # Analysis only mode
    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='Only analyze market, do not trade'
    )
    
    # Trading parameters
    parser.add_argument(
        '--symbol',
        type=str,
        default=None,
        help='Trading symbol (e.g., BTC/USDT)'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        nargs='+',
        default=None,
        help='Multiple trading symbols (e.g., BTC/USDT ETH/USDT)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=900,
        help='Trading loop interval in seconds (default: 900 = 15 min)'
    )
    parser.add_argument(
        '--capital',
        type=float,
        default=None,
        help='Initial capital in USDT (default from config)'
    )
    
    # Logging
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set default to dry-run if no mode specified
    if not args.testnet and not args.mainnet:
        args.dry_run = True
    
    return args


def main():
    """Main entry point"""
    # Parse arguments
    args = parse_arguments()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    # Display banner
    print("\n" + "="*80)
    print("   AI CRYPTO TRADING BOT")
    print("   ML + Sentiment Analysis + Risk Management")
    print("="*80 + "\n")
    
    # Determine mode
    if args.dry_run:
        mode = "DRY RUN (Simulation)"
        testnet = True
        dry_run = True
    elif args.testnet:
        mode = "TESTNET (Paper Trading)"
        testnet = True
        dry_run = False
    else:  # mainnet
        mode = "MAINNET (LIVE TRADING - REAL MONEY!)"
        testnet = False
        dry_run = False
        
        # Safety confirmation for mainnet
        print("[WARNING] You are about to trade with REAL MONEY on MAINNET!")
        print("[WARNING] Make sure you have thoroughly tested on testnet first.")
        confirm = input("\nType 'I UNDERSTAND THE RISKS' to continue: ")
        
        if confirm != "I UNDERSTAND THE RISKS":
            print("\n[ABORT] Mainnet trading cancelled.")
            return 1
    
    logger.info(f"Mode: {mode}")
    logger.info(f"Testnet: {testnet}, Dry Run: {dry_run}")
    
    # Get symbols
    config = get_config()
    if args.symbol:
        symbols = [args.symbol]
    elif args.symbols:
        symbols = args.symbols
    else:
        symbols = config.get('symbols', default=['BTC/USDT'])
    
    logger.info(f"Trading symbols: {symbols}")
    logger.info(f"Interval: {args.interval}s ({args.interval/60:.0f} min)")
    
    # Initialize executor
    try:
        executor = TradingExecutor(
            testnet=testnet,
            initial_capital=args.capital
        )
        
        logger.info(f"Trading Executor initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize executor: {e}")
        return 1
    
    # Analyze only mode
    if args.analyze_only:
        logger.info("Analysis-only mode - No trading will occur")
        
        for symbol in symbols:
            print(f"\n{'='*80}")
            print(f"   ANALYZING {symbol}")
            print(f"{'='*80}\n")
            
            try:
                analysis = executor.analyze_market(symbol)
                should_trade, reason, direction = executor.generate_signal(analysis)
                
                print(f"\n[ANALYSIS]")
                print(f"  Price:            ${analysis['price']:.2f}")
                print(f"  ATR:              ${analysis['atr']:.2f}")
                print(f"  ML Signal:        {analysis['ml_signal']} ({analysis['ml_confidence']:.2%})")
                print(f"  Sentiment:        {analysis['sentiment_label']} ({analysis['sentiment_score']:.4f})")
                print(f"\n[SIGNAL]")
                print(f"  Trade:            {'YES' if should_trade else 'NO'}")
                print(f"  Direction:        {direction if direction else 'N/A'}")
                print(f"  Reason:           {reason}")
                
            except Exception as e:
                logger.error(f"Analysis failed for {symbol}: {e}")
        
        print(f"\n{'='*80}")
        print("   ANALYSIS COMPLETE")
        print(f"{'='*80}\n")
        
        return 0
    
    # Trading mode
    logger.info(f"Starting trading loop...")
    
    try:
        executor.run_trading_loop(
            symbols=symbols,
            interval_seconds=args.interval,
            dry_run=dry_run
        )
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Trading loop error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    logger.info("Bot shutdown complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
