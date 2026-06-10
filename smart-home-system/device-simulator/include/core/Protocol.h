#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <string>
#include <sstream>
#include <vector>
#include "CommandRegistry.h"
#include "Logger.h"

/// @brief 协议层 — 解析 stdin 行，通过 CommandRegistry 派发，返回 JSON
///         不再硬编码任何命令，全由注册表驱动
class Protocol {
private:
    CommandRegistry& registry_;
    Logger logger_;

public:
    explicit Protocol(CommandRegistry& reg)
        : registry_(reg), logger_("Protocol") {}

    /// @brief 处理一行协议命令，返回 JSON 响应字符串
    std::string Handle(const std::string& line) {
        std::istringstream iss(line);
        std::string cmd;
        iss >> cmd;

        logger_.Info(">> ", line);

        // 提取参数
        std::vector<std::string> args;
        std::string arg;
        while (iss >> arg) {
            args.push_back(arg);
        }

        // 特殊命令：describe — 返回协议定义
        if (cmd == "describe") {
            return registry_.GenerateProtocolJson();
        }

        return registry_.Dispatch(cmd, args);
    }
};

#endif // PROTOCOL_H
