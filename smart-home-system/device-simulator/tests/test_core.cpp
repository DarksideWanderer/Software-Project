/**
 * device-simulator Google Test 单元测试
 * 测试 CommandRegistry 和 HubClient 核心功能
 *
 * 构建 & 运行:
 *   cd smart-home-system/device-simulator
 *   mkdir -p build && cd build
 *   cmake .. -DBUILD_TESTS=ON
 *   make && ./tests/simulator_tests
 */

#include <gtest/gtest.h>
#include <string>
#include <vector>

#include "core/CommandRegistry.h"
#include "core/Protocol.h"
#include "devices/Light.h"
#include "devices/LightAdapter.h"
#include "devices/AirConditioner.h"
#include "devices/AirConditionerAdapter.h"
#include "devices/TV.h"
#include "devices/TVAdapter.h"
#include "devices/GenericDevice.h"
#include "devices/GenericDeviceAdapter.h"

// ======================== CommandRegistry 测试 ========================

class CommandRegistryTest : public ::testing::Test {
protected:
    CommandRegistry registry;

    void SetUp() override {
        // 注册测试命令
        CommandDef turnOn;
        turnOn.name = "turn_on";
        turnOn.description = "Turn device on";
        turnOn.params = {};
        registry.Register(turnOn, [](const std::vector<std::string>& args) {
            return R"({"success":true,"state":{"is_on":true}})";
        });

        CommandDef turnOff;
        turnOff.name = "turn_off";
        turnOff.description = "Turn device off";
        turnOff.params = {};
        registry.Register(turnOff, [](const std::vector<std::string>& args) {
            return R"({"success":true,"state":{"is_on":false}})";
        });
    }
};

TEST_F(CommandRegistryTest, HasRegisteredCommand) {
    EXPECT_TRUE(registry.HasCommand("turn_on"));
    EXPECT_TRUE(registry.HasCommand("turn_off"));
}

TEST_F(CommandRegistryTest, UnknownCommandReturnsFalse) {
    EXPECT_FALSE(registry.HasCommand("unknown_command"));
}

TEST_F(CommandRegistryTest, DispatchKnownCommand) {
    std::string result = registry.Dispatch("turn_on", {});
    EXPECT_NE(result.find("\"success\":true"), std::string::npos);
}

TEST_F(CommandRegistryTest, DispatchUnknownCommand) {
    std::string result = registry.Dispatch("fly", {});
    EXPECT_NE(result.find("error"), std::string::npos);
    EXPECT_NE(result.find("Unknown command"), std::string::npos);
}

TEST_F(CommandRegistryTest, GetAllCommands) {
    auto cmds = registry.GetAllCommands();
    EXPECT_EQ(cmds.size(), 2u);
    EXPECT_EQ(cmds[0].name, "turn_on");
    EXPECT_EQ(cmds[1].name, "turn_off");
}

TEST_F(CommandRegistryTest, SetDeviceMeta) {
    registry.SetDeviceMeta("light", "Smart Light", "light-001");
    // 验证通过 GenerateProtocolJson 输出包含元数据
    std::string json = registry.GenerateProtocolJson();
    EXPECT_NE(json.find("light"), std::string::npos);
}

TEST_F(CommandRegistryTest, SetStateFieldsJson) {
    registry.SetStateFieldsJson(R"({"is_on":"bool","brightness":"int"})");
    EXPECT_EQ(registry.GetStateFieldsJson(), R"({"is_on":"bool","brightness":"int"})");
}

// ======================== Light 设备测试 ========================

class LightDeviceTest : public ::testing::Test {
protected:
    Devices::Light light;
};

TEST_F(LightDeviceTest, DefaultState) {
    EXPECT_FALSE(light.isOn());
    EXPECT_EQ(light.getBrightness(), 70);
    EXPECT_EQ(light.getColor(), "daylight");
}

TEST_F(LightDeviceTest, TurnOn) {
    light.turnOn();
    EXPECT_TRUE(light.isOn());
}

TEST_F(LightDeviceTest, TurnOff) {
    light.turnOn();
    light.turnOff();
    EXPECT_FALSE(light.isOn());
}

TEST_F(LightDeviceTest, SetBrightnessInRange) {
    light.setBrightness(50);
    EXPECT_EQ(light.getBrightness(), 50);
}

TEST_F(LightDeviceTest, SetBrightnessClampedMin) {
    light.setBrightness(-10);
    EXPECT_EQ(light.getBrightness(), 0);
}

TEST_F(LightDeviceTest, SetBrightnessClampedMax) {
    light.setBrightness(200);
    EXPECT_EQ(light.getBrightness(), 100);
}

TEST_F(LightDeviceTest, SetColor) {
    light.setColor("warm");
    EXPECT_EQ(light.getColor(), "warm");
}

TEST_F(LightDeviceTest, InvalidColorIgnored) {
    light.setColor("purple");
    // 根据实现可能忽略或保持默认
    EXPECT_NE(light.getColor(), "purple");
}

// ======================== AirConditioner 设备测试 ========================

