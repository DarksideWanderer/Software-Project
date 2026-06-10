#!/bin/bash
# 智能家居系统环境配置脚本 (跨平台全兼容版: macOS / Linux / Windows MSYS2)

echo "开始配置环境..."

# 1. 检查是否安装了 uv
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到 uv。"
    echo "请根据您的系统安装: "
    echo "  - Mac/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  - Windows MSYS2: pacman -S mingw-w64-x86_64-uv"
    exit 1
fi

# 2. 操作系统探测与差异化补丁设定
OS="$(uname -s)"
IS_WINDOWS=false
UV_EXTRA_ARGS=""

case "$OS" in
    CYGWIN*|MINGW*|MSYS*|MINGW32*)
        IS_WINDOWS=true
        echo "检测到 Windows 衍生终端 ($OS)，启用物理复制与无渲染补丁以防止底层死锁..."
        export UV_LINK_MODE=copy
        export UV_PYTHON_DOWNLOADS=never
        UV_EXTRA_ARGS="--no-progress --color never"
        ;;
    *)
        echo "检测到原生 Unix 系统 ($OS)，使用默认极速模式..."
        ;;
esac

setup_module() {
    local target="$1"
    echo "========================================"
    echo "模块: $target"
    
    if [ -d "$target" ]; then
        cd "$target" || return
        
        # 移除旧环境避免干扰
        rm -rf venv
        
        echo "使用 uv 创建 Python 3.12 虚拟环境..."
        uv venv --python 3.12 venv $UV_EXTRA_ARGS
        
        # 3. 动态定位 Python 解释器 (抹平 Scripts 和 bin 的跨平台差异)
        local PY_EXEC=""
        if [ -f "venv/Scripts/python.exe" ]; then
            PY_EXEC="venv/Scripts/python.exe"
            # 兼容 MSYS2 传统的 source venv/bin/activate 习惯
            if [ "$IS_WINDOWS" = true ] && [ ! -d "venv/bin" ]; then
                echo "应用 MSYS2 兼容补丁: 增加 bin 软链接"
                cd venv && ln -s Scripts bin && cd ..
            fi
        elif [ -f "venv/bin/python" ]; then
            PY_EXEC="venv/bin/python"
        elif [ -f "venv/bin/python.exe" ]; then
            PY_EXEC="venv/bin/python.exe"
        fi
        
        if [ -z "$PY_EXEC" ]; then
            echo "错误: 虚拟环境创建失败，找不到 Python 解释器。"
            cd - > /dev/null
            return
        fi

        if [ -f "requirements.txt" ]; then
            echo "使用 uv 安装依赖..."
            # 放弃不可靠的 VIRTUAL_ENV 环境变量
            # 直接使用 --python [绝对或相对路径] 强制定向，消除跨平台路径解析歧义！
            uv pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --python "$PY_EXEC" $UV_EXTRA_ARGS
        fi
        
        cd - > /dev/null
    fi
}

setup_module "smart-home-system/backend-core"
setup_module "smart-home-system/ai-service"

echo "========================================"
echo "所有环境配置结束。"
