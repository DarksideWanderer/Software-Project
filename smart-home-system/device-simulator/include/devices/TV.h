#ifndef TV_H
#define TV_H

namespace Commands {
    struct SetChannel { int channel; };
    struct SetVolume  { int volume; };
}

namespace Devices {

/// @brief 电视 — 纯设备逻辑（与 AirConditioner 风格统一）
class TV {
    bool is_on_ = false;
    int channel_ = 1;
    int volume_ = 30;

public:
    void Execute(Commands::TurnOn)      { is_on_ = true; }
    void Execute(Commands::TurnOff)     { is_on_ = false; }
    void Execute(Commands::SetChannel c){ if (is_on_) channel_ = c.channel; }
    void Execute(Commands::SetVolume v) { if (is_on_) volume_ = v.volume; }

    bool IsOn()    const { return is_on_; }
    int  Channel() const { return channel_; }
    int  Volume()  const { return volume_; }
};

} // namespace Devices
#endif
