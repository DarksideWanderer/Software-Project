#include <iostream>
#include <string>
#include <cstring>
#include <vector>

#include "devices/AirConditioner.h"
#include "devices/AirConditionerAdapter.h"
#include "devices/Light.h"
#include "devices/LightAdapter.h"
#include "devices/TV.h"
#include "devices/TVAdapter.h"
#include "devices/GenericDevice.h"
#include "devices/GenericDeviceAdapter.h"
#include "core/CommandRegistry.h"
#include "core/Logger.h"
#include "core/Protocol.h"
#include "core/HubClient.h"

// ═══════════════════════════════════════════════════════
//  智能家居设备仿真器 — 多设备独立进程
//
//  每个设备作为独立 TCP 客户端连接到后端 Hub，
//  自动发送注册信息。后续只需替换 HubClient 即可
//  升级为 WiFi/MQTT。
//
//  用法:
//    simulator --device ac    启动空调进程（TCP 注册）
//    simulator --device light 启动灯光进程（TCP 注册）
//    simulator --device tv    启动电视进程（TCP 注册）
//    simulator                演示模式
// ═══════════════════════════════════════════════════════

static const char* GetArg(int argc, char* argv[], const char* key) {
    for (int i = 1; i < argc - 1; ++i)
        if (strcmp(argv[i], key) == 0) return argv[i + 1];
    return nullptr;
}

// ── 通用：创建设备 → 注册适配器 → 连接 Hub ──
template<typename Device, typename Adapter>
int RunDevice(const std::string& dev_type, const std::string& dev_id,
              const std::string& host = "127.0.0.1", int port = 9760) {
    Device dev;
    CommandRegistry registry;
    Adapter::Register(registry, dev);

    HubClient client(registry, dev_type, dev_id);
    return client.Run(host, port) ? 0 : 1;
}

int RunGenericDevice(
    const std::string& dev_type,
    const std::string& dev_id,
    const std::string& description,
    const std::vector<GenericValueDef>& values,
    bool default_on = false,
    const std::string& host = "127.0.0.1",
    int port = 9760) {
    Devices::GenericDevice dev(default_on);
    CommandRegistry registry;
    GenericDeviceAdapter::Register(registry, dev, dev_type, description, dev_id, values);

    HubClient client(registry, dev_type, dev_id);
    return client.Run(host, port) ? 0 : 1;
}

int main(int argc, char* argv[]) {
    const char* dev_type = GetArg(argc, argv, "--device");
    const char* dev_id_arg = GetArg(argc, argv, "--id");

    if (dev_type) {
        auto chosen_id = [&](const std::string& default_id) {
            return dev_id_arg ? std::string(dev_id_arg) : default_id;
        };

        if (strcmp(dev_type, "ac") == 0)
            return RunDevice<Devices::AirConditioner, AirConditionerAdapter>("air_conditioner", chosen_id("ac-001"));
        if (strcmp(dev_type, "light") == 0)
            return RunDevice<Devices::Light, LightAdapter>("light", chosen_id("light-001"));
        if (strcmp(dev_type, "tv") == 0)
            return RunDevice<Devices::TV, TVAdapter>("tv", chosen_id("tv-001"));
        if (strcmp(dev_type, "fridge") == 0)
            return RunGenericDevice("fridge", chosen_id("fridge-001"), "Fridge", {
                {"set_temperature", "temperature", "Set fridge temperature", 2, 8, 4},
            }, true);
        if (strcmp(dev_type, "washer") == 0)
            return RunGenericDevice("washer", chosen_id("washer-001"), "Washer", {
                {"set_progress", "progress", "Set washing progress", 0, 100, 0},
            });
        if (strcmp(dev_type, "heater") == 0)
            return RunGenericDevice("water_heater", chosen_id("heater-001"), "Water heater", {
                {"set_temperature", "temperature", "Set water temperature", 35, 65, 45},
            });
        if (strcmp(dev_type, "purifier") == 0)
            return RunGenericDevice("air_purifier", chosen_id("purifier-001"), "Air purifier", {
                {"set_speed", "speed", "Set purifier speed", 1, 5, 1},
                {"set_air_quality", "air_quality", "Set air quality", 0, 500, 42},
            });
        if (strcmp(dev_type, "curtain") == 0)
            return RunGenericDevice("curtain", chosen_id("curtain-001"), "Curtain", {
                {"set_open_percent", "percent", "Set open percent", 0, 100, 100},
            }, true);
        if (strcmp(dev_type, "socket") == 0)
            return RunGenericDevice("socket", chosen_id("socket-001"), "Socket", {});
        if (strcmp(dev_type, "robot") == 0)
            return RunGenericDevice("robot_vacuum", chosen_id("robot-001"), "Robot vacuum", {
                {"set_battery", "battery", "Set battery", 0, 100, 82},
            });

        std::cerr << "Unknown device: " << dev_type
                  << "\nAvailable: ac, light, tv, fridge, washer, heater, purifier, curtain, socket, robot\n";
        return 1;
    }

    // ── 演示模式 ──
    Devices::AirConditioner ac;
    ac.Execute(Commands::TurnOn{});
    ac.Execute(Commands::SetTemperature{24});
    ac.Execute(Commands::TurnOff{});
    std::cout << "Demo: AC cycled on(24°C)→off. Use --device <type> to run.\n";
    return 0;
}
