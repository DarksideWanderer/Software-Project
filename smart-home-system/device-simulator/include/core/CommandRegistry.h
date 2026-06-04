#ifndef COMMAND_REGISTRY_H
#define COMMAND_REGISTRY_H

#include <functional>
#include <map>
#include <string>
#include <sstream>
#include <vector>
#include "Logger.h"

/// @brief 参数类型描述
enum class ParamType { INT, FLOAT, STRING, BOOL, NONE };

struct ParamDef {
    std::string name;
    ParamType   type;
    std::string description;
};

struct CommandDef {
    std::string name;
    std::string description;
    std::vector<ParamDef> params;
};

/// @brief 命令注册表 — 设备注册命令，Protocol 统一调度
///         加新命令只需注册 + 实现，不需要改 Protocol
class CommandRegistry {
public:
    using Handler = std::function<std::string(const std::vector<std::string>&)>;

private:
    struct Entry {
        CommandDef def;
        Handler    handler;
    };
    std::map<std::string, Entry> entries_;
    std::string state_fields_json_ = "{}";
    Logger logger_;

public:
    CommandRegistry() : logger_("Registry") {}

    void SetStateFieldsJson(const std::string& json) { state_fields_json_ = json; }
    const std::string& GetStateFieldsJson() const { return state_fields_json_; }

    /// 注册一条命令
    void Register(const CommandDef& def, Handler handler) {
        entries_[def.name] = {def, handler};
        logger_.Debug("Registered command: ", def.name);
    }

    /// 派发命令 — 根据名称查找并执行
    std::string Dispatch(const std::string& cmd_name, const std::vector<std::string>& args) {
        auto it = entries_.find(cmd_name);
        if (it == entries_.end()) {
            return BuildError("Unknown command: " + cmd_name + ". See protocol.json");
        }
        return it->second.handler(args);
    }

    /// 检查命令是否存在
    bool HasCommand(const std::string& name) const {
        return entries_.find(name) != entries_.end();
    }

    /// 获取所有命令定义
    std::vector<CommandDef> GetAllCommands() const {
        std::vector<CommandDef> result;
        for (const auto& [_, entry] : entries_) {
            result.push_back(entry.def);
        }
        return result;
    }

    /// 生成协议 JSON
    std::string GenerateProtocolJson() const {
        std::ostringstream os;
        os << "{\n";
        os << "  \"version\": \"1.0\",\n";
        os << "  \"devices\": {\n";
        os << "    \"air_conditioner\": {\n";
        os << "      \"description\": \"空调设备\",\n";
        os << "      \"default_id\": \"ac-001\",\n";
        os << "      \"commands\": {\n";

        bool first = true;
        for (const auto& [name, entry] : entries_) {
            if (!first) os << ",\n";
            first = false;
            const auto& def = entry.def;
            os << "        \"" << def.name << "\": {\n";
            os << "          \"description\": \"" << def.description << "\",\n";
            os << "          \"params\": [\n";

            for (size_t i = 0; i < def.params.size(); ++i) {
                const auto& p = def.params[i];
                os << "            {\"name\":\"" << p.name << "\",";
                os << "\"type\":\"" << ParamTypeToString(p.type) << "\",";
                os << "\"description\":\"" << p.description << "\"}";
                if (i < def.params.size() - 1) os << ",";
                os << "\n";
            }

            os << "          ]\n";
            os << "        }";
        }

        os << "\n      }\n";
        os << "    }\n";
        os << "  },\n";
        os << "  \"response_format\": {\n";
        os << "    \"schema\": {\n";
        os << "      \"success\": {\"type\": \"bool\"},\n";
        os << "      \"message\": {\"type\": \"string\"},\n";
        os << "      \"state\": {\"type\": \"object\"}\n";
        os << "    }\n";
        os << "  }\n";
        os << "}\n";
        return os.str();
    }

private:
    static std::string ParamTypeToString(ParamType t) {
        switch (t) {
            case ParamType::INT:    return "int";
            case ParamType::FLOAT:  return "float";
            case ParamType::STRING: return "string";
            case ParamType::BOOL:   return "bool";
            default: return "unknown";
        }
    }

    static std::string BuildError(const std::string& msg) {
        std::ostringstream os;
        os << "{\"success\":false,\"message\":\"" << msg << "\",\"state\":{}}";
        return os.str();
    }
};

#endif // COMMAND_REGISTRY_H
