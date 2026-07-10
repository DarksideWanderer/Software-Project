#ifndef GENERIC_DEVICE_ADAPTER_H
#define GENERIC_DEVICE_ADAPTER_H

#include <sstream>
#include <string>
#include <vector>
#include "GenericDevice.h"
#include "../core/CommandRegistry.h"

struct GenericValueDef {
    std::string command;
    std::string field;
    std::string description;
    int min;
    int max;
    int default_value;
};

class GenericDeviceAdapter {
public:
    static void Register(
        CommandRegistry& registry,
        Devices::GenericDevice& device,
        const std::string& type,
        const std::string& description,
        const std::string& device_id,
        const std::vector<GenericValueDef>& values
    ) {
        registry.SetDeviceMeta(type, description, device_id);
        registry.SetStateFieldsJson(StateFields(values));

        registry.Register({"turn_on", "Turn on device", {}}, [&](const std::vector<std::string>&) {
            device.TurnOn();
            return Resp(true, "Device turned on", device, type, device_id, values);
        });
        registry.Register({"turn_off", "Turn off device", {}}, [&](const std::vector<std::string>&) {
            device.TurnOff();
            return Resp(true, "Device turned off", device, type, device_id, values);
        });
        for (const auto& value : values) {
            device.SetInitialValue(value.field, value.default_value);
            registry.Register(
                {value.command, value.description, {{value.field, ParamType::INT, value.description}}},
                [&device, type, device_id, values, value](const std::vector<std::string>& args) {
                    if (args.empty()) return Resp(false, value.field + " required", device, type, device_id, values);
                    int number = std::stoi(args[0]);
                    if (number < value.min || number > value.max) {
                        return Resp(false, value.field + " out of range", device, type, device_id, values);
                    }
                    bool was_on = device.IsOn();
                    device.SetValue(value.field, number);
                    if (!was_on) return Resp(false, "Device is off", device, type, device_id, values);
                    return Resp(true, value.field + " updated", device, type, device_id, values);
                }
            );
        }
        registry.Register({"get_state", "Get state", {}}, [&](const std::vector<std::string>&) {
            return Resp(true, "OK", device, type, device_id, values);
        });
    }

private:
    static std::string StateFields(const std::vector<GenericValueDef>& values) {
        std::ostringstream os;
        os << R"({"is_on":"bool")";
        for (const auto& value : values) {
            os << R"(,")" << value.field << R"(":"int")";
        }
        os << "}";
        return os.str();
    }

    static std::string Esc(const std::string& s) {
        std::string out;
        for (char c : s) {
            switch (c) {
                case '"': out += "\\\""; break;
                case '\\': out += "\\\\"; break;
                default: out += c;
            }
        }
        return out;
    }

    static std::string State(
        const Devices::GenericDevice& device,
        const std::string& type,
        const std::string& device_id,
        const std::vector<GenericValueDef>& values
    ) {
        std::ostringstream os;
        os << R"({"device_id":")" << Esc(device_id) << R"(","device_type":")" << Esc(type) << R"(",)"
           << R"("is_on":)" << (device.IsOn() ? "true" : "false");
        for (const auto& value : values) {
            os << R"(,")" << value.field << R"(":)" << device.GetValue(value.field, value.default_value);
        }
        os << "}";
        return os.str();
    }

    static std::string Resp(
        bool ok,
        const std::string& message,
        const Devices::GenericDevice& device,
        const std::string& type,
        const std::string& device_id,
        const std::vector<GenericValueDef>& values
    ) {
        std::ostringstream os;
        os << R"({"success":)" << (ok ? "true" : "false")
           << R"(,"message":")" << Esc(message)
           << R"(","state":)" << State(device, type, device_id, values) << "}";
        return os.str();
    }
};

#endif
