import asyncio
import db

COMPLAINTS = [
    {
        "complaint_number": "SRV-1001",
        "caller_name": "Rahul Shah",
        "mobile": "9876543210",
        "city": "Mumbai",
        "area": "Andheri",
        "category": "Service & Repair",
        "description": "Car makes a loud grinding noise when braking. Issue started 3 days ago.",
        "timestamp": "2026-10-14T09:30:00",
        "status": "Pending",
        "cluster_alert": 0,
    },
    {
        "complaint_number": "TKT-2042",
        "caller_name": "Priya Mehta",
        "mobile": "9123456789",
        "city": "Pune",
        "area": "Kothrud",
        "category": "Warranty",
        "description": "Air conditioner stopped working within warranty period. Vehicle is 8 months old.",
        "timestamp": "2026-10-14T11:15:00",
        "status": "In Progress",
        "cluster_alert": 0,
    },
    {
        "complaint_number": "CAR-3301",
        "caller_name": "Aditya Verma",
        "mobile": "9988776655",
        "city": "Mumbai",
        "area": "Andheri",
        "category": "Vehicle Complaint",
        "description": "Engine warning light keeps coming on. Taken to service center twice but issue persists.",
        "timestamp": "2026-10-15T08:00:00",
        "status": "Pending",
        "cluster_alert": 1,
    },
    {
        "complaint_number": "SRV-1002",
        "caller_name": "Sneha Iyer",
        "mobile": "9001234567",
        "city": "Bangalore",
        "area": "Koramangala",
        "category": "Roadside Assistance",
        "description": "Vehicle broke down on highway. Need towing service urgently.",
        "timestamp": "2026-10-15T14:22:00",
        "status": "Resolved",
        "cluster_alert": 0,
    },
    {
        "complaint_number": "TKT-2043",
        "caller_name": "Vikram Nair",
        "mobile": "9765432100",
        "city": "Mumbai",
        "area": "Andheri",
        "category": "Vehicle Complaint",
        "description": "Power steering feels heavy and unresponsive at low speeds.",
        "timestamp": "2026-10-15T16:45:00",
        "status": "Pending",
        "cluster_alert": 1,
    },
    {
        "complaint_number": "CAR-3302",
        "caller_name": "Neha Gupta",
        "mobile": "9654321098",
        "city": "Delhi",
        "area": "Dwarka",
        "category": "Billing",
        "description": "Charged twice for the same service visit. Need refund of ₹4,200.",
        "timestamp": "2026-10-16T10:05:00",
        "status": "In Progress",
        "cluster_alert": 0,
    },
    {
        "complaint_number": "SRV-1003",
        "caller_name": "Arjun Sharma",
        "mobile": "9543210987",
        "city": "Mumbai",
        "area": "Andheri",
        "category": "Vehicle Complaint",
        "description": "Rear suspension feels very bumpy. Three other cars from same batch have same issue.",
        "timestamp": "2026-10-16T11:30:00",
        "status": "Pending",
        "cluster_alert": 1,
    },
    {
        "complaint_number": "TKT-2044",
        "caller_name": "Kavya Reddy",
        "mobile": "9432109876",
        "city": "Hyderabad",
        "area": "Banjara Hills",
        "category": "Test Drive",
        "description": "Requested test drive for new SUV model 5 days ago, no confirmation received yet.",
        "timestamp": "2026-10-16T13:00:00",
        "status": "Pending",
        "cluster_alert": 0,
    },
]

TRANSCRIPTS = {
    "SRV-1001": [
        {"role": "agent",  "content": "Hello, thank you for calling Saruti Muzuki Customer Support. How may I assist you today?", "index": 0},
        {"role": "caller", "content": "Hi, my car is making a loud grinding noise when I brake. It started about 3 days ago.", "index": 1},
        {"role": "agent",  "content": "I'm sorry to hear that. That does sound concerning. Could I get your name and mobile number to look up your account?", "index": 2},
        {"role": "caller", "content": "Sure, it's Rahul Shah, 9876543210.", "index": 3},
        {"role": "agent",  "content": "Thank you Rahul. And which city and area are you calling from?", "index": 4},
        {"role": "caller", "content": "I'm in Andheri, Mumbai.", "index": 5},
        {"role": "agent",  "content": "Got it. This sounds like a brake-related issue which falls under Service & Repair. Let me register a complaint for you. Could you describe the issue once more for the record?", "index": 6},
        {"role": "caller", "content": "Yes, it's a grinding noise every time I press the brake pedal, especially at lower speeds.", "index": 7},
        {"role": "agent",  "content": "Thank you. I've registered your complaint with ticket number SRV-1001. Our service team will contact you within 24 hours. Is there anything else I can help you with?", "index": 8},
        {"role": "caller", "content": "No that's all, thank you.", "index": 9},
        {"role": "agent",  "content": "You're welcome, Rahul. Have a great day!", "index": 10},
    ],
    "TKT-2042": [
        {"role": "agent",  "content": "Hello, thank you for calling Saruti Muzuki Customer Support. How may I assist you today?", "index": 0},
        {"role": "caller", "content": "My car's AC has completely stopped working. The car is only 8 months old, it should be under warranty.", "index": 1},
        {"role": "agent",  "content": "Absolutely, a vehicle that new should definitely be covered. May I get your name and contact number?", "index": 2},
        {"role": "caller", "content": "Priya Mehta, 9123456789.", "index": 3},
        {"role": "agent",  "content": "Thank you Priya. Your complaint TKT-2042 has been registered under Warranty. Our team will reach out to schedule an inspection at no cost to you.", "index": 4},
        {"role": "caller", "content": "Thank you.", "index": 5},
    ],
    "SRV-1002": [
        {"role": "agent",  "content": "Hello, thank you for calling Saruti Muzuki Customer Support. How may I assist you today?", "index": 0},
        {"role": "caller", "content": "My car broke down on the Mumbai-Pune highway! I need a tow truck immediately.", "index": 1},
        {"role": "agent",  "content": "I understand, please stay calm. I'm registering a Roadside Assistance request right now. Can you share your name and number?", "index": 2},
        {"role": "caller", "content": "Sneha Iyer, 9001234567. I'm near Khopoli exit.", "index": 3},
        {"role": "agent",  "content": "Got it Sneha. Ticket SRV-1002 is raised. A tow truck has been dispatched and will reach you in approximately 45 minutes. You'll receive an SMS with the driver's details.", "index": 4},
        {"role": "caller", "content": "Thank god. Thank you so much!", "index": 5},
        {"role": "agent",  "content": "Stay safe. We're on it!", "index": 6},
    ],
}


async def seed():
    await db.init_db()
    import aiosqlite
    async with aiosqlite.connect(db.DB_PATH) as conn:
        for c in COMPLAINTS:
            await conn.execute("""
                INSERT OR REPLACE INTO complaints
                  (complaint_number, caller_name, mobile, city, area, category,
                   description, timestamp, status, cluster_alert)
                VALUES
                  (:complaint_number, :caller_name, :mobile, :city, :area, :category,
                   :description, :timestamp, :status, :cluster_alert)
            """, c)
        await conn.commit()

    for complaint_number, turns in TRANSCRIPTS.items():
        await db.save_transcript(complaint_number, turns)

    print(f"Seeded {len(COMPLAINTS)} complaints and {len(TRANSCRIPTS)} transcripts.")


if __name__ == "__main__":
    asyncio.run(seed())
