#ifndef LIGHT_ADAPTER_H
#define LIGHT_ADAPTER_H

#include <sstream>
#include "Light.h"
#include "../core/CommandRegistry.h"
#include "../core/Logger.h"

class LightAdapter {
public:
    static void Register(CommandRegistry& r, Devices::Light& light) {
        r.SetDeviceMeta("light", "灯光设备", "light-001");
        r.SetStateFieldsJson(
            R"({"is_on":"bool","brightness":"int","color":"string"})");

        r.Register({"turn_on", "打开灯光", {}}, [&](auto&) {
            light.Execute(Commands::TurnOn{});
            return Ok("Light turned on", light);
        });
        r.Register({"turn_off", "关闭灯光", {}}, [&](auto&) {
            light.Execute(Commands::TurnOff{});
            return Ok("Light turned off", light);
        });
        r.Register({"set_brightness", "设置亮度 0-100",
                    {{"brightness", ParamType::INT, "亮度"}}}, [&](auto& a) {
            if (a.empty()) return Err("brightness required", light);
            bool was = light.IsOn();
            light.Execute(Commands::SetBrightness{std::stoi(a[0])});
            if (!was) return Err("Light is off", light);
            return Ok("Brightness " + a[0], light);
        });
        r.Register({"set_color", "设置色温",
                    {{"color", ParamType::STRING, "warm/cool/daylight"}}}, [&](auto& a) {
            if (a.empty()) return Err("color required", light);
            bool was = light.IsOn();
            light.Execute(Commands::SetColor{a[0]});
            if (!was) return Err("Light is off", light);
            return Ok("Color " + a[0], light);
        });
        r.Register({"get_state", "查询状态", {}}, [&](auto&) {
            return Ok("OK", light);
        });
    }

private:
    static std::string Esc(const std::string& s) {
        std::string o; for (char c:s)
            switch(c){case'"':o+="\\\"";break;case'\\':o+="\\\\";break;default:o+=c;}
        return o;
    }
    static std::string State(const Devices::Light& l) {
        std::ostringstream os;
        os << R"({"device_id":"light-001","device_type":"light",)"
           << R"("is_on":)" << (l.IsOn()?"true":"false") << ","
           << R"("brightness":)" << l.Brightness() << ","
           << R"("color":")" << l.Color() << "\"}";
        return os.str();
    }
    static std::string Ok(const std::string& m, const Devices::Light& l) {
        std::ostringstream os;
        os << R"({"success":true,"message":")" << Esc(m)
           << R"(","state":)" << State(l) << "}";
        return os.str();
    }
    static std::string Err(const std::string& m, const Devices::Light& l) {
        std::ostringstream os;
        os << R"({"success":false,"message":")" << Esc(m)
           << R"(","state":)" << State(l) << "}";
        return os.str();
    }
};

#endif // LIGHT_ADAPTER_H
