#ifndef GENERIC_DEVICE_H
#define GENERIC_DEVICE_H

#include <map>
#include <string>

namespace Devices {

class GenericDevice {
    bool is_on_;
    std::map<std::string, int> values_;

public:
    explicit GenericDevice(bool default_on = false) : is_on_(default_on) {}

    void TurnOn() { is_on_ = true; }
    void TurnOff() { is_on_ = false; }
    bool IsOn() const { return is_on_; }

    void SetValue(const std::string& key, int value) {
        if (!is_on_) return;
        values_[key] = value;
    }

    void SetInitialValue(const std::string& key, int value) {
        values_[key] = value;
    }

    int GetValue(const std::string& key, int fallback) const {
        auto it = values_.find(key);
        return it == values_.end() ? fallback : it->second;
    }
};

} // namespace Devices

#endif
