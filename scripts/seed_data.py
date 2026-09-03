"""
Seed script — generates 500+ realistic fake customer records and inserts them into SQLite.
Run from project root with:
    python scripts/seed_data.py
"""
import random
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from faker import Faker
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models.customer import Base, Customer

fake = Faker("en_IN")  # Indian locale for realistic names

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PLANS = ["Basic", "Standard", "Premium"]
PLAN_WEIGHTS = [0.45, 0.35, 0.20]   # Basic is most common
NUM_CUSTOMERS = 600
RANDOM_SEED = 42

random.seed(RANDOM_SEED)
Faker.seed(RANDOM_SEED)

# ---------------------------------------------------------------------------
# Per-plan spend ranges — makes data more realistic for analytics
# ---------------------------------------------------------------------------
PLAN_SPEND = {
    "Basic": (10.0, 49.99),
    "Standard": (50.0, 149.99),
    "Premium": (150.0, 499.99),
}

# ---------------------------------------------------------------------------
# Churn logic — probability varies by plan and engagement
# ---------------------------------------------------------------------------

def should_churn(plan: str, satisfaction: float, tickets: int, last_login: int) -> bool:
    """
    Rule-based churn assignment for seed data.
    Mirrors the risk logic used in analytics queries so stats are meaningful.
    """
    risk_score = 0
    if satisfaction < 4.0:
        risk_score += 3
    elif satisfaction < 6.0:
        risk_score += 1
    if tickets > 7:
        risk_score += 2
    elif tickets > 4:
        risk_score += 1
    if last_login > 45:
        risk_score += 2
    elif last_login > 20:
        risk_score += 1
    if plan == "Basic":
        risk_score += 1

    # Higher risk score → higher churn probability
    churn_probability = min(0.05 + risk_score * 0.08, 0.85)
    return random.random() < churn_probability


def generate_customers(n: int) -> list[Customer]:
    customers = []
    seen_emails: set[str] = set()

    for i in range(1, n + 1):
        plan = random.choices(PLANS, weights=PLAN_WEIGHTS)[0]
        spend_min, spend_max = PLAN_SPEND[plan]
        satisfaction = round(random.uniform(1.0, 10.0), 1)
        tickets = random.randint(0, 15)
        last_login = random.randint(0, 90)

        # Unique email
        email = fake.email()
        while email in seen_emails:
            email = fake.email()
        seen_emails.add(email)

        customers.append(
            Customer(
                customer_id=f"C{i:04d}",
                name=fake.name(),
                email=email,
                age=random.randint(18, 70),
                plan=plan,
                monthly_spend=round(random.uniform(spend_min, spend_max), 2),
                tenure_months=random.randint(1, 72),
                support_tickets=tickets,
                last_login_days=last_login,
                satisfaction_score=satisfaction,
                churn=should_churn(plan, satisfaction, tickets, last_login),
            )
        )

    return customers


def main():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        existing = db.query(Customer).count()
        if existing > 0:
            print(f"Database already has {existing} customers. Skipping seed.")
            print("To re-seed, delete the .db file and run this script again.")
            return

        print(f"Generating {NUM_CUSTOMERS} customer records...")
        customers = generate_customers(NUM_CUSTOMERS)

        db.bulk_save_objects(customers)
        db.commit()

        total = db.query(Customer).count()
        churned = db.query(Customer).filter(Customer.churn == True).count()  # noqa: E712
        print(f"\n[OK] Seeded {total} customers")
        print(f"  Churned: {churned} ({churned/total*100:.1f}%)")
        print(f"  Active:  {total - churned} ({(total-churned)/total*100:.1f}%)")
        print("\nPlan breakdown:")
        for plan in PLANS:
            count = db.query(Customer).filter(Customer.plan == plan).count()
            print(f"  {plan}: {count}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
