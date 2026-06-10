#ifndef AIR_CONDITIONER_H
#define AIR_CONDITIONER_H

namespace Commands {
    struct TurnOn {};
    struct TurnOff {};
    struct SetTemperature { int temperature; };
}

namespace Devices {

/// @brief 空调设备 — 纯设备逻辑，不涉及任何协议/JSON/IO
class AirConditioner {
private:
    bool is_on_;
    int temperature_;

public:
    AirConditioner() : is_on_(false), temperature_(24) {}

    /// 打开
    void Execute(Commands::TurnOn) {
        is_on_ = true;
    }

    /// 关闭
    void Execute(Commands::TurnOff) {
        is_on_ = false;
    }

    /// 设置温度（仅开机有效）
    void Execute(Commands::SetTemperature cmd) {
        if (!is_on_) return;
        temperature_ = cmd.temperature;
    }

    // ── 状态查询（供外部使用，不参与逻辑） ──
    bool IsOn()    const { return is_on_; }
    int  GetTemperature() const { return temperature_; }
};

} // namespace Devices

#endif // AIR_CONDITIONER_H
