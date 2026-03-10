"""
Тесты для эндпоинта POST /log/event
Проверка приёма событий (обычных и безопасности)
"""
import pytest

class TestLogEvent:
    """Группа E1-E14: Позитивные тесты (успешные сценарии)"""

    def test_E1_single_event_success(self, client, valid_api_key):
        """E1: Успешная отправка одного события"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "Test event"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_E2_thousand_events_success(self, client, valid_api_key):
        """E2: Успешная отправка 1000 событий"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890 + i,
            "service": "infopanel",
            "service_id": 1,
            "message": f"Event {i}"
        } for i in range(1000)]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1000}

    def test_E3_event_type_event(self, client, valid_api_key):
        """E3: Событие с event_type: "event" """
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "event_type": "event",
            "service": "infopanel",
            "service_id": 1,
            "message": "Regular event"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_E4_event_type_safety_event(self, client, valid_api_key):
        """E4: Событие с event_type: "safety_event" """
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "event_type": "safety_event",
            "service": "infopanel",
            "service_id": 1,
            "message": "Security alert!"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_E5_event_type_optional(self, client, valid_api_key):
        """E5: Событие без event_type (optional поле)"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            # event_type не передано
            "service": "infopanel",
            "service_id": 1,
            "message": "Event without type"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_E6_severity_provided(self, client, valid_api_key):
        """E6: Событие с severity"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "severity": "warning",
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with severity"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_E7_severity_optional(self, client, valid_api_key):
        """E7: Событие без severity (optional поле)"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            # severity не передано
            "service": "infopanel",
            "service_id": 1,
            "message": "Event without severity"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    @pytest.mark.parametrize("service_name", [
        "delivery", "queen", "inspector", "agriculture",
        "GCS", "aggregator", "insurance", "regulator",
        "dronePort", "OrAT_drones", "operator",
        "SITL", "Gazebo", "infopanel", "registry"
    ])
    def test_E8_all_service_values(self, client, valid_api_key, service_name):
        """E8: Все 15 значений service из enum"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": service_name,
            "service_id": 1,
            "message": f"Event from {service_name}"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    @pytest.mark.parametrize("severity_level", [
        "debug", "info", "notice", "warning",
        "error", "critical", "alert", "emergency"
    ])
    def test_E9_all_severity_values(self, client, valid_api_key, severity_level):
        """E9: Все 8 значений severity из enum"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "severity": severity_level,
            "service": "infopanel",
            "service_id": 1,
            "message": f"Event with {severity_level} severity"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    @pytest.mark.parametrize("api_version", ["1.0.0", "1.0.0.0"])
    def test_E10_api_version_boundaries(self, client, valid_api_key, api_version):
        """E10: Граничные значения api_version (5 и 8 символов)"""
        payload = [{
            "api_version": api_version,
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with boundary api_version"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200

    def test_E11_timestamp_zero(self, client, valid_api_key):
        """E11: timestamp = 0 (минимальное допустимое)"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 0,
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with timestamp 0"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_E12_service_id_minimum(self, client, valid_api_key):
        """E12: service_id = 1 (минимальное допустимое)"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with service_id 1"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_E13_message_min_length(self, client, valid_api_key):
        """E13: message = 1 символ (минимальная длина)"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "X"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_E14_message_max_length(self, client, valid_api_key):
        """E14: message = 1024 символа (максимальная длина)"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "X" * 1024
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}


    """Группа E15-E20: Валидация обязательных полей"""

    def test_E15_missing_api_version(self, client, valid_api_key):
        """E15: Отсутствует api_version -> 400"""
        payload = [{
            # api_version отсутствует
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "Event without api_version"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E16_missing_timestamp(self, client, valid_api_key):
        """E16: Отсутствует timestamp -> 400"""
        payload = [{
            "api_version": "1.0.0",
            # timestamp отсутствует
            "service": "infopanel",
            "service_id": 1,
            "message": "Event without timestamp"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E17_missing_service(self, client, valid_api_key):
        """E17: Отсутствует service -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            # service отсутствует
            "service_id": 1,
            "message": "Event without service"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E18_missing_service_id(self, client, valid_api_key):
        """E18: Отсутствует service_id -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            # service_id отсутствует
            "message": "Event without service_id"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E19_missing_message(self, client, valid_api_key):
        """E19: Отсутствует message -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            # message отсутствует
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E20_empty_array(self, client, valid_api_key):
        """E20: Пустой массив событий -> 400"""
        payload = []
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    """Группа E21-E30: Валидация типов и форматов"""

    def test_E21_api_version_too_short(self, client, valid_api_key):
        """E21: api_version < 5 символов -> 400"""
        payload = [{
            "api_version": "1.0",  # 3 символа
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with short api_version"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E22_api_version_too_long(self, client, valid_api_key):
        """E22: api_version > 8 символов -> 400"""
        payload = [{
            "api_version": "1.0.0.0.0",  # 9 символов
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with long api_version"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E23_timestamp_negative(self, client, valid_api_key):
        """E23: timestamp < 0 -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": -1,
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with negative timestamp"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400


    def test_E24_service_id_zero(self, client, valid_api_key):
        """E24: service_id = 0 -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 0,  # минимум 1
            "message": "Event with service_id 0"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E25_service_id_negative(self, client, valid_api_key):
        """E25: service_id < 0 -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": -1,
            "message": "Event with negative service_id"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E26_message_empty(self, client, valid_api_key):
        """E26: message пустой -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": ""  # min_length=1
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E27_message_too_long(self, client, valid_api_key):
        """E27: message > 1024 символов -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "X" * 1025
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E28_message_wrong_type(self, client, valid_api_key):
        """E28: message — число вместо string -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": 123  # число
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    """Группа E29-E33: Валидация enum-полей"""

    def test_E29_invalid_event_type(self, client, valid_api_key):
        """E29: event_type не из enum -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "event_type": "hack_event",  # нет в enum
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with invalid event_type"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E30_invalid_service(self, client, valid_api_key):
        """E30: service не из enum -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "unknown_service",  # нет в enum
            "service_id": 1,
            "message": "Event with invalid service"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E31_invalid_severity(self, client, valid_api_key):
        """E31: severity не из enum -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "severity": "panic",  # нет в enum
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with invalid severity"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E32_event_type_wrong_type(self, client, valid_api_key):
        """E32: event_type — число вместо string -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "event_type": 1,  # число
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with number event_type"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E33_severity_wrong_type(self, client, valid_api_key):
        """E33: severity — число вместо string -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "severity": 5,  # число
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with number severity"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    """Группа E34-E38: Структура запроса"""

    def test_E34_body_not_array(self, client, valid_api_key):
        """E34: Тело — объект, не массив -> 400"""
        payload = {
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "Single object instead of array"
        }
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E35_extra_field_forbidden(self, client, valid_api_key):
        """E35: Лишнее поле в объекте -> 400 (StrictModel)"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with extra field",
            "extra_field": "should_fail"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E36_wrong_content_type(self, client, valid_api_key):
        """E36: Неверный Content-Type -> 400 """
        response = client.post(
            "/log/event",
            content='[{"api_version": "1.0.0"}]',
            headers={
                "X-API-Key": valid_api_key,
                "Content-Type": "text/plain"
            }
        )
        
        assert response.status_code == 400

    def test_E37_malformed_json(self, client, valid_api_key):
        """E37: Malformed JSON -> 400"""
        response = client.post(
            "/log/event",
            content='{"invalid": json}',
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E38_mixed_valid_invalid(self, client, valid_api_key):
        """E38: Смешанные валидные/невалидные -> 400 (весь запрос)"""
        payload = [
            {
                "api_version": "1.0.0",
                "timestamp": 1234567890,
                "service": "infopanel",
                "service_id": 1,
                "message": "Valid event"
            },
            {
                "api_version": "1.0.0",
                "timestamp": 1234567890,
                "service": "invalid_service",  # невалидный
                "service_id": 1,
                "message": "Invalid event"
            }
        ]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400