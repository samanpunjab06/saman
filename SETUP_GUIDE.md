# Setup guide (about 30 minutes, no coding knowledge needed)

You do this once. Nothing here uses real money.

## Step 1: Alpaca paper account
1. Go to https://app.alpaca.markets and sign up (free).
2. Switch to **Paper Trading** (top-left menu). It starts with $100,000 of fake money. Set it to $10,000 via the account's reset option.
3. Click **Generate API Keys** and copy both the Key and the Secret somewhere private (Notes app). **Never paste them in chat or on GitHub.**

## Step 2: Install Python
**Windows:** go to https://www.python.org/downloads, download the latest Python, run it, and **tick "Add Python to PATH"** before clicking Install.
**Mac:** go to https://www.python.org/downloads and install the latest version.

## Step 3: Install Git
Download from https://git-scm.com/downloads and install with the default options.

## Step 4: Get the bot
Open **Command Prompt** (Windows: press the Windows key, type `cmd`) or **Terminal** (Mac). Type these one at a time, pressing Enter after each:
```
git clone https://github.com/samanpunjab06/saman
cd saman
pip install -r requirements.txt
```
(On Mac, if `pip` isn't found, use `pip3`, and `python3` instead of `python` below.)

## Step 5: Test it on real old prices
```
python run_compare.py --download
```
It prints a table. **Copy the table and paste it into the chat.** That tells us which strategy looks best.

## Step 6 (later, together)
Put in your Alpaca keys and do a "dry run" that shows what the bot would buy, without buying anything.
