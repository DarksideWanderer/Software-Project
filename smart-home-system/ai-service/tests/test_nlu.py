from app.nlu import parse_text
from app.schemas import NluContext


def test_turn_on_living_room_light():
    result = parse_text("打开客厅灯")

    assert result.intent == "device_control"
    assert result.slots.device_type == "light"
    assert result.slots.location == "living_room"
    assert result.slots.action == "turn_on"
    assert result.need_clarification is False


def test_set_bedroom_air_conditioner_temperature():
    result = parse_text("把卧室空调调到26度")

    assert result.intent == "device_control"
    assert result.slots.device_type == "air_conditioner"
    assert result.slots.location == "bedroom"
    assert result.slots.action == "set_temperature"
    assert result.slots.value == 26
    assert result.slots.unit == "celsius"


def test_close_curtain_with_context_location():
    result = parse_text("关闭窗帘", NluContext(last_location="living_room"))

    assert result.intent == "device_control"
    assert result.slots.device_type == "curtain"
    assert result.slots.location == "living_room"
    assert result.slots.action == "close"


def test_query_light_status():
    result = parse_text("查询客厅灯状态")

    assert result.intent == "device_query"
    assert result.slots.device_type == "light"
    assert result.slots.action == "query_status"


def test_weather_query_city():
    result = parse_text("今天上海天气怎么样")

    assert result.intent == "weather_query"
    assert result.slots.city == "上海"
    assert result.need_clarification is False


def test_reminder_create():
    result = parse_text("提醒我晚上八点吃药")

    assert result.intent == "reminder_create"
    assert result.slots.datetime == "晚上八点"
    assert result.slots.content == "吃药"
    assert result.need_clarification is False


def test_missing_location_needs_clarification():
    result = parse_text("打开灯")

    assert result.intent == "device_control"
    assert result.slots.device_type == "light"
    assert result.slots.action == "turn_on"
    assert result.need_clarification is True


def test_unknown_intent():
    result = parse_text("给我讲个故事")

    assert result.intent == "unknown"
    assert result.need_clarification is False


def test_turn_off_living_room_light():
    result = parse_text("关闭客厅灯")

    assert result.intent == "device_control"
    assert result.slots.device_type == "light"
    assert result.slots.location == "living_room"
    assert result.slots.action == "turn_off"


def test_turn_on_bedroom_light():
    result = parse_text("打开卧室灯")

    assert result.intent == "device_control"
    assert result.slots.device_type == "light"
    assert result.slots.location == "bedroom"
    assert result.slots.action == "turn_on"


def test_set_living_room_light_brightness():
    result = parse_text("把客厅灯亮度调到80")

    assert result.intent == "device_control"
    assert result.slots.device_type == "light"
    assert result.slots.location == "living_room"
    assert result.slots.action == "set_brightness"
    assert result.slots.value == 80
    assert result.slots.unit == "percent"


def test_turn_on_bedroom_air_conditioner():
    result = parse_text("打开卧室空调")

    assert result.intent == "device_control"
    assert result.slots.device_type == "air_conditioner"
    assert result.slots.location == "bedroom"
    assert result.slots.action == "turn_on"


def test_turn_off_bedroom_air_conditioner():
    result = parse_text("关闭卧室空调")

    assert result.intent == "device_control"
    assert result.slots.device_type == "air_conditioner"
    assert result.slots.location == "bedroom"
    assert result.slots.action == "turn_off"


def test_increase_air_conditioner_temperature_with_context():
    result = parse_text(
        "空调调高两度",
        NluContext(last_device_type="air_conditioner", last_location="bedroom"),
    )

    assert result.intent == "device_control"
    assert result.slots.device_type == "air_conditioner"
    assert result.slots.location == "bedroom"
    assert result.slots.action == "increase_temperature"
    assert result.slots.value == 2
    assert result.slots.unit == "celsius"


def test_open_living_room_curtain():
    result = parse_text("打开客厅窗帘")

    assert result.intent == "device_control"
    assert result.slots.device_type == "curtain"
    assert result.slots.location == "living_room"
    assert result.slots.action == "open"


def test_close_bedroom_curtain():
    result = parse_text("关闭卧室窗帘")

    assert result.intent == "device_control"
    assert result.slots.device_type == "curtain"
    assert result.slots.location == "bedroom"
    assert result.slots.action == "close"


def test_set_curtain_half_open_with_context():
    result = parse_text("窗帘开一半", NluContext(last_location="living_room"))

    assert result.intent == "device_control"
    assert result.slots.device_type == "curtain"
    assert result.slots.location == "living_room"
    assert result.slots.action == "set_open_percent"
    assert result.slots.value == 50
    assert result.slots.unit == "percent"


def test_weather_query_tomorrow_beijing():
    result = parse_text("明天北京天气怎么样")

    assert result.intent == "weather_query"
    assert result.slots.city == "北京"
    assert result.need_clarification is False


def test_reminder_create_after_ten_minutes():
    result = parse_text("提醒我十分钟后关空调")

    assert result.intent == "reminder_create"
    assert result.slots.datetime == "十分钟后"
    assert result.slots.content == "关空调"
    assert result.need_clarification is False
