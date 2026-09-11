# Manual acceptance test

Start the stack with `docker compose up --build -d`, then open `http://localhost:5173`.

| Stage | Account | Action | Expected result |
| --- | --- | --- | --- |
| Farmer | `9876543210` / `farmer123` | Sign in, open **Book Slot**, choose crop, quantity, mandi, date and time, then confirm. | A token and QR code are generated; the booking appears in the farmer timeline. |
| Mandi staff | `9876543220` / `staff123` | Sign in, open **Gate Entry**, enter the token, then mark entry. Open **Queue Manager** and call the next farmer. | The token is accepted and the queue advances. |
| Mandi staff | same | Open the called farmer's transaction; enter quality and weighment values. | Net quantity is calculated and saved. Invalid tare weight is rejected. |
| Mandi officer | `9876543230` / `officer123` | Open the same transaction, confirm procurement, and initiate payment. | Procurement is confirmed and mock PFMS returns a PAID status and UTR. |
| Farmer | same | Refresh the dashboard and notifications. | The timeline shows quality, weighment, confirmation and payment. |
| Government admin | `9876543240` / `admin123` | Open the government dashboard. | Procurement totals, drill-down data and anomaly flags render. |
| CSC operator | `9876543250` / `csc123` | Sign in and use the farmer booking flow. | CSC role can assist with booking and grievances. |

## API health checks

Open `http://localhost:8000/health` and verify an `ok` response. Interactive API documentation is at `http://localhost:8000/docs`.

## Resetting the demo

`docker compose down -v` removes the local demo database. Start the stack again to recreate and reseed it.
