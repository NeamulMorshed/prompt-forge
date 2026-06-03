def test_signup_login_me_roundtrip(client):
    # signup
    r = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw123456"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

    # duplicate signup rejected
    r2 = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw123456"})
    assert r2.status_code == 409

    # login
    r3 = client.post("/auth/login", json={"email": "a@b.com", "password": "pw123456"})
    assert r3.status_code == 200
    login_token = r3.json()["access_token"]

    # wrong password
    r4 = client.post("/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert r4.status_code == 401

    # me with token
    r5 = client.get("/auth/me", headers={"Authorization": f"Bearer {login_token}"})
    assert r5.status_code == 200
    body = r5.json()
    assert body["email"] == "a@b.com"
    assert body["plan"] == "free"

    # me without token
    r6 = client.get("/auth/me")
    assert r6.status_code == 401
