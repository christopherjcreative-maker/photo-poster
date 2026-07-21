# Photo poster

Dumps photos into a folder, posts one a day (with an AI-generated caption) to
Instagram, X, Facebook, or whatever else you connect through Buffer.

## How it works

```
You drop images into inbox/
        ↓
GitHub Actions runs once a day
        ↓
Script picks the OLDEST image in inbox/
        ↓
Sends it to Claude → gets a caption
        ↓
Posts image + caption to Buffer (which posts it to your real channels)
        ↓
Moves the image from inbox/ → posted/ and commits that change
```

**Important:** this repo needs to be **public**. Buffer requires a publicly
reachable URL for each image (Google Drive and private repos don't work —
Buffer can't retrieve files that require sign-in). The script builds that URL
from `raw.githubusercontent.com`, which only works for public repos. If you'd
rather keep your repo private, see "Alternative: private repo" at the bottom.

## One-time setup

### 1. Create the repo
Push this folder to a new **public** GitHub repository.

### 2. Get an Anthropic API key
Create one at [console.anthropic.com](https://console.anthropic.com) →
Settings → API Keys. This is billed separately from your claude.ai
subscription (pay-per-use, and captioning a photo costs a fraction of a cent).

### 3. Set up Buffer
1. Create a free account at [buffer.com](https://buffer.com).
2. Connect the channels you want to post to (Instagram, X, Facebook — the
   free plan supports up to 3 channels).
3. Go to **Settings → API → Personal Keys → + New Key**. Give it all
   permissions, set an expiration (1 year is easiest so you're not
   renewing constantly), and copy the key.
4. Get each channel's ID: in Buffer, go to **Settings → API**, and use the
   "Get Channels" example query in their [API reference](https://developers.buffer.com/reference.html)
   with your new key to list your channels and their IDs. Copy the IDs for
   the channels you want this bot to post to.

### 4. Add secrets to GitHub
In your repo: **Settings → Secrets and variables → Actions → New repository secret**.
Add three secrets:

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `BUFFER_API_KEY` | your Buffer personal API key |
| `BUFFER_CHANNEL_IDS` | comma-separated channel IDs, e.g. `abc123,def456` |

### 5. Drop in some photos
Add image files (`.jpg`, `.jpeg`, `.png`, `.webp`) to `inbox/` and push.
The bot posts the **oldest** file in that folder each run, so name/date them
however you want them ordered (e.g. `001-sunset.jpg`, `002-market.jpg`, or
just rely on file modification order).

### 6. Test it
Go to the **Actions** tab in your repo → "Daily photo post" → **Run workflow**
to trigger it manually and confirm everything works before waiting for the
schedule.

## Changing the schedule

Edit the `cron` line in `.github/workflows/post.yml`. It's currently
`0 15 * * *` (once a day, 15:00 UTC). [crontab.guru](https://crontab.guru) is
handy for building other schedules.

## Alternative: private repo

If you don't want a public repo, swap the image hosting step: instead of
building a `raw.githubusercontent.com` URL, upload the image to
[Cloudinary](https://cloudinary.com) (free tier) at the start of
`post_photo.py` and use the URL it gives back. Buffer's docs explicitly call
out Cloudinary and Cloudflare R2 as working options. Happy to wire this up if
you'd rather go this route.
