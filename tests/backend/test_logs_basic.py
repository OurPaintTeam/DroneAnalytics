import pytest

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
