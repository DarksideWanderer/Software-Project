#ifndef LIGHT_H
#define LIGHT_H

#include <string>

namespace Commands {
    struct SetBrightness { int brightness; };
    struct SetColor      { std::string color; };
}

namespace Devices {

/// @brief 智能灯 — 纯设备逻辑（与 AirConditioner 风格统一）
class Light {
    bool is_on_ = false;
    int brightness_ = 100;
    std::string color_ = "warm";

public:
    void Execute(Commands::TurnOn)           { is_on_ = true; }
    void Execute(Commands::TurnOff)          { is_on_ = false; }
    void Execute(Commands::SetBrightness b)  { if (is_on_) brightness_ = b.brightness; }
    void Execute(Commands::SetColor c)       { if (is_on_) color_ = c.color; }

    bool        IsOn()       const { return is_on_; }
    int         Brightness() const { return brightness_; }
    std::string Color()      const { return color_; }
};

} // namespace Devices
#endif
