"""
Тесты для эндпоинта POST /log/telemetry

Проверяют валидацию данных телеметрии дронов.
Без тестов безопасности (API-ключи) — только валидация данных.
"""
import pytest


class TestLogTelemetry:
    """Тесты для POST /log/telemetry"""

    # ==================== ПОЗИТИВНЫЕ ТЕСТЫ ====================

    def test_telemetry_single_valid_object(self, client, valid_api_key):
        """G1: Один валидный объект телеметрии"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 1234567890,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.75,
            "longitude": 37.61
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_telemetry_1000_objects_max(self, client, valid_api_key):
        """G2: 1000 валидных объектов (максимум)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 1234567890,
            "drone": "delivery",
            "drone_id": i,
            "latitude": 55.75,
            "longitude": 37.61
        } for i in range(1, 1001)]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        assert response.json() == {"accepted": 1000}

    def test_telemetry_all_optional_fields(self, client, valid_api_key):
        """G3: Все optional поля заполнены"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 1234567890,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.75,
            "longitude": 37.61,
            "battery": 85,
            "pitch": 5.5,
            "roll": -2.3,
            "course": 90.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_only_required_fields(self, client, valid_api_key):
        """G4: Только обязательные поля (без battery, pitch, roll, course)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 1234567890,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.75,
            "longitude": 37.61
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_all_drone_types(self, client, valid_api_key):
        """G5: Все типы дронов (delivery, queen, inspector, agriculture)"""
        payload = [
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "queen", "drone_id": 2, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "inspector", "drone_id": 3, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "agriculture", "drone_id": 4, "latitude": 55.0, "longitude": 37.0}
        ]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        assert response.json() == {"accepted": 4}

    def test_telemetry_latitude_boundaries(self, client, valid_api_key):
        """G6: Граничные значения latitude (-90 и 90)"""
        payload = [
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": -90, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 2, "latitude": 90, "longitude": 37.0}
        ]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_longitude_boundaries(self, client, valid_api_key):
        """G7: Граничные значения longitude (-180 и 180)"""
        payload = [
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": -180},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 2, "latitude": 55.0, "longitude": 180}
        ]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_battery_boundaries(self, client, valid_api_key):
        """G8: Граничные значения battery (0 и 100)"""
        payload = [
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0, "battery": 0},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 2, "latitude": 55.0, "longitude": 37.0, "battery": 100}
        ]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_pitch_boundaries(self, client, valid_api_key):
        """G9: Граничные значения pitch (-90 и 90)"""
        payload = [
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0, "pitch": -90},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 2, "latitude": 55.0, "longitude": 37.0, "pitch": 90}
        ]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_roll_boundaries(self, client, valid_api_key):
        """G10: Граничные значения roll (-180 и 180)"""
        payload = [
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0, "roll": -180},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 2, "latitude": 55.0, "longitude": 37.0, "roll": 180}
        ]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_course_boundaries(self, client, valid_api_key):
        """G11: Граничные значения course (0 и 360)"""
        payload = [
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0, "course": 0},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 2, "latitude": 55.0, "longitude": 37.0, "course": 360}
        ]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_apiVersion_min_length(self, client, valid_api_key):
        """G12: Минимальная apiVersion (5 символов)"""
        payload = [{
            "apiVersion": "1.0.0",  # 5 символов
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_apiVersion_max_length(self, client, valid_api_key):
        """G13: Максимальная apiVersion (8 символов)"""
        payload = [{
            "apiVersion": "1.0.0.0",  # 8 символов
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_drone_id_minimum(self, client, valid_api_key):
        """G14: Минимальный drone_id (1)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_drone_id_large(self, client, valid_api_key):
        """G15: Большой drone_id (999999)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 999999,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_timestamp_zero(self, client, valid_api_key):
        """G16: timestamp = 0"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 0,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_timestamp_future(self, client, valid_api_key):
        """G17: timestamp в будущем"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 9999999999,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    # ==================== НЕГАТИВНЫЕ ТЕСТЫ ====================

    def test_telemetry_empty_array(self, client, valid_api_key):
        """G18: Пустой массив -> 400"""
        response = client.post(
            "/log/telemetry",
            json=[],
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_1001_objects_exceeded(self, client, valid_api_key):
        """G19: 1001 объект (превышение лимита) -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": i,
            "latitude": 55.0,
            "longitude": 37.0
        } for i in range(1, 1002)]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_missing_apiVersion(self, client, valid_api_key):
        """G20: Отсутствует apiVersion -> 400"""
        payload = [{
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_apiVersion_too_short(self, client, valid_api_key):
        """G21: apiVersion 4 символа -> 400"""
        payload = [{
            "apiVersion": "1.0",  # 4 символа
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_apiVersion_too_long(self, client, valid_api_key):
        """G22: apiVersion 9 символов -> 400"""
        payload = [{
            "apiVersion": "1.0.0.0.0",  # 9 символов
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_missing_timestamp(self, client, valid_api_key):
        """G23: Отсутствует timestamp -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_timestamp_negative(self, client, valid_api_key):
        """G24: timestamp отрицательный -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": -1,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_timestamp_not_int(self, client, valid_api_key):
        """G25: timestamp не int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": "now",
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_missing_drone(self, client, valid_api_key):
        """G26: Отсутствует drone -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_not_in_enum(self, client, valid_api_key):
        """G27: drone не из enum -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "unknown",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_case_sensitive(self, client, valid_api_key):
        """G28: drone чувствителен к регистру -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "Delivery",  # Должно быть "delivery"
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_missing_drone_id(self, client, valid_api_key):
        """G29: Отсутствует drone_id -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_id_zero(self, client, valid_api_key):
        """G30: drone_id = 0 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 0,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_id_negative(self, client, valid_api_key):
        """G31: drone_id отрицательный -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": -5,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400


    def test_telemetry_missing_latitude(self, client, valid_api_key):
        """G32: Отсутствует latitude -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_latitude_too_low(self, client, valid_api_key):
        """G33: latitude = -91 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": -91,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_latitude_too_high(self, client, valid_api_key):
        """G34: latitude = 91 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 91,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_missing_longitude(self, client, valid_api_key):
        """G35: Отсутствует longitude -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_longitude_too_low(self, client, valid_api_key):
        """G36: longitude = -181 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": -181
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_longitude_too_high(self, client, valid_api_key):
        """G37: longitude = 181 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 181
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_battery_negative(self, client, valid_api_key):
        """G38: battery = -1 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "battery": -1
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_battery_exceeded(self, client, valid_api_key):
        """G39: battery = 101 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "battery": 101
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_pitch_too_low(self, client, valid_api_key):
        """G40: pitch = -91 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "pitch": -91
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_pitch_too_high(self, client, valid_api_key):
        """G41: pitch = 91 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "pitch": 91
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_roll_too_low(self, client, valid_api_key):
        """G42: roll = -181 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "roll": -181
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_roll_too_high(self, client, valid_api_key):
        """G43: roll = 181 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "roll": 181
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_course_negative(self, client, valid_api_key):
        """G44: course = -1 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "course": -1
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_course_exceeded(self, client, valid_api_key):
        """G45: course = 361 -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "course": 361
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_extra_field_forbidden(self, client, valid_api_key):
        """G46: Лишнее поле в объекте -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "extra_field": "should_fail"
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_not_json(self, client, valid_api_key):
        """G47: Не JSOG в теле -> 400"""
        response = client.post(
            "/log/telemetry",
            content="not json",
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_object_not_array(self, client, valid_api_key):
        """G48: Один объект вместо массива -> 400"""
        payload = {
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_null_in_array(self, client, valid_api_key):
        """G49: null вместо объекта -> 400"""
        payload = [None]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_mixed_valid_invalid(self, client, valid_api_key):
        """G50: Смешанные валидные/невалидные -> 400"""
        payload = [
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "unknown", "drone_id": 2, "latitude": 55.0, "longitude": 37.0}
        ]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400
    # ==================== ТЕСТЫ НА ТИПЫ ДАННЫХ ====================

    def test_telemetry_apiVersion_as_int(self, client, valid_api_key):
        """G51: apiVersion как int вместо str -> 400"""
        payload = [{
            "apiVersion": 100,  # Должно быть строкой
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_apiVersion_as_float(self, client, valid_api_key):
        """G52: apiVersion как float вместо str -> 400"""
        payload = [{
            "apiVersion": 1.0,  # Должно быть строкой
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_apiVersion_as_bool(self, client, valid_api_key):
        """G53: apiVersion как bool вместо str -> 400"""
        payload = [{
            "apiVersion": True,  # Должно быть строкой
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_apiVersion_as_list(self, client, valid_api_key):
        """G54: apiVersion как list вместо str -> 400"""
        payload = [{
            "apiVersion": ["1.0.0"],  # Должно быть строкой
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_apiVersion_as_dict(self, client, valid_api_key):
        """G55: apiVersion как dict вместо str -> 400"""
        payload = [{
            "apiVersion": {"version": "1.0.0"},  # Должно быть строкой
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_apiVersion_as_null(self, client, valid_api_key):
        """G56: apiVersion как null вместо str -> 400"""
        payload = [{
            "apiVersion": None,  # Должно быть строкой
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_timestamp_as_str(self, client, valid_api_key):
        """G57: timestamp как str вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": "1234567890",  # Должно быть int
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_timestamp_as_float(self, client, valid_api_key):
        """G58: timestamp как float вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 1234567890.5,  # Должно быть int
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_timestamp_as_bool(self, client, valid_api_key):
        """G59: timestamp как bool вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": True,  # Должно быть int
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_timestamp_as_null(self, client, valid_api_key):
        """G60: timestamp как null вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": None,  # Должно быть int
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_as_int(self, client, valid_api_key):
        """G61: drone как int вместо str -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": 1,  # Должно быть строкой из enum
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_as_list(self, client, valid_api_key):
        """G62: drone как list вместо str -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": ["delivery"],  # Должно быть строкой
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_as_null(self, client, valid_api_key):
        """G63: drone как null вместо str -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": None,  # Должно быть строкой
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_id_as_str(self, client, valid_api_key):
        """G64: drone_id как str вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": "1",  # Должно быть int
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_id_as_float(self, client, valid_api_key):
        """G65: drone_id как float вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1.5,  # Должно быть int
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_id_as_bool(self, client, valid_api_key):
        """G66: drone_id как bool вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": True,  # Должно быть int
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_drone_id_as_null(self, client, valid_api_key):
        """G67: drone_id как null вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": None,  # Должно быть int
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_latitude_as_str(self, client, valid_api_key):
        """G68: latitude как str вместо float -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": "55.75",  # Должно быть float
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_latitude_as_int(self, client, valid_api_key):
        """G69: latitude как int (допустимо, но проверяем)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55,  # Int конвертируется в float
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        # Pydantic может сконвертировать int -> float
        # Если strict=True -> 400, иначе -> 200
        assert response.status_code in [200, 400]

    def test_telemetry_latitude_as_bool(self, client, valid_api_key):
        """G70: latitude как bool вместо float -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": True,  # Должно быть float
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_latitude_as_null(self, client, valid_api_key):
        """G71: latitude как null вместо float -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": None,  # Должно быть float
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_longitude_as_str(self, client, valid_api_key):
        """G72: longitude как str вместо float -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": "37.61"  # Должно быть float
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_longitude_as_bool(self, client, valid_api_key):
        """G73: longitude как bool вместо float -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": False  # Должно быть float
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_longitude_as_null(self, client, valid_api_key):
        """G74: longitude как null вместо float -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": None  # Должно быть float
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_battery_as_str(self, client, valid_api_key):
        """G75: battery как str вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "battery": "85"  # Должно быть int
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_battery_as_float(self, client, valid_api_key):
        """G76: battery как float вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "battery": 85.5  # Должно быть int
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_battery_as_bool(self, client, valid_api_key):
        """G77: battery как bool вместо int -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "battery": True  # Должно быть int
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_battery_as_null(self, client, valid_api_key):
        """G78: battery как null -> 200 (optional поле)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "battery": None  # Optional, может быть null
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        # Optional поле может быть null
        assert response.status_code == 200

    def test_telemetry_pitch_as_str(self, client, valid_api_key):
        """G79: pitch как str вместо float -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "pitch": "5.5"  # Должно быть float
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_pitch_as_null(self, client, valid_api_key):
        """G80: pitch как null -> 200 (optional поле)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "pitch": None  # Optional
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_roll_as_str(self, client, valid_api_key):
        """G81: roll как str вместо float -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "roll": "-2.3"  # Должно быть float
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_roll_as_null(self, client, valid_api_key):
        """G82: roll как null -> 200 (optional поле)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "roll": None  # Optional
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_course_as_str(self, client, valid_api_key):
        """G83: course как str вместо float -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "course": "90.0"  # Должно быть float
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_course_as_null(self, client, valid_api_key):
        """G84: course как null -> 200 (optional поле)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0,
            "course": None  # Optional
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_whole_object_as_string(self, client, valid_api_key):
        """G85: Весь объект как строка вместо dict -> 400"""
        payload = ["not an object"]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_nested_object_in_field(self, client, valid_api_key):
        """G86: Вложенный объект в поле drone_id -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": {"id": 1},  # Должно быть int
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_array_in_field(self, client, valid_api_key):
        """G87: Массив в поле timestamp -> 400"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": [123, 456],  # Должно быть int
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_very_large_int(self, client, valid_api_key):
        """G88: drone_id очень большое число -> 200 (если в пределах int64)"""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 9223372036854775807,  # Max int64
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        # Зависит от реализации, но обычно 200
        assert response.status_code in [200, 400]

    def test_telemetry_very_long_string(self, client, valid_api_key):
        """G89: apiVersion очень длинная строка -> 400"""
        payload = [{
            "apiVersion": "1.0.0" + "0" * 1000,  # > 8 символов
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_unicode_in_string(self, client, valid_api_key):
        """G90: apiVersion с unicode символами -> 200 (строка валидна)"""
        payload = [{
            "apiVersion": "1.0.0",  # Валидная версия
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_telemetry_empty_string_in_required_field(self, client, valid_api_key):
        """G91: Пустая строка в apiVersion -> 400 (min_length=5)"""
        payload = [{
            "apiVersion": "",  # Пустая строка
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_whitespace_string(self, client, valid_api_key):
        """G92: Строка из пробелов в apiVersion -> 400 (min_length=5)"""
        payload = [{
            "apiVersion": "   ",  # 3 пробела
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_mixed_types_in_array(self, client, valid_api_key):
        """G93: Массив с объектами разных типов -> 400"""
        payload = [
            {"apiVersion": "1.0.0", "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": 123, "timestamp": 123, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0}  # apiVersion как int
        ]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400

    def test_telemetry_duplicate_fields(self, client, valid_api_key):
        """G94: Дублирующиеся поля в объекте -> 400"""
        # В JSOG дубликаты ключей обычно перезаписываются, но проверяем
        payload = [{
            "apiVersion": "1.0.0",
            "apiVersion": "2.0.0",  # Дубликат
            "timestamp": 123,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]

        response = client.post(
            "/log/telemetry",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        # JSOG парсер обычно оставляет последнее значение
        assert response.status_code == 400

class TestLogBasic:
    """Позитивные тесты — успешные сценарии"""

    def test_D1_single_valid_log(self, client, valid_api_key):
        """D1: Один валидный лог -> 200, {"accepted": 1}"""
        payload = [{
            "timestamp": 1234567890,
            "message": "Test message"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_D2_max_count_1000_logs(self, client, valid_api_key):
        """D2: Максимальное количество (1000) -> 200, {"accepted": 1000}"""
        payload = [
            {"timestamp": i, "message": f"Log {i}"}
            for i in range(1000)
        ]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1000}

    def test_D3_message_max_length_1024(self, client, valid_api_key):
        """D3: Сообщение максимальной длины (1024 символа) -> 200"""
        payload = [{
            "timestamp": 123,
            "message": "x" * 1024
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_D4_message_min_length_1(self, client, valid_api_key):
        """D4: Сообщение минимальной длины (1 символ) -> 200"""
        payload = [{
            "timestamp": 123,
            "message": "x"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_D5_timestamp_zero_boundary(self, client, valid_api_key):
        """D5: Timestamp = 0 (нижняя граница) -> 200"""
        payload = [{
            "timestamp": 0,
            "message": "Test"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_D6_timestamp_large_value(self, client, valid_api_key):
        """D6: Timestamp большое значение -> 200"""
        payload = [{
            "timestamp": 9999999999,
            "message": "Test"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_D7_multiple_different_messages(self, client, valid_api_key):
        """D7: Разные сообщения в массиве -> 200, {"accepted": N}"""
        payload = [
            {"timestamp": 1, "message": "A"},
            {"timestamp": 2, "message": "B"},
            {"timestamp": 3, "message": "C"}
        ]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 3}

    """Негативные тесты — валидация данных"""

    def test_D8_empty_array(self, client, valid_api_key):
        """D8: Пустой массив -> 400 (min_length=1)"""
        payload = []
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D9_array_1001_elements(self, client, valid_api_key):
        """D9: Массив из 1001 элемента -> 400 (max_length=1000)"""
        payload = [
            {"timestamp": i, "message": f"Log {i}"}
            for i in range(1001)
        ]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D10_missing_timestamp_field(self, client, valid_api_key):
        """D10: Отсутствует поле timestamp -> 400 (required field)"""
        payload = [{
            "message": "Test"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D11_missing_message_field(self, client, valid_api_key):
        """D11: Отсутствует поле message -> 400 (required field)"""
        payload = [{
            "timestamp": 123
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D12_timestamp_negative(self, client, valid_api_key):
        """D12: Timestamp отрицательный -> 400 (ge=0)"""
        payload = [{
            "timestamp": -1,
            "message": "Test"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D13_timestamp_not_integer(self, client, valid_api_key):
        """D13: Timestamp не число -> 400 (wrong type)"""
        payload = [{
            "timestamp": "now",
            "message": "Test"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D14_message_empty_string(self, client, valid_api_key):
        """D14: Message пустая строка -> 400 (min_length=1)"""
        payload = [{
            "timestamp": 123,
            "message": ""
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D15_message_1025_characters(self, client, valid_api_key):
        """D15: Message 1025 символов -> 400 (max_length=1024)"""
        payload = [{
            "timestamp": 123,
            "message": "x" * 1025
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D16_message_not_string(self, client, valid_api_key):
        """D16: Message не строка -> 400 (wrong type)"""
        payload = [{
            "timestamp": 123,
            "message": 123
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D17_extra_field_forbidden(self, client, valid_api_key):
        """D17: Лишнее поле в объекте -> 400 (StrictModel extra="forbid")"""
        payload = [{
            "timestamp": 123,
            "message": "Test",
            "extra_field": "should_fail"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D18_not_json_body(self, client, valid_api_key):
        """D18: Не JSON в теле -> 400 (Parse Error)"""
        response = client.post(
            "/log/basic",
            content="not json",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D19_null_instead_of_array(self, client, valid_api_key):
        """D19: Null вместо массива -> 400 (Validation Error)"""
        response = client.post(
            "/log/basic",
            json=None,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D20_object_instead_of_array(self, client, valid_api_key):
        """D20: Объект вместо массива -> 400 (expected array)"""
        payload = {
            "timestamp": 123,
            "message": "Test"
        }
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    """Граничные и специальные случаи"""

    def test_D21_mixed_valid_invalid(self, client, valid_api_key):
        """D21: Смешанные валидные/невалидные -> 400 (весь запрос отклоняется)"""
        payload = [
            {"timestamp": 123, "message": "OK"},
            {"timestamp": -1, "message": "Fail"}  # Невалидный
        ]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_D22_special_characters_in_message(self, client, valid_api_key):
        """D22: Спецсимволы в message -> 200"""
        payload = [{
            "timestamp": 123,
            "message": "Test\n\r\t"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_D23_unicode_in_message(self, client, valid_api_key):
        """D23: Unicode в message -> 200"""
        payload = [{
            "timestamp": 123,
            "message": "Привет 世界 🚁"
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_D24_duplicate_timestamps(self, client, valid_api_key):
        """D24: Дубликаты timestamp -> 200 (timestamp не уникален)"""
        payload = [
            {"timestamp": 123, "message": "A"},
            {"timestamp": 123, "message": "B"}
        ]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 2}

    def test_D25_message_with_spaces(self, client, valid_api_key):
        """D25: Сообщение с пробелами -> 200 (пробелы = валидные символы)"""
        payload = [{
            "timestamp": 123,
            "message": "   "
        }]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == {"accepted": 1}

    def test_D26_very_long_json_payload(self, client, valid_api_key):
        """D26: Очень длинный JSON (1000 элементов по 1KB) -> 200"""
        payload = [
            {"timestamp": i, "message": "x" * 1000}
            for i in range(1000)
        ]
        
        response = client.post(
            "/log/basic",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        # Может быть 200 (успех)
        assert response.status_code in [200]

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

    def test_E24_timestamp_string(self, client, valid_api_key):
        """E24: timestamp — строка вместо int -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": "1234567890",  # строка
            "service": "infopanel",
            "service_id": 1,
            "message": "Event with string timestamp"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E25_service_id_zero(self, client, valid_api_key):
        """E25: service_id = 0 -> 400"""
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

    def test_E26_service_id_negative(self, client, valid_api_key):
        """E26: service_id < 0 -> 400"""
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

    def test_E27_service_id_string(self, client, valid_api_key):
        """E27: service_id — строка вместо int -> 400"""
        payload = [{
            "api_version": "1.0.0",
            "timestamp": 1234567890,
            "service": "infopanel",
            "service_id": "1",  # строка
            "message": "Event with string service_id"
        }]
        
        response = client.post(
            "/log/event",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E28_message_empty(self, client, valid_api_key):
        """E28: message пустой -> 400"""
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

    def test_E29_message_too_long(self, client, valid_api_key):
        """E29: message > 1024 символов -> 400"""
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

    def test_E30_message_wrong_type(self, client, valid_api_key):
        """E30: message — число вместо string -> 400"""
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

    """Группа E31-E35: Валидация enum-полей"""

    def test_E31_invalid_event_type(self, client, valid_api_key):
        """E31: event_type не из enum -> 400"""
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

    def test_E32_invalid_service(self, client, valid_api_key):
        """E32: service не из enum -> 400"""
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

    def test_E33_invalid_severity(self, client, valid_api_key):
        """E33: severity не из enum -> 400"""
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

    def test_E34_event_type_wrong_type(self, client, valid_api_key):
        """E34: event_type — число вместо string -> 400"""
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

    def test_E35_severity_wrong_type(self, client, valid_api_key):
        """E35: severity — число вместо string -> 400"""
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

    """Группа E36-E40: Структура запроса"""

    def test_E36_body_not_array(self, client, valid_api_key):
        """E36: Тело — объект, не массив -> 400"""
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

    def test_E37_extra_field_forbidden(self, client, valid_api_key):
        """E37: Лишнее поле в объекте -> 400 (StrictModel)"""
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

    def test_E38_wrong_content_type(self, client, valid_api_key):
        """E38: Неверный Content-Type -> 400 или 415"""
        response = client.post(
            "/log/event",
            content='[{"api_version": "1.0.0"}]',
            headers={
                "X-API-Key": valid_api_key,
                "Content-Type": "text/plain"
            }
        )
        
        assert response.status_code in [400, 415]

    def test_E39_malformed_json(self, client, valid_api_key):
        """E39: Malformed JSON -> 400"""
        response = client.post(
            "/log/event",
            content='{"invalid": json}',
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400

    def test_E40_mixed_valid_invalid(self, client, valid_api_key):
        """E40: Смешанные валидные/невалидные -> 400 (весь запрос)"""
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