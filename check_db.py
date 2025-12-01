"""
Проверка записей в базе данных TradeLogger
"""

from src.utils.trade_logger import TradeLogger
import pandas as pd
import json

def main():
    logger = TradeLogger()
    
    print("\n" + "="*80)
    print("   TRADE DATABASE RECORDS")
    print("="*80)
    
    # 1. Все сделки
    trades_df = logger.get_trades(limit=10)
    print(f"\n[TRADES] Total: {len(trades_df)}")
    
    if len(trades_df) > 0:
        for _, trade in trades_df.iterrows():
            status = "CLOSED" if pd.notna(trade['exit_price']) else "OPEN"
            pnl_str = f"${trade['pnl']:+.2f} ({trade['pnl_pct']:+.2f}%)" if pd.notna(trade['pnl']) else "N/A"
            print(f"  ID={trade['id']} | {trade['symbol']} {trade['side']} | "
                  f"Entry: ${trade['entry_price']:.2f} | {status} | PnL: {pnl_str}")
    else:
        print("  No trades found")
    
    # 2. Только закрытые сделки
    closed_trades_df = logger.get_trades(status='closed', limit=10)
    print(f"\n[CLOSED TRADES] Total: {len(closed_trades_df)}")
    
    if len(closed_trades_df) > 0:
        for _, trade in closed_trades_df.iterrows():
            print(f"  ID={trade['id']} | {trade['symbol']} {trade['side']} | "
                  f"Entry: ${trade['entry_price']:.2f} | Exit: ${trade['exit_price']:.2f} | "
                  f"PnL: ${trade['pnl']:+.2f} ({trade['pnl_pct']:+.2f}%)")
    else:
        print("  No closed trades found")
    
    # 3. Последние события
    events_df = logger.get_events(limit=5)
    print(f"\n[EVENTS] Last 5:")
    
    if len(events_df) > 0:
        for _, event in events_df.iterrows():
            print(f"  [{event['event_type']}] {event['severity']}: {event['message']}")
    else:
        print("  No events found")
    
    # 4. Анализы рынка  
    conn = logger.db_path
    import sqlite3
    db_conn = sqlite3.connect(conn)
    cursor = db_conn.cursor()
    
    cursor.execute("SELECT * FROM analysis ORDER BY timestamp DESC LIMIT 3")
    analyses = cursor.fetchall()
    
    print(f"\n[MARKET ANALYSIS] Last 3:")
    if analyses:
        for analysis in analyses:
            # id, timestamp, symbol, price, atr, rsi, ml_signal, ml_confidence, sentiment_score, sentiment_label, decision, reason
            print(f"  {analysis[2]} @ ${analysis[3]:.2f} | "
                  f"ML: {analysis[6]} ({analysis[7]:.1f}%) | "
                  f"Sentiment: {analysis[9]} ({analysis[8]:.3f})")
    else:
        print("  No analysis records found")
    
    db_conn.close()
    
    # 5. Метрики производительности
    summary = logger.get_performance_summary()
    print(f"\n[PERFORMANCE SUMMARY]")
    print(f"  Total Trades:     {summary['total_trades']}")
    print(f"  Winning Trades:   {summary['winning_trades']}")
    print(f"  Losing Trades:    {summary['losing_trades']}")
    print(f"  Win Rate:         {summary['win_rate']:.1f}%")
    print(f"  Total PnL:        ${summary['total_pnl']:+.2f}")
    print(f"  Avg Win:          ${summary['avg_win']:.2f}")
    print(f"  Avg Loss:         ${summary['avg_loss']:.2f}")
    print(f"  Profit Factor:    {summary['profit_factor']:.2f}")
    print(f"  Best Trade:       ${summary['max_win']:+.2f}")
    print(f"  Worst Trade:      ${summary['max_loss']:+.2f}")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
