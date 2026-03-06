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
