"""
LLM-ERP V2 — Integration tests for Organization, Production, and Warehouse APIs.
Run: cd backend && python -m pytest tests/test_v2.py -v
"""
import pytest
import asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app

BASE = "/api"


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ─── ORGANIZATION ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_department(client):
    r = await client.post(f"{BASE}/org/departments", json={
        "code": "TEST-DEPT", "name": "Test Department", "level": 1,
    })
    assert r.status_code in (200, 201)
    data = r.json()
    # Could be old format or new format
    if isinstance(data, dict) and "id" in data:
        assert data["code"] == "TEST-DEPT"


@pytest.mark.asyncio
async def test_list_departments(client):
    r = await client.get(f"{BASE}/org/departments")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_login_admin(client):
    r = await client.post(f"{BASE}/org/login", json={
        "username": "admin", "password": "123456",
    })
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data["user"]["employee_name"] is not None


@pytest.mark.asyncio
async def test_login_failed(client):
    r = await client.post(f"{BASE}/org/login", json={
        "username": "admin", "password": "wrongpassword",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_employee(client):
    r = await client.post(f"{BASE}/org/employees", json={
        "employee_no": "T001", "name": "Test Employee",
        "department_code": "IT", "title": "Tester",
    })
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_list_roles(client):
    r = await client.get(f"{BASE}/org/roles")
    assert r.status_code == 200
    data = r.json()
    assert len(data.get("roles", [])) > 0


# ─── PRODUCTION ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_work_centers(client):
    r = await client.get(f"{BASE}/dispatch/work-centers")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_shop_floor(client):
    r = await client.get(f"{BASE}/production/shop-floor")
    assert r.status_code == 200
    data = r.json()
    assert "machines" in data
    assert "orders" in data


@pytest.mark.asyncio
async def test_mps(client):
    r = await client.get(f"{BASE}/production/mps")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "products" in data


@pytest.mark.asyncio
async def test_mps_gantt(client):
    r = await client.get(f"{BASE}/production/mps/gantt")
    assert r.status_code == 200


# ─── WAREHOUSE ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_zones(client):
    r = await client.get(f"{BASE}/warehouse/zones")
    assert r.status_code == 200
    data = r.json()
    assert len(data.get("zones", [])) > 0


@pytest.mark.asyncio
async def test_list_bins(client):
    r = await client.get(f"{BASE}/warehouse/bins")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_supplier_evaluations(client):
    r = await client.get(f"{BASE}/warehouse/eval")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_reorder_check(client):
    r = await client.post(f"{BASE}/warehouse/reorder/check")
    assert r.status_code == 200


# ─── EXISTING V1 MODULES ────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_parts(client):
    r = await client.get(f"{BASE}/inventory/parts")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_suppliers(client):
    r = await client.get(f"{BASE}/purchase/suppliers")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_products(client):
    r = await client.get(f"{BASE}/bom/products")
    assert r.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
