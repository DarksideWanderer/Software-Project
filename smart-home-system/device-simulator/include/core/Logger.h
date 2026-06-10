#ifndef LOGGER_H
#define LOGGER_H

#include <iostream>
#include <sstream>
#include <string>
#include <ctime>

/// @brief 日志级别
enum class LogLevel {
    DEBUG = 0,
    INFO  = 1,
    WARN  = 2,
    ERROR = 3
};

/// @brief 简易日志系统 — 输出到 stderr，自动加时间戳和标签
class Logger {
private:
    std::string tag_;
    LogLevel min_level_;

    static const char* LevelName(LogLevel lv) {
        switch (lv) {
            case LogLevel::DEBUG: return "DEBUG";
            case LogLevel::INFO:  return "INFO";
            case LogLevel::WARN:  return "WARN";
            case LogLevel::ERROR: return "ERROR";
        }
        return "UNKNOWN";
    }

    static std::string Timestamp() {
        std::time_t now = std::time(nullptr);
        char buf[20];
        std::strftime(buf, sizeof(buf), "%H:%M:%S", std::localtime(&now));
        return buf;
    }

public:
    explicit Logger(const std::string& tag, LogLevel min_level = LogLevel::INFO)
        : tag_(tag), min_level_(min_level) {}

    void SetMinLevel(LogLevel lv) { min_level_ = lv; }

    template<typename... Args>
    void Log(LogLevel lv, const Args&... args) {
        if (lv < min_level_) return;

        std::ostringstream os;
        os << "[" << Timestamp() << "]"
           << "[" << LevelName(lv) << "]"
           << "[" << tag_ << "] ";
        ((os << args), ...);
        os << std::endl;

        std::cerr << os.str();
    }

    template<typename... Args>
    void Debug(const Args&... args) { Log(LogLevel::DEBUG, args...); }

    template<typename... Args>
    void Info(const Args&... args)  { Log(LogLevel::INFO,  args...); }

    template<typename... Args>
    void Warn(const Args&... args)  { Log(LogLevel::WARN,  args...); }

    template<typename... Args>
    void Error(const Args&... args) { Log(LogLevel::ERROR, args...); }
};

#endif // LOGGER_H
