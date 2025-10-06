# OpenAI API Credits Guide

## 🎯 Quick Summary

You need to add credits to your OpenAI account to use the API for generating embeddings. Here's how to do it step-by-step.

## 📍 Step-by-Step Instructions

### Step 1: Access Your OpenAI Account
1. **Go to**: https://platform.openai.com/
2. **Sign in** with your OpenAI account credentials
3. **Click on your profile** (top-right corner)

### Step 2: Navigate to Billing
1. Click on **"Settings"** or **"Billing"** from the dropdown menu
2. Or go directly to: https://platform.openai.com/settings/organization/billing/overview

### Step 3: Add Payment Method
1. Look for **"Payment methods"** section
2. Click **"Add payment method"**
3. Enter your **credit/debit card** details:
   - Card number
   - Expiration date
   - CVV/CVC code
   - Billing address
4. Click **"Save"** or **"Add card"**

### Step 4: Add Credits
You have two options:

#### Option A: Manual Credit Purchase (Recommended for Testing)
1. Go to **"Billing"** → **"Add credits"**
2. Choose an amount:
   - **$5** - Good for testing (covers ~5,000-10,000 messages)
   - **$10** - Recommended for your full ingestion (~13,719 messages)
   - **$20+** - If you plan to use the API regularly
3. Click **"Continue"** or **"Purchase"**
4. Confirm the payment

#### Option B: Auto-Recharge (Recommended for Regular Use)
1. Go to **"Billing"** → **"Auto-recharge"**
2. Enable auto-recharge
3. Set:
   - **Recharge amount**: $10-$20
   - **Trigger threshold**: When balance drops below $5
4. This ensures you never run out of credits

### Step 5: Verify Credits
1. Go back to **Billing Overview**
2. Check that your **"Credit balance"** shows the amount you added
3. Wait 1-2 minutes for the system to update

## 💰 Cost Breakdown for Your Project

### Your Sparky Ingestion
- **Total messages**: ~13,719
- **Embedding model**: `text-embedding-3-small`
- **Cost per 1M tokens**: $0.020
- **Average tokens per message**: ~100-200 tokens
- **Estimated total tokens**: ~1.4-2.7M tokens
- **Estimated cost**: **$0.03-$0.05** (very cheap!)

### Why You Might Need More
The actual cost is very low, but you might need credits for:
- **Rate limits**: Free tier has very low limits
- **Minimum purchase**: OpenAI typically requires minimum $5 purchase
- **Future use**: Additional API calls, testing, etc.

### Recommended Purchase
**$10** - This will:
- ✅ Cover your entire Sparky ingestion (200x over)
- ✅ Provide buffer for retries and errors
- ✅ Leave credits for future API usage
- ✅ Unlock higher rate limits

## 🔑 Important Notes

### API Keys vs Credits
- **API Key**: You already have this (in your `.env` file)
- **Credits**: Money in your OpenAI account to pay for API usage
- **Both are required**: Key authenticates you, credits pay for usage

### Billing Plans
OpenAI has different tiers:

1. **Free Tier** (Your current situation)
   - Very limited rate limits
   - Often causes 429 errors
   - Not suitable for batch processing

2. **Pay-as-you-go** (Recommended)
   - Add credits as needed
   - Higher rate limits
   - Only pay for what you use
   - **This is what you need**

3. **Prepaid Credits**
   - Buy credits in advance
   - No monthly commitment
   - Credits don't expire (for 1 year)

### Rate Limits After Adding Credits
Once you add credits, your rate limits increase:
- **Free tier**: 3 requests/minute, 200 requests/day
- **Paid tier 1**: 500 requests/minute, 10,000 requests/day
- **Higher tiers**: Even more capacity

## 🚨 Troubleshooting

### "Continue" Button Greyed Out
This is a common issue. Try:
1. **Clear browser cache** and cookies
2. **Try a different browser** (Chrome, Firefox, Edge)
3. **Disable browser extensions** (especially ad blockers)
4. **Use incognito/private mode**
5. **Try on mobile device** if desktop doesn't work

### Payment Method Not Accepted
- **Check card details** are correct
- **Ensure international payments** are enabled on your card
- **Try a different card** (Visa/Mastercard work best)
- **Contact your bank** - they might be blocking the transaction
- **Try PayPal** if available in your region

### Credits Not Showing Up
- **Wait 2-5 minutes** for the system to update
- **Refresh the page** (hard refresh: Ctrl+F5)
- **Check email** for payment confirmation
- **Contact OpenAI support** if still not showing after 10 minutes

### Still Getting 429 Errors After Adding Credits
- **Wait 5-10 minutes** for rate limits to update
- **Check billing overview** to confirm credits are there
- **Verify your API key** is correct in `.env` file
- **Try a test API call** to confirm it's working

## 🔗 Important Links

### OpenAI Platform Links
- **Billing Overview**: https://platform.openai.com/settings/organization/billing/overview
- **Payment Methods**: https://platform.openai.com/settings/organization/billing/payment-methods
- **Usage Dashboard**: https://platform.openai.com/usage
- **API Keys**: https://platform.openai.com/api-keys
- **Pricing Info**: https://platform.openai.com/docs/pricing

### Support
- **Help Center**: https://help.openai.com/
- **Community Forum**: https://community.openai.com/
- **Status Page**: https://status.openai.com/

## ✅ After Adding Credits

Once you've successfully added credits:

### 1. Verify Credits
```bash
# Check your billing page shows positive balance
# URL: https://platform.openai.com/settings/organization/billing/overview
```

### 2. Test API Access
```bash
# Run a quick test
C:\Python313\python.exe test_connectivity.py
```

### 3. Resume Ingestion
```bash
# Start the ingestion process
C:\Python313\python.exe ingest_sparky_export.py chat-history
```

### 4. Monitor Progress
```bash
# In another terminal, check progress
C:\Python313\python.exe check_ingestion_progress.py --estimate-time
```

## 📊 Expected Timeline

After adding credits:
- **Setup time**: 5-10 minutes (adding credits, verification)
- **Ingestion time**: 8-12 hours (can run in sessions)
- **Total cost**: ~$0.03-$0.10 (very affordable!)

## 💡 Pro Tips

### Save Money
1. **Use the cheapest embedding model**: `text-embedding-3-small` (already configured)
2. **Filter content wisely**: The script already filters out low-value content
3. **Monitor usage**: Check the usage dashboard regularly

### Avoid Issues
1. **Add more than you need**: $10 is safer than $5
2. **Enable auto-recharge**: Prevents interruptions
3. **Keep payment method updated**: Expired cards cause issues
4. **Monitor rate limits**: Don't run multiple scripts simultaneously

### Best Practices
1. **Start with $10**: Good balance of cost and capacity
2. **Run in sessions**: 1-2 hours at a time, resume as needed
3. **Check progress regularly**: Use the progress checker
4. **Keep the resume file**: Don't delete `sparky_ingestion_progress.json` until complete

## 🎉 Ready to Go!

Once you've added credits:
1. ✅ Your API quota will be restored
2. ✅ Rate limits will be increased
3. ✅ The ingestion script will work smoothly
4. ✅ Resume mechanism will track all progress

The entire process should be smooth and affordable. Your 544 conversations will be safely ingested into your context management system! 🚀

---

**Need Help?** If you encounter any issues:
1. Check the troubleshooting section above
2. Visit the OpenAI community forum
3. Contact OpenAI support through the help center
4. Check the status page for any ongoing issues
