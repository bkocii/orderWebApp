# Bar Ordering System

A Django-based web app for bar/restaurant order flow.

## Current Phase
Phase 1 in progress:
- product management
- waiter login
- waiter mobile ordering page
- pending live orders screen
- finish/cancel order actions
- real-time live updates with WebSockets

---

## Tech Stack
- Django
- Django Channels
- Redis
- Daphne
- SQLite for local development

---

## Core Flow
1. Waiter logs in and opens the waiter page.
2. Waiter selects drinks/products and submits an order.
3. Django creates an `Order` and related `OrderItem` records.
4. Django broadcasts an event through Redis using Channels.
5. Staff users connected to the live orders page receive the event through WebSocket.
6. The live orders screen updates instantly without page refresh.

One-line summary:

`Waiter -> Django -> Redis -> WebSocket -> Live page`

---

## Apps
- `products` — menu/product catalog
- `orders` — ordering, live screen, realtime flow

---

## Main Models
### Product
Stores drinks/items available for ordering.
- name
- category
- price
- is_active

### Order
Stores one submitted order.
- waiter
- table_number
- note
- status (`pending`, `finished`, `canceled`)
- timestamps
- total

### OrderItem
Stores items inside an order.
- order
- product
- quantity
- unit_price
- subtotal

Notes:
- `unit_price` is copied from product price automatically
- `subtotal` is calculated automatically
- `Order.total` is recalculated automatically

---

## Access Rules
### Waiter page
- authenticated users can access

### Live orders page
- staff users only (`is_staff=True`)
- WebSocket consumer also checks for authenticated staff users

---

## Important Realtime Setup
### Required packages
- `channels`
- `channels_redis`
- `daphne`

### Required services
- Redis must be running

### Important note
This project uses WebSockets for the live orders page.
Because of that, it must run through the ASGI app.

The live socket route is:

`/ws/orders/live/`

---

## Development Setup
### 1. Create and activate virtual environment
#### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run database migrations
```bash
python manage.py migrate
```

### 4. Create superuser
```bash
python manage.py createsuperuser
```

---

## Running Redis locally
### Docker option
```bash
docker run --rm -p 6379:6379 redis:7
```

Redis is used as the Channels channel layer backend.

---

## Running the project
### Preferred command for realtime development
```bash
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

### About `runserver`
This project includes realtime WebSocket functionality.
If `python manage.py runserver` works correctly in your environment after installing `daphne`, you may use it.
If WebSocket routes fail or return 404, use Daphne directly.

For this project, Daphne is the safest command to remember.

---

## Local URLs
- Home: `http://127.0.0.1:8000/`
- Login: `http://127.0.0.1:8000/accounts/login/`
- Waiter page: `http://127.0.0.1:8000/waiter/`
- Live orders page: `http://127.0.0.1:8000/live/`
- Admin: `http://127.0.0.1:8000/admin/`

---

## Current Features Implemented
- Django project initialized with Git
- `products` and `orders` apps created
- `Product` model and admin
- `Order` and `OrderItem` models and admin
- automatic price fill from product to order item
- automatic subtotal calculation
- automatic order total recalculation
- login/logout flow
- protected pages
- waiter ordering page UI with cart
- submit order endpoint
- live orders page showing pending orders
- finish and cancel actions
- realtime updates for live orders page with Channels + Redis + Daphne

---

## Realtime Architecture Notes
### Files involved
- `config/asgi.py`
- `orders/routing.py`
- `orders/consumers.py`
- `orders/utils.py`
- `orders/views.py`
- `templates/orders/live_orders_page.html`

### Broadcast flow
- order creation calls `broadcast_order_event(...)`
- finish/cancel actions also call `broadcast_order_event(...)`
- events are sent to Channels group: `live_orders`
- `LiveOrdersConsumer` subscribes staff browser sessions to that group
- frontend JavaScript listens for messages and updates the DOM

---

## Known Important Notes
- inactive products do not appear on waiter page
- inactive products are also blocked server-side during submit
- live orders page is restricted to staff users
- realtime depends on Redis being available
- realtime works when the ASGI app is served correctly

---

## Suggested Next Improvements
- WebSocket auto-reconnect
- sound alert for new orders
- visual highlight for newly arrived orders
- shift/day close functionality
- waiter totals
- daily reporting/export





