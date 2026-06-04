#ifndef TV_ADAPTER_H
#define TV_ADAPTER_H

#include <sstream>
#include "TV.h"
#include "../core/CommandRegistry.h"
#include "../core/Logger.h"

class TVAdapter {
public:
    static void Register(CommandRegistry& r, Devices::TV& tv) {
        r.SetStateFieldsJson(
            R"({"is_on":"bool","channel":"int","volume":"int"})");

        r.Register({"turn_on", "打开电视", {}}, [&](auto&) {
            tv.Execute(Commands::TurnOn{});
            return Ok("TV turned on", tv);
        });
        r.Register({"turn_off", "关闭电视", {}}, [&](auto&) {
            tv.Execute(Commands::TurnOff{});
            return Ok("TV turned off", tv);
        });
        r.Register({"set_channel", "切换频道 1-999",
                    {{"channel", ParamType::INT, "频道"}}}, [&](auto& a) {
            if (a.empty()) return Err("channel required", tv);
            bool was = tv.IsOn();
            tv.Execute(Commands::SetChannel{std::stoi(a[0])});
            if (!was) return Err("TV is off", tv);
            return Ok("Channel " + a[0], tv);
        });
        r.Register({"set_volume", "设置音量 0-100",
                    {{"volume", ParamType::INT, "音量"}}}, [&](auto& a) {
            if (a.empty()) return Err("volume required", tv);
            bool was = tv.IsOn();
            tv.Execute(Commands::SetVolume{std::stoi(a[0])});
            if (!was) return Err("TV is off", tv);
            return Ok("Volume " + a[0], tv);
        });
        r.Register({"get_state", "查询状态", {}}, [&](auto&) {
            return Ok("OK", tv);
        });
    }

private:
    static std::string Esc(const std::string& s) {
        std::string o; for (char c:s)
            switch(c){case'"':o+="\\\"";break;case'\\':o+="\\\\";break;default:o+=c;}
        return o;
    }
    static std::string State(const Devices::TV& tv) {
        std::ostringstream os;
        os << R"({"device_id":"tv-001","device_type":"tv",)"
           << R"("is_on":)" << (tv.IsOn()?"true":"false") << ","
           << R"("channel":)" << tv.Channel() << ","
           << R"("volume":)" << tv.Volume() << "}";
        return os.str();
    }
    static std::string Ok(const std::string& m, const Devices::TV& tv) {
        std::ostringstream os;
        os << R"({"success":true,"message":")" << Esc(m)
           << R"(","state":)" << State(tv) << "}";
        return os.str();
    }
    static std::string Err(const std::string& m, const Devices::TV& tv) {
        std::ostringstream os;
        os << R"({"success":false,"message":")" << Esc(m)
           << R"(","state":)" << State(tv) << "}";
        return os.str();
    }
};

#endif // TV_ADAPTER_H
