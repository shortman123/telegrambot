#!/bin/bash

# Railway Deployment Helper Script
# This script helps set up the webhook for Railway deployment

echo "🚂 Railway Deployment Helper"
echo "============================"

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Install it first:"
    echo "   npm install -g @railway/cli"
    echo "   or visit: https://docs.railway.app/develop/cli"
    exit 1
fi

# Get Railway domain
echo "🔍 Getting Railway domain..."
DOMAIN=$(railway domain 2>/dev/null)

if [ -z "$DOMAIN" ]; then
    echo "❌ Could not get Railway domain. Make sure you're in the right project:"
    echo "   railway link"
    exit 1
fi

echo "✅ Railway domain: $DOMAIN"

# Get bot token from environment or ask user
if [ -z "$BOT_TOKEN" ]; then
    echo ""
    echo "🤖 Enter your bot token (or set BOT_TOKEN environment variable):"
    read -s BOT_TOKEN
fi

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Bot token is required!"
    exit 1
fi

# Set webhook
WEBHOOK_URL="$DOMAIN/webhook"
echo ""
echo "🔗 Setting webhook to: $WEBHOOK_URL"

curl -s "https://api.telegram.org/bot$BOT_TOKEN/setWebhook?url=$WEBHOOK_URL" | jq . || echo "Response: $(curl -s "https://api.telegram.org/bot$BOT_TOKEN/setWebhook?url=$WEBHOOK_URL")"

echo ""
echo "✅ Webhook setup complete!"
echo "🌐 Health check: $DOMAIN/health"
echo "📊 Bot info: https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"