from app import create_app

def test_dashboard_api():
    app = create_app()
    client = app.test_client()
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "risk" in data["data"]
