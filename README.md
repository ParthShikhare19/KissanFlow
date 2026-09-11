# KissanFlow

KissanFlow is an SIH demo for transparent agricultural procurement: farmers book slots, mandi staff manage gate entry and queues, officers verify procurement and payments, and administrators see operational analytics.

## Run the demo

1. Install and start Docker Desktop.
2. From this folder, run `start.bat`, or run `docker compose up --build -d`.
3. Open [http://localhost:5173](http://localhost:5173). The API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

The first start builds the images, creates PostgreSQL tables, and loads demo data. Later starts retain that data and do not duplicate it.

## Demo accounts

| Role | Mobile | Password |
| --- | --- | --- |
| Farmer | 9876543210 | farmer123 |
| Mandi staff | 9876543220 | staff123 |
| Mandi officer | 9876543230 | officer123 |
| Government admin | 9876543240 | admin123 |
| CSC operator | 9876543250 | csc123 |

## Stop or reset

Stop services with `docker compose down`. To remove demo data as well, use `docker compose down -v`; this permanently deletes the local PostgreSQL volume.

## Tests

The backend has an automated test suite (booking validation, slot capacity, gate-entry rules, ownership checks, IVR signature, payment cycle, notifications):

```
cd backend
pip install -r requirements.txt
python -m pytest tests/ -q
```

Demo data is deterministic: every fresh installation produces identical farmers, bookings, transactions, and timings, so demos and judging are reproducible.

## Production note

Before deployment, set strong `JWT_SECRET` and `JWT_REFRESH_SECRET` values in a root `.env` file and point `DATABASE_URL` to managed PostgreSQL. The included defaults are for local SIH demonstration only.

Schema columns added after the first release (`users.assigned_centre_id`, `transactions.quality_done_at/weighment_done_at/confirmed_at/payment_initiated_at/paid_at`) are created automatically at API startup and by the seed container, so existing volumes upgrade in place — no manual migration needed.
