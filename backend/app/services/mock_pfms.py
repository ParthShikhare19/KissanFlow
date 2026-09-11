"""Mock PFMS (Public Financial Management System) integration service."""
import asyncio
import uuid
import random
import string
from datetime import datetime, timezone


def _random_ref(prefix: str, length: int = 12) -> str:
    return prefix + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class MockPFMSService:
    """
    Simulates PFMS payment processing with realistic delays.
    All results are mocked — no real API calls.
    """

    async def initiate_payment(
        self,
        farmer_id: uuid.UUID,
        amount: float,
        bank_account: str | None,
        bank_ifsc: str | None,
    ) -> dict:
        """Simulate payment initiation — 2 second delay."""
        await asyncio.sleep(2)
        pfms_ref = _random_ref("PFMS-", 10)
        return {
            "success": True,
            "pfms_ref": pfms_ref,
            "status": "INITIATED",
            "message": f"Payment of ₹{amount:,.2f} initiated via PFMS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def confirm_payment(self, pfms_ref: str) -> dict:
        """Simulate payment confirmation — 3 second delay."""
        await asyncio.sleep(3)
        utr = _random_ref("UTR", 18)
        return {
            "success": True,
            "pfms_ref": pfms_ref,
            "utr": utr,
            "status": "PAID",
            "message": "Payment successfully credited to farmer's account",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class MockAadhaarService:
    """Simulates Aadhaar number verification — 1.5 second delay."""

    async def verify(self, aadhaar_number: str) -> dict:
        await asyncio.sleep(1.5)
        if len(aadhaar_number.replace(" ", "")) != 12:
            return {"verified": False, "error": "Invalid Aadhaar format"}
        return {
            "verified": True,
            "aadhaar_suffix": aadhaar_number[-4:],
            "message": "Aadhaar verified successfully",
        }


class MockSMSService:
    """Simulates SMS sending — logs to console and stores in Notification table."""

    async def send(self, mobile: str, message: str) -> dict:
        await asyncio.sleep(0.1)
        print(f"[SMS] To: +91{mobile} | {message}")
        return {"sent": True, "mobile": mobile}
