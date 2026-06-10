#include <iostream>
#include <string>
#include <cstring>

#include "devices/AirConditioner.h"
#include "devices/AirConditionerAdapter.h"
#include "devices/Light.h"
#include "devices/LightAdapter.h"
#include "devices/TV.h"
#include "devices/TVAdapter.h"
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

int main(int argc, char* argv[]) {
    const char* dev_type = GetArg(argc, argv, "--device");

    if (dev_type) {
        if (strcmp(dev_type, "ac") == 0)
            return RunDevice<Devices::AirConditioner, AirConditionerAdapter>("air_conditioner", "ac-001");
        if (strcmp(dev_type, "light") == 0)
            return RunDevice<Devices::Light, LightAdapter>("light", "light-001");
        if (strcmp(dev_type, "tv") == 0)
            return RunDevice<Devices::TV, TVAdapter>("tv", "tv-001");

        std::cerr << "Unknown device: " << dev_type << "\nAvailable: ac, light, tv\n";
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
