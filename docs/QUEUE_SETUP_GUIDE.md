# Queue: setup guide

This guide takes you from "code on my computer" to "anyone can message Queue on WhatsApp".
There are four steps, and each one is finished before the next starts.

| Step | What you'll have at the end | Accounts you need |
|---|---|---|
| 1. Save leads in Supabase | Test chats on your computer save real leads to an online database | Supabase (free) |
| 2. Bot server + Meta test number | You message a test WhatsApp number from your phone and Queue replies | Meta developer (free), GitHub (free), Render (free to start) |
| 3. Dashboard with login | The consultant sees and updates leads in a web page with a password | none new |
| 4. Go live | Any new user can message Queue's own WhatsApp number | Meta Business verification, a phone number |

## Rules for keys and passwords (read this first)

Several steps give you secret values: a database password, an access token, an app secret.

- Put them **only** in the `.env` file on your computer, and later in Render's "Environment" settings.
- **Never** paste them into this chat, an email or a screenshot. If one leaks, reset it on the website it came from.
- `.env` is listed in `.gitignore`, so it is never uploaded to GitHub.

---

## Step 1: Save leads in Supabase

**What Supabase is:** an online PostgreSQL database with a website for looking at your tables. Queue stores conversations and leads there, so nothing is lost when the server restarts.

### 1a. Create the project (about 5 minutes)

1. Go to **supabase.com** and sign up (signing in with GitHub is easiest).
2. Click **New project**.
   - Name: `queue`
   - Database password: click **Generate a password**, then save it in a password manager. You'll need it in 1c.
   - Region: pick the one closest to your clients (for Canada, *Canada (Central)*).
3. Wait a minute or two while it says "Setting up project".

### 1b. Create the tables

1. In the left menu, open **SQL Editor**, then **New query**.
2. Open `sql/schema.sql` from the Queue folder in a text editor, copy everything, and paste it in.
3. Click **Run**. You should see "Success. No rows returned".
4. Open **Table Editor** in the left menu. You should see six tables: `businesses`, `services`, `conversation_sessions`, `leads`, `lead_audit_log` and `message_events`.

### 1c. Connect your computer to it

1. In Supabase, click **Connect** at the top of the page.
2. Choose **Transaction pooler** and copy the URI. It looks like
   `postgresql://postgres.abcd:[YOUR-PASSWORD]@aws-0-ca-central-1.pooler.supabase.com:6543/postgres`.
3. In the Queue folder, copy `.env.example` to a new file called `.env`.
4. In `.env`, set `DATABASE_URL=` to that URI, replacing `[YOUR-PASSWORD]` (brackets included) with your database password.

### 1d. Try it

In a terminal, inside the Queue folder:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.simulate
```

The first line should say **"Saving to Supabase."** Chat as a client would (Hi, 1, yes, your name, skip, yes).
Then, in Supabase's **Table Editor**, open `leads`: your test lead should be there.

**Step 1 is done when** a test chat appears in the `leads` table.

---

## Step 2: Bot server with Meta's free test number

**What happens here:** Meta gives you a free test WhatsApp number. When someone messages it, Meta sends the message to *your server* over the internet (a "webhook"). Queue works out the reply and sends it back through Meta. For Meta to reach your server, the server has to be online, so we put it on **Render**.

**Why Render:** you connect a GitHub repository, click a few buttons, and it gives you a public `https://…onrender.com` address with HTTPS already set up. No server administration.
The free plan "sleeps" after about 15 minutes without traffic, so the first message after a quiet spell takes about a minute to answer. That's fine for testing. For going live, use the paid Starter plan (about US$7 a month; check Render's pricing page) so replies are always quick.

### 2a. GitHub (so Render can get the code)

1. Create a free account at **github.com** if you don't have one.
2. Create a new **private** repository called `queue`. Leave it empty (no README).
3. Connect GitHub to Claude: https://claude.ai/connect-github. Then tell me the repository name, and I'll upload the code once you say go.

### 2b. Meta developer app and test number

1. Go to **developers.facebook.com**, log in with Facebook, and register as a developer.
2. **My Apps → Create App**. Choose the use case **"Connect with customers through WhatsApp"**, type *Business*, and name it `Queue`.
3. In the app, open **WhatsApp → API Setup**. Meta shows:
   - a **test phone number** (free, can message up to 5 numbers you add)
   - a **Phone number ID**
   - a **temporary access token** (lasts 24 hours)
4. Under "To", **add your own WhatsApp number** as a recipient and confirm the code WhatsApp sends you.
5. In **App settings → Basic**, click **Show** next to *App secret*.

Put these in your `.env` (never in chat):

```
WHATSAPP_ACCESS_TOKEN=the temporary access token
WHATSAPP_PHONE_NUMBER_ID=the Phone number ID
WHATSAPP_VERIFY_TOKEN=any long random words you make up
META_APP_SECRET=the App secret
```

### 2c. Put Queue online (I'll give exact click-by-click steps when we get here)

1. On **render.com**, sign up with GitHub and create a **Web Service** from the `queue` repository.
2. Copy the values from your `.env` into Render's **Environment** page.
3. Render gives you an address like `https://queue-xxxx.onrender.com`. Opening `/health` there should show `{"status":"ok"}`.

### 2d. Tell Meta where Queue lives

1. In Meta: **WhatsApp → Configuration → Webhook → Edit**.
   - Callback URL: `https://queue-xxxx.onrender.com/webhooks/whatsapp`
   - Verify token: the same `WHATSAPP_VERIFY_TOKEN` you chose
2. Click **Verify and save**, then **subscribe** to the `messages` field.
3. From your phone, send **Hi** to the test number. Queue should reply with the welcome menu.

**Step 2 is done when** you can complete a full enquiry from your phone and the lead appears in Supabase.

---

## Step 3: Dashboard with login

A small password-protected web page where the consultant sees leads, changes their status (New, Contacted…) and adds private notes. It runs on Render next to the bot. I'll build it once Step 2 works, and you'll only need to choose the login email(s).

---

## Step 4: Go live with Queue's own number

This is where any new user can start a WhatsApp chat with Queue. Most of it is Meta paperwork, and it can take a few days, so you can start it during Step 2 or 3.

1. **A phone number** that is *not* already registered on WhatsApp (including WhatsApp Business). A new SIM, or a landline that can receive a call or SMS for the code, both work.
2. **Meta Business verification:** in Meta Business Settings, verify your business (legal name, address, website or documents).
3. **Display name:** request "Queue" (or the consultant's business name). Meta reviews it against their naming rules, and the name should match your business or website.
4. **Permanent access token:** the 24-hour test token is replaced by a "System User" token. I'll walk you through it.
5. **Payment method:** add one in Meta. Under Meta's current pricing, replies to a customer within 24 hours of their message are generally free, but check Meta's WhatsApp pricing page for your country.
6. **Before real clients:** the consultant approves the menu and checklists, and you confirm the privacy wording and how long data is kept.

Once live, share the number as a link: `https://wa.me/<number without + or spaces>`, or as a QR code. Anyone who taps it starts a new chat with Queue.