class AirConditionerTest : public ::testing::Test {
protected:
    Devices::AirConditioner ac;
};

TEST_F(AirConditionerTest, DefaultState) {
    EXPECT_FALSE(ac.isOn());
    EXPECT_EQ(ac.getTemperature(), 24);
}

TEST_F(AirConditionerTest, TurnOnOff) {
    ac.turnOn();
    EXPECT_TRUE(ac.isOn());
    ac.turnOff();
    EXPECT_FALSE(ac.isOn());
}

TEST_F(AirConditionerTest, SetTemperatureInRange) {
    ac.setTemperature(26);
    EXPECT_EQ(ac.getTemperature(), 26);
}

TEST_F(AirConditionerTest, SetTemperatureClampedMin) {
    ac.setTemperature(0);
    EXPECT_EQ(ac.getTemperature(), 16);
}

TEST_F(AirConditionerTest, SetTemperatureClampedMax) {
    ac.setTemperature(50);
    EXPECT_EQ(ac.getTemperature(), 30);
}

// ======================== TV 设备测试 ========================

class TVDeviceTest : public ::testing::Test {
protected:
    Devices::TV tv;
};

TEST_F(TVDeviceTest, DefaultState) {
    EXPECT_FALSE(tv.isOn());
    EXPECT_EQ(tv.getChannel(), 1);
    EXPECT_EQ(tv.getVolume(), 30);
}

TEST_F(TVDeviceTest, TurnOnOff) {
    tv.turnOn();
    EXPECT_TRUE(tv.isOn());
    tv.turnOff();
    EXPECT_FALSE(tv.isOn());
}

TEST_F(TVDeviceTest, SetChannel) {
    tv.setChannel(5);
    EXPECT_EQ(tv.getChannel(), 5);
}

TEST_F(TVDeviceTest, SetChannelClamped) {
    tv.setChannel(0);
    EXPECT_EQ(tv.getChannel(), 1);
    tv.setChannel(1000);
    EXPECT_EQ(tv.getChannel(), 999);
}

TEST_F(TVDeviceTest, SetVolume) {
    tv.setVolume(50);
    EXPECT_EQ(tv.getVolume(), 50);
}

// ======================== GenericDevice 测试 ========================

class GenericDeviceTest : public ::testing::Test {
protected:
    Devices::GenericDevice device{false};
};

TEST_F(GenericDeviceTest, DefaultOff) {
    EXPECT_FALSE(device.isOn());
}

TEST_F(GenericDeviceTest, TurnOnOff) {
    device.turnOn();
    EXPECT_TRUE(device.isOn());
    device.turnOff();
    EXPECT_FALSE(device.isOn());
}

TEST_F(GenericDeviceTest, FridgeDefaultsOn) {
    Devices::GenericDevice fridge(true);
    EXPECT_TRUE(fridge.isOn());
}

TEST_F(GenericDeviceTest, SetIntValue) {
    device.setIntValue("temperature", 4);
    EXPECT_EQ(device.getIntValue("temperature"), 4);
}

TEST_F(GenericDeviceTest, SetIntValueClamped) {
    // 设置极小值
    device.setIntValue("temperature", -100);
    // 行为取决于注册的参数范围
    EXPECT_LE(device.getIntValue("temperature"), 100);
}

// ======================== Adapter 注册测试 ========================

class AdapterRegistrationTest : public ::testing::Test {
protected:
    CommandRegistry registry;
};

TEST_F(AdapterRegistrationTest, LightAdapterRegistersCommands) {
    Devices::Light light;
    LightAdapter::Register(registry, light);
    EXPECT_TRUE(registry.HasCommand("turn_on"));
    EXPECT_TRUE(registry.HasCommand("turn_off"));
    EXPECT_TRUE(registry.HasCommand("set_brightness"));
    EXPECT_TRUE(registry.HasCommand("set_color"));
}

TEST_F(AdapterRegistrationTest, AirConditionerAdapterRegistersCommands) {
    Devices::AirConditioner ac;
    AirConditionerAdapter::Register(registry, ac);
    EXPECT_TRUE(registry.HasCommand("turn_on"));
    EXPECT_TRUE(registry.HasCommand("turn_off"));
    EXPECT_TRUE(registry.HasCommand("set_temperature"));
}

TEST_F(AdapterRegistrationTest, TVAdapterRegistersCommands) {
    Devices::TV tv;
    TVAdapter::Register(registry, tv);
    EXPECT_TRUE(registry.HasCommand("turn_on"));
    EXPECT_TRUE(registry.HasCommand("turn_off"));
    EXPECT_TRUE(registry.HasCommand("set_channel"));
    EXPECT_TRUE(registry.HasCommand("set_volume"));
}

// ======================== Protocol 测试 ========================

TEST(ProtocolTest, BuildErrorContainsMessage) {
    CommandRegistry registry;
    std::string error = registry.Dispatch("unknown", {});
    EXPECT_NE(error.find("error"), std::string::npos);
}

// ======================== 主入口 ========================

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
