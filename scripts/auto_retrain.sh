#!/bin/bash
# Auto-Retrain ML Models
# Runs weekly to keep models fresh with latest market data

echo "=================================================="
echo "  AI Crypto Bot - Auto ML Retraining"
echo "=================================================="
echo "Started at: $(date)"
echo ""

# Change to bot directory
cd /opt/aicryptobot || exit 1

# Activate virtual environment
source venv/bin/activate || exit 1

# Run training script
echo "Starting model training..."
python scripts/train_ensemble.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Training completed successfully!"
    echo "Restarting bot with new models..."
    
    # Restart bot service
    systemctl restart aibot-dashboard
    
    echo "✅ Bot restarted"
    echo "=================================================="
    echo "Completed at: $(date)"
    exit 0
else
    echo ""
    echo "❌ Training failed! Check logs for details."
    echo "Bot NOT restarted (using old models)"
    echo "=================================================="
    echo "Failed at: $(date)"
    exit 1
fi
