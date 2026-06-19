import pyaudio
import wave
import sys
from threading import Event

def record_audio(filename, duration=None, sample_rate=44100, chunk=1024,
                 channels=1, format_pa=pyaudio.paInt16):
    """
    录制音频并保存为 WAV 文件。

    参数:
        filename (str):     保存的 WAV 文件名。
        duration (float):   录音时长（秒），None 表示持续录制直到按下 Ctrl+C。
        sample_rate (int):  采样率，默认 44100 Hz。
        chunk (int):        每次读取的帧数，影响实时性，通常 1024。
        channels (int):     声道数，1 为单声道，2 为立体声。
        format_pa:          样本格式，默认 paInt16（16位整型）。
    """
    p = pyaudio.PyAudio()

    try:
        # 打开音频流
        stream = p.open(format=format_pa,
                        channels=channels,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=chunk)

        print("* 开始录音...")
        if duration:
            print(f"  录音时长: {duration} 秒")
        else:
            print("  按 Ctrl+C 停止录音")

        frames = []
        stop_event = Event()  # 用于无时长模式下的优雅中断

        # 录制循环
        while True:
            # 如果指定了时长，计算剩余帧数并读取，最后一次可能不足 chunk
            if duration:
                total_frames = int(sample_rate * duration)
                remaining = total_frames - len(frames)
                if remaining <= 0:
                    break
                # 计算本次读取帧数，不超过 chunk 和 remaining
                frames_to_read = min(chunk, remaining)
                data = stream.read(frames_to_read, exception_on_overflow=False)
                frames.append(data)
            else:
                # 无时长模式，持续读取直到 Ctrl+C
                try:
                    data = stream.read(chunk, exception_on_overflow=False)
                    frames.append(data)
                except KeyboardInterrupt:
                    print("\n  录音手动停止")
                    break

    except KeyboardInterrupt:
        print("\n* 录音被用户中断")
    except Exception as e:
        print(f"录音出错: {e}", file=sys.stderr)
        return False
    finally:
        # 确保资源释放
        stream.stop_stream()
        stream.close()
        p.terminate()

    # ----- 保存为 WAV -----
    try:
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(format_pa))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        print(f"* 录音完成，文件已保存至: {filename}")
        return True
    except Exception as e:
        print(f"保存文件失败: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    # 示例 1：录制 5 秒音频并保存
    record_audio("output.wav", duration=5.0)

    # 示例 2：持续录制，手动 Ctrl+C 停止并保存
    # record_audio("output_manual.wav", duration=None)