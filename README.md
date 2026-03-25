# Bar Ordering System

A Django-based bar/restaurant ordering system with waiter ordering, live staff order monitoring, shift management, and realtime updates via WebSockets.

---

## Current Phase

Core ordering and shift workflow is implemented:

- product management
- product categories with active/inactive control
- waiter login
- waiter mobile ordering page with cart
- pending live orders screen
- finish/cancel order actions
- realtime live updates with WebSockets
- shift open/close flow
- multiple same-day shifts
- shift summary page
- per-shift waiter totals and overall totals
- recent finished orders section
- live category ON/OFF controls from staff page
- waiter page category hide/show updates live without refresh
- collapsible waiter categories
- improved live operations layout

---

## Tech Stack

- Django
- Django Channels
- Redis
- Daphne
- PostgreSQL for deployment
- SQLite for local development if needed

---

## Core Flow

1. Waiter logs in and opens the waiter page.
2. Waiter selects products and submits an order.
3. Django creates an `Order` and related `OrderItem` records.
4. Django attaches the order to the currently open shift.
5. Django broadcasts events through Redis using Channels.
6. Staff users connected to the live page receive updates through WebSocket.
7. Waiter pages also receive shift/category updates through WebSocket.
8. Live pages and waiter pages update instantly without page refresh.

One-line summary:

`Waiter -> Django -> Redis -> WebSocket -> Live staff/waiter pages`

---

## Apps

- `products` — product catalog and product categories
- `orders` — ordering flow, shifts, live screen, realtime behavior

---

## Main Models

### ProductCategory
Stores product groupings used on the waiter page.

Fields:
- `name`
- `slug`
- `is_active`
- `sort_order`
- `show_on_live_controls`

Notes:
- categories can be turned on/off
- inactive categories are hidden from waiter ordering
- category changes can be pushed live to connected waiter pages
- `show_on_live_controls` determines whether a category appears in the live-page control toolbar

### Product
Stores drinks/items available for ordering.

Fields:
- `name`
- `category` (`ForeignKey` to `ProductCategory`)
- `price`
- `is_active`

### Shift
Stores one operating shift for a business date.

Fields:
- `business_date`
- `sequence_number`
- `status` (`open`, `closed`)
- `opened_at` / `closed_at`
- `opened_by` / `closed_by`

Notes:
- multiple shifts can exist on the same day
- only one shift can be open at a time

### Order
Stores one submitted order.

Fields:
- `waiter`
- `shift`
- `table_number`
- `note`
- `status` (`pending`, `finished`, `canceled`)
- timestamps
- `total`

### OrderItem
Stores items inside an order.

Fields:
- `order`
- `product`
- `quantity`
- `unit_price`
- `subtotal`

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

### WebSocket access
- authenticated users can connect
- staff users join the live staff group
- waiter/staff users can receive shift updates
- waiter/staff users can receive category state updates

---

## Important Realtime Setup

### Required packages
- `channels`
- `channels_redis`
- `daphne`

### Required services
- Redis must be running

### Important note
This project uses WebSockets for realtime updates.
Because of that, it should run through the ASGI app.

The socket route is:

`/ws/orders/live/`

---

## WebSocket Groups

Current split group design:

- `live_orders_staff` — staff live order events
- `shift_updates` — shift status updates and category state updates

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

### Local binary
```bash
redis-server
```

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
If `python manage.py runserver` works correctly in your environment after installing the needed ASGI/realtime packages, you may use it.
If WebSocket routes fail or return 404, use Daphne directly.

For this project, Daphne is the safest command to remember.

---

## Static Files

Current static setup:

```python
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
```

During development, `config/urls.py` should include static file serving in `DEBUG`.

---

## Local URLs

- Home: `http://127.0.0.1:8000/`
- Login: `http://127.0.0.1:8000/accounts/login/`
- Waiter page: `http://127.0.0.1:8000/waiter/`
- Live orders page: `http://127.0.0.1:8000/live/`
- Shift summary page: `http://127.0.0.1:8000/shift-summary/`
- Admin: `http://127.0.0.1:8000/admin/`

---

## Current Features Implemented

- Django project initialized with Git
- `products` and `orders` apps created
- `ProductCategory` model and admin
- `Product` model and admin
- `Order`, `OrderItem`, and `Shift` workflow implemented
- automatic price fill from product to order item
- automatic subtotal calculation
- automatic order total recalculation
- login/logout flow
- protected waiter/staff pages
- waiter ordering page UI with cart
- submit order endpoint
- live orders page grouped by waiter
- finish and cancel actions
- recent finished orders section on live page
- realtime updates for live orders page with Channels + Redis + Daphne
- shift open/close actions
- multiple same-day shift support
- shift assignment to orders
- per-shift waiter summaries and overall totals
- category ON/OFF control from live page
- waiter page filters products by:
  - product active
  - category active
- backend submit also enforces active category
- waiter page category visibility updates live without refresh
- cart cleanup when a category is turned off live
- waiter categories can be collapsed
- live page category controls can be filtered with `show_on_live_controls`

---

## Realtime Architecture Notes

### Files involved
- `config/asgi.py`
- `orders/routing.py`
- `orders/consumers.py`
- `orders/utils.py`
- `orders/views.py`
- `templates/orders/live_orders_page.html`
- `templates/orders/waiter_order_page.html`

### Broadcast flow
- order creation calls `broadcast_order_event(...)`
- finish/cancel actions also call `broadcast_order_event(...)`
- shift open/close calls `broadcast_shift_event(...)`
- category state changes call `broadcast_category_event(...)`

### Current event types
- `order_created`
- `order_updated`
- `shift_updated`
- `category_updated`

### Current behavior
- staff live pages update instantly for new/finished/canceled orders
- waiter pages react to shift open/close instantly
- waiter pages react to category enable/disable instantly
- categories that become active can appear live without refresh

---

## Important Business Rules

- only active products appear on waiter page
- only products from active categories appear on waiter page
- inactive categories are blocked server-side during order submit
- orders can only be submitted when there is an open shift
- orders are linked to the currently open shift
- live orders page is restricted to staff users
- realtime depends on Redis being available
- realtime works when the ASGI app is served correctly

---

## Production Notes

For deployment, the recommended stack is:

- Ubuntu server
- PostgreSQL
- Redis
- Daphne
- Nginx

Minimum deployment checklist:
- `DEBUG = False`
- `ALLOWED_HOSTS` configured
- secret key in environment variables
- PostgreSQL configured
- Redis running
- `collectstatic` completed
- service restarts documented
- automated backups enabled

---

## Testing Checklist

### Basic startup
```bash
python manage.py check
python manage.py migrate
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

### Realtime order flow
- log in as waiter
- submit an order
- verify it appears instantly on live page
- finish/cancel it
- verify live page updates instantly

### Shift flow
- open a shift
- verify waiter page shows active shift
- close the shift
- verify waiter page disables ordering

### Category flow
- turn a category off on live page
- verify waiter page hides it instantly
- verify cart removes those products if present
- turn the category on again
- verify waiter page shows it instantly without refresh

---

## Documentation

Detailed project architecture and flow documentation is available in:

- `PROJECT_EXPLANATION.md`

---

## Suggested Next Improvements

- automated PostgreSQL backups
- operational monitoring for Daphne / Redis / PostgreSQL / Nginx
- transaction wrapping and locking around sensitive state transitions
- audit trail for order/shift actions
- deployment/restart script
- waiter-only role restrictions if needed
- printer / receipt integration
- reporting export
