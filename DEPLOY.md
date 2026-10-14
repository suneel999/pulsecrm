# Make Pulse Desk live

Staff URL after DNS: **https://desk.thepulseheart.com/login**

## Important: which EC2?

Ports **80** and **443** can belong to only one Caddy/nginx stack.

- **Best:** new small Ubuntu EC2 only for the desk (same as World Heart Day run setup).
- **Or** put it on the existing **event.thepulseheart.com** EC2 and add `desk.thepulseheart.com` to that Caddyfile (both sites on one server).
- Do **not** put this on the Hi Pulse **api.thepulseheart.com** box unless that server’s reverse proxy is already set up for a second hostname.

## 1. Hostinger DNS

In DNS for `thepulseheart.com`:

| Type | Name | Value |
|------|------|--------|
| A | `desk` | **public IP of the desk EC2** |

Wait 5–30 minutes. Security group on that EC2 must allow **22, 80, 443**.

## 2. On the EC2

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo git clone https://github.com/suneel999/pulse_desk.git /opt/pulse-desk
cd /opt/pulse-desk
sudo cp .env.example .env
sudo nano .env
```

Set at least:

```
FLASK_SECRET=long-random-text
ADMIN_USER=pulse
ADMIN_PASS=choose-a-strong-password
CRM_INGEST_KEY=another-long-random-secret
PUBLIC_URL=https://desk.thepulseheart.com
APP_API_URL=https://api.thepulseheart.com
APP_API_EMAIL=reception@thepulseheart.com
APP_API_PASSWORD=Reception@123
```

Then:

```bash
sudo docker compose up -d --build
sudo docker compose ps
curl -s https://desk.thepulseheart.com/health
```

Login: https://desk.thepulseheart.com/login  
Username / password = `ADMIN_USER` / `ADMIN_PASS` from `.env`.

## 3. Wire website forms (Hostinger)

Edit `crm-endpoint.php` on Hostinger:

```php
return [
    'url' => 'https://desk.thepulseheart.com/api/ingest',
    'secret' => 'the-same-CRM_INGEST_KEY-as-on-the-server',
];
```

Also upload the updated site files (WHD removed + preferred time on forms):

- `index.html`
- `contact.html`
- `about-us.html`
- `sendemail.php`
- `crm-endpoint.php`
- `.htaccess`
- `run.html` (redirect stub)
- `world-heart-day-angiogram.html` (redirect stub)
- `sitemap.xml`
- `llms.txt`
- `Js/pulse-tracking.js`
- `cardiac-hospital-hyderabad/index.html`

Email to `appointments@thepulseheart.com` keeps working. Desk gets a copy via ingest.

## 4. Later updates

```bash
cd /opt/pulse-desk
sudo git pull
sudo docker compose up -d --build
```

## Quick check

1. Open desk → **Sync Hi Pulse App** → App rows appear.  
2. Submit a test form on thepulseheart.com → email arrives **and** desk shows a **Web** row.  
3. Change status / notes on desk → saves.
