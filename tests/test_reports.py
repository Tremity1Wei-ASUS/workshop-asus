import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.routers import reports


def test_sales_report(client: TestClient) -> None:
    response = client.get("/reports/sales", params={"category": "Gaming Laptop"})

    assert response.status_code == 200
    assert response.json() == {
        "category": "Gaming Laptop",
        "items": [
            {
                "id": 2,
                "name": "ROG Zephyrus G14",
                "category": "Gaming Laptop",
                "price": 62900.0,
            }
        ],
        "total": 62900.0,
    }


def test_sales_report_does_not_interpolate_category(client: TestClient) -> None:
    category = "Laptop' OR 1=1 --"

    response = client.get("/reports/sales", params={"category": category})

    assert response.status_code == 200
    assert response.json() == {"category": category, "items": [], "total": 0.0}


def test_sales_report_rejects_executable_formula(
    client: TestClient,
    tmp_path: Path,
) -> None:
    marker = tmp_path / "executed"
    formula = f"__import__('pathlib').Path({str(marker)!r}).touch()"

    response = client.get(
        "/reports/sales",
        params={"category": "Laptop", "formula": formula},
    )

    assert response.status_code == 422
    assert not marker.exists()


def test_sales_report_hides_database_errors(
    client: TestClient,
    monkeypatch,
) -> None:
    database_detail = "no such table: private_customer_records"

    def fail_query(category: str) -> list[object]:
        raise sqlite3.OperationalError(database_detail)

    monkeypatch.setattr(reports, "list_sales_products", fail_query)

    response = client.get("/reports/sales", params={"category": "Laptop"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to generate sales report"}
    assert database_detail not in response.text
