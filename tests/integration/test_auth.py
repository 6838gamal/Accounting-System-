"""
اختبارات تكامل المصادقة
"""
import pytest
from fastapi.testclient import TestClient


def test_login_page(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "تسجيل الدخول" in response.text


def test_login_with_correct_credentials(client, admin_user):
    response = client.post("/auth/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
    assert response.status_code in [200, 302]


def test_login_with_wrong_credentials(client, admin_user):
    response = client.post("/auth/login", data={"username": "admin", "password": "wrongpassword"})
    assert "غير صحيحة" in response.text


def test_root_redirects_to_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
