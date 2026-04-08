"""Test suite for Prompt Vault API."""

SAMPLE = {
    "title": "Explain recursion",
    "text": "Explain {concept} using a simple real-world analogy. Avoid jargon.",
    "model": "claude-sonnet-4-6",
    "category": "learning",
    "task_type": "explain concept",
    "effectiveness": 5,
    "tags": "teaching, recursion",
    "token_count": 120,
}


# --- health ---

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Prompt Vault"


# --- create ---

def test_create_prompt_returns_201(client):
    response = client.post("/prompts", json=SAMPLE)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Explain recursion"
    assert data["effectiveness"] == 5


def test_create_normalizes_tags(client):
    payload = {**SAMPLE, "tags": "  Python , FastAPI , AI  "}
    response = client.post("/prompts", json=payload)
    assert response.status_code == 201
    assert response.json()["tags"] == "python,fastapi,ai"


def test_create_rejects_effectiveness_out_of_range(client):
    response = client.post("/prompts", json={**SAMPLE, "effectiveness": 6})
    assert response.status_code == 422

    response = client.post("/prompts", json={**SAMPLE, "effectiveness": 0})
    assert response.status_code == 422


def test_create_rejects_missing_required_fields(client):
    response = client.post("/prompts", json={"title": "Missing fields"})
    assert response.status_code == 422


def test_create_rejects_invalid_category(client):
    response = client.post("/prompts", json={**SAMPLE, "category": "nonsense"})
    assert response.status_code == 422


def test_create_rejects_negative_token_count(client):
    response = client.post("/prompts", json={**SAMPLE, "token_count": -5})
    assert response.status_code == 422


# --- list ---

def test_list_prompts_empty(client):
    response = client.get("/prompts")
    assert response.status_code == 200
    assert response.json() == []


def test_list_prompts_returns_created(client):
    client.post("/prompts", json=SAMPLE)
    response = client.get("/prompts")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_prompts_pagination(client):
    for i in range(5):
        client.post("/prompts", json={**SAMPLE, "title": f"Prompt {i}"})
    response = client.get("/prompts?skip=2&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


# --- get by id ---

def test_get_prompt_by_id(client):
    created = client.post("/prompts", json=SAMPLE).json()
    response = client.get(f"/prompts/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Explain recursion"


def test_get_missing_prompt_returns_404(client):
    response = client.get("/prompts/9999")
    assert response.status_code == 404


# --- update ---

def test_update_effectiveness(client):
    created = client.post("/prompts", json=SAMPLE).json()
    response = client.patch(f"/prompts/{created['id']}", json={"effectiveness": 3})
    assert response.status_code == 200
    assert response.json()["effectiveness"] == 3


def test_update_missing_prompt_returns_404(client):
    response = client.patch("/prompts/9999", json={"effectiveness": 3})
    assert response.status_code == 404


def test_partial_update_does_not_overwrite_other_fields(client):
    created = client.post("/prompts", json=SAMPLE).json()
    client.patch(f"/prompts/{created['id']}", json={"notes": "Works great!"})
    response = client.get(f"/prompts/{created['id']}")
    data = response.json()
    assert data["notes"] == "Works great!"
    assert data["title"] == "Explain recursion"


# --- delete ---

def test_delete_prompt(client):
    created = client.post("/prompts", json=SAMPLE).json()
    response = client.delete(f"/prompts/{created['id']}")
    assert response.status_code == 204

    get_response = client.get(f"/prompts/{created['id']}")
    assert get_response.status_code == 404


def test_delete_missing_prompt_returns_404(client):
    response = client.delete("/prompts/9999")
    assert response.status_code == 404
