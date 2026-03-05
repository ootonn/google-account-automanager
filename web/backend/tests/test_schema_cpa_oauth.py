from web.backend.schemas import ConfigResponse, ConfigUpdate, TaskType


def test_task_type_contains_cpa_oauth_bind():
    assert TaskType.cpa_oauth_bind.value == "cpa_oauth_bind"


def test_config_contains_cpa_fields():
    update = ConfigUpdate(
        cpa_base_url="https://cpa.example.com",
        cpa_management_token="token",
        cpa_poll_timeout_seconds=300,
        cpa_poll_interval_seconds=2,
        cpa_oauth_capture_timeout_seconds=180,
    )
    assert update.cpa_base_url.startswith("https://")


def test_config_response_contains_cpa_fields():
    response = ConfigResponse(
        cpa_base_url="https://cpa.example.com",
        cpa_management_token="token",
        cpa_poll_timeout_seconds=300,
        cpa_poll_interval_seconds=2,
        cpa_oauth_capture_timeout_seconds=180,
    )
    assert response.cpa_poll_interval_seconds == 2
