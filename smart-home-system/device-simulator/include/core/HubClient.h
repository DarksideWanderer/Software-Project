#ifndef HUB_CLIENT_H
#define HUB_CLIENT_H

#include <string>
#include <sstream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include "CommandRegistry.h"
#include "Logger.h"

/// @brief TCP 客户端 — 连接后端 Hub，自动注册 + 响应命令
class HubClient {
    CommandRegistry& registry_;
    Logger logger_;
    int sock_ = -1;
    std::string dev_type_;
    std::string dev_id_;

public:
    HubClient(CommandRegistry& reg, std::string device_type, std::string device_id)
        : registry_(reg), logger_("HubClient"),
          dev_type_(std::move(device_type)), dev_id_(std::move(device_id)) {}

    ~HubClient() { if (sock_ >= 0) close(sock_); }

    bool Run(const std::string& host = "127.0.0.1", int port = 9760) {
        sock_ = socket(AF_INET, SOCK_STREAM, 0);
        if (sock_ < 0) { logger_.Error("socket() failed"); return false; }

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port   = htons(port);
        inet_pton(AF_INET, host.c_str(), &addr.sin_addr);

        if (connect(sock_, (sockaddr*)&addr, sizeof(addr)) < 0) {
            logger_.Error("connect to ", host, ":", port, " failed");
            return false;
        }

        if (!SendLine(BuildRegistrationJson())) return false;
        logger_.Info("Registered ", dev_type_, ":", dev_id_, ". Waiting...");

        std::string line;
        while (RecvLine(line)) {
            if (line.empty()) continue;
            SendLine(HandleCommand(line));
        }
        logger_.Info("Disconnected.");
        return true;
    }

private:
    bool SendLine(const std::string& line) {
        auto data = line + "\n";
        return send(sock_, data.c_str(), data.size(), 0) > 0;
    }
    bool RecvLine(std::string& out) {
        out.clear(); char ch;
        while (recv(sock_, &ch, 1, 0) > 0) {
            if (ch == '\n') return true;
            out += ch;
        }
        return false;
    }

    std::string BuildRegistrationJson() const {
        std::ostringstream os;
        os << "{\"type\":\"register\",\"device\":{"
           << "\"id\":\""   << Esc(dev_id_)   << "\","
           << "\"type\":\"" << Esc(dev_type_) << "\","
           << "\"commands\":[";

        auto cmds = registry_.GetAllCommands();
        for (size_t i = 0; i < cmds.size(); ++i) {
            if (i > 0) os << ",";
            os << "{\"name\":\""     << Esc(cmds[i].name) << "\","
               << "\"description\":\"" << Esc(cmds[i].description) << "\","
               << "\"params\":[";
            for (size_t j = 0; j < cmds[i].params.size(); ++j) {
                if (j > 0) os << ",";
                os << "{\"name\":\"" << Esc(cmds[i].params[j].name)
                   << "\",\"type\":\"" << ParamStr(cmds[i].params[j].type) << "\"}";
            }
            os << "]}";
        }
        os << "],\"state_fields\":" << registry_.GetStateFieldsJson() << "}}";
        return os.str();
    }

    std::string HandleCommand(const std::string& json) {
        auto val = [&](const char* key) -> std::string {
            size_t p = json.find(std::string("\"") + key + "\"");
            if (p == std::string::npos) return "";
            p = json.find('"', p + strlen(key) + 2);
            if (p == std::string::npos) return "";
            size_t end = json.find('"', p + 1);
            return end == std::string::npos ? "" : json.substr(p + 1, end - p - 1);
        };

        std::string cmd = val("command");
        if (cmd.empty()) return R"({"success":false,"message":"missing command"})";

        std::vector<std::string> args;
        for (const auto& c : registry_.GetAllCommands()) {
            if (c.name == cmd) {
                for (const auto& p : c.params)
                    args.push_back(val(p.name.c_str()));
                break;
            }
        }
        logger_.Info(">> ", cmd);
        return registry_.Dispatch(cmd, args);
    }

    static const char* ParamStr(ParamType t) {
        switch (t) {
            case ParamType::INT: return "int"; case ParamType::FLOAT: return "float";
            case ParamType::STRING: return "string"; case ParamType::BOOL: return "bool";
        }
        return "string";
    }
    static std::string Esc(const std::string& s) {
        std::string o; for (char c : s)
            switch(c) { case '"': o+="\\\""; break; case '\\': o+="\\\\"; break; default: o+=c; }
        return o;
    }
};

#endif // HUB_CLIENT_H
