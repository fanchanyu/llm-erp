"""
LLM-ERP V2 — Organization Seed Data
Run: python -m app.seed_org
"""

import asyncio
from app.database import async_session, init_db
from app.services.organization_service import seed_organization


async def main():
    await init_db()
    async with async_session() as db:
        await seed_organization(db)
        await db.commit()
    print("✅ Organization seed data loaded successfully!")
    print("   Users: admin/123456, manager/123456, purchaser/123456, ...")
    print("   Departments: HQ → FACTORY → ADMIN → IT/HR/FINANCE, PURCHASE, WAREHOUSE...")
    print("   Roles: admin, plant_manager, manager, section_chief, clerk, operator")


if __name__ == "__main__":
    asyncio.run(main())
