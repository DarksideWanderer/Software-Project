#ifndef AIR_CONDITIONER_ADAPTER_H
#define AIR_CONDITIONER_ADAPTER_H

#include <sstream>
#include "AirConditioner.h"
#include "../core/CommandRegistry.h"
#include "../core/Logger.h"

/// @brief AirConditioner 的命令注册适配器
///         负责把 AirConditioner 的命令注册到 CommandRegistry
class AirConditionerAdapter {
public:
    static void Register(CommandRegistry& registry, Devices::AirConditioner& ac) {
        registry.SetStateFieldsJson(
            R"({"is_on":"bool","temperature":"int"})");

        registry.Register(
            {"turn_on", "打开空调", {}},
            [&ac](const std::vector<std::string>&) -> std::string {
                ac.Execute(Commands::TurnOn{});
                return Resp(true, "AC turned on. Temp: " + std::to_string(ac.GetTemperature()) + "°C", ac);
            }
        );
        registry.Register(
            {"turn_off", "关闭空调", {}},
            [&ac](const std::vector<std::string>&) -> std::string {
                ac.Execute(Commands::TurnOff{});
                return Resp(true, "AC turned off", ac);
            }
        );
        registry.Register(
            {"set_temperature", "设置温度 16-30°C",
             {{"temperature", ParamType::INT, "目标温度"}}},
            [&ac](const std::vector<std::string>& args) -> std::string {
                if (args.empty()) return Resp(false, "temperature required", ac);
                int t = std::stoi(args[0]);
                if (t < 16 || t > 30) return Resp(false, "temperature 16-30", ac);
                bool was = ac.IsOn();
                ac.Execute(Commands::SetTemperature{t});
                if (!was) return Resp(false, "AC is off", ac);
                return Resp(true, "Temperature set to " + std::to_string(t) + "°C", ac);
            }
        );
        registry.Register(
            {"get_state", "查询状态", {}},
            [&ac](const std::vector<std::string>&) -> std::string {
                return Resp(true, "OK", ac);
            }
        );
    }

private:
    static std::string Esc(const std::string& s) {
        std::string o; for (char c:s)
            switch(c){case'"':o+="\\\"";break;case'\\':o+="\\\\";break;default:o+=c;}
        return o;
    }
    static std::string State(const Devices::AirConditioner& ac) {
        std::ostringstream os;
        os << R"({"device_id":"ac-001","device_type":"air_conditioner",)"
           << R"("is_on":)" << (ac.IsOn()?"true":"false") << ","
           << R"("temperature":)" << ac.GetTemperature() << "}";
        return os.str();
    }
    static std::string Resp(bool ok, const std::string& m, const Devices::AirConditioner& ac) {
        std::ostringstream os;
        os << R"({"success":)" << (ok?"true":"false")
           << R"(,"message":")" << Esc(m)
           << R"(","state":)" << State(ac) << "}";
        return os.str();
    }
};

#endif // AIR_CONDITIONER_ADAPTER_H
