"""
Seed script to populate the database with demo data for testing.

Usage:
    python seed_data.py --base-url http://localhost:8000
"""

import argparse
import json
import sys

import httpx

DEMO_USERS = [
    {"email": "alice@fincloud.demo", "password": "SecurePass123!", "full_name": "Alice Johnson", "phone": "+1234567890"},
    {"email": "bob@fincloud.demo", "password": "SecurePass123!", "full_name": "Bob Smith", "phone": "+1234567891"},
    {"email": "charlie@fincloud.demo", "password": "SecurePass123!", "full_name": "Charlie Brown", "phone": "+1234567892"},
]


def seed(base_url: str):
    base_url = base_url.rstrip("/")
    client = httpx.Client(base_url=base_url, timeout=10.0)

    print("Registering demo users...")
    user_ids = {}
    for user in DEMO_USERS:
        resp = client.post("/api/v1/users/register", json=user)
        if resp.status_code == 201:
            data = resp.json()
            user_ids[user["email"]] = data["id"]
            print(f"  Created: {user['full_name']} ({data['id']})")
        elif resp.status_code == 409:
            print(f"  Exists:  {user['full_name']}")
            login_resp = client.post("/api/v1/users/login", json={"email": user["email"], "password": user["password"]})
            if login_resp.status_code == 200:
                user_ids[user["email"]] = login_resp.json()["user_id"]
        else:
            print(f"  Error:   {user['full_name']} — {resp.status_code}: {resp.text}")

    if len(user_ids) < 2:
        print("Need at least 2 users for demo transactions")
        return

    print("\nCreating demo transactions...")
    alice_login = client.post("/api/v1/users/login", json={"email": "alice@fincloud.demo", "password": "SecurePass123!"})
    if alice_login.status_code != 200:
        print("  Failed to login as Alice")
        return

    token = alice_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    bob_id = user_ids.get("bob@fincloud.demo")
    charlie_id = user_ids.get("charlie@fincloud.demo")

    transactions = [
        {"receiver_id": bob_id, "amount": 50.00, "description": "Lunch payment"},
        {"receiver_id": charlie_id, "amount": 25.50, "description": "Book reimbursement"},
        {"receiver_id": bob_id, "amount": 100.00, "description": "Rent split"},
        {"receiver_id": charlie_id, "amount": 15.75, "description": "Coffee"},
        {"receiver_id": bob_id, "amount": 200.00, "description": "Monthly subscription"},
    ]

    for txn in transactions:
        if txn["receiver_id"]:
            resp = client.post("/api/v1/transactions/transfer", json=txn, headers=headers)
            if resp.status_code == 201:
                data = resp.json()
                print(f"  Transfer: ${txn['amount']:.2f} → {txn['description']} (id: {data['id'][:8]}...)")
            else:
                print(f"  Failed:   ${txn['amount']:.2f} — {resp.status_code}: {resp.text[:100]}")

    print("\nChecking Alice's wallet...")
    wallet_resp = client.get("/api/v1/transactions/wallet", headers=headers)
    if wallet_resp.status_code == 200:
        wallet = wallet_resp.json()
        print(f"  Balance: ${wallet['balance']}")

    print("\nSeed complete!")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed FinCloud with demo data")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    seed(args.base_url)
